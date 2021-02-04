import field as field
from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .forms import EmployeeForm
from .models import Organization, Production_Task, Subdivision, Department, Scheduled_Production_Task, Employee, \
    Business_Indicator, Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Subdivision)
class SubdivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'get_companies']


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


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeForm

    list_display = ['user',
                    'subdivision',
                    'personnel_number',
                    'position',
                    'get_duties',
                    'get_part_job_org']


@admin.register(Business_Indicator)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']
