from django.db import transaction

from .models import Scheduled_Production_Task, Appointed_Production_Task


class TaskProcessing:

    @staticmethod
    @transaction.atomic
    def assign_tasks(subdivision):
        # Appointed_Production_Task.objects.filter(scheduled_task__subdivision_id=subdivision.pk,
        #                                          date__gte=1).select_related('scheduled_task').delete()

        tasks = Scheduled_Production_Task.objects.filter(subdivision_id=subdivision.pk)
