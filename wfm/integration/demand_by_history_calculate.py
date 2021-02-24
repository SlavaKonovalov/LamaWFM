from ..models import Subdivision, Predictable_Production_Task, Production_Task_Business_Indicator, \
    Predicted_Production_Task, Business_Indicator_Norm
from ..db import DataBase
from decimal import *
from datetime import timedelta


class DemandByHistoryDataCalculate:

    def __init__(self, subdivision_id, from_date, to_date):
        self.subdivision_id = subdivision_id
        self.from_date = from_date
        self.to_date = to_date

    def run(self):
        try:
            subdivision = Subdivision.objects.get(id=self.subdivision_id)
        except Subdivision.DoesNotExist:
            return "Subdivision with id " + str(self.subdivision_id) + " not found in DB "

        predictable_Production_Tasks = Predictable_Production_Task.objects.filter(subdivision_id=subdivision.pk)

        for predictable_Production_Task in predictable_Production_Tasks:
            production_Task_Business_Indicators = Production_Task_Business_Indicator.objects.filter(
                task_id=predictable_Production_Task.task)

            for production_Task_Business_Indicator in production_Task_Business_Indicators:
                self.calculate_predicted_production_task(production_Task_Business_Indicator.business_indicator,
                                                         predictable_Production_Task)

        return "Demand data by subdivision: " + subdivision.name + " success calculated !"

    def calculate_predicted_production_task(self, business_indicator, predictable_production_task):

        try:
            business_Indicator_Norm = Business_Indicator_Norm.objects.get(business_indicator_id=business_indicator.pk)
        except Business_Indicator_Norm.DoesNotExist:
            return "Norm on business indicator with id " + str(business_indicator.pk) + " not found in DB "

        self.clear_predicted_production_task(predictable_production_task.pk, business_indicator.pk)

        query = "SELECT " \
                "begin_date_time, " \
                "CAST(date_part('isodow',begin_date_time) AS INT) AS dayofweek, " \
                "begin_date_time::time AS begin_time, " \
                "CAST((EXTRACT(HOUR FROM begin_date_time) * 3600 + EXTRACT(MIN FROM begin_date_time) * 60 + EXTRACT(SECOND FROM begin_date_time))AS INT)  AS begin_time_in_sec," \
                "CAST(indicator_value AS DECIMAL(32,16)) AS indicator_value, " \
                "time_interval_length, " \
                "business_indicator_id, " \
                "subdivision_id " \
                "FROM public.wfm_business_indicator_data " \
                "WHERE subdivision_id = " + str(self.subdivision_id) + " AND business_indicator_id = " + str(business_indicator.pk)

        df = DataBase.get_dataframe_by_query(query)
        if not df.empty:
            avg_by_dayofweek = df.groupby(['dayofweek', 'begin_time_in_sec'])['indicator_value'].mean().reset_index()

            cur_date = self.from_date
            while cur_date < self.to_date:
                cur_date = cur_date + timedelta(minutes=15)
                utcoffset_in_sec = cur_date.utcoffset().seconds
                time_in_sec = cur_date.hour * 3600 + cur_date.minute * 60 + cur_date.second + utcoffset_in_sec
                weekday = cur_date.isoweekday()
                avg_by_dayofweek_row = avg_by_dayofweek.loc[(avg_by_dayofweek['dayofweek'] == weekday)
                                                            & (avg_by_dayofweek['begin_time_in_sec'] == time_in_sec)]
                if not avg_by_dayofweek_row.empty:
                    indicator_value = round(Decimal(list(avg_by_dayofweek_row['indicator_value'])[0]), 2)

                    predicted_Production_Task = Predicted_Production_Task()
                    predicted_Production_Task.begin_date_time = cur_date
                    predicted_Production_Task.predictable_task = predictable_production_task
                    predicted_Production_Task.business_indicator = business_indicator
                    predicted_Production_Task.work_scope_time = int(
                        (indicator_value * business_Indicator_Norm.norm_value) / 60)
                    predicted_Production_Task.save()

    def clear_predicted_production_task(self, predictable_task_id, business_indicator_id):
        Predicted_Production_Task.objects.filter(predictable_task_id=predictable_task_id,
                                                 business_indicator_id=business_indicator_id,
                                                 begin_date_time__gte=self.from_date,
                                                 begin_date_time__lte=self.to_date).delete()
