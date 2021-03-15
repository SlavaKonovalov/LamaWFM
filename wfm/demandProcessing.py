import pandas
from django.db import transaction, connection
from django.db.models import Sum, OuterRef, F, Exists
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from rest_framework import status

from .additionalFunctions import Global
from .models import Demand_Detail_Main, Demand_Detail_Task, Global_Parameters, \
    Appointed_Production_Task, Predicted_Production_Task, Production_Task, Tasks_In_Duty
import datetime as datetime
import sys

sys.path.append('..')
from LamaWFM.settings import TIME_ZONE


class DemandProcessing:

    @staticmethod
    def create_demand_main_chain(subdivision_id, date_step, duration):
        apt_step = Appointed_Production_Task.objects \
            .filter(scheduled_task__subdivision_id=subdivision_id, date=date_step)
        apt_step_earliest = Global.add_timezone(
            apt_step.earliest('scheduled_task__begin_time__time').scheduled_task.begin_time)
        apt_step_earliest = apt_step_earliest.replace(year=date_step.year,
                                                      month=date_step.month,
                                                      day=date_step.day,
                                                      )
        apt_step_latest = Global.add_timezone(apt_step.latest('scheduled_task__end_time__time').scheduled_task.end_time)
        apt_step_latest = apt_step_latest.replace(year=date_step.year,
                                                  month=date_step.month,
                                                  day=date_step.day,
                                                  )
        date_step = apt_step_earliest
        while date_step < apt_step_latest:
            demand_detail_main, created_main = Demand_Detail_Main.objects.get_or_create(
                subdivision_id=subdivision_id,
                date_time_value=date_step,
                defaults={'rounded_value': 0}
            )
            date_step += duration

    @staticmethod
    # Копирование статистических данных
    def copy_statistical_data(subdivision_id, date_begin):
        predicted_tasks = Predicted_Production_Task.objects.select_related('predictable_task') \
            .filter(begin_date_time__gte=date_begin) \
            .filter(predictable_task__subdivision_id=subdivision_id) \
            .annotate(task_id=F('predictable_task__task')) \
            .values('begin_date_time', 'task_id') \
            .annotate(demand_sum=Coalesce(Sum("work_scope_time"), 0))

        for predicted_task in predicted_tasks.iterator():
            demand_detail_main, create_main = Demand_Detail_Main.objects.get_or_create(
                subdivision_id=subdivision_id,
                date_time_value=Global.add_timezone(predicted_task.get('begin_date_time')),
                rounded_value=0
            )
            Demand_Detail_Task.objects.create(
                demand_detail_main_id=demand_detail_main.id,
                task_id=predicted_task.get('task_id'),
                demand_value=Global.toFixed(predicted_task.get('demand_sum') / 15, 2)
            )

    @staticmethod
    def calculate_rounded_value(date_begin, tz):
        cursor = connection.cursor()
        query = """
                UPDATE wfm_demand_detail_main
                SET rounded_value =
                (
                SELECT COALESCE(ROUND(AVG(ddt.demand_value)), 0) AS demand_sum
                FROM wfm_demand_detail_main ddm
                LEFT OUTER JOIN wfm_demand_detail_task ddt
                ON (ddm.id = ddt.demand_detail_main_id)
                WHERE (
                    DATE_TRUNC('day', ddm.date_time_value AT TIME ZONE '%s') = DATE_TRUNC('day', wfm_demand_detail_main.date_time_value AT TIME ZONE '%s')
                    AND EXTRACT('hour' FROM ddm.date_time_value AT TIME ZONE '%s') = EXTRACT('hour' FROM wfm_demand_detail_main.date_time_value AT TIME ZONE '%s')
                    )
                GROUP BY DATE_TRUNC('day', ddm.date_time_value AT TIME ZONE 'Asia/Tomsk'),
                         EXTRACT('hour' FROM ddm.date_time_value AT TIME ZONE 'Asia/Tomsk')
                LIMIT 1
                )
                WHERE wfm_demand_detail_main.date_time_value >= '%s'
                """ % (tz, tz, tz, tz, date_begin)
        cursor.execute(query)

    @staticmethod
    # Расчет потребности для задач со равномерным распределением
    def calculate_demand_hard(appointed_task, begin_date_time, end_date_time, work_scope_step, duration):
        date_time_counter = begin_date_time

        while date_time_counter < end_date_time:
            demand_detail_main, created_main = Demand_Detail_Main.objects.get_or_create(
                subdivision_id=appointed_task.scheduled_task.subdivision_id,
                date_time_value=date_time_counter,
                defaults={'rounded_value': 0}
            )
            if demand_detail_main is not None:
                demand_detail_task, created_task = Demand_Detail_Task.objects.update_or_create(
                    demand_detail_main_id=demand_detail_main.id,
                    task_id=appointed_task.scheduled_task.task_id,
                    defaults={'demand_value': work_scope_step}
                )
            date_time_counter += duration

    @staticmethod
    # Расчет потребности для задач со свободным распределением
    def calculate_demand_soft(appointed_task, begin_date_time, end_date_time, work_scope_step, work_scope_all):
        demand_detail_main_sum = Demand_Detail_Main.objects \
            .filter(date_time_value__gte=begin_date_time,
                    date_time_value__lt=end_date_time,
                    subdivision_id=appointed_task.scheduled_task.subdivision_id) \
            .annotate(demand_sum=Coalesce(Sum("demand_detail_task_set__demand_value"), 0)) \
            .order_by('date_time_value')

        df_demand = demand_detail_main_sum.to_dataframe(['demand_sum'], index='id')
        df_demand['demand_sum'] = pandas.to_numeric(df_demand['demand_sum'])

        while work_scope_all > 0:
            work_scope_step = min(work_scope_all, work_scope_step)

            if df_demand.empty:
                demand_detail_main = Demand_Detail_Main.objects.create(
                    subdivision_id=appointed_task.scheduled_task.subdivision_id,
                    date_time_value=begin_date_time,
                    rounded_value=0
                )
                Demand_Detail_Task.objects.create(
                    demand_detail_main_id=demand_detail_main.id,
                    task_id=appointed_task.scheduled_task.task_id,
                    demand_value=work_scope_step
                )

                df_demand_row = pandas.Series(data={'demand_sum': work_scope_step},
                                              name=demand_detail_main.id)
                df_demand = df_demand.append(df_demand_row, ignore_index=False)
            else:
                df_demand_min_idx = df_demand['demand_sum'].idxmin()
                df_demand_min_value = df_demand.loc[df_demand_min_idx, 'demand_sum']

                demand_detail_task, created_task = Demand_Detail_Task.objects.get_or_create(
                    demand_detail_main_id=df_demand_min_idx,
                    task_id=appointed_task.scheduled_task.task_id,
                    defaults={'demand_value': work_scope_step}
                )

                if not created_task:
                    demand_detail_task.demand_value = float(demand_detail_task.demand_value) + work_scope_step
                    demand_detail_task.save(update_fields=['demand_value'])

                # Скорректируем строку DataFrame с выбранным индексом на величину work_scope_step
                df_demand.at[df_demand_min_idx, 'demand_sum'] = df_demand_min_value + work_scope_step

            work_scope_all = Global.toFixed(work_scope_all - work_scope_step, 2)

    @staticmethod
    # Расчет потребности для задач с непрерывным распределением
    def calculate_demand_continuous(appointed_task, begin_date_time, end_date_time, work_scope_step, work_scope_all):
        df_demand_res = pandas.DataFrame()

        demand_detail_main_sum = Demand_Detail_Main.objects \
            .filter(date_time_value__gte=begin_date_time,
                    date_time_value__lt=end_date_time,
                    subdivision_id=appointed_task.scheduled_task.subdivision_id) \
            .annotate(demand_sum=Coalesce(Sum("demand_detail_task_set__demand_value"), 0)) \
            .order_by('date_time_value')

        df_demand = demand_detail_main_sum.to_dataframe(['demand_sum'], index='id')
        df_demand['demand_sum'] = pandas.to_numeric(df_demand['demand_sum'])
        df_demand_last_pos = len(df_demand) - 1

        if not df_demand.empty:
            df_demand_min_idx = df_demand['demand_sum'].idxmin()
            df_demand_min_value = df_demand.loc[df_demand_min_idx, 'demand_sum']
            df_demand_min_pos = df_demand.index.get_loc(df_demand_min_idx)
            if df_demand_min_pos == 0:
                df_demand_res = df_demand.iloc[0:2]
            else:
                df_demand_res = df_demand.iloc[(df_demand_min_pos - 1):(df_demand_min_pos + 2)]
            df_demand_res.at[df_demand_min_idx, 'demand_sum'] = df_demand_min_value + work_scope_step
            demand_detail_task, created_task = Demand_Detail_Task.objects.get_or_create(
                demand_detail_main_id=df_demand_min_idx,
                task_id=appointed_task.scheduled_task.task_id,
                defaults={'demand_value': work_scope_step}
            )

            if not created_task:
                demand_detail_task.demand_value = float(demand_detail_task.demand_value) + work_scope_step
                demand_detail_task.save(update_fields=['demand_value'])

            work_scope_all = Global.toFixed(work_scope_all - work_scope_step, 2)

        if not df_demand_res.empty:
            while work_scope_all > 0:
                work_scope_step = min(work_scope_all, work_scope_step)
                df_demand_res_last_pos = len(df_demand_res) - 1
                df_demand_res_min_idx = df_demand_res['demand_sum'].idxmin()
                df_demand_res_min_value = df_demand_res.loc[df_demand_res_min_idx, 'demand_sum']
                df_demand_res_min_pos = df_demand_res.index.get_loc(df_demand_res_min_idx)

                df_demand_res.at[df_demand_res_min_idx, 'demand_sum'] = df_demand_res_min_value + work_scope_step
                work_scope_all = Global.toFixed(work_scope_all - work_scope_step, 2)

                if df_demand_res_last_pos != df_demand_last_pos and df_demand_res_min_pos in [0, df_demand_res_last_pos] and work_scope_all > 0:
                    if df_demand_res_min_pos == 0 or df_demand_res_min_pos == df_demand_res_last_pos:
                        df_demand_min_pos = df_demand.index.get_loc(df_demand_res_min_idx)
                        if df_demand_res_min_pos == 0:
                            if df_demand_min_pos != 0:
                                df_for_concat = df_demand.iloc[[df_demand_min_pos-1]]
                                df_demand_res = pandas.concat([df_for_concat, df_demand_res])
                        else:
                            if df_demand_min_pos != df_demand_last_pos:
                                df_for_concat = df_demand.iloc[[df_demand_min_pos + 1]]
                                df_demand_res = pandas.concat([df_demand_res, df_for_concat])

                demand_detail_task, created_task = Demand_Detail_Task.objects.get_or_create(
                    demand_detail_main_id=df_demand_res_min_idx,
                    task_id=appointed_task.scheduled_task.task_id,
                    defaults={'demand_value': work_scope_step}
                )

                if not created_task:
                    demand_detail_task.demand_value = float(demand_detail_task.demand_value) + work_scope_step
                    demand_detail_task.save(update_fields=['demand_value'])

    @staticmethod
    @transaction.atomic
    # Пересчёт потребности
    def recalculate_demand(subdivision_id):
        date_step = Global.get_current_midnight(datetime.datetime.now())
        date_begin = date_step + datetime.timedelta(days=1)

        # Удаление записей по подразделению с завтрашнего числа
        Demand_Detail_Main.objects.filter(subdivision_id=subdivision_id) \
            .filter(date_time_value__gte=date_begin).delete()

        # Закачиваем статистику
        DemandProcessing.copy_statistical_data(subdivision_id, date_begin)
        appointed_tasks = Appointed_Production_Task.objects.select_related('scheduled_task__task') \
            .filter(scheduled_task__subdivision_id=subdivision_id) \
            .filter(date__gte=date_begin) \
            .order_by('scheduled_task__task__demand_allocation_method', 'date', 'scheduled_task__begin_time__time')

        interval_length = Global_Parameters.objects.all().first().demand_detail_interval_length
        duration = datetime.timedelta(minutes=interval_length)

        for appointed_task in appointed_tasks.iterator():

            appointed_date_time = Global.add_timezone(appointed_task.date)

            if date_step != appointed_date_time:
                date_step = appointed_date_time
                # Создаём цепочку заголовков для потребности на день
                DemandProcessing.create_demand_main_chain(subdivision_id, date_step, duration)

            # Подготовительные процедуры
            begin_date_time = Global.add_timezone(appointed_task.scheduled_task.begin_time)
            begin_date_time = begin_date_time.replace(year=appointed_date_time.year,
                                                      month=appointed_date_time.month,
                                                      day=appointed_date_time.day,
                                                      )
            end_date_time = Global.add_timezone(appointed_task.scheduled_task.end_time)
            end_date_time = end_date_time.replace(year=appointed_date_time.year,
                                                  month=appointed_date_time.month,
                                                  day=appointed_date_time.day,
                                                  )
            work_scope_all = Global.toFixed(appointed_task.work_scope_time / 60, 2)
            work_scope_step = Global.toFixed(
                appointed_task.work_scope_time * interval_length / appointed_task.scheduled_task.get_task_duration() / 60,
                2)
            work_scope_step = min(work_scope_all, work_scope_step)

            # равномерное распределение:
            if appointed_task.scheduled_task.task.demand_allocation_method == '0_hard':
                DemandProcessing.calculate_demand_hard(appointed_task, begin_date_time, end_date_time,
                                                       work_scope_step, duration)
            # свободное распределение:
            if appointed_task.scheduled_task.task.demand_allocation_method == '1_soft':
                DemandProcessing.calculate_demand_soft(appointed_task, begin_date_time, end_date_time,
                                                       work_scope_step, work_scope_all)
            # непрерывное распределение:
            if appointed_task.scheduled_task.task.demand_allocation_method == '2_continuous':
                DemandProcessing.calculate_demand_continuous(appointed_task, begin_date_time, end_date_time,
                                                             work_scope_step, work_scope_all)

        # собираем среднее значение потребностей по каждому экземпляру main и округляем, сразу обновляем rounded_value:
        DemandProcessing.calculate_rounded_value(date_begin, TIME_ZONE)
