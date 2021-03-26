import pandas
from django.db import transaction, connection
import sys

from .models import Employee_Availability, Employee

sys.path.append('..')
from LamaWFM.settings import TIME_ZONE


class ShiftPlanning:

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
    def get_availability_dataframe(subdivision_id, begin_date, end_date, employee_id=None):
        query = """
                SELECT job_duty_id as duty, wfm_employee.id as employee, begin_date_time, end_date_time,
                DATE_TRUNC('day', begin_date_time AT TIME ZONE 'Asia/Tomsk') as date,
                EXTRACT('hour' FROM begin_date_time AT TIME ZONE 'Asia/Tomsk') as begin_hour,
                EXTRACT('hour' FROM end_date_time AT TIME ZONE 'Asia/Tomsk') as end_hour
                FROM wfm_employee
                INNER JOIN wfm_employee_duties
                ON wfm_employee.id = wfm_employee_duties.employee_id
                INNER JOIN wfm_employee_availability
                ON wfm_employee.id = wfm_employee_availability.employee_id
                WHERE wfm_employee.subdivision_id = '%s'
                AND begin_date_time >= '%s'
                AND begin_date_time < '%s'
                """ % (subdivision_id, begin_date, end_date)
        if employee_id:
            query += "AND wfm_employee.id = '%s'" % employee_id
        df = pandas.read_sql_query(query, connection)
        return df

    @staticmethod
    @transaction.atomic
    # Планирование смен
    def plan_shifts(subdivision_id, begin_date, end_date, employee_id=None):
        df_demand = ShiftPlanning.get_demand_dataframe(subdivision_id, begin_date, end_date, TIME_ZONE)
        df_demand['qty'] = df_demand.groupby(['date', 'hour', 'duty'])['demand_sum'].transform('sum').round(0)
        df_demand_unique = df_demand[['date', 'hour', 'duty', 'qty']].drop_duplicates()
        df_demand_unique['qty'] = df_demand_unique['qty'].apply(lambda x: 1 if x == 0 else x)

        df_availability = ShiftPlanning.get_availability_dataframe(subdivision_id, begin_date, end_date, employee_id)
        df_availability.begin_date_time = df_availability.begin_date_time.dt.tz_convert(TIME_ZONE)
        df_availability.end_date_time = df_availability.end_date_time.dt.tz_convert(TIME_ZONE)

        for row in df_demand_unique.itertuples():
            res = df_availability[
                (df_availability.date == row.date) & (df_availability.begin_hour <= row.hour) & row.duty == df_availability.duty]
            # ТУТ ДОЛЖНА БЫТЬ ПРОВЕРКА, У КОГО МЕНЬШЕ ЧАСОВ, затем берем рандомного челика
            # b = 1
        # a = 1
