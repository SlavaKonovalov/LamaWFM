from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from pandas import Series
from django_pandas.managers import DataFrameManager
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


class Retail_Store_Format(models.Model):
    name = models.CharField('Название', max_length=60)

    class Meta:
        verbose_name = 'Формат магазина'
        verbose_name_plural = 'Форматы магазина'

        ordering = ['name']

    def __str__(self):
        return self.name


class Subdivision(models.Model):
    name = models.CharField('Подразделение', max_length=60)
    external_code = models.CharField('Внешний код', max_length=20, null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE,
                                     verbose_name='Организация', related_name='subdivision_set')
    retail_store_format = models.ForeignKey(Retail_Store_Format, on_delete=models.SET_NULL, null=True, blank=True,
                                            verbose_name='Формат магазина', related_name='subdivision_set')
    shop_open_time = models.TimeField('Время открытия магазина', null=True, blank=True)
    shop_close_time = models.TimeField('Время закрытия магазина', null=True, blank=True)
    area_coefficient = models.DecimalField(max_digits=32, decimal_places=16, verbose_name='Коэффициент площади')

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
        ('1_soft', 'Свободное'),
        ('2_continuous', 'Непрерывное'),
        ('0_hard', 'Равномерное'),
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
    use_area_coefficient = models.BooleanField('Использовать коэффициент площади', default=False)
    pieces_to_minutes_coefficient = models.DecimalField(max_digits=32, decimal_places=16,
                                                        verbose_name='Коэффициент перевода штук в минуты',
                                                        validators=[MinValueValidator(Decimal('0.0000000000000001'))],
                                                        default=1)

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
        work_scope = self.work_scope
        if self.task.work_scope_measure == 'pieces':
            work_scope = self.task.pieces_to_minutes_coefficient * work_scope
        if self.task.use_area_coefficient:
            work_scope = self.subdivision.area_coefficient * work_scope
        return work_scope

    def get_week_series(self):
        return Series([self.day1_selection,
                       self.day2_selection,
                       self.day3_selection,
                       self.day4_selection,
                       self.day5_selection,
                       self.day6_selection,
                       self.day7_selection])


class Predictable_Production_Task(models.Model):
    task = models.ForeignKey(Production_Task, on_delete=models.CASCADE,
                             verbose_name='Задание')
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE,
                                    verbose_name='Подразделение')

    class Meta:
        verbose_name = 'Прогнозируемые задача'
        verbose_name_plural = 'Прогнозируемые задачи'

    def __str__(self):
        return str(self.pk)


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
    subdivision = models.ForeignKey(Subdivision, on_delete=models.PROTECT, verbose_name='Подразделение',
                                    related_name='employee_set', null=True, blank=True)
    position = models.ForeignKey(Employee_Position, on_delete=models.PROTECT, verbose_name='Должность',
                                 related_name='employee_position_set', null=True, blank=True)
    duties = models.ManyToManyField(Job_Duty, verbose_name='Обязанности', null=True, blank=True)
    part_time_job_org = models.ManyToManyField(Company, verbose_name='Юр. лица (подработка)',
                                               null=True, blank=True)
    pf_reg_id = models.CharField('СНИЛС', max_length=14, null=False, blank=False, unique=True)

    objects = DataFrameManager()

    class Meta:
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

        ordering = ['subdivision', 'user']

    def __str__(self):
        return str(self.user.first_name + ' ' + self.user.last_name + ' (' + self.user.username + ')')

    def get_duties(self):
        return ", ".join([duty.name for duty in self.duties.all()])

    get_duties.short_description = 'Обязанности'

    def get_part_job_org(self):
        return ", ".join([part_job_org.name for part_job_org in self.part_time_job_org.all()])

    get_part_job_org.short_description = 'Юр. лица (подработка)'


class Business_Indicator(models.Model):
    interval_for_calculation = (
        (15, '15 минут'),
        (1440, '1 день'),
    )

    name = models.CharField('Название', max_length=60)
    external_code = models.CharField('Внешний код', max_length=20, null=True, blank=True)
    interval_for_calculation = models.PositiveIntegerField(choices=interval_for_calculation,
                                                           verbose_name='Интервал времени для расчёта')

    class Meta:
        verbose_name = 'Показатель бизнеса'
        verbose_name_plural = 'Показатели бизнеса'

    def __str__(self):
        return self.name


class Business_Indicator_Norm(models.Model):
    business_indicator = models.ForeignKey(Business_Indicator, on_delete=models.CASCADE,
                                           verbose_name='Бизнес показатель')

    norm_value = models.DecimalField(max_digits=32, decimal_places=16, verbose_name='Значение норматива (в секундах)')

    class Meta:
        verbose_name = 'Норматив по показателям бизнеса'
        verbose_name_plural = 'Нормативы по показателям бизнеса'


class Holiday(models.Model):
    name = models.CharField('Праздник', max_length=60)

    class Meta:
        verbose_name = 'Праздник'
        verbose_name_plural = 'Праздники'

        ordering = ['name']

    def __str__(self):
        return self.name


class Holiday_Period(models.Model):
    holiday = models.ForeignKey(Holiday, on_delete=models.CASCADE,
                                verbose_name='Праздник', related_name='holiday_period_set')
    begin_date_time = models.DateTimeField('Дата начала')
    end_date_time = models.DateTimeField('Дата окончания')
    begin_date_time_for_calc = models.DateTimeField('Дата начала для расчётов')
    end_date_time_for_calc = models.DateTimeField('Дата окончания для расчётов')

    class Meta:
        verbose_name = 'Период праздника'
        verbose_name_plural = 'Периоды праздников'

        ordering = ['holiday', 'begin_date_time']

    def __str__(self):
        return str(self.holiday)

#class Increasing_sales_Ratio


class Business_Indicator_Data(models.Model):
    time_interval_length_choices = (
        (15, '15 минут'),
        (30, '30 минут'),
        (60, '1 Час'),
    )
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE,
                                    verbose_name='Подразделение')
    business_indicator = models.ForeignKey(Business_Indicator, on_delete=models.CASCADE,
                                           verbose_name='Показатель бизнеса')
    begin_date_time = models.DateTimeField(verbose_name='Дата и время начала временного интервала')
    indicator_value = models.DecimalField(max_digits=32, decimal_places=16, verbose_name='Значение показателя бизнеса')
    time_interval_length = models.PositiveIntegerField(choices=time_interval_length_choices,
                                                       verbose_name='Длинна временного интервала')
    holiday_period = models.ForeignKey(Holiday_Period, on_delete=models.SET_NULL,
                                       verbose_name='Праздник', null=True, blank=True)

    def __str__(self):
        return 'Подразделение:' + self.subdivision.name \
               + ' Показатель: ' + self.business_indicator.name \
               + ' Дата и аремя начала интервала: ' + self.begin_date_time.__str__() \
               + ' Длина интервала ' + self.time_interval_length.__str__() \
               + ' Значение: ' + self.indicator_value.__str__()


class Demand_Detail_Main(models.Model):
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, verbose_name='Подразделение',
                                    related_name='demand_detail_set')
    date_time_value = models.DateTimeField()
    rounded_value = models.DecimalField(max_digits=32, decimal_places=16, verbose_name='Значение потребности')

    objects = DataFrameManager()

    class Meta:
        verbose_name = 'Потребность'
        verbose_name_plural = 'Потребность'
        unique_together = ('subdivision', 'date_time_value')


class Demand_Detail_Task(models.Model):
    demand_detail_main = models.ForeignKey(Demand_Detail_Main, on_delete=models.CASCADE,
                                           related_name='demand_detail_task_set')
    task = models.ForeignKey(Production_Task, on_delete=models.SET_NULL, null=True)
    demand_value = models.DecimalField(max_digits=32, decimal_places=16, verbose_name='Значение потребности')


class Global_Parameters(models.Model):
    demand_detail_interval_length = models.PositiveIntegerField('Длина периода детализации потребности', default=0)
    scheduling_period = models.PositiveIntegerField('Длина периода для построения графика запланированных задач',
                                                    default=0)


class Production_Task_Business_Indicator(models.Model):
    task = models.ForeignKey(Production_Task, on_delete=models.CASCADE,
                             verbose_name='Задание')
    business_indicator = models.ForeignKey(Business_Indicator, on_delete=models.CASCADE,
                                           verbose_name='Показатель бизнеса')

    class Meta:
        verbose_name = 'Показатели для расчёта производственной задачи'
        verbose_name_plural = 'Показатели для расчёта производственной задачи'


class Predicted_Production_Task(models.Model):
    predictable_task = models.ForeignKey(Predictable_Production_Task, on_delete=models.CASCADE,
                                         verbose_name='Прогнозируемое задание', related_name='predicted_task_set')
    business_indicator = models.ForeignKey(Business_Indicator, on_delete=models.CASCADE,
                                           verbose_name='Показатель бизнеса')
    begin_date_time = models.DateTimeField('Дата и время выполнения')
    work_scope_time = models.PositiveIntegerField('Объём работ (минуты)')

    class Meta:
        verbose_name = 'Спрогнозированное задание'
        verbose_name_plural = 'Спрогнозированное задания'

        ordering = ['predictable_task', 'begin_date_time']

class Availability_Template(models.Model):
    type_choices = (
        ('week', 'Неделя'),
        ('day', 'День')
    )
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, verbose_name='Подразделение',
                                    related_name='availability_template_set', null=True, blank=True)
    name = models.CharField('Название', max_length=60)
    type = models.CharField('Распределение', max_length=20,
                            choices=type_choices, default='week')

    class Meta:
        verbose_name = 'Шаблон доступности'
        verbose_name_plural = 'Шаблоны доступности'
        unique_together = ('subdivision', 'name')


class Availability_Template_Data(models.Model):
    template = models.ForeignKey(Availability_Template, on_delete=models.CASCADE,
                                 verbose_name='Шаблон', related_name='data_set')
    week_num = models.PositiveIntegerField('Номер недели', default=0)
    week_day = models.PositiveIntegerField('День недели', default=0)
    begin_time = models.TimeField('Время начала')
    end_time = models.TimeField('Время окончания')

    objects = DataFrameManager()

    class Meta:
        verbose_name = 'Строки шаблона доступности'
        verbose_name_plural = 'Строки шаблона доступности'


class Employee_Availability_Templates(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='Сотрудник',
                                 related_name='availability_template_set')
    template = models.ForeignKey(Availability_Template, on_delete=models.CASCADE, verbose_name='Шаблон',
                                 related_name='availability_template_set')
    week_num_appointed = models.PositiveIntegerField('Номер выбранной недели из шаблона', default=0)
    begin_date = models.DateTimeField('Дата начала')
    end_date = models.DateTimeField('Дата окончания', null=True, blank=True)

    class Meta:
        verbose_name = 'Назначенный шаблон доступности'
        verbose_name_plural = 'Назначенные шаблоны доступности'


class Employee_Availability(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='Сотрудник',
                                 related_name='availability_set', null=True, blank=True)
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, verbose_name='Подразделение',
                                    related_name='availability_set')
    begin_date_time = models.DateTimeField('Дата/время начала')
    end_date_time = models.DateTimeField('Дата/время окончания')

    class Meta:
        verbose_name = 'Назначенная доступность сотрудника'
        verbose_name_plural = 'Назначенная доступность сотрудников'


class Work_Shift_Planning_Rule(models.Model):
    time_between_shift = models.PositiveIntegerField('Минимальное время между сменами, ч.', default=0)
    continuous_weekly_rest = models.PositiveIntegerField('Еженедельный непрерывный отдых, ч.', default=0)

    class Meta:
        verbose_name = 'Справочник правил планирования смен'
        verbose_name_plural = 'Справочник правил планирования смен'


class Breaking_Rule(models.Model):
    name = models.CharField('Название', max_length=60, default='')
    break_first = models.PositiveIntegerField('Продолжительность первого перерыва, мин.', default=0)
    break_second = models.PositiveIntegerField('Продолжительность второго перерыва, мин.', default=0)
    first_break_starting_after_going = models.PositiveIntegerField('Время от начала смены до первого перерыва, мин.',
                                                                   default=0)
    time_between_breaks = models.PositiveIntegerField('Время между перерывами, мин.', default=0)
    second_break_starting_before_end = models.PositiveIntegerField('Время окончания последнего перерыва до конца смены, мин.',
                                                                   default=0)

    class Meta:
        verbose_name = 'Правила планирования перерывов'
        verbose_name_plural = 'Правила планирования перерывов'

    def __str__(self):
        return self.name


class Planning_Method(models.Model):
    name = models.CharField('Название', max_length=60)
    type = (
        ('flexible', 'Гибкий график'),
        ('fix', 'Фиксированный график'),
        ('availability_with_break', 'Доступность с перерывами'),
    )

    shift_type = models.CharField('Тип графика', max_length=40, choices=type, default='flexible')
    working_days_for_flexible_min = models.PositiveIntegerField('Гибкий график - рабочие дни (от)', null=True,
                                                                blank=True)
    working_days_for_flexible_max = models.PositiveIntegerField('Гибкий график - рабочие дни (до)', null=True,
                                                                blank=True)
    weekends_for_flexible_min = models.PositiveIntegerField('Гибкий график - выходные дни (от)', null=True, blank=True)
    weekends_for_flexible_max = models.PositiveIntegerField('Гибкий график - выходные дни (до)', null=True, blank=True)
    count_days_continuous_rest_min = models.PositiveIntegerField('Количество дней непрерывного отдыха (от)', null=True,
                                                                 blank=True)
    count_days_continuous_rest_max = models.PositiveIntegerField('Количество дней непрерывного отдыха (до)', null=True,
                                                                 blank=True)
    count_days_continuous_work_min = models.PositiveIntegerField('Количество дней непрерывной работы (от)', null=True,
                                                                 blank=True)
    count_days_continuous_work_max = models.PositiveIntegerField('Количество дней непрерывной работы (до)', null=True,
                                                                 blank=True)
    shift_duration_min = models.PositiveIntegerField('Продолжительность смены (от)', default=0)
    shift_duration_max = models.PositiveIntegerField('Продолжительность смены (до)', default=0)

    class Meta:
        verbose_name = 'Способ планирования смен'
        verbose_name_plural = 'Способ планирования смен'

    def __str__(self):
        return str(self.name)


class Working_Hours_Rate(models.Model):
    name = models.CharField('Название', max_length=100)
    count_working_hours_in_month_min = models.PositiveIntegerField('Количество рабочих часов в месяц (от)', default=0)
    count_working_hours_in_month_max = models.PositiveIntegerField('Количество рабочих часов в месяц (до)', default=0)

    class Meta:
        verbose_name = 'Рабочие часы'
        verbose_name_plural = 'Рабочие часы'

    def __str__(self):
        return str(self.name)


class Employee_Planning_Rules(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='Сотрудник',
                                 related_name='planning_rules_set')
    working_hours_rate = models.ForeignKey(Working_Hours_Rate, on_delete=models.CASCADE, verbose_name='Рабочие часы',
                                           related_name='planning_rules_set')
    planning_method = models.ForeignKey(Planning_Method, on_delete=models.CASCADE,
                                        verbose_name='Способы планирования смен', related_name='planning_rules_set')
    breaking_rule = models.ForeignKey(Breaking_Rule, on_delete=models.CASCADE, verbose_name='Планирования перерывов',
                                      related_name='planning_rules_set')
    date_rules_start = models.DateField('Дата начала действия правила для сотрудника')
    date_rules_end = models.DateField('Дата окончания действия правила для сотрудника', null=True, blank=True)

    class Meta:
        verbose_name = 'Сотрудник - Правила планирования'
        verbose_name_plural = 'Сотрудник - Правила планирования'


class Employee_Shift(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name='Сотрудник',
                                 related_name='shift_set')
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, verbose_name='Подразделение',
                                    related_name='shift_set')
    shift_date = models.DateField('Дата смены')
    handle_correct = models.PositiveIntegerField('Ручная корректировка смены', default=0)
    fixed = models.PositiveIntegerField('Фиксированный', default=0)

    objects = DataFrameManager()

    class Meta:
        verbose_name = 'Смена сотрудника'
        verbose_name_plural = 'Смены сотрудников'
        unique_together = ('employee', 'subdivision', 'shift_date')


class Employee_Shift_Detail_Plan(models.Model):
    interval_type_choices = (
        ('job', 'Работа'),
        ('break', 'Перерыв'),
    )
    shift = models.ForeignKey(Employee_Shift, on_delete=models.CASCADE, verbose_name='Смена',
                              related_name='detail_plan_set')
    type = models.CharField('Тип интервала', max_length=20, choices=interval_type_choices, default='job')
    time_from = models.TimeField('Время начала')
    time_to = models.TimeField('Время окончания')

    objects = DataFrameManager()


class Employee_Shift_Detail_Fact(models.Model):
    shift = models.ForeignKey(Employee_Shift, on_delete=models.CASCADE, verbose_name='Смена',
                              related_name='detail_fact_set')
    time_from = models.TimeField('Время начала')
    time_to = models.TimeField('Время окончания')


class Open_Shift(models.Model):
    subdivision = models.ForeignKey(Subdivision, on_delete=models.CASCADE, verbose_name='Подразделение',
                                    related_name='open_shift_set')
    shift_date = models.DateField('Дата смены')

    class Meta:
        verbose_name = 'Открытая смена'
        verbose_name_plural = 'Открытые смены'


class Open_Shift_Detail(models.Model):
    interval_type_choices = (
        ('job', 'Работа'),
        ('break', 'Перерыв'),
    )
    open_shift = models.ForeignKey(Open_Shift, on_delete=models.CASCADE, verbose_name='Открытая смена', related_name='detail_open_shift_set')
    type = models.CharField('Тип интервала', max_length=20, choices=interval_type_choices, default='job')
    time_from = models.TimeField('Время начала')
    time_to = models.TimeField('Время окончания')

    objects = DataFrameManager()
