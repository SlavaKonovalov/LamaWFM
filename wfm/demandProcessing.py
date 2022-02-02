from decimal import Decimal

import pandas
from django.db import transaction, connection
from django.db.models import Sum, OuterRef, F, Exists, Count, Subquery, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from rest_framework import status

from .additionalFunctions import Global
from .models import Demand_Detail_Main, Demand_Detail_Task, Global_Parameters, \
    Appointed_Production_Task, Predicted_Production_Task, Production_Task, Tasks_In_Duty, Demand_Hour_Main, \
    Demand_Hour_Shift
import datetime as datetime
import sys

sys.path.append('..')
from LamaWFM.settings import TIME_ZONE


class DemandProcessing:

    @staticmethod
    def create_demand_main_chain(subdivision_id, chain_date, duration):
        apt_step = Appointed_Production_Task.objects \
            .filter(scheduled_task__subdivision_id=subdivision_id, date=chain_date)

        apt_step_earliest_time = apt_step.earliest('scheduled_task__begin_time').scheduled_task.begin_time
        apt_step_earliest = Global.get_combine_datetime(chain_date, apt_step_earliest_time)

        apt_step_latest_time = apt_step.latest('scheduled_task__end_time').scheduled_task.end_time
        apt_step_latest = Global.get_combine_datetime(chain_date, apt_step_latest_time)

        date_step = apt_step_earliest
        objects = []
        while date_step < apt_step_latest:
            demand_detail_main = Demand_Detail_Main(
                subdivision_id=subdivision_id,
                date_time_value=date_step,
                rounded_value=0
            )
            objects.append(demand_detail_main)
            date_step += duration
        Demand_Detail_Main.objects.bulk_create(objects, ignore_conflicts=True)

    @staticmethod
    # Копирование статистических данных
    def copy_statistical_data(subdivision_id, date_begin):
        predicted_tasks = Predicted_Production_Task.objects.select_related('predictable_task__task') \
            .filter(begin_date_time__gte=date_begin) \
            .filter(predictable_task__subdivision_id=subdivision_id) \
            .annotate(task_id=F('predictable_task__task')) \
            .annotate(source_type=F('predictable_task__task__demand_data_source')) \
            .values('begin_date_time', 'task_id', 'source_type') \
            .annotate(demand_sum=Coalesce(Sum("work_scope_time"), 0))

        objects = []

        for predicted_task in predicted_tasks.iterator():
            source_type = predicted_task.get('source_type')
            if source_type == 'statistical_data':
                # Прямая заливка статистики
                demand_detail_main, create_main = Demand_Detail_Main.objects.get_or_create(
                    subdivision_id=subdivision_id,
                    date_time_value=Global.add_timezone(predicted_task.get('begin_date_time')),
                    defaults={'rounded_value': 0}
                )
                Demand_Detail_Task.objects.create(
                    demand_detail_main_id=demand_detail_main.id,
                    task_id=predicted_task.get('task_id'),
                    demand_value=Global.toFixed(predicted_task.get('demand_sum') / 15, 2)
                )
            if source_type == 'statistical_scheduler':
                appointed_production_task = Appointed_Production_Task.objects.select_related(
                    'scheduled_task__task').filter(scheduled_task__task_id=predicted_task.get('task_id')).filter(
                    date=predicted_task.get('begin_date_time')).first()

                if appointed_production_task:
                    appointed_production_task.work_scope_time = float(predicted_task.get('demand_sum'))
                    objects.append(appointed_production_task)

        if objects:
            Appointed_Production_Task.objects.bulk_update(objects, ['work_scope_time'])

    @staticmethod
    # 1. находим среднее значение потребности по каждой задаче в разрезе часа
    # 2. находим фун-ю обяз-ть с наименьшим приоритетом, связанную с этой задачей
    # 3. находим сумму потребностей внутри ФО, затем округляем. Если получаем 0, то повышаем до 1.
    # 4. находим сумму по всем ФО в разрезе часа.
    def calculate_rounded_value(date_begin, tz, subdivision_id):
        cursor = connection.cursor()
        query = """
                UPDATE wfm_demand_detail_main
                SET rounded_value =
                (
                SELECT SUM(demand_sum)
                FROM
                (
                SELECT
                CASE WHEN COALESCE(SUM(task_sum.demand_sum), 0) = 0 THEN 0
                WHEN COALESCE(ROUND(SUM(task_sum.demand_sum)), 0) = 0 THEN 1
                ELSE COALESCE(ROUND(SUM(task_sum.demand_sum)), 0)
                END AS demand_sum,
                date, hour, duty_id
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
                GROUP BY date, hour, duty_id
                ) as result
                WHERE (
                date = DATE_TRUNC('day', wfm_demand_detail_main.date_time_value AT TIME ZONE '%s')
                AND hour = EXTRACT('hour' FROM wfm_demand_detail_main.date_time_value AT TIME ZONE '%s')
                )
                GROUP BY date, hour
                LIMIT 1
                )
                WHERE wfm_demand_detail_main.date_time_value >= '%s'
                AND wfm_demand_detail_main.subdivision_id = '%s'
                """ % (tz, tz, date_begin, subdivision_id, tz, tz, tz, tz, date_begin, subdivision_id)
        cursor.execute(query)

    @staticmethod
    @transaction.atomic
    def recreate_demand_hour_main(date_begin, tz, subdivision_id):
        demand_hour_shift = Demand_Hour_Shift.objects.select_related('demand_hour_main').filter(
            demand_hour_main__subdivision_id=subdivision_id,
            demand_hour_main__demand_date__gte=date_begin)
        df_demand_hour_shift_prev = pandas.DataFrame(
            demand_hour_shift.values_list('demand_hour_main__subdivision_id', 'demand_hour_main__demand_date',
                                          'demand_hour_main__demand_hour', 'demand_hour_main__duty_id',
                                          'shift_id', 'break_value'),
            columns=['subdivision_id', 'demand_date', 'demand_hour', 'duty_id', 'shift_id', 'break_value'])

        # Удаление записей по подразделению с завтрашнего числа
        Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id) \
            .filter(demand_date__gte=date_begin).delete()
        # Добавление записей в таблицу на основании потребности
        cursor = connection.cursor()
        query = """
                INSERT INTO wfm_demand_hour_main(subdivision_id, demand_date, demand_hour, duty_id, demand_value, covering_value, breaks_value)
                (
                    SELECT
                    '%s' as subdivision_id,
                    date,
                    hour,
                    duty_id,
                    CASE WHEN COALESCE(SUM(task_sum.demand_sum), 0) = 0 THEN 0
                    WHEN COALESCE(ROUND(SUM(task_sum.demand_sum)), 0) = 0 THEN 1
                    ELSE COALESCE(ROUND(SUM(task_sum.demand_sum)), 0)
                    END AS demand_value,
                    0,
                    0
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
                    GROUP BY date, duty_id, hour
                )
                """ % (subdivision_id, tz, tz, date_begin, subdivision_id, tz, tz)
        cursor.execute(query)

        # Восстанавливаем смены (какие сможем)
        demand_hour_main = Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id) \
            .filter(demand_date__gte=date_begin)
        df_demand_hour_main = pandas.DataFrame(
            demand_hour_main.values_list('id', 'subdivision_id', 'demand_date', 'demand_hour', 'duty_id'),
            columns=['id', 'subdivision_id', 'demand_date', 'demand_hour', 'duty_id'])
        df_demand_hour_main = pandas.merge(df_demand_hour_main, df_demand_hour_shift_prev, how='left',
                                           left_on=['subdivision_id', 'demand_date', 'demand_hour', 'duty_id'],
                                           right_on=['subdivision_id', 'demand_date', 'demand_hour', 'duty_id'])
        df_demand_hour_main = df_demand_hour_main[(df_demand_hour_main.shift_id.notna())]
        objects = []
        for row_main in df_demand_hour_main.itertuples():
            line = Demand_Hour_Shift(
                demand_hour_main_id=row_main.id,
                shift_id=row_main.shift_id,
                break_value=row_main.break_value
            )
            objects.append(line)
        if objects:
            # заливаем восстановленные смены
            Demand_Hour_Shift.objects.bulk_create(objects, ignore_conflicts=True)
            # Пересчитываем показатель покрытия
            DemandProcessing.recalculate_covering(subdivision_id, date_begin)
            # Пересчитываем показатель обеденных перерывов
            DemandProcessing.recalculate_breaks_value(subdivision_id, date_begin)

    @staticmethod
    # Расчет потребности для задач со равномерным распределением
    def calculate_demand_hard(appointed_task, begin_date_time, end_date_time, work_scope_step, duration):
        date_time_counter = begin_date_time

        objects = []
        while date_time_counter < end_date_time:
            demand_detail_main, created_main = Demand_Detail_Main.objects.get_or_create(
                subdivision_id=appointed_task.scheduled_task.subdivision_id,
                date_time_value=date_time_counter,
                defaults={'rounded_value': 0}
            )
            if demand_detail_main is not None:
                demand_detail_task = Demand_Detail_Task(
                    demand_detail_main_id=demand_detail_main.id,
                    task_id=appointed_task.scheduled_task.task_id,
                    demand_value=work_scope_step
                )
                objects.append(demand_detail_task)
            date_time_counter += duration
        Demand_Detail_Task.objects.bulk_create(objects, ignore_conflicts=True)

    @staticmethod
    # Расчет потребности для задач со свободным распределением
    def calculate_demand_soft(appointed_task, begin_date_time, end_date_time, work_scope_step, work_scope_all):
        demand_detail_main_sum = Demand_Detail_Main.objects \
            .filter(date_time_value__gte=begin_date_time,
                    date_time_value__lt=end_date_time,
                    subdivision_id=appointed_task.scheduled_task.subdivision_id) \
            .annotate(demand_sum=Coalesce(Sum("demand_detail_task_set__demand_value"), Decimal(0))) \
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
            .annotate(demand_sum=Coalesce(Sum("demand_detail_task_set__demand_value"), Decimal(0))) \
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

                if df_demand_res_last_pos != df_demand_last_pos and df_demand_res_min_pos in [0,
                                                                                              df_demand_res_last_pos] and work_scope_all > 0:
                    if df_demand_res_min_pos == 0 or df_demand_res_min_pos == df_demand_res_last_pos:
                        df_demand_min_pos = df_demand.index.get_loc(df_demand_res_min_idx)
                        if df_demand_res_min_pos == 0:
                            if df_demand_min_pos != 0:
                                df_for_concat = df_demand.iloc[[df_demand_min_pos - 1]]
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
        # проверка связи задач и ФО
        production_task_check = Production_Task.objects.filter(
            ~Exists(Tasks_In_Duty.objects.filter(task_id=OuterRef('pk'))),
        )
        if len(list(production_task_check)) > 0:
            return JsonResponse({'message': 'Не все задачи сопоставлены с обязанностями!'},
                                status=status.HTTP_404_NOT_FOUND)

        date_step = datetime.datetime.now().date()
        date_begin = date_step + datetime.timedelta(days=1)

        # Удаление записей по подразделению с завтрашнего числа
        Demand_Detail_Main.objects.filter(subdivision_id=subdivision_id) \
            .filter(date_time_value__gte=date_begin).delete()

        # Закачиваем статистику
        DemandProcessing.copy_statistical_data(subdivision_id, date_begin)

        appointed_tasks = Appointed_Production_Task.objects.select_related('scheduled_task__task') \
            .filter(scheduled_task__subdivision_id=subdivision_id) \
            .filter(date__gte=date_begin) \
            .filter(~Q(work_scope_time=0)) \
            .order_by('scheduled_task__task__demand_allocation_method', 'date', 'scheduled_task__begin_time')

        interval_length = Global_Parameters.objects.all().first().demand_detail_interval_length
        duration = datetime.timedelta(minutes=interval_length)

        for appointed_task in appointed_tasks.iterator():

            if date_step != appointed_task.date:
                date_step = appointed_task.date
                # Создаём цепочку заголовков для потребности на день
                DemandProcessing.create_demand_main_chain(subdivision_id, date_step, duration)

            # Подготовительные процедуры
            begin_date_time = Global.get_combine_datetime(appointed_task.date, appointed_task.scheduled_task.begin_time)
            end_date_time = Global.get_combine_datetime(appointed_task.date, appointed_task.scheduled_task.end_time)

            work_scope_all = Global.toFixed(appointed_task.work_scope_time / interval_length, 2)
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

        # собираем среднее значение потребностей и обновляем rounded_value:
        DemandProcessing.calculate_rounded_value(date_begin, TIME_ZONE, subdivision_id)
        # пересоздаём Почасовую потребность по ФО
        DemandProcessing.recreate_demand_hour_main(date_begin, TIME_ZONE, subdivision_id)

        return JsonResponse({'message': 'request processed'}, status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    # Пересчёт покрытия потребности
    def recalculate_covering(subdivision_id, date_begin):
        Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id, demand_date__gte=date_begin).update(
            covering_value=Subquery(
                Demand_Hour_Main.objects.prefetch_related('demand_hour_shift_set').filter(
                    id=OuterRef('id'), subdivision_id=subdivision_id, demand_date__gte=date_begin
                ).annotate(
                    Count('demand_hour_shift_set')
                ).values('demand_hour_shift_set__count')[:1]
            )
        )

    @staticmethod
    # Пересчёт покрытия потребности за определенный день
    def recalculate_covering_on_date(subdivision_id, date_begin):
        Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id, demand_date=date_begin).update(
            covering_value=Subquery(
                Demand_Hour_Main.objects.prefetch_related('demand_hour_shift_set').filter(
                    id=OuterRef('id'), subdivision_id=subdivision_id, demand_date=date_begin
                ).annotate(
                    Count('demand_hour_shift_set')
                ).values('demand_hour_shift_set__count')[:1]
            )
        )

    @staticmethod
    # Добавление смены за период (покрытие потребности)
    def add_shift_to_demand(subdivision_id, demand_date, duty_id, shift_id, hour_from, hour_to):
        demand_hour_main = Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id, demand_date=demand_date,
                                                           duty_id=duty_id,
                                                           demand_hour__gte=hour_from, demand_hour__lt=hour_to)
        objects = []
        hours_main = []
        hours_list = []
        for dhm in demand_hour_main.iterator():
            line = Demand_Hour_Shift(
                demand_hour_main_id=dhm.id,
                shift_id=shift_id
            )
            objects.append(line)
            hours_main.append(dhm.demand_hour)

        if objects:
            Demand_Hour_Shift.objects.bulk_create(objects, ignore_conflicts=True)

        if (hour_to - hour_from) != len(hours_main):
            hour_step = hour_from
            while hour_step < hour_to:
                if not hours_main.count(hour_step):
                    hours_list.append(hour_step)
                hour_step += 1
        return hours_list

    @staticmethod
    # Добавление смены за час (покрытие потребности)
    def add_shift_to_demand_on_hour(subdivision_id, demand_date, duty_id, shift_id, hour):
        demand_hour_main, dhm_create = Demand_Hour_Main.objects.get_or_create(
            subdivision_id=subdivision_id,
            demand_date=demand_date,
            duty_id=duty_id,
            demand_hour=hour
        )
        dhm_id = demand_hour_main.id

        Demand_Hour_Shift.objects.get_or_create(
            demand_hour_main_id=dhm_id,
            shift_id=shift_id
        )

    @staticmethod
    # Добавление значения продолжительности обеденного перерыва
    def add_shift_break_value(subdivision_id, demand_date, hour, shift_id):
        dhs = Demand_Hour_Shift.objects.select_related('demand_hour_main').filter(
            shift_id=shift_id,
            demand_hour_main__subdivision_id=subdivision_id,
            demand_hour_main__demand_date=demand_date,
            demand_hour_main__demand_hour=hour
        )
        rec = dhs.first()
        if rec:
            rec.break_value = float(rec.break_value) + 0.5
            rec.save(update_fields=['break_value'])

    @staticmethod
    # Пересчёт значения продолжительности обеденных перерывов
    def recalculate_breaks_value(subdivision_id, date_begin):
        Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id, demand_date__gte=date_begin).update(
            breaks_value=Subquery(
                Demand_Hour_Main.objects.prefetch_related('demand_hour_shift_set').filter(
                    id=OuterRef('id'), subdivision_id=subdivision_id, demand_date__gte=date_begin
                ).annotate(
                    break_value_sum=Coalesce(Sum('demand_hour_shift_set__break_value'), Decimal(0))
                ).values('break_value_sum')[:1]
            )
        )

    @staticmethod
    # Пересчёт значения продолжительности обеденных перерывов за определенную дату
    def recalculate_breaks_value_on_date(subdivision_id, date_begin):
        Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id, demand_date=date_begin).update(
            breaks_value=Subquery(
                Demand_Hour_Main.objects.prefetch_related('demand_hour_shift_set').filter(
                    id=OuterRef('id'), subdivision_id=subdivision_id, demand_date=date_begin
                ).annotate(
                    break_value_sum=Coalesce(Sum('demand_hour_shift_set__break_value'), Decimal(0))
                ).values('break_value_sum')[:1]
            )
        )
