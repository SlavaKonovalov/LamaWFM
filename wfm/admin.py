from django.contrib import admin
from .forms import EmployeeForm
from .models import Organization, Production_Task, Subdivision, Scheduled_Production_Task, Employee, \
    Business_Indicator, Company, Job_Duty, Tasks_In_Duty, Employee_Position, Predictable_Production_Task, \
    Work_Shift_Planning_Rule, Breaking_Rule, Planning_Method, Working_Hours_Rate, Employee_Planning_Rules, \
    Production_Task_Business_Indicator, Business_Indicator_Norm, Holiday, Holiday_Period, Retail_Store_Format


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Retail_Store_Format)
class RetailStoreFormatAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Subdivision)
class SubdivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'external_code', 'organization', 'retail_store_format', 'get_companies', 'shop_open_time', 'shop_close_time', 'area_coefficient']


# @admin.register(Department)
# class DepartmentAdmin(admin.ModelAdmin):
#     list_display = ['subdivision', 'name', 'get_organization']


@admin.register(Production_Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'demand_calculate', 'organization',
                    'demand_data_source', 'work_scope_measure', 'demand_allocation_method', 'use_area_coefficient', 'pieces_to_minutes_coefficient')
    list_filter = ('demand_calculate', 'demand_data_source', 'demand_allocation_method')
    search_fields = ['name']


@admin.register(Scheduled_Production_Task)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ('task', 'subdivision', 'begin_date_format',
                    'begin_time_format', 'end_time_format', 'end_date_format', 'work_scope')
    list_filter = ('task', 'subdivision')
    search_fields = ['task__name']


@admin.register(Employee_Position)
class EmployeePositionAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'name', 'organization')
    list_filter = ['organization']
    search_fields = ['name']


@admin.register(Job_Duty)
class JobDutyAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'get_tasks')
    list_filter = ['organization']
    search_fields = ['name']


@admin.register(Tasks_In_Duty)
class TasksInDutyAdmin(admin.ModelAdmin):
    list_display = ('duty', 'task', 'priority')
    list_filter = ('duty', 'task')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeForm

    list_display = ('user',
                    'subdivision',
                    'personnel_number',
                    'position',
                    'get_duties',
                    'get_part_job_org')


@admin.register(Business_Indicator)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Predictable_Production_Task)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['subdivision', 'task']


@admin.register(Production_Task_Business_Indicator)
class Production_Task_Business_Indicator(admin.ModelAdmin):
    list_display = ['task', 'business_indicator']


@admin.register(Business_Indicator_Norm)
class Production_Task_Business_Indicator(admin.ModelAdmin):
    list_display = ['business_indicator', 'norm_value']


@admin.register(Holiday)
class Holiday(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Holiday_Period)
class HolidayPeriod(admin.ModelAdmin):
    list_display = ['holiday', 'begin_date_time', 'end_date_time']


@admin.register(Work_Shift_Planning_Rule)
class Work_Shift_Planning_RuleAdmin(admin.ModelAdmin):
    list_display = ['time_between_shift', 'continuous_weekly_rest']


@admin.register(Breaking_Rule)
class Breaking_RuleAdmin(admin.ModelAdmin):
    list_display = ['break_first',
                    'break_second',
                    'first_break_starting_after_going',
                    'time_between_breaks',
                    'second_break_starting_before_end']


@admin.register(Planning_Method)
class Planning_MethodAdmin(admin.ModelAdmin):
    list_display = ['name',
                    'shift_type',
                    'working_days_for_flexible_min',
                    'working_days_for_flexible_max',
                    'weekends_for_flexible_min',
                    'weekends_for_flexible_max',
                    'count_days_continuous_rest_min',
                    'count_days_continuous_rest_max',
                    'count_days_continuous_work_min',
                    'count_days_continuous_work_max',
                    'shift_duration_min',
                    'shift_duration_max']


@admin.register(Working_Hours_Rate)
class Working_Hours_RateAdmin(admin.ModelAdmin):
    list_display = ['name',
                    'count_working_hours_in_month']


@admin.register(Employee_Planning_Rules)
class Employee_Planning_RulesAdmin(admin.ModelAdmin):
    list_display = ['employee',
                    'working_hours_rate',
                    'planning_methods',
                    'date_rules_start',
                    "date_rules_end"]


