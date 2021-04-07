import datetime

import pandas
from django.db import transaction, connection
import sys
from django.db.models import Q, Max
from django.http import JsonResponse
from numpy.random import random

from .models import Employee_Availability, Employee, Employee_Shift, Employee_Shift_Detail_Plan, Employee_Planning_Rules

sys.path.append('..')
from LamaWFM.settings import TIME_ZONE


class ShiftPlanning:

    @staticmethod
    @transaction.atomic
    def assign_employee_planning_rules(serializer):
        employee = serializer.validated_data.get('employee')
        date_rules_start = serializer.validated_data.get('date_rules_start')

        employee_planning_rules = Employee_Planning_Rules.objects.all()
        # удаляем правила для сотрудника, которые начинаются позже begin_date
        employee_planning_rules_delete = employee_planning_rules.filter(employee_id=employee.id,
                                                                        date_rules_start__gte=date_rules_start)
        employee_planning_rules_delete.delete()
        # Корректировка даты окончания действующих шаблонов
        employee_planning_rules_for_change = employee_planning_rules.filter(
            Q(date_rules_end__gte=date_rules_start) | Q(date_rules_end__isnull=True),
            employee_id=employee.id)
        for step in employee_planning_rules_for_change.iterator():
            step.date_rules_end = date_rules_start
            step.save(update_fields=['date_rules_end'])
        # сохраняем новый шаблон
        serializer.save()

        return JsonResponse(serializer.data)

    @staticmethod
    def get_demand_dataframe(subdivision_id, begin_date, end_date, tz):
        query = """
                SELECT date, hour, duty_id as duty, task_sum.task_id as task, demand_sum
                FROM
                (
                SELECT task_id,
                AVG(ddt.demand_value) AS demand_sum,
                DATE_TRUNC('day', ddm.date_time_value AT TIME ZONE '%s') as date,
                EXTRACT('hour' FROM ddm.date_time_value AT TIME ZONE '%s') as hour
                FROM wfm_demand_detail_main ddm
                LEFT OUTER JOIN wfm_demand_detail_task ddt
                ON (ddm.id = ddt.demand_detail_main_id)
                WHERE ddm.date_time_value >= '%s'
                AND ddm.date_time_value < '%s'
                AND ddm.subdivision_id = '%s'
                GROUP BY ddt.task_id,
                        DATE_TRUNC('day', ddm.date_time_value AT TIME ZONE '%s'),
                        EXTRACT('hour' FROM ddm.date_time_value AT TIME ZONE '%s')
                ) AS task_sum
                LEFT OUTER JOIN 
                (
                SELECT tid1.task_id, tid1.duty_id FROM wfm_tasks_in_duty AS tid1
                LEFT OUTER JOIN wfm_tasks_in_duty AS tid2
                ON tid1.task_id = tid2.task_id AND tid1.priority > tid2.priority
                WHERE tid2.task_id IS NULL
                ) as tid
                ON task_sum.task_id = tid.task_id
                WHERE duty_id IS NOT NULL
                ORDER BY date, duty_id, hour, task_sum.task_id
                """ % (tz, tz, begin_date, end_date, subdivision_id, tz, tz)
        df = pandas.read_sql_query(query, connection)
        return df

    @staticmethod
    def get_availability_dataframe(subdivision_id, begin_date, end_date, tz, employee_id=None):
        query = """
                SELECT job_duty_id as duty, wfm_employee.id as employee, begin_date_time, end_date_time,
                DATE_TRUNC('day', begin_date_time AT TIME ZONE '%s') as date,
                EXTRACT('hour' FROM begin_date_time AT TIME ZONE '%s') as av_begin_hour,
                EXTRACT('hour' FROM end_date_time AT TIME ZONE '%s') as av_end_hour,
                shift_duration_min,
                shift_duration_max
                FROM wfm_employee
                INNER JOIN wfm_employee_duties
                ON wfm_employee.id = wfm_employee_duties.employee_id
                INNER JOIN wfm_employee_availability
                ON wfm_employee.id = wfm_employee_availability.employee_id
                INNER JOIN wfm_employee_planning_rules
                ON wfm_employee.id = wfm_employee_planning_rules.employee_id
                INNER JOIN wfm_planning_method
                ON wfm_planning_method.id = wfm_employee_planning_rules.planning_method_id
                WHERE wfm_employee.subdivision_id = '%s'
                AND begin_date_time >= '%s'
                AND begin_date_time < '%s'
                AND date_rules_start <= begin_date_time
                AND (date_rules_end > begin_date_time OR date_rules_end IS NULL)
                """ % (tz, tz, tz, subdivision_id, begin_date, end_date)
        if employee_id:
            query += "AND wfm_employee.id = '%s'" % employee_id
        df = pandas.read_sql_query(query, connection)
        return df

    @staticmethod
    @transaction.atomic
    # Планирование смен
    def plan_shifts(subdivision_id, begin_date_time, end_date_time, employee_id=None):
        # TODO Удаление данных

        # Получаем dataframe
        df_demand = ShiftPlanning.get_demand_dataframe(subdivision_id, begin_date_time, end_date_time, TIME_ZONE)
        # считаем сумму, затем округляем
        df_demand['qty'] = df_demand.groupby(['date', 'hour', 'duty'])['demand_sum'].transform('sum').round(0)
        # Убираем дубликаты
        df_demand_unique = df_demand[['date', 'hour', 'duty', 'qty']].drop_duplicates()
        # Задача не может иметь 0 потребность. Ставим 1, где округлилось до 0
        df_demand_unique['qty'] = df_demand_unique['qty'].apply(lambda x: 1 if x == 0 else x)
        # Вычисляем значения "Кол-во часов" и "Последний требуемый час"
        df_demand_unique['count'] = df_demand_unique.groupby(['date', 'duty'])['hour'].transform("count")
        df_demand_unique['last_hour'] = df_demand_unique.groupby(['date', 'duty'])['hour'].transform("max")
        # Сортируем
        df_demand_unique = df_demand_unique.sort_values(by=['date', 'count', 'duty', 'hour'],
                                                        ascending=[True, False, True, True])
        df_demand_unique = df_demand_unique.reset_index()
        df_demand_date = df_demand_unique[['date']].drop_duplicates()

        df_availability = ShiftPlanning.get_availability_dataframe(subdivision_id, begin_date_time, end_date_time,
                                                                   TIME_ZONE,
                                                                   employee_id)
        df_availability.begin_date_time = df_availability.begin_date_time.dt.tz_convert(TIME_ZONE)
        df_availability.end_date_time = df_availability.end_date_time.dt.tz_convert(TIME_ZONE)

        begin_date = begin_date_time.date().replace(day=1)

        shift_detail_plan = Employee_Shift_Detail_Plan.objects.select_related('shift').filter(
            shift__subdivision_id=subdivision_id,
            shift__shift_date__gte=begin_date)
        df_shift_plan = pandas.DataFrame(
            shift_detail_plan.values_list('shift__employee_id', 'shift__subdivision_id', 'shift__shift_date', 'type',
                                          'time_from', 'time_to'),
            columns=['employee', 'subdivision', 'shift_date', 'type', 'time_from', 'time_to'])
        df_shift_plan['hour_from'] = pandas.to_datetime(df_shift_plan['time_from'], format='%H:%M:%S').dt.hour
        df_shift_plan['hour_to'] = pandas.to_datetime(df_shift_plan['time_to'], format='%H:%M:%S').dt.hour
        df_shift_plan['hours'] = df_shift_plan.hour_to - df_shift_plan.hour_from

        df_covering = df_shift_plan[(df_shift_plan.type == 'job')][['employee', 'hours']]
        df_covering['hours_sum'] = df_covering.groupby('employee')['hours'].transform('sum')
        df_covering = df_covering[['employee', 'hours_sum']].drop_duplicates()

        for row_date in df_demand_date.itertuples():
            # берем покрытие за выбранную дату
            df_demand_on_date = df_demand_unique[(df_demand_unique.date == row_date.date)]
            # добавляем признак "Покрывалось". Устанавливается на ФО, если назначалась хоть одна смена
            df_demand_on_date['covered'] = 0
            while True:
                df_demand_on_date = df_demand_on_date[(df_demand_on_date.qty > 0)]
                # Пересчитываем 'count' и 'last_hour'
                df_demand_on_date['count'] = df_demand_on_date.groupby(['date', 'duty'])['hour'].transform("count")
                df_demand_on_date['last_hour'] = df_demand_on_date.groupby(['date', 'duty'])['hour'].transform("max")
                # Сброс индекса
                df_demand_on_date = df_demand_on_date.reset_index()
                # Берем первую запись
                row_demand = list(df_demand_on_date.itertuples())[0]

                # TODO Нужно сначала проверить, есть ли уже сотрудник со сменой, можно ли продлить смену?
                # Если нет, ищем другого сотрудника

                # Ищем доступных сотрудников по определенным условиям
                df_res = df_availability[
                    (df_availability.date == row_demand.date) &
                    (df_availability.av_begin_hour <= row_demand.hour) &  # доступен в этом часу
                    (df_availability.av_end_hour - 1 > row_demand.hour) &  # может покрыть как минимум 2 часа
                    # минимальная длина смены укладывается в доступность:
                    (df_availability.av_end_hour - df_availability.av_begin_hour >= df_availability.shift_duration_min) &
                    (row_demand.duty == df_availability.duty)]
                if df_res.empty:
                    # Никого не нашли - зануляем кол-во
                    df_demand_on_date.at[0, 'qty'] = 0
                else:
                    df_res = pandas.merge(df_res, df_covering, on=['employee'], how='left')
                    df_res.hours_sum = df_res.hours_sum.fillna(0)
                    min_hours_sum = df_res.hours_sum.min()
                    df_res = df_res[(df_res.hours_sum <= min_hours_sum + 2)]  # 2 - это погрешность (в часах)
                    df_res_sample = df_res.sample()
                    res_sample = list(df_res_sample.itertuples())[0]
                    shift_begin = 0
                    shift_end = 0
                    # max_hour_value - либо граница потребности, либо граница доступности
                    max_hour_value = min(row_demand.last_hour + 1, res_sample.av_end_hour)

                    # если требуется покрыть меньше минимальной длины смены
                    if max_hour_value - row_demand.hour <= res_sample.shift_duration_min:
                        # В этом случае всегда длина смены = shift_duration_min
                        # Проверяем, выходит ли начало смены за границу начала доступности:
                        if max_hour_value - res_sample.shift_duration_min < res_sample.av_begin_hour:
                            shift_begin = res_sample.av_begin_hour
                        else:
                            shift_begin = max_hour_value - res_sample.shift_duration_min
                        # Вычисляем конец смены
                        shift_end = shift_begin + res_sample.shift_duration_min
                    else:
                        shift_begin = row_demand.hour
                        if res_sample.shift_duration_max:  # если продолжительность смены не фиксирована
                            if max_hour_value - row_demand.hour <= res_sample.shift_duration_max:  # можем покрыть всё?
                                shift_end = max_hour_value
                            else:
                                shift_end = shift_begin + random.randint(res_sample.shift_duration_min,
                                                                         res_sample.shift_duration_max)
                        else:
                            shift_end = shift_begin + res_sample.shift_duration_min
                    shift_length = shift_end - shift_begin

                    # Минимальная доступность. Вариант отбора -->
                    # res['min_availability'] = df_availability.av_end_hour - df_availability.av_begin_hour
                    # min_availability = res.min_availability.min()
                    # Минимальная доступность. Вариант отбора <--
                    # Максимальное покрытие. Вариант отбора -->
                    # res['max_covering'] = res.av_end_hour - row.hour
                    # max_covering = res.max_covering.max()
                    # Максимальное покрытие. Вариант отбора <--

                    # Добавляем смену и кол-во часов новой смены сотруднику
                    if df_covering.employee.isin([res_sample.employee]).any().any():
                        df_covering.loc[df_covering.employee == res_sample.employee, ['hours_sum']] += shift_length
                    else:
                        df_covering_row = pandas.Series(data={'employee': res_sample.employee,
                                                              'hours_sum': shift_length})
                        df_covering = df_covering.append(df_covering_row, ignore_index=True)

                    employee_shift, created_shift = Employee_Shift.objects.get_or_create(
                        employee_id=res_sample.employee,
                        subdivision_id=subdivision_id,
                        shift_date=begin_date_time.date()
                    )
                    employee_shift_detail_plan, created_shift_plan = Employee_Shift_Detail_Plan.objects.update_or_create(
                        shift_id=employee_shift.id,
                        type='job',
                        defaults={
                            'time_from': datetime.time(int(shift_begin), 0),
                            'time_to': datetime.time(int(shift_end), 0)
                        }
                    )

                    # TODO уменьшить qty на всём интервале!
                    # df_demand_on_date.at[0, 'qty'] = 0
