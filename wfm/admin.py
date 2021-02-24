from django.contrib import admin
from .forms import EmployeeForm
from .models import Organization, Production_Task, Subdivision, Scheduled_Production_Task, Employee, \
    Business_Indicator, Company, Job_Duty, Tasks_In_Duty, Employee_Position, Predictable_Production_Task, \
    Production_Task_Business_Indicator, Business_Indicator_Norm


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Subdivision)
class SubdivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'external_code', 'organization', 'get_companies', 'shop_open_time', 'shop_close_time']


# @admin.register(Department)
# class DepartmentAdmin(admin.ModelAdmin):
#     list_display = ['subdivision', 'name', 'get_organization']


@admin.register(Production_Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'demand_calculate', 'organization',
                    'demand_data_source', 'work_scope_measure', 'demand_allocation_method')
    list_filter = ('demand_calculate', 'demand_data_source', 'demand_allocation_method')
    search_fields = ['name']


@admin.register(Scheduled_Production_Task)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = ('task', 'subdivision', 'begin_date_format',
                    'begin_time_format', 'end_time_format', 'end_date_format', 'work_scope')
    list_filter = ('task', 'subdivision')
    search_fields = ['task']


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
