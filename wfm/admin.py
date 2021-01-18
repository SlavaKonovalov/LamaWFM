import field as field
from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .forms import EmployeeForm
from .models import Organization, Production_Task, Subdivision, Department, Scheduled_Production_Task, Employee, Business_Indicator


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(Subdivision)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['organization', 'name']


@admin.register(Department)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['subdivision', 'name', 'get_organization']


@admin.register(Production_Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'demand_calculate', 'organization',
                    'demand_data_source', 'work_scope_measure', 'demand_allocation_method')
    list_filter = ('demand_calculate', 'demand_data_source', 'demand_allocation_method')
    search_fields = ['name']
    # prepopulated_fields = {'slug': ('title',)}
    # raw_id_fields = ('author',)
    # date_hierarchy = 'publish'
    # ordering = ('status', 'publish')


@admin.register(Scheduled_Production_Task)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Scheduled_Production_Task._meta.get_fields()]
    list_filter = ('task', 'subdivision')
    search_fields = ['task']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeForm

    # def save_model(self, request, obj, form, change):
    #     obj.user.first_name = form.cleaned_data['first_name']
    #     obj.user.last_name = form.cleaned_data['last_name']
    #     obj.user.save()
    #     obj.save()

    list_display = ['user', 'get_duties', 'get_part_job_org']

@admin.register(Business_Indicator)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['name']