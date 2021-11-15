from django.db import transaction

from .models import Part_Time_Job_Vacancy


class PartTimeJobProcessing:

    @staticmethod
    def update_vacancy_check(serializer):
        errors = []
        vacancy = Part_Time_Job_Vacancy()
        vacancy_id = serializer.validated_data.get('id')
        vacancy_status_choices = Part_Time_Job_Vacancy.vacancy_status_choices
        if vacancy_id:
            vacancy = Part_Time_Job_Vacancy.objects.get(pk=vacancy_id)
        status = serializer.validated_data.get('status')
        if status == Part_Time_Job_Vacancy.vacancy_status_choices.created:
            if vacancy:
                if vacancy.vacancy_status != 1:
                    return errors
            else:
                return errors
        return True

    """
    @staticmethod
    def update_vacancy(serializer):
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
    """
