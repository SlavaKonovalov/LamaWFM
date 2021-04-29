import datetime
import pandas
from django.db import transaction, connection
import sys
from django.db.models import Q, F
from django.http import JsonResponse
from random import randint
from .demandProcessing import DemandProcessing
from .models import Employee_Shift, Employee_Shift_Detail_Plan, Employee_Planning_Rules, Demand_Hour_Main, \
    Open_Shift

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
                AND ddm.subdivision_id = %s
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
    def get_availability_dataframe(subdivision_id, begin_date, end_date, tz, shift_type, employees=None):
        query = """
                SELECT job_duty_id as duty, wfm_employee.id as employee, begin_date_time, end_date_time,
                DATE_TRUNC('day', begin_date_time AT TIME ZONE '%s') as date,
                EXTRACT('hour' FROM begin_date_time AT TIME ZONE '%s') as av_begin_hour,
                EXTRACT('hour' FROM end_date_time AT TIME ZONE '%s') as av_end_hour,
                working_days_for_flexible_min,
                working_days_for_flexible_max,
                weekends_for_flexible_min,
                weekends_for_flexible_max,
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
                WHERE wfm_employee.subdivision_id = %s
                AND begin_date_time >= '%s'
                AND begin_date_time < '%s'
                AND date_rules_start <= begin_date_time
                AND (date_rules_end > begin_date_time OR date_rules_end IS NULL)
                AND shift_type = '%s'
                """ % (tz, tz, tz, subdivision_id, begin_date, end_date, shift_type)
        if employees:
            query += "AND wfm_employee.id in (%s)" % str(employees).strip('[]')
        df = pandas.read_sql_query(query, connection)
        return df

    @staticmethod
    # Создание смены
    def add_shift(subdivision_id, employee_id, shift_date, shift_type, interval_type, shift_begin, shift_end):
        employee_shift, created_shift = Employee_Shift.objects.get_or_create(
            employee_id=employee_id,
            subdivision_id=subdivision_id,
            shift_date=shift_date,
            defaults={'shift_type': shift_type}
        )
        employee_shift_detail_plan, created_shift_plan = Employee_Shift_Detail_Plan.objects.update_or_create(
            shift_id=employee_shift.id,
            type=interval_type,
            defaults={
                'time_from': datetime.time(int(shift_begin), 0),
                'time_to': datetime.time(int(shift_end), 0)
            }
        )
        return employee_shift.id

    @staticmethod
    # Удаление смен
    def delete_shifts(subdivision_id, begin_date_time, end_date_time, employees=None):
        begin_date = begin_date_time.date()
        end_date = end_date_time.date()
        employee_shift = Employee_Shift.objects.all()
        if employees:
            employee_shift = employee_shift.filter(subdivision_id=subdivision_id, employee_id__in=employees)
        else:
            employee_shift = employee_shift.filter(subdivision_id=subdivision_id)
        # Удаляем смены
        employee_shift.filter(fixed=0, shift_date__gte=begin_date, shift_date__lt=end_date).delete()
        # Удаляем открытые смены
        if not employees:
            Open_Shift.objects.filter(subdivision_id=subdivision_id, shift_date__gte=begin_date,
                                      shift_date__lt=end_date).delete()

    @staticmethod
    def plan_fix_shifts(subdivision_id, begin_date_time, end_date_time, employees=None):
        begin_date = begin_date_time.date()
        end_date = end_date_time.date()
        # Получаем dataframe для доступности + правила планирования для фиксированных смен
        df_availability = ShiftPlanning.get_availability_dataframe(subdivision_id, begin_date_time, end_date_time,
                                                                   TIME_ZONE, 'fix', employees)
        if df_availability.empty:
            return
        df_availability['shift_date'] = df_availability.date.dt.date
        df_availability = df_availability[['employee', 'shift_date', 'av_begin_hour', 'av_end_hour']].drop_duplicates()
        # Фиксированные смены
        employee_shift = Employee_Shift.objects.filter(subdivision_id=subdivision_id, shift_type='fix',
                                                       shift_date__gte=begin_date, shift_date__lt=end_date)
        if employees:
            employee_shift = employee_shift.filter(employee_id__in=employees)
        df_employee_shift = pandas.DataFrame(
            employee_shift.values_list('employee_id', 'shift_date', 'fixed'),
            columns=['employee', 'shift_date', 'fixed'])

        df_availability = pandas.merge(df_availability, df_employee_shift, how='left',
                                       left_on=['employee', 'shift_date'],
                                       right_on=['employee', 'shift_date'])
        # Исключаем доступность с существующими сменами
        df_availability = df_availability[(df_availability.fixed.isna())]
        for row_availability in df_availability.itertuples():
            ShiftPlanning.add_shift(subdivision_id, row_availability.employee, row_availability.shift_date,
                                    'fix', 'job', row_availability.av_begin_hour, row_availability.av_end_hour)

    @staticmethod
    # Планирование гибких смен
    def plan_flexible_shifts(subdivision_id, begin_date_time, end_date_time, employees=None):
        begin_date = begin_date_time.date()
        end_date = end_date_time.date()

        # Получаем dataframe для потребности
        demand_hour_main = Demand_Hour_Main.objects.filter(subdivision_id=subdivision_id,
                                                           demand_date__gte=begin_date,
                                                           demand_date__lt=end_date,
                                                           demand_value__gt=F('covering_value')
                                                           )
        df_demand_unique = pandas.DataFrame(
            demand_hour_main.values_list('id', 'demand_date', 'demand_hour', 'duty_id', 'demand_value',
                                         'covering_value'),
            columns=['id', 'date', 'hour', 'duty', 'demand_value', 'covering_value'])
        df_demand_unique['qty'] = df_demand_unique.demand_value - df_demand_unique.covering_value
        # Вычисляем значения "Кол-во часов" и "Последний требуемый час"
        df_demand_unique['count_hour'] = df_demand_unique.groupby(['date', 'duty'])['hour'].transform("count")
        df_demand_unique['last_hour'] = df_demand_unique.groupby(['date', 'duty'])['hour'].transform("max")
        # Сортируем
        df_demand_unique = df_demand_unique.sort_values(by=['date', 'count_hour', 'duty', 'hour'],
                                                        ascending=[True, False, True, True])
        # Получаем dataframe со списком дат
        df_demand_date = df_demand_unique[['date']].drop_duplicates()

        # Получаем dataframe для доступности + правила планирования для гибких смен
        df_availability = ShiftPlanning.get_availability_dataframe(subdivision_id, begin_date_time, end_date_time,
                                                                   TIME_ZONE, 'flexible', employees)
        df_availability.begin_date_time = df_availability.begin_date_time.dt.tz_convert(TIME_ZONE)
        df_availability.end_date_time = df_availability.end_date_time.dt.tz_convert(TIME_ZONE)
        df_availability['appointed'] = 0  # 1, если сотруднику в процессе назначена смена на данный день
        df_availability.date = df_availability.date.dt.date
        # Дата для расчета смен за неделю до пересчета
        prev_shifts_date = (begin_date_time - datetime.timedelta(days=7)).date()
        # Сделаем begin_date началом месяца
        begin_date = begin_date.replace(day=1)
        min_date = min(begin_date, prev_shifts_date)
        # Получаем dataframe текущих смен за месяц
        shift_detail_plan = Employee_Shift_Detail_Plan.objects.select_related('shift').filter(
            shift__subdivision_id=subdivision_id,
            shift__shift_type='flexible',
            shift__shift_date__gte=min_date,
            shift__shift_date__lt=end_date)
        df_shift_plan = pandas.DataFrame(
            shift_detail_plan.values_list('shift__employee_id', 'shift__subdivision_id', 'shift__shift_date', 'type',
                                          'time_from', 'time_to', 'shift__fixed'),
            columns=['employee', 'subdivision', 'shift_date', 'type', 'time_from', 'time_to', 'fixed'])
        df_shift_plan['hour_from'] = pandas.to_datetime(df_shift_plan['time_from'], format='%H:%M:%S').dt.hour
        df_shift_plan['hour_to'] = pandas.to_datetime(df_shift_plan['time_to'], format='%H:%M:%S').dt.hour
        df_shift_plan['hours'] = df_shift_plan.hour_to - df_shift_plan.hour_from
        # Исключаем доступность с существующими сменами
        df_covering = df_shift_plan[(df_shift_plan.type == 'job') &
                                    (df_shift_plan.shift_date >= begin_date)][
            ['employee', 'shift_date', 'hours', 'fixed']]
        df_existing_shifts = df_covering[(df_covering.shift_date >= begin_date_time.date())]
        df_availability = pandas.merge(df_availability, df_existing_shifts, how='left',
                                       left_on=['employee', 'date'],
                                       right_on=['employee', 'shift_date'])
        df_availability = df_availability[(df_availability.fixed.isna())]
        # Получаем dataframe с суммарным кол-вом часов по каждому сотруднику из df_existing_shifts
        df_covering['hours_sum'] = df_covering.groupby('employee')['hours'].transform('sum')
        df_covering = df_covering[['employee', 'hours_sum']].drop_duplicates()
        # Далее определяем, кто отдыхал или работал перед началом моделирования, и продолжительность периода
        # Начало -->
        # Находим смены за неделю до даты моделирования
        df_prev_shift_plan = df_shift_plan[(df_shift_plan.type == 'job') &
                                           (df_shift_plan.shift_date >= prev_shifts_date) &
                                           (df_shift_plan.shift_date < begin_date_time.date())][
            ['employee', 'shift_date']]
        if not df_prev_shift_plan.empty:
            # last_date - дата последней смены
            df_prev_shift_plan['last_date'] = df_prev_shift_plan.groupby('employee')['shift_date'].transform("max")
            date_step = 1
            prev_date = (begin_date_time - datetime.timedelta(days=date_step)).date()
            # date_diff - разница (в днях) между prev_date и last_date
            df_prev_shift_plan['date_diff'] = (prev_date - df_prev_shift_plan.last_date).dt.days
            # works - человек работал за день до начала пересчета? 1 - да, 0 - нет
            df_prev_shift_plan['works'] = df_prev_shift_plan['date_diff'].apply(lambda x: 1 if x == 0 else 0)
            # work_check - промежуточный признак для расчета рабочих дней подряд
            df_prev_shift_plan['work_check'] = df_prev_shift_plan['works']

            # Зануляем work_check для строк, если человек работал в день перед началом пересчета
            df_prev_shift_plan.loc[(df_prev_shift_plan.work_check == 1) &
                                   (df_prev_shift_plan.shift_date == prev_date), ['work_check']] = 0
            # Цикл пока есть 1 в столбце work_check
            while df_prev_shift_plan.work_check.isin([1]).any().any():
                df_prev_shift_plan['last_date'] = df_prev_shift_plan.groupby(['employee', 'work_check'])[
                    'shift_date'].transform("max")
                date_step += 1
                prev_date = (begin_date_time - datetime.timedelta(days=date_step)).date()
                df_prev_shift_plan.loc[(df_prev_shift_plan.work_check == 1), ['date_diff']] = (
                        prev_date - df_prev_shift_plan.last_date).dt.days
                df_prev_shift_plan.loc[(df_prev_shift_plan.work_check == 1) &
                                       (df_prev_shift_plan.date_diff > 0), ['date_diff']] = date_step - 1
                df_prev_shift_plan.loc[(df_prev_shift_plan.work_check == 1) &
                                       ((df_prev_shift_plan.date_diff > 0) |
                                        (df_prev_shift_plan.shift_date == prev_date)), ['work_check']] = 0
            # в qty кол-во рабочих или выходных дней подряд перед началом пересчета
            df_prev_shift_plan['qty'] = df_prev_shift_plan.groupby('employee')['date_diff'].transform("max")
        else:
            df_prev_shift_plan['works'] = 0
            df_prev_shift_plan['qty'] = 0
        # df_shift_period - результаты
        df_shift_period = df_prev_shift_plan[['employee', 'works', 'qty']].drop_duplicates()
        # признак назначения смены для дневной обработки
        df_shift_period['shift_check'] = 0
        # <-- Конец

        # Цикл по датам
        for row_date in df_demand_date.itertuples():
            # Берем потребность за выбранную дату
            df_demand_on_date = df_demand_unique[(df_demand_unique.date == row_date.date)]
            # Добавляем признак "Покрывалось". Устанавливается на ФО, если назначалась хоть одна смена
            df_demand_on_date['covered'] = -df_demand_on_date['covering_value']

            df_shift_on_date = pandas.DataFrame(columns=['employee', 'shift_id', 'hour_from',
                                                         'hour_to', 'shift_duration_max'])
            while True:
                df_res_with_shifts = pandas.DataFrame()
                # Бегаем, пока df_demand_on_date не пуст
                df_demand_on_date = df_demand_on_date[(df_demand_on_date.qty > 0)]
                # Если пусто - выходим из цикла
                if df_demand_on_date.empty:
                    break
                # Пересчитываем 'count_hour' и 'last_hour'
                df_demand_on_date['count_hour'] = df_demand_on_date.groupby(['date', 'duty'])['hour'].transform("count")
                df_demand_on_date['last_hour'] = df_demand_on_date.groupby(['date', 'duty'])['hour'].transform("max")

                # Берем первую запись
                row_demand = df_demand_on_date.iloc[0]

                # Ищем доступных сотрудников по определенным условиям
                df_res = df_availability[
                    (df_availability.appointed == 0) &
                    (df_availability.date == row_demand.date) &
                    (df_availability.av_begin_hour <= row_demand.hour) &  # доступен в этом часу
                    (df_availability.av_end_hour - 1 > row_demand.hour) &  # может покрыть как минимум 2 часа
                    # минимальная длина смены укладывается в доступность:
                    (df_availability.av_end_hour - df_availability.av_begin_hour >= df_availability.shift_duration_min)
                    & (row_demand.duty == df_availability.duty)]
                # добавляем df_shift_period, проверяем параметры продолжительности рабочих и выходных дней
                if not df_res.empty:
                    df_res = pandas.merge(df_res, df_shift_period, on=['employee'], how='left')
                    df_res.works = df_res.works.fillna(1)  # Меняем NULL на 1 для works
                    df_res.qty = df_res.qty.fillna(0)  # Меняем NULL на 0 для qty
                    df_res = df_res[((df_res.works == 1) & (df_res.qty < df_res.working_days_for_flexible_max) |
                                     (df_res.works == 0) & (df_res.qty >= df_res.weekends_for_flexible_min))]

                # Ищем смены, которые закончились на текущем часе
                df_shift_on_hour = df_shift_on_date[(df_shift_on_date.hour_to == row_demand.hour) &
                                                    (
                                                            df_shift_on_date.hour_to - df_shift_on_date.hour_from != df_shift_on_date.shift_duration_max)][
                    ['employee', 'shift_id', 'hour_from', 'hour_to']]
                if not df_shift_on_hour.empty:
                    # Находим список сотрудников, которым можно продлить смены
                    df_res_with_shifts = df_availability[
                        (df_availability.appointed == 1) &
                        (df_availability.date == row_demand.date) &
                        (df_availability.av_begin_hour < row_demand.hour) &  # доступен в этом часу
                        (df_availability.av_end_hour > row_demand.hour) &  # может покрыть как минимум 2 часа
                        (df_availability.shift_duration_max is not None) &  # определена верхняя граница длины смены
                        # доступность больше минимальной длины смены:
                        (
                                df_availability.av_end_hour - df_availability.av_begin_hour > df_availability.shift_duration_min)
                        & (row_demand.duty == df_availability.duty)]
                    df_res_with_shifts = pandas.merge(df_res_with_shifts, df_shift_on_hour, on=['employee'],
                                                      how='inner')

                # Если ФО уже покрывалась, требуется на данный час 1 сотрудник и всего непокрытых часов <= 2
                # выводить нового сотрудника не имеет смысла
                # проверяем, можно ли продлить смену уже назначенному. Если нет, то прекращаем расчет остатка
                row_demand_check = True if (
                        row_demand.qty == 1 and row_demand.count_hour <= 2 and row_demand.covered != 0) else False

                if row_demand_check or df_res.empty:
                    # Если можно продлить смену
                    if not df_res_with_shifts.empty:
                        df_res_with_shifts_sample = df_res_with_shifts.sample()  # берем любого
                        res_sample = df_res_with_shifts_sample.iloc[0]  # получаем серию из dataframe
                        value = 1
                        if row_demand_check and (
                                1 + row_demand.last_hour - res_sample.hour_to) == row_demand.count_hour:
                            value = min(row_demand.count_hour,
                                        res_sample.shift_duration_max - (res_sample.hour_to - res_sample.hour_from))

                        df_covering.loc[df_covering.employee == res_sample.employee, ['hours_sum']] += value

                        employee_shift_detail_plan, created_shift_plan = Employee_Shift_Detail_Plan.objects.update_or_create(
                            shift_id=res_sample.shift_id,
                            type='job',
                            defaults={
                                'time_from': datetime.time(int(res_sample.hour_from), 0),
                                'time_to': datetime.time(int(res_sample.hour_to + value), 0)
                            }
                        )

                        # добавление смены в Demand_Hour_Shift
                        DemandProcessing.add_shift_to_demand(subdivision_id, row_demand.date, row_demand.duty,
                                                             res_sample.shift_id, res_sample.hour_to,
                                                             res_sample.hour_to + value)

                        df_shift_on_date.loc[df_shift_on_date.employee == res_sample.employee,
                                             ['hour_to']] += value

                        # Уменьшаем qty (потребность) и covered на 1
                        df_demand_on_date.loc[(df_demand_on_date.date == row_demand.date) &
                                              (df_demand_on_date.duty == row_demand.duty) &
                                              (df_demand_on_date.hour < row_demand.hour + value), ['qty',
                                                                                                   'covered']] -= 1

                    else:
                        if row_demand_check:
                            df_demand_on_date.loc[(df_demand_on_date.date == row_demand.date) &
                                                  (df_demand_on_date.duty == row_demand.duty), ['qty']] = 0
                        else:
                            df_demand_on_date.iloc[0, df_demand_on_date.columns.get_loc('qty')] = 0
                else:
                    # Подключаем к доступным сотрудникам их плановые часы
                    df_res = pandas.merge(df_res, df_covering, on=['employee'], how='left')
                    df_res.hours_sum = df_res.hours_sum.fillna(0)  # Меняем NULL на 0
                    min_hours_sum = df_res.hours_sum.min()  # находим минимальное кол-во часов
                    # Ищем сотрудников с минимальным кол-вом часов
                    df_res = df_res[(df_res.hours_sum <= min_hours_sum + 2)]  # 2 - это погрешность (в часах)

                    # Минимальная доступность. Вариант отбора -->
                    # res['min_availability'] = df_availability.av_end_hour - df_availability.av_begin_hour
                    # min_availability = res.min_availability.min()
                    # Минимальная доступность. Вариант отбора <--
                    # Максимальное покрытие. Вариант отбора -->
                    # res['max_covering'] = res.av_end_hour - row.hour
                    # max_covering = res.max_covering.max()
                    # Максимальное покрытие. Вариант отбора <--

                    df_res_sample = df_res.sample()  # берем любого
                    res_sample = df_res_sample.iloc[0]  # получаем серию из dataframe
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
                                shift_end = shift_begin + randint(res_sample.shift_duration_min,
                                                                  res_sample.shift_duration_max)
                        else:
                            shift_end = shift_begin + res_sample.shift_duration_min
                    shift_length = shift_end - shift_begin

                    # Добавляем смену и кол-во часов новой смены сотруднику
                    if df_covering.employee.isin([res_sample.employee]).any().any():
                        df_covering.loc[df_covering.employee == res_sample.employee, ['hours_sum']] += shift_length
                    else:
                        df_covering_row = pandas.Series(data={'employee': res_sample.employee,
                                                              'hours_sum': shift_length})
                        df_covering = df_covering.append(df_covering_row, ignore_index=True)

                    employee_shift_id = ShiftPlanning.add_shift(subdivision_id, res_sample.employee, row_demand.date,
                                                                'flexible', 'job', shift_begin, shift_end)

                    # добавление смены в Demand_Hour_Shift
                    DemandProcessing.add_shift_to_demand(subdivision_id, row_demand.date, row_demand.duty,
                                                         employee_shift_id, shift_begin, shift_end)

                    shift_duration_max = res_sample.shift_duration_max if res_sample.shift_duration_max else res_sample.shift_duration_min
                    df_shift_on_date_row = pandas.Series(data={'employee': res_sample.employee,
                                                               'shift_id': employee_shift_id,
                                                               'hour_from': shift_begin,
                                                               'hour_to': shift_end,
                                                               'shift_duration_max': shift_duration_max})
                    df_shift_on_date = df_shift_on_date.append(df_shift_on_date_row, ignore_index=True)

                    # удаляем доступность сотрудника в этот день из dataframe
                    df_availability.loc[(df_availability.date == row_demand.date) &
                                        (df_availability.employee == res_sample.employee), ['appointed']] = 1
                    # Уменьшаем qty (потребность) и covered на всём интервале на 1
                    df_demand_on_date.loc[(df_demand_on_date.date == row_demand.date) &
                                          (df_demand_on_date.duty == row_demand.duty) &
                                          (shift_begin <= df_demand_on_date.hour) &
                                          (df_demand_on_date.hour < shift_end), ['qty', 'covered']] -= 1

                    if not res_sample.qty:
                        df_shift_period_row = pandas.Series(data={'employee': res_sample.employee,
                                                                  'works': 1,
                                                                  'qty': 0,
                                                                  'shift_check': 1})
                        df_shift_period = df_shift_period.append(df_shift_period_row, ignore_index=True)
                    if not res_sample.works:
                        df_shift_period.loc[(df_shift_period.employee == res_sample.employee), ['works']] = 1
                        df_shift_period.loc[(df_shift_period.employee == res_sample.employee), ['qty']] = 0
                    df_shift_period.loc[(df_shift_period.employee == res_sample.employee), ['shift_check']] = 1

            # обработка df_shift_period для фиксированных смен
            # Начало -->
            df_existing_shifts_on_date = df_existing_shifts[(df_existing_shifts.shift_date == row_date.date)]
            if not df_existing_shifts_on_date.empty:
                df_existing_shifts_on_date = pandas.merge(df_existing_shifts_on_date, df_shift_period, on=['employee'],
                                                          how='left')
                # Меняем NULL на 1 для works
                df_existing_shifts_on_date.works = df_existing_shifts_on_date.works.fillna(1)
                df_existing_shifts_on_date.qty = df_existing_shifts_on_date.qty.fillna(0)  # Меняем NULL на 0 для qty
                for row_existing_shifts in df_existing_shifts_on_date.itertuples():
                    if not row_existing_shifts.qty:
                        df_shift_period_row = pandas.Series(data={'employee': row_existing_shifts.employee,
                                                                  'works': 1,
                                                                  'qty': 0,
                                                                  'shift_check': 1})
                        df_shift_period = df_shift_period.append(df_shift_period_row, ignore_index=True)
                    if not row_existing_shifts.works:
                        df_shift_period.loc[
                            (df_shift_period.employee == row_existing_shifts.employee), ['works']] = 1
                        df_shift_period.loc[
                            (df_shift_period.employee == row_existing_shifts.employee), ['qty']] = 0
                    df_shift_period.loc[
                        (df_shift_period.employee == row_existing_shifts.employee), ['shift_check']] = 1
            # <-- Конец

            # Ставим выходные, если смены не назначены
            df_shift_period.loc[(df_shift_period.works == 1) & (df_shift_period.shift_check == 0), ['qty']] = 0
            df_shift_period.loc[(df_shift_period.works == 1) & (df_shift_period.shift_check == 0), ['works']] = 0
            # Инкремент qty
            df_shift_period = df_shift_period.assign(qty=df_shift_period.qty + 1)
            # Сбрасываем shift_check
            df_shift_period['shift_check'] = 0

    @staticmethod
    @transaction.atomic
    def plan_shifts(subdivision_id, begin_date_time, end_date_time, employees=None):
        ShiftPlanning.delete_shifts(subdivision_id, begin_date_time, end_date_time, employees)
        DemandProcessing.recalculate_covering(subdivision_id, begin_date_time.date())
        ShiftPlanning.plan_fix_shifts(subdivision_id, begin_date_time, end_date_time, employees)
        ShiftPlanning.plan_flexible_shifts(subdivision_id, begin_date_time, end_date_time, employees)
        DemandProcessing.recalculate_covering(subdivision_id, begin_date_time.date())
