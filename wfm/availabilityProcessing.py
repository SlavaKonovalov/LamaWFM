import pandas
import sys
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

sys.path.append('..')
from LamaWFM.settings import TIME_ZONE


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
        employee_availability = employee_availability.filter(begin_date_time__gte=begin_date,
                                                             begin_date_time__lt=end_date)
        # удаляем незаблокированную доступность
        employee_availability.filter(availability_type=0).delete()
        # получаем список заблокированной доступности
        employee_availability = employee_availability.filter(availability_type=1)
        df_blocked_availability = pandas.DataFrame(
            employee_availability.values_list('employee_id', 'begin_date_time'),
            columns=['employee_id', 'begin_date_time'])
        df_blocked_availability.begin_date_time = df_blocked_availability.begin_date_time.dt.tz_convert(TIME_ZONE)
        df_blocked_availability['date'] = df_blocked_availability.begin_date_time.dt.date
        # собираем назначенные сотрудникам шаблоны
        templates = Employee_Availability_Templates.objects.filter(
            Q(end_date__gt=begin_date) | Q(end_date__isnull=True)).order_by('begin_date')
        if employee_id:
            templates = templates.filter(employee_id=employee_id)
        else:
            templates = templates.select_related('employee').filter(employee__subdivision_id=subdivision_id)

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
                df_blocked_availability_step = df_blocked_availability[
                    (df_blocked_availability.date == date_step.date())
                    & (df_blocked_availability.employee_id == template.employee_id)]
                # проверяем заблокированную доступность
                if not df_blocked_availability_step.empty:
                    date_step += datetime.timedelta(days=1)
                    continue
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
        datetime_start = Global.get_current_midnight(begin_date)
        datetime_end = Global.get_current_midnight(end_date)
        date_step = datetime_start
        availabilities_for_update = []
        availabilities_for_create = []
        employee_list = [employee.id]
        shift_planning = ShiftPlanning()
        shift_planning.delete_all_shifts(subdivision.id, datetime_start, datetime_end, employee_list)

        demand_processing = DemandProcessing()
        demand_processing.recalculate_covering(subdivision.id, datetime_start.date())

        while date_step < datetime_end:
            date_step_start = date_step + datetime.timedelta(days=1) - datetime.timedelta(hours=1)

            employee_availability = Employee_Availability.objects.filter(employee_id=employee.id,
                                                                         subdivision_id=subdivision.id,
                                                                         begin_date_time__lt=date_step_start,
                                                                         end_date_time__gte=date_step)
            if employee_availability:
                for row in employee_availability.iterator():
                    if row.availability_type == 1 and row.personnel_document:
                        return JsonResponse({'message': 'availability with document already exists'},
                                            status=status.HTTP_400_BAD_REQUEST)
                    if row.availability_type == 0:
                        row.begin_date_time = date_step
                        row.end_date_time = date_step_start
                        row.availability_type = 1
                        row.type = 1
                        availabilities_for_update.append(row)
            else:
                row = Employee_Availability(employee=employee, subdivision=subdivision, type=1, availability_type=1,
                                            begin_date_time=date_step,
                                            end_date_time=date_step_start)
                availabilities_for_create.append(row)
            date_step += datetime.timedelta(days=1)
        Employee_Availability.objects.bulk_create(availabilities_for_create)
        Employee_Availability.objects.bulk_update(availabilities_for_update, ['availability_type', 'type',
                                                                              'begin_date_time', 'end_date_time'])
        return JsonResponse({'message': 'success'}, status=status.HTTP_200_OK)

    @staticmethod
    def load_availability_from_doc_ins():
        personal_documents = Personal_Documents.objects.filter(operation_type='INS')
        availabilities_for_create = []
        documents = []
        for personal_document in personal_documents.iterator():
            try:
                employee = Employee.objects.get(ref_id_1C=personal_document.ref_id_1C)
            except employee.DoesNotExist:
                continue
            try:
                subdivision = Subdivision.objects.get(pk=employee.subdivision_id)
            except subdivision.DoesNotExist:
                continue

            date_start = Global.get_combine_datetime(personal_document.date_from, datetime.time.min)
            date_end = Global.get_combine_datetime(personal_document.date_to, datetime.time.min) + datetime.timedelta(
                days=1)
            date_step = date_start

            employee_list = [employee.id]
            # Удаляем все смены по сотруднику за этот период
            ShiftPlanning.delete_all_shifts(subdivision.id, date_start, date_end, employee_list)
            # Пересчитываем покрытие
            DemandProcessing.recalculate_covering(subdivision.id, date_start.date())
            # Удаляем доступность сотрудника
            Employee_Availability.objects.filter(employee_id=employee.id,
                                                 subdivision_id=subdivision.id,
                                                 begin_date_time__gte=date_start,
                                                 begin_date_time__lt=date_end).delete()
            while date_step < date_end:
                date_step_end = date_step + datetime.timedelta(days=1) - datetime.timedelta(hours=1)
                line = Employee_Availability(employee=employee, subdivision=subdivision, type=0,
                                             availability_type=1, personnel_document=personal_document,
                                             begin_date_time=date_step,
                                             end_date_time=date_step_end)
                availabilities_for_create.append(line)

                date_step += datetime.timedelta(days=1)

            doc_line = personal_document
            doc_line.operation_type = 'FIN'
            documents.append(doc_line)
        # Создание заблокированной доступности
        Employee_Availability.objects.bulk_create(availabilities_for_create)
        # Обновляем статусы обработанных документов
        Personal_Documents.objects.bulk_update(documents, ['operation_type'])

    @staticmethod
    def load_availability_from_doc_upd():
        personal_documents = Personal_Documents.objects.filter(operation_type='UPD')
        documents = []
        for personal_document in personal_documents.iterator():
            try:
                employee = Employee.objects.get(ref_id_1C=personal_document.ref_id_1C)
            except employee.DoesNotExist:
                continue
            try:
                subdivision = Subdivision.objects.get(pk=employee.subdivision_id)
            except subdivision.DoesNotExist:
                continue

            # Удаляем доступность сотрудника
            Employee_Availability.objects.filter(employee_id=employee.id,
                                                 subdivision_id=subdivision.id,
                                                 personnel_document_id=personal_document.id).delete()

            doc_line = personal_document
            # Меняем статус на повторную вставку
            doc_line.operation_type = 'INS'
            documents.append(doc_line)
        # Обновляем статусы обработанных документов
        Personal_Documents.objects.bulk_update(documents, ['operation_type'])

    @staticmethod
    def load_availability_from_doc_del():
        Personal_Documents.objects.filter(operation_type='DEL').delete()
        return

    @staticmethod
    @transaction.atomic
    def load_availability_from_documents():
        # Порядок выполнения: DEL, UPD, INS
        AvailabilityProcessing.load_availability_from_doc_del()
        AvailabilityProcessing.load_availability_from_doc_upd()
        AvailabilityProcessing.load_availability_from_doc_ins()
