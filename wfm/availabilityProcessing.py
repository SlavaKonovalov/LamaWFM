from django.db import transaction
from django.db.models import Q, Max
from django.http import JsonResponse
from rest_framework import status

from .additionalFunctions import Global
from .demandProcessing import DemandProcessing
from .models import Employee_Availability_Templates, Employee_Availability, Availability_Template_Data, Subdivision, \
    Employee, Personal_Documents
import datetime as datetime

from .shiftPlanning import ShiftPlanning


class AvailabilityProcessing:

    @staticmethod
    @transaction.atomic
    def assign_availability_template(serializer):
        employee = serializer.validated_data.get('employee')
        begin_date = serializer.validated_data.get('begin_date')

        employee_templates = Employee_Availability_Templates.objects.all()
        # удаляем шаблоны сотрудника, которые начинаются позже begin_date
        employee_templates_for_delete = employee_templates.filter(employee_id=employee.id, begin_date__gte=begin_date)
        employee_templates_for_delete.delete()
        # Корректировка даты окончания действующих шаблонов
        employee_templates_for_change = employee_templates.filter(
            Q(end_date__gte=begin_date) | Q(end_date__isnull=True),
            employee_id=employee.id)
        for step in employee_templates_for_change.iterator():
            step.end_date = begin_date
            step.save(update_fields=['end_date'])
        # сохраняем новый шаблон
        serializer.save()

        return JsonResponse(serializer.data)

    @staticmethod
    @transaction.atomic
    def recalculate_availability(subdivision_id, begin_date, end_date, employee_id=None):
        # удаляем доступность с date_begin до end_date
        employee_availability = Employee_Availability.objects.all()
        if employee_id:
            employee_availability = employee_availability.filter(employee_id=employee_id, subdivision_id=subdivision_id)
        else:
            employee_availability = employee_availability.filter(subdivision_id=subdivision_id)
        employee_availability.filter(begin_date_time__gte=begin_date, begin_date_time__lt=end_date).delete()
        # собираем назначенные сотрудникам шаблоны
        templates = Employee_Availability_Templates.objects.filter(
            Q(end_date__gt=begin_date) | Q(end_date__isnull=True)).order_by('begin_date')
        if employee_id:
            templates = templates.filter(employee_id=employee_id)

        objects = []

        for template in templates.iterator():
            # определяем границы периода для расчета доступности по конкретному шаблону
            template_begin_date = Global.add_timezone(template.begin_date)
            min_border = max(template_begin_date, begin_date)
            max_border = end_date
            if template.end_date is not None:
                max_border = min(end_date, Global.add_timezone(template.end_date))
            # находим расписание шаблона
            template_data = Availability_Template_Data.objects \
                .filter(template_id=template.template_id) \
                .order_by('week_num', 'week_day', 'begin_time', 'end_time')
            # Вычисляем кол-во недель в шаблоне
            week_count = template_data.aggregate(Max('week_num')).get('week_num__max') + 1
            # Формируем DataFrame на основании полученного расписания
            df_availability = template_data.to_dataframe(['week_num', 'week_day', 'begin_time', 'end_time'])

            date_step = min_border
            while date_step < max_border:
                week_delta = Global.get_week_delta(template_begin_date, date_step)
                df_day_of_week = date_step.weekday()
                df_week_num = (week_delta + template.week_num_appointed) % week_count

                res = df_availability[
                    (df_availability.week_num == df_week_num) & (df_availability.week_day == df_day_of_week)][
                    ['begin_time', 'end_time']]
                for row in res.itertuples():
                    line = Employee_Availability(
                        employee_id=template.employee_id,
                        subdivision_id=subdivision_id,
                        begin_date_time=Global.get_combine_datetime(date_step.date(), row.begin_time),
                        end_date_time=Global.get_combine_datetime(date_step.date(), row.end_time)
                    )
                    objects.append(line)

                date_step += datetime.timedelta(days=1)

        Employee_Availability.objects.bulk_create(objects)
        return JsonResponse({'message': 'request processed'}, status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    @transaction.atomic
    def create_not_availability_handle(subdivision, begin_date, end_date, employee):
        datetime_start = Global.add_timezone(begin_date)
        datetime_start += datetime.timedelta(hours=11)
        datetime_end = Global.add_timezone(end_date)
        datetime_end += datetime.timedelta(hours=11)
        date_step = datetime_start
        availabilities_for_update = []
        availabilities_for_create = []
        employee_list = [employee.id]
        shift_planning = ShiftPlanning()
        shift_planning.delete_all_shifts(subdivision.id, datetime_start, datetime_end, employee_list)

        demand_processing = DemandProcessing()
        demand_processing.recalculate_covering(subdivision.id, datetime_start.date())

        while date_step < datetime_end:
            employee_availability = Employee_Availability.objects.filter(employee_id=employee.id,
                                                                         subdivision_id=subdivision.id,
                                                                         begin_date_time__lt=date_step,
                                                                         end_date_time__gte=date_step)
            if employee_availability:
                for row in employee_availability.iterator():
                    if row.availability_type == 1 and row.personnel_document:
                        return JsonResponse({'message': 'availability with document already exists'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    if row.availability_type == 0:
                        row.begin_date_time = datetime.datetime.combine(date_step, datetime.time.min)
                        row.end_date_time = datetime.datetime.combine(date_step, datetime.time.max)
                        row.availability_type = 1
                        row.type = 1
                        availabilities_for_update.append(row)
            else:
                row = Employee_Availability(employee=employee, subdivision=subdivision, type=1, availability_type=1,
                                            begin_date_time=datetime.datetime.combine(date_step, datetime.time.min),
                                            end_date_time=datetime.datetime.combine(date_step, datetime.time.max))
                availabilities_for_create.append(row)
            date_step += datetime.timedelta(days=1)
        Employee_Availability.objects.bulk_create(availabilities_for_create)
        Employee_Availability.objects.bulk_update(availabilities_for_update, ['availability_type', 'type',
                                                                              'begin_date_time', 'end_date_time'])
        return JsonResponse({'message': 'success'}, status=status.HTTP_200_OK)

    @staticmethod
    @transaction.atomic
    def load_not_availability():
        personal_documents = Personal_Documents.objects.filter(operation_type='INS')
        availabilities_for_update = []
        availabilities_for_create = []
        documents = []
        for personal_document in personal_documents.iterator():
            employee = Employee.objects.get(personnel_number=personal_document.personnel_number)
            if not employee:
                continue
            subdivision = Subdivision.objects.get(id=employee.subdivision_id)
            if not subdivision:
                continue

            date_start = Global.get_current_midnight(personal_document.date_from)
            date_start += datetime.timedelta(hours=11)
            date_end = Global.get_current_midnight(personal_document.date_to)
            date_end += datetime.timedelta(hours=11)
            date_step = date_start

            employee_list = [employee.id]
            shift_planning = ShiftPlanning()
            shift_planning.delete_all_shifts(subdivision.id, date_start, date_end, employee_list)

            demand_processing = DemandProcessing()
            demand_processing.recalculate_covering(subdivision.id, date_start.date())

            while date_step < date_end:
                employee_availability = Employee_Availability.objects.filter(employee_id=employee.id,
                                                                             subdivision_id=subdivision.id,
                                                                             begin_date_time__lt=date_step,
                                                                             end_date_time__gte=date_step)
                if employee_availability:
                    for row in employee_availability.iterator():
                        line = row
                        line.availability_type = 1
                        line.personnel_document = personal_document
                        line.type = 0
                        line.begin_date_time = datetime.datetime.combine(date_step, datetime.time.min)
                        line.begin_date_time = Global.add_timezone(line.begin_date_time)
                        line.end_date_time = datetime.datetime.combine(date_step, datetime.time.max)
                        line.end_date_time = Global.add_timezone(line.end_date_time)
                        availabilities_for_update.append(line)
                else:
                    line = Employee_Availability(employee=employee, subdivision=subdivision, type=0,
                                                 availability_type=1, personnel_document=personal_document,
                                                 begin_date_time=datetime.datetime.combine(date_step,
                                                                                           datetime.time.min),
                                                 end_date_time=datetime.datetime.combine(date_step, datetime.time.max))
                    availabilities_for_create.append(line)

                date_step += datetime.timedelta(days=1)

            doc_line = personal_document
            doc_line.operation_type = 'FIN'
            documents.append(doc_line)
        Employee_Availability.objects.bulk_create(availabilities_for_create)
        Employee_Availability.objects.bulk_update(availabilities_for_update, ['availability_type', 'personnel_document',
                                                                              'begin_date_time', 'end_date_time', 'type'])
        Personal_Documents.objects.bulk_update(documents, ['operation_type'])

