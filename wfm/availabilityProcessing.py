import datetime

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from rest_framework import status

from .models import Employee_Availability_Templates


class AvailabilityProcessing:

    @staticmethod
    @transaction.atomic
    def assign_availability_template(serializer):
        employee = serializer.validated_data.get('employee')
        begin_date = serializer.validated_data.get('begin_date')

        employee_templates = Employee_Availability_Templates.objects.all()
        # удаляем шаблоны сотрудника, которые начинаются позже begin_date
        employee_templates_for_delete = employee_templates.filter(employee_id=employee.id, begin_date__gte=begin_date)
        employee_templates_for_delete.delete()
        # Корректировка даты окончания действующих шаблонов
        employee_templates_for_change = employee_templates.filter(Q(end_date__gte=begin_date) | Q(end_date__isnull=True))
        for step in employee_templates_for_change.iterator():
            step.end_date = begin_date
            step.save(update_fields=['end_date'])
        # сохраняем новый шаблон
        serializer.save()

        return JsonResponse(serializer.data)
