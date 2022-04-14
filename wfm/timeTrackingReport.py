from decimal import Decimal

import pandas
from django.db import transaction, connection
from django.db.models import Sum, OuterRef, F, Exists, Count, Subquery, Q
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from rest_framework import status

from .db import DataBase
import math
import datetime as datetime
import sys


class TimeTrackingReport:

    @staticmethod
    def get_count_plan_shift(subdivision_id, date_start, date_end, employee_id):
        count_plan_shift = 0
        query = ""

        if employee_id is None:
            query = """
                            SELECT 
                                COUNT(*) AS countPlanShift 
                            FROM public.wfm_employee_shift  
                            WHERE shift_date >= '%s' 
                                AND shift_date <= '%s'
                                AND subdivision_id = %s
                    """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                        SELECT 
                            COUNT(*) AS countPlanShift 
                        FROM public.wfm_employee_shift  
                        WHERE employee_id = %s
                            AND shift_date >= '%s' 
                            AND shift_date <= '%s'
                            AND subdivision_id = %s
                """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            count_plan_shift = df_row.countplanshift

        return count_plan_shift

    @staticmethod
    def get_count_fact_shift(subdivision_id, date_start, date_end, employee_id):
        count_fact_shift = 0
        query = ""

        if employee_id is None:
            query = """
                        SELECT 
                            COUNT(*) AS countFactShift 
                        FROM public.wfm_employee_fact_scan  
                        WHERE scan_date >= '%s' 
                            AND scan_date <= '%s'
                            AND subdivision_id = %s
                """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                        SELECT 
                            COUNT(*) AS countFactShift 
                        FROM public.wfm_employee_fact_scan  
                        WHERE employee_id = %s
                            AND scan_date >= '%s' 
                            AND scan_date <= '%s'
                            AND subdivision_id = %s
                """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            count_fact_shift = df_row.countfactshift

        return count_fact_shift

    @staticmethod
    def get_sum_hours_plan_shift(subdivision_id, date_start, date_end, employee_id):
        sum_hours_plan_shift = 0
        query = ""
        if employee_id is None:
            query = """
                        SELECT 
                            SUM(DATE_PART('hour', esdp.time_to - esdp.time_from)) as CountHourPlan
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        WHERE es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                        SELECT 
                            SUM(DATE_PART('hour', esdp.time_to - esdp.time_from)) as CountHourPlan
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        WHERE es.employee_id = %s
                            AND es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            sum_hours_plan_shift = df_row.counthourplan

        if sum_hours_plan_shift is None:
            sum_hours_plan_shift = 0

        return sum_hours_plan_shift

    @staticmethod
    def get_sum_hours_fact_shift(subdivision_id, date_start, date_end, employee_id):
        sum_hours_fact_shift = 0
        query = ""
        if employee_id is None:
            query = """
                        SELECT 
                            SUM((DATE_PART('hour', efs.time_to - efs.time_from) * 60 +
                                DATE_PART('minute', efs.time_to - efs.time_from))/60) AS CountHourFact
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_from - efs.time_from) >= '-00:00:59') -- опоздание на минуту 
                            AND ((esdp.time_from - efs.time_from) <= '00:15:00') -- сотрудник раньше не нужен
                            AND ((esdp.time_to - efs.time_to) >= '-00:15:00') --  сотрудник позже не нужен
                            AND ((esdp.time_to - efs.time_to) <= '00:00:59') -- ушел раньше на минуту
                    """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                        SELECT 
                            SUM((DATE_PART('hour', efs.time_to - efs.time_from) * 60 +
                                DATE_PART('minute', efs.time_to - efs.time_from))/60) AS CountHourFact
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.employee_id = %s
                            AND es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_from - efs.time_from) >= '-00:00:59') -- опоздание на минуту 
                            AND ((esdp.time_from - efs.time_from) <= '00:15:00') -- сотрудник раньше не нужен
                            AND ((esdp.time_to - efs.time_to) >= '-00:15:00') --  сотрудник позже не нужен
                            AND ((esdp.time_to - efs.time_to) <= '00:00:59') -- ушел раньше на минуту
                    """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            sum_hours_fact_shift = df_row.counthourfact

        if sum_hours_fact_shift is None:
            sum_hours_fact_shift = 0

        return sum_hours_fact_shift

    @staticmethod
    def get_equality_plan_fact(subdivision_id, date_start, date_end, employee_id):
        equality_plan_fact = 0
        query = ""
        if employee_id is None:
            query = """
                    SELECT 
                        count(*) as EqualityPlanFact
                    FROM public.wfm_employee_shift es
                    JOIN public.wfm_employee_shift_detail_plan esdp
                        ON esdp.shift_id = es.id  
                        AND esdp.type = 'job'
                    JOIN public.wfm_employee_fact_scan efs
                        ON efs.employee_id = es.employee_id
                        AND efs.subdivision_id = es.subdivision_id
                        AND efs.scan_date = es.shift_date
                    WHERE es.shift_date >= '%s' 
                        AND es.shift_date <= '%s'
                        AND es.subdivision_id = %s
                        AND ((esdp.time_from - efs.time_from) >= '-00:00:59') -- опоздание на минуту 
                        AND ((esdp.time_from - efs.time_from) <= '00:15:00') -- сотрудник раньше не нужен
                        AND ((esdp.time_to - efs.time_to) >= '-00:15:00') --  сотрудник позже не нужен
                        AND ((esdp.time_to - efs.time_to) <= '00:00:59') -- ушел раньше на минуту	
                    """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                        SELECT 
                            count(*) as EqualityPlanFact
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.employee_id = %s
                            AND es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_from - efs.time_from) >= '-00:00:59') -- опоздание на минуту 
                            AND ((esdp.time_from - efs.time_from) <= '00:15:00') -- сотрудник раньше не нужен
                            AND ((esdp.time_to - efs.time_to) >= '-00:15:00') --  сотрудник позже не нужен
                            AND ((esdp.time_to - efs.time_to) <= '00:00:59') -- ушел раньше на минуту	
                    """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            equality_plan_fact = df_row.equalityplanfact

        return equality_plan_fact

    @staticmethod
    def get_part_off_lateness(subdivision_id, date_start, date_end, employee_id):
        part_off_lateness = 0
        query = ""
        if employee_id is None:
            query = """
                         SELECT 
                            count(*) AS countAllLateness
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_from - efs.time_from) < '-00:15:00') 
                    """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                     SELECT 
                        count(*) AS countAllLateness
                    FROM public.wfm_employee_shift es
                    JOIN public.wfm_employee_shift_detail_plan esdp
                        ON esdp.shift_id = es.id  
                        AND esdp.type = 'job'
                    JOIN public.wfm_employee_fact_scan efs
                        ON efs.employee_id = es.employee_id
                        AND efs.subdivision_id = es.subdivision_id
                        AND efs.scan_date = es.shift_date
                    WHERE es.employee_id = %s
                        AND es.shift_date >= '%s' 
                        AND es.shift_date <= '%s'
                        AND es.subdivision_id = %s
                        AND ((esdp.time_from - efs.time_from) < '-00:15:00') 
                """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            part_off_lateness = df_row.countalllateness

        return part_off_lateness

    @staticmethod
    def get_hour_late(subdivision_id, date_start, date_end, employee_id):
        hour_late = 0
        query = ""
        if employee_id is None:
            query = """
                        SELECT 
                            SUM((DATE_PART('hour', esdp.time_from - efs.time_from) * 60 +
                                      DATE_PART('minute', esdp.time_from - efs.time_from))/60) as hourLate
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_from - efs.time_from) < '-00:00:59') 	--опоздал 
                    """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                        SELECT 
                            SUM((DATE_PART('hour', esdp.time_from - efs.time_from) * 60 +
                                      DATE_PART('minute', esdp.time_from - efs.time_from))/60) as hourLate
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.employee_id = %s
                            AND es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_from - efs.time_from) < '-00:00:59') 	--опоздал 
                    """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            hour_late = df_row.hourlate

        if hour_late is None:
            hour_late = 0

        return hour_late

    @staticmethod
    def get_hour_earlier(subdivision_id, date_start, date_end, employee_id):
        hour_earlier = 0
        query = ""
        if employee_id is None:
            query = """
                        SELECT 
                            SUM((DATE_PART('hour', esdp.time_to - efs.time_to) * 60 +
                                      DATE_PART('minute', esdp.time_to - efs.time_to))/60) as hourEarlier
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_to - efs.time_to) > '00:00:59') -- ушел раньше 
                    """ % (date_start, date_end, subdivision_id)
        else:
            query = """
                        SELECT 
                            SUM((DATE_PART('hour', esdp.time_to - efs.time_to) * 60 +
                                      DATE_PART('minute', esdp.time_to - efs.time_to))/60) as hourEarlier
                        FROM public.wfm_employee_shift es
                        JOIN public.wfm_employee_shift_detail_plan esdp
                            ON esdp.shift_id = es.id  
                            AND esdp.type = 'job'
                        JOIN public.wfm_employee_fact_scan efs
                            ON efs.employee_id = es.employee_id
                            AND efs.subdivision_id = es.subdivision_id
                            AND efs.scan_date = es.shift_date
                        WHERE es.employee_id = %s
                            AND es.shift_date >= '%s' 
                            AND es.shift_date <= '%s'
                            AND es.subdivision_id = %s
                            AND ((esdp.time_to - efs.time_to) > '00:00:59') -- ушел раньше 
                    """ % (employee_id, date_start, date_end, subdivision_id)

        dataframe = DataBase.get_dataframe_by_query(query)
        for df_row in dataframe.itertuples():
            hour_earlier = df_row.hourearlier

        if hour_earlier is None:
            hour_earlier = 0

        return hour_earlier

    @staticmethod
    def get_time_tracking_for_employee(subdivision_id, date_start, date_end, employee_id):
        response_data = {}
        record_data = []
        count_plan_shift = TimeTrackingReport.get_count_plan_shift(subdivision_id, date_start, date_end, employee_id)
        count_fact_shift = TimeTrackingReport.get_count_fact_shift(subdivision_id, date_start, date_end, employee_id)
        sum_hours_plan_shift = TimeTrackingReport.get_sum_hours_plan_shift(subdivision_id, date_start, date_end,
                                                                           employee_id)
        sum_hours_fact_shift = round(TimeTrackingReport.get_sum_hours_fact_shift(subdivision_id, date_start, date_end,
                                                                                 employee_id), 2)
        equality_plan_fact = TimeTrackingReport.get_equality_plan_fact(subdivision_id, date_start, date_end,
                                                                       employee_id)
        part_off_equality_plan_fact = 0

        if count_plan_shift > 0:
            part_off_equality_plan_fact = round((equality_plan_fact * 100 / count_plan_shift), 2)

        lateness = TimeTrackingReport.get_part_off_lateness(subdivision_id, date_start, date_end, employee_id)

        part_off_lateness = 0
        if count_fact_shift:
            part_off_lateness = round((lateness * 100)/count_fact_shift, 2)

        hour_late = math.fabs(TimeTrackingReport.get_hour_late(subdivision_id, date_start, date_end, employee_id))
        hour_earlier = math.fabs(TimeTrackingReport.get_hour_earlier(subdivision_id, date_start, date_end, employee_id))
        hour_late_and_earlier = round(hour_late + hour_earlier, 2)

        record = {'count_plan_shift': count_plan_shift,
                  'count_fact_shift': count_fact_shift,
                  'equality_plan_fact': equality_plan_fact,
                  'part_off_equality_plan_fact': part_off_equality_plan_fact,
                  'part_off_lateness': part_off_lateness,
                  'sum_hours_plan_shift': sum_hours_plan_shift,
                  'sum_hours_fact_shift': sum_hours_fact_shift,
                  'hour_late_and_earlier': hour_late_and_earlier}
        record_data.append(record)

        response_data['data'] = record_data

        return JsonResponse(response_data, status=status.HTTP_200_OK)

    @staticmethod
    def get_time_tracking_for_subdivision(subdivision_id, date_start, date_end):
        response_data = {}
        record_data = []
        count_plan_shift = TimeTrackingReport.get_count_plan_shift(subdivision_id, date_start, date_end, None)
        count_fact_shift = TimeTrackingReport.get_count_fact_shift(subdivision_id, date_start, date_end, None)
        sum_hours_plan_shift = TimeTrackingReport.get_sum_hours_plan_shift(subdivision_id, date_start, date_end, None)
        sum_hours_fact_shift = round(TimeTrackingReport.get_sum_hours_fact_shift(subdivision_id, date_start, date_end,
                                                                                 None), 2)
        equality_plan_fact = TimeTrackingReport.get_equality_plan_fact(subdivision_id, date_start, date_end, None)
        part_off_equality_plan_fact = 0

        if count_plan_shift > 0:
            part_off_equality_plan_fact = round((equality_plan_fact * 100 / count_plan_shift), 2)

        lateness = TimeTrackingReport.get_part_off_lateness(subdivision_id, date_start, date_end, None)

        part_off_lateness = 0
        if count_fact_shift:
            part_off_lateness = round((lateness * 100) / count_fact_shift, 2)

        hour_late = math.fabs(TimeTrackingReport.get_hour_late(subdivision_id, date_start, date_end, None))
        hour_earlier = math.fabs(TimeTrackingReport.get_hour_earlier(subdivision_id, date_start, date_end, None))
        hour_late_and_earlier = round(hour_late + hour_earlier, 2)

        record = {'count_plan_shift': count_plan_shift,
                  'count_fact_shift': count_fact_shift,
                  'equality_plan_fact': equality_plan_fact,
                  'part_off_equality_plan_fact': part_off_equality_plan_fact,
                  'part_off_lateness': part_off_lateness,
                  'sum_hours_plan_shift': sum_hours_plan_shift,
                  'sum_hours_fact_shift': sum_hours_fact_shift,
                  'hour_late_and_earlier': hour_late_and_earlier}
        record_data.append(record)

        response_data['data'] = record_data

        return JsonResponse(response_data, status=status.HTTP_200_OK)
