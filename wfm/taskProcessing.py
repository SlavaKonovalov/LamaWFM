from django.db import transaction
from django.db.models import Q
from .models import Scheduled_Production_Task, Appointed_Production_Task, Global_Parameters
from .additionalFunctions import Global
import datetime as datetime


class TaskProcessing:

    @staticmethod
    @transaction.atomic
    def assign_tasks(subdivision_id, scheduled_task_id=None):
        interval_length = Global_Parameters.objects.all().first().scheduling_period
        date_begin = Global.get_current_midnight(datetime.datetime.now() + datetime.timedelta(days=1))
        date_end = date_begin + datetime.timedelta(days=interval_length)
        # удаляем всё, начиная с date_begin
        appointed_task = Appointed_Production_Task.objects.all()
        if scheduled_task_id:
            appointed_task = appointed_task.filter(scheduled_task_id=scheduled_task_id)
        else:
            appointed_task = appointed_task.filter(scheduled_task__subdivision_id=subdivision_id)\
                .select_related('scheduled_task')
        appointed_task.filter(date__gte=date_begin).delete()
        # Фильтруем запланированные задачи
        tasks = Scheduled_Production_Task.objects.all().select_related('task')
        if scheduled_task_id:
            tasks = tasks.filter(id=scheduled_task_id)
        else:
            tasks = tasks.filter(subdivision_id=subdivision_id)
        tasks = tasks.filter(Q(end_date__isnull=True) | Q(end_date__gte=date_begin))\
            .filter(task__demand_calculate=True)\
            .exclude(task__demand_data_source='statistical_data')
        for task in tasks.iterator():
            date_step = datetime.timedelta(days=1)
            begin_date_task = Global.get_current_midnight(task.begin_date)
            end_date_task = date_end if task.end_date is None else Global.get_current_midnight(task.end_date)
            # проверка задачи без повторения
            if task.repetition_type == 'empty':
                if begin_date_task < date_begin:
                    continue
                if begin_date_task <= date_end:
                    Appointed_Production_Task.create_instance(task.id, begin_date_task, task.work_scope_normalize())
            if task.repetition_type == 'day':
                date_iterator = max(begin_date_task, date_begin)
                date_border = min(end_date_task, date_end)
                while date_iterator <= date_border:
                    date_delta = (date_iterator - begin_date_task).days
                    if task.repetition_interval > 1:
                        # смотрим повторение
                        remainder = date_delta % task.repetition_interval
                        if remainder:
                            date_iterator += date_step
                            continue
                        elif date_step.days != task.repetition_interval:
                            date_step = datetime.timedelta(days=task.repetition_interval)
                    Appointed_Production_Task.create_instance(task.id, date_iterator, task.work_scope_normalize())
                    date_iterator += date_step
            if task.repetition_type == 'week':
                week_series = task.get_week_series()
                week_series_checked = week_series[week_series == True]
                if week_series_checked.size == 0:
                    # не проставлены дни недели
                    continue
                date_iterator = max(begin_date_task, date_begin)
                date_border = min(end_date_task, date_end)
                while date_iterator <= date_border:
                    week_delta = Global.get_week_delta(begin_date_task, date_iterator)
                    if task.repetition_interval > 1:
                        # смотрим повторение
                        remainder = week_delta % task.repetition_interval
                        if remainder:
                            # прыжок на следующий понедельник
                            date_iterator += datetime.timedelta(days=(7 - date_iterator.weekday()))
                            continue
                    dayOfWeek = date_iterator.weekday()
                    if week_series[dayOfWeek]:
                        Appointed_Production_Task.create_instance(task.id, date_iterator, task.work_scope_normalize())
                    date_iterator += date_step
