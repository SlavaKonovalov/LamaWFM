import datetime

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
from django.db.models.signals import post_save
from django.dispatch import receiver


class Organization(models.Model):
    name = models.CharField('Организация', max_length=60)

    class Meta:
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'

    def __str__(self):
        return self.name


class Subdivision(models.Model):
    name = models.CharField('Подразделение', max_length=60)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='subdivision_set')

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'

    def __str__(self):
        return self.name


class Department(models.Model):
    name = models.CharField('Отдел', max_length=60)
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE,
                                    verbose_name='Подразделение', related_name='department_set')

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'

    def __str__(self):
        return self.name

    def get_organization(self):
        return self.subdivision.organization.name

    get_organization.short_description = 'Организация'


class Production_Task(models.Model):
    demand_data_source_choices = (
        ('scheduler', 'Планировщик'),
        ('statistical_data', 'Статистика'),
    )
    work_scope_measure_choices = (
        ('minutes', 'Минуты'),
        ('pieces', 'Штуки'),
    )
    demand_allocation_method_choices = (
        ('soft', 'Свободное'),
        ('continuous', 'Непрерывное'),
        ('hard', 'Равномерное'),
    )

    name = models.CharField('Название', max_length=60)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='task_set')
    demand_calculate = models.BooleanField('Расчет потребности', default=False)
    demand_data_source = models.CharField('Источник данных', max_length=20,
                                          choices=demand_data_source_choices, default='scheduler')
    work_scope_measure = models.CharField('Мера объема работ', max_length=20,
                                          choices=work_scope_measure_choices, default='minutes')
    demand_allocation_method = models.CharField('Распределение', max_length=20,
                                                choices=demand_allocation_method_choices, default='soft')

    class Meta:
        verbose_name = 'Производственная задача'
        verbose_name_plural = 'Производственные задачи'

    def __str__(self):
        return self.name


class Scheduled_Production_Task(models.Model):
    repetition_type_choices = (
        ('empty', 'Не задано'),
        ('day', 'День'),
        ('week', 'Неделя'),
        ('month', 'Месяц'),
    )

    task = models.ForeignKey(Production_Task, on_delete=models.CASCADE,
                             verbose_name='Задание', related_name='scheduled_task_set')
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE,
                                    verbose_name='Подразделение', related_name='scheduled_task_set')
    begin_date = models.DateField('Дата начала')
    begin_time = models.TimeField('Время начала', default=datetime.time(7, 00))
    end_time = models.TimeField('Время окончания', default=datetime.time(18, 00))
    work_scope = models.PositiveIntegerField('Объём работ', default=0)
    repetition_type = models.CharField('Повторение', max_length=20, choices=repetition_type_choices, default='empty')
    end_date = models.DateField('Дата завершения', null=True, blank=True)
    repetition_interval = models.PositiveIntegerField('Интервал повторения', null=True, blank=True)
    exclude_holidays = models.BooleanField('Исключить праздники', default=False)
    exclude_weekdays = models.BooleanField('Исключить будни', default=False)
    exclude_weekend = models.BooleanField('Исключить выходные', default=False)
    day1_selection = models.BooleanField('пн', default=False)
    day2_selection = models.BooleanField('вт', default=False)
    day3_selection = models.BooleanField('ср', default=False)
    day4_selection = models.BooleanField('чт', default=False)
    day5_selection = models.BooleanField('пт', default=False)
    day6_selection = models.BooleanField('сб', default=False)
    day7_selection = models.BooleanField('вс', default=False)

    class Meta:
        verbose_name = 'Запланированная задача'
        verbose_name_plural = 'Запланированные задачи'

    def __str__(self):
        return str(self.pk)


class Job_Duty(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='duty_set')
    name = models.CharField('Название', max_length=60)

    class Meta:
        verbose_name = 'Функциональная обязанность'
        verbose_name_plural = 'Функциональные обязанности'

    def __str__(self):
        return self.name


class Tasks_In_Duty(models.Model):
    task = models.ForeignKey(Production_Task, on_delete=models.CASCADE,
                             verbose_name='Задание', related_name='task_in_duty_set')
    duty = models.ForeignKey(Job_Duty, on_delete=models.CASCADE,
                             verbose_name='Обязанность', related_name='task_in_duty_set')
    priority = models.PositiveIntegerField('Приоритет', default=0)

    class Meta:
        verbose_name = 'Функциональная обязанность'
        verbose_name_plural = 'Функциональные обязанности'

    def __str__(self):
        return str(self.pk)


class Employee_Position(models.Model):
    name = models.CharField('Название', max_length=60)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='employee_position_set')

    class Meta:
        verbose_name = 'Должность сотрудника'
        verbose_name_plural = 'Должности сотрудников'

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,
                                verbose_name="Пользователь", null=True, blank=True)
    middle_name = models.CharField('Отчество', max_length=30, null=True, blank=True)
    personnel_number = models.CharField('Табельный номер', max_length=30, null=True, blank=True)
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, verbose_name='Подразделение',
                                    related_name='employee_set', null=True, blank=True)
    position = models.ForeignKey(Employee_Position, on_delete=models.CASCADE, verbose_name='Должность',
                                 related_name='employee_position_set', null=True, blank=True)
    duties = models.ManyToManyField(Job_Duty, null=True, blank=True)
    part_time_job_org = models.ManyToManyField(Organization, null=True, blank=True)

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

    def __str__(self):
        return str(self.pk)

    def get_duties(self):
        return ", ".join([duty.name for duty in self.duties.all()])

    get_duties.short_description = 'Обязанности'

    def get_part_job_org(self):
        return ", ".join([part_job_org.name for part_job_org in self.part_time_job_org.all()])

    get_part_job_org.short_description = 'Организации (подработка)'


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Employee.objects.create(user=instance)
    else:
        instance.employee.save()


class Business_Indicator(models.Model):
    name = models.CharField('Название', max_length=60)

    class Meta:
        verbose_name = 'Показатель бизнеса'
        verbose_name_plural = 'Показатели бизнеса'

    def __str__(self):
        return self.name
