from django.db.models import Q
from ..models import Subdivision, Predictable_Production_Task, Production_Task_Business_Indicator, \
    Predicted_Production_Task, Business_Indicator_Norm, Holiday_Period_For_Calc
from ..db import DataBase
from ..additionalFunctions import Global
from decimal import Decimal
from datetime import timedelta


class DemandByHistoryDataCalculate:

    def __init__(self, subdivision_id, from_date, to_date):
        self.subdivision_id = subdivision_id
        self.from_date = from_date
        self.to_date = to_date + timedelta(1,-1)
        self.history_from_date = self.from_date
        self.history_to_date = self.to_date

    def find_history_from_date(self, start_date, history_period):
        i = 0
        cur_date = start_date + timedelta(-1,1)
        while(i < history_period):
            holiday_period_for_calc = Holiday_Period_For_Calc.objects.filter(Q(begin_date_time__lte=cur_date)&Q(end_date_time__gte=cur_date))
            if not holiday_period_for_calc:
                i += 1
            cur_date -= timedelta(1)
        return cur_date

    def run(self):
        try:
            subdivision = Subdivision.objects.get(id=self.subdivision_id)
        except Subdivision.DoesNotExist:
            return "Subdivision with id " + str(self.subdivision_id) + " not found in DB "

        predictable_production_tasks = Predictable_Production_Task.objects.select_related('task').select_related('subdivision').filter(subdivision_id=subdivision.pk)

        for predictable_production_task in predictable_production_tasks:
            production_task_business_indicators = Production_Task_Business_Indicator.objects.filter(
                task_id=predictable_production_task.task)

            for production_Task_Business_Indicator in production_task_business_indicators:
                if production_Task_Business_Indicator.business_indicator.external_code != 'inventory':
                    continue
                self.calculate_predicted_production_task(production_Task_Business_Indicator.business_indicator,
                                                         predictable_production_task)

    def calculate_predicted_production_task(self, business_indicator, predictable_production_task):
        try:
            business_indicator_norm = Business_Indicator_Norm.objects.get(business_indicator_id=business_indicator.pk)
        except Business_Indicator_Norm.DoesNotExist:
            return "Norm on business indicator with id " + str(business_indicator.pk) + " not found in DB "

        if not business_indicator.is_calculated:
            self.history_to_date = self.from_date - timedelta(0, 1)
            self.history_from_date = self.find_history_from_date(self.history_to_date, business_indicator.history_period) + timedelta(1, 0)

        self.clear_predicted_production_task(predictable_production_task.pk, business_indicator.pk)

        query = "SELECT " \
                "begin_date_time::TIMESTAMP AS begin_date_time, " \
                "CAST(date_part('isodow',begin_date_time) AS INT) AS dayofweek, " \
                "begin_date_time::time AS begin_time, " \
                "CAST((EXTRACT(HOUR FROM begin_date_time) * 3600 + EXTRACT(MIN FROM begin_date_time) * 60 " \
                "+ EXTRACT(SECOND FROM begin_date_time))AS INT)  AS begin_time_in_sec," \
                "CAST(indicator_value AS DECIMAL(32,16)) AS indicator_value, " \
                "time_interval_length, " \
                "business_indicator_id, " \
                "subdivision_id " \
                "FROM public.wfm_business_indicator_data " \
                "WHERE subdivision_id = " + str(self.subdivision_id) \
                + " AND business_indicator_id = " + str(business_indicator.pk) \
                + " AND begin_date_time >= '" + (str(self.from_date) if business_indicator.is_calculated else str(self.history_from_date)) + "'" \
                + " AND begin_date_time <= '" + (str(self.to_date) if business_indicator.is_calculated else str(self.history_to_date)) + "'" \
                + " AND holiday_period_for_calc_id is NULL"

        df = DataBase.get_dataframe_by_query(query)
        if not df.empty:
            if not business_indicator.is_calculated:
                avg_by_dayofweek = df.groupby(['dayofweek', 'begin_time_in_sec'])['indicator_value'].median().reset_index()
                cur_date = self.from_date
                while cur_date <= self.to_date:
                    time_in_sec = cur_date.hour * 3600 + cur_date.minute * 60 + cur_date.second
                    weekday = cur_date.isoweekday()
                    avg_by_dayofweek_row = avg_by_dayofweek.loc[(avg_by_dayofweek['dayofweek'] == weekday)
                                                                & (avg_by_dayofweek['begin_time_in_sec'] == time_in_sec)]
                    if not avg_by_dayofweek_row.empty:
                        indicator_value = round(Decimal(list(avg_by_dayofweek_row['indicator_value'])[0]), 2)
                        self.create_predicted_production_task(business_indicator, predictable_production_task,
                                                              business_indicator_norm, cur_date, indicator_value)
                    cur_date = cur_date + timedelta(minutes=business_indicator.interval_for_calculation)
            else:
                cur_date = self.from_date
                while cur_date <= self.to_date:
                    row_by_date = df.loc[df['begin_date_time'] == cur_date]
                    if not row_by_date.empty:
                        indicator_value = round(Decimal(list(row_by_date['indicator_value'])[0]), 2)
                        self.create_predicted_production_task(business_indicator, predictable_production_task,
                                                              business_indicator_norm, cur_date, indicator_value)
                    cur_date = cur_date + timedelta(minutes=business_indicator.interval_for_calculation)

    def create_predicted_production_task(self, business_indicator, predictable_production_task, business_indicator_norm, cur_date, indicator_value):
        predicted_production_task = Predicted_Production_Task()
        predicted_production_task.begin_date_time = cur_date
        predicted_production_task.predictable_task = predictable_production_task
        predicted_production_task.business_indicator = business_indicator
        work_scope_time = (indicator_value * business_indicator_norm.norm_value) / 60
        work_scope_time = work_scope_time * predictable_production_task.subdivision.retail_store_format.queue_coefficient \
            if business_indicator.use_queue_coefficient \
            else work_scope_time
        if predictable_production_task.task.use_area_coefficient:
            work_scope_time = Global.round_math(predictable_production_task.subdivision.area_coefficient * work_scope_time)
        predicted_production_task.work_scope_time = work_scope_time if work_scope_time else 1
        predicted_production_task.save()

    def clear_predicted_production_task(self, predictable_task_id, business_indicator_id):
        Predicted_Production_Task.objects.filter(predictable_task_id=predictable_task_id,
                                                 business_indicator_id=business_indicator_id,
                                                 begin_date_time__gte=self.from_date,
                                                 begin_date_time__lte=self.to_date).delete()
