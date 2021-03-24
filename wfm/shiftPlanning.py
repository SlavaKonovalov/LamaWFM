import pandas
from django.db import transaction, connection
import sys

from .models import Employee_Availability

sys.path.append('..')
from LamaWFM.settings import TIME_ZONE


class ShiftPlanning:

    @staticmethod
    def get_dataframe(date_begin, end_date, tz):
        query = """
                SELECT date, hour, duty_id, task_sum.task_id, demand_sum
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
                ORDER BY date, hour, duty_id, task_sum.task_id
                """ % (tz, tz, date_begin, end_date, tz, tz)
        df = pandas.read_sql_query(query, connection)
        return df

    @staticmethod
    @transaction.atomic
    # Планирование смен
    def plan_shifts(subdivision_id, begin_date, end_date, employee_id=None):
        df = ShiftPlanning.get_dataframe(begin_date, end_date, TIME_ZONE)
        employee_availabilities = Employee_Availability.objects.filter(subdivision_id=subdivision_id)
