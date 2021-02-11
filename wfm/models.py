from django.db import models
from django.contrib.auth.models import User
from pandas import Series

from .additionalFunctions import Global


class Company(models.Model):
    name = models.CharField('Юр. лицо', max_length=60)

    class Meta:
        verbose_name = 'Юр. лицо'
        verbose_name_plural = 'Юр. лица'

        ordering = ['name']

    def __str__(self):
        return self.name


class Organization(models.Model):
    name = models.CharField('Организация', max_length=60)

    class Meta:
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'

        ordering = ['name']

    def __str__(self):
        return self.name


class Subdivision(models.Model):
    name = models.CharField('Подразделение', max_length=60)
    external_code = models.CharField('Внешний код', max_length=20, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='subdivision_set')

    companies = models.ManyToManyField(Company, verbose_name='Юр. лица', null=True, blank=True)

    class Meta:
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'

        ordering = ['organization', 'name']

    def __str__(self):
        return self.name

    def get_companies(self):
        return ", ".join([company.name for company in self.companies.all()])

    get_companies.short_description = 'Юр. лица'


class Department(models.Model):
    name = models.CharField('Отдел', max_length=60)
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE,
                                    verbose_name='Подразделение', related_name='department_set')

    class Meta:
        verbose_name = 'Отдел'
        verbose_name_plural = 'Отделы'

        ordering = ['subdivision', 'name']

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

        ordering = ['organization', 'name']

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
    begin_date = models.DateTimeField('Дата начала', null=True, blank=True)
    begin_time = models.DateTimeField('Время начала', null=True, blank=True)
    end_time = models.DateTimeField('Время окончания', null=True, blank=True)
    work_scope = models.PositiveIntegerField('Объём работ', default=0)
    repetition_type = models.CharField('Повторение', max_length=20, choices=repetition_type_choices, default='empty')
    end_date = models.DateTimeField('Дата завершения', null=True, blank=True)
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

        ordering = ['subdivision', 'task', 'begin_time']

    def __str__(self):
        return str(self.pk)

    def begin_date_format(self):
        if self.begin_date is not None:
            begin_date = Global.add_timezone(self.begin_date)
            return begin_date.strftime('%d.%m.%Y')
        return self.begin_date

    def begin_time_format(self):
        if self.begin_time is not None:
            begin_time = Global.add_timezone(self.begin_time)
            return begin_time.strftime('%H:%M')
        return self.begin_time

    def end_date_format(self):
        if self.end_date is not None:
            end_date = Global.add_timezone(self.end_date)
            return end_date.strftime('%d.%m.%Y')
        return self.end_date

    def end_time_format(self):
        if self.end_time is not None:
            end_time = Global.add_timezone(self.end_time)
            return end_time.strftime('%H:%M')
        return self.end_time

    begin_date_format.short_description = 'Дата начала'
    begin_time_format.short_description = 'Время начала'
    end_date_format.short_description = 'Дата завершения'
    end_time_format.short_description = 'Время окончания'

    def get_task_duration(self):
        end_time = Global.add_timezone(self.end_time)
        begin_time = Global.add_timezone(self.begin_time)
        return (end_time.hour * 60 + end_time.minute) - (begin_time.hour * 60 + begin_time.minute)

    def work_scope_normalize(self):
        # здесь будет вызов нормализации
        return self.work_scope

    def get_week_series(self):
        return Series([self.day1_selection,
                       self.day2_selection,
                       self.day3_selection,
                       self.day4_selection,
                       self.day5_selection,
                       self.day6_selection,
                       self.day7_selection])


class Appointed_Production_Task(models.Model):
    scheduled_task = models.ForeignKey(Scheduled_Production_Task, on_delete=models.CASCADE,
                                       verbose_name='Запланированное задание', related_name='appointed_task_set')
    date = models.DateTimeField('Дата выполнения')
    work_scope_time = models.PositiveIntegerField('Объём работ (минуты)')

    class Meta:
        verbose_name = 'Назначенное задание'
        verbose_name_plural = 'Назначенные задания'

        ordering = ['date', 'scheduled_task']

    @staticmethod
    def create_instance(scheduled_task_id, date, work_scope):
        return Appointed_Production_Task.objects.create(
            scheduled_task_id=scheduled_task_id,
            date=date,
            work_scope_time=work_scope
        )


class Job_Duty(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='duty_set')
    name = models.CharField('Название', max_length=60)

    class Meta:
        verbose_name = 'Функциональная обязанность'
        verbose_name_plural = 'Функциональные обязанности'

        ordering = ['organization', 'name']

    def __str__(self):
        return self.name

    def get_tasks(self):
        return " | ".join([tasks_in_duty.task.name for tasks_in_duty
                           in self.task_in_duty_set.all().select_related('task')])


class Tasks_In_Duty(models.Model):
    task = models.ForeignKey(Production_Task, on_delete=models.CASCADE,
                             verbose_name='Задание', related_name='task_in_duty_set')
    duty = models.ForeignKey(Job_Duty, on_delete=models.CASCADE,
                             verbose_name='Обязанность', related_name='task_in_duty_set')
    priority = models.PositiveIntegerField('Приоритет', default=0)

    class Meta:
        verbose_name = 'Функциональная обязанность. Настройка'
        verbose_name_plural = 'Функциональные обязанности. Настройка'

        ordering = ['duty', 'task', 'priority']

    def __str__(self):
        return str(self.pk)


class Employee_Position(models.Model):
    name = models.CharField('Название', max_length=60)
    short_name = models.CharField('Краткое название', max_length=20, unique=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='employee_position_set')

    class Meta:
        verbose_name = 'Должность сотрудника'
        verbose_name_plural = 'Должности сотрудников'

        ordering = ['organization', 'name']

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
    duties = models.ManyToManyField(Job_Duty, verbose_name='Обязанности', null=True, blank=True)
    part_time_job_org = models.ManyToManyField(Company, verbose_name='Юр. лица (подработка)',
                                               null=True, blank=True)

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

        ordering = ['subdivision', 'user']

    def __str__(self):
        return str(self.pk)

    def get_duties(self):
        return ", ".join([duty.name for duty in self.duties.all()])

    get_duties.short_description = 'Обязанности'

    def get_part_job_org(self):
        return ", ".join([part_job_org.name for part_job_org in self.part_time_job_org.all()])

    get_part_job_org.short_description = 'Юр. лица (подработка)'


class Business_Indicator(models.Model):
    name = models.CharField('Название', max_length=60)

    class Meta:
        verbose_name = 'Показатель бизнеса'
        verbose_name_plural = 'Показатели бизнеса'

    def __str__(self):
        return self.name


class Demand_Detail_Main(models.Model):
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, verbose_name='Подразделение',
                                    related_name='demand_detail_set')
    date_time_value = models.DateTimeField()
    rounded_value = models.DecimalField(max_digits=32, decimal_places=16, verbose_name='Значение потребности')

    class Meta:
        verbose_name = 'Потребность'
        verbose_name_plural = 'Потребность'


class Demand_Detail_Task(models.Model):
    demand_detail_main = models.ForeignKey(Demand_Detail_Main, on_delete=models.CASCADE,
                                           related_name='demand_detail_task_set')
    task = models.ForeignKey(Production_Task, on_delete=models.SET_NULL, null=True)
    demand_value = models.DecimalField(max_digits=32, decimal_places=16, verbose_name='Значение потребности')


class Global_Parameters(models.Model):
    demand_detail_interval_length = models.PositiveIntegerField('Длина периода детализации потребности', default=0)
    scheduling_period = models.PositiveIntegerField('Длина периода для построения графика запланированных задач',
                                                    default=0)
