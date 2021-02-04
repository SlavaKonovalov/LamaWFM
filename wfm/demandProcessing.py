from django.db.models import Sum, Subquery, OuterRef, FloatField, F
from django.db.models.functions import Round
from django.utils import timezone

from .additionalFunctions import AdditionalFunctionsWFM
from .models import Scheduled_Production_Task, Demand_Detail_Parameters, Demand_Detail_Main, Demand_Detail_Task
import datetime as datetime


class DemandProcessing:

    @staticmethod
    def recalculate_demand_on_date(subdivision, process_date):
        work_scope_for_interval = 0
        tasks = Scheduled_Production_Task.objects.filter(subdivision_id=subdivision.pk).order_by('begin_time')
        interval_length = Demand_Detail_Parameters.objects.all().first().time_interval_length
        duration = datetime.timedelta(minutes=interval_length)
        for task in tasks:
            counter = datetime.timedelta(minutes=0)
            work_scope_for_interval = task.work_scope * interval_length / task.task_duration()
            begin_date_time = AdditionalFunctionsWFM.add_timezone(task.begin_time)
            end_time = AdditionalFunctionsWFM.add_timezone(task.end_time).time()
            while (begin_date_time + counter).time() < end_time:
                date_time_value = (begin_date_time + counter).replace(year=process_date.year,
                                                                      month=process_date.month,
                                                                      day=process_date.day,
                                                                      )
                demand_detail_main, created_main = Demand_Detail_Main.objects.get_or_create(
                    subdivision_id=task.subdivision_id,
                    date_time_value=date_time_value,
                    defaults={'rounded_value': 0}
                )
                if demand_detail_main is not None:
                    demand_detail_task, created_task = Demand_Detail_Task.objects.update_or_create(
                        demand_detail_main_id=demand_detail_main.id,
                        task_id=task.task.id,
                        defaults={'demand_value': AdditionalFunctionsWFM.toFixed(work_scope_for_interval, 2)}
                    )
                counter += duration

        # собираем сумму потребностей по каждому экземпляру main и округляем, сразу обновляем rounded_value:
        Demand_Detail_Main.objects.update(
            rounded_value=Subquery(
                Demand_Detail_Main.objects.filter(id=OuterRef('id')).annotate(
                    demand_sum=Round(Sum('demand_detail_task_set__demand_value'))
                ).values('demand_sum')[:1]
            )
        )
