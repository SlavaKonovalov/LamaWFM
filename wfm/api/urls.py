from django.urls import path
from . import views

app_name = 'wfm'

urlpatterns = [
    path('productionTasks/',
         views.ProductionTaskListView.as_view(),
         name='task_list'),
    path('productionTasks/<int:pk>/',
         views.ProductionTaskDetailView.as_view(),
         name='task_detail'),

    path('organizations/',
         views.organization_list,
         name='org_list'),
    path('organizations/<int:pk>/',
         views.organization_detail,
         name='org_detail'),

    path('subdivisions/',
         views.SubdivisionListView.as_view(),
         name='subdiv_list'),
    path('subdivisions/<int:pk>/',
         views.SubdivisionDetailView.as_view(),
         name='subdiv_detail'),

    path('employee_positions/',
         views.EmployeePositionListView.as_view(),
         name='employee_position_list'),
    path('employee_positions/<int:pk>/',
         views.EmployeePositionDetailView.as_view(),
         name='employee_position_detail'),

    path('job_duties/',
         views.JobDutyListView.as_view(),
         name='job_duty_list'),
    path('job_duties/<int:pk>/',
         views.JobDutyDetailView.as_view(),
         name='job_duty_detail'),

    path('employees/',
         views.EmployeeListView.as_view(),
         name='employee_list'),
    path('employees/<int:pk>/',
         views.EmployeeDetailView.as_view(),
         name='employee_detail'),

    path('scheduled_tasks/',
         views.scheduled_task_list,
         name='scheduled_task_list'),

    path('scheduled_tasks/<int:pk>/',
         views.scheduled_task_detail,
         name='scheduled_task_detail'),

    path('appointed_tasks/',
         views.AppointedTaskListView.as_view(),
         name='appointed_task_list'),

    path('demand_main/',
         views.DemandMainListView.as_view(),
         name='demand_main_list'),

    path('assign_tasks/',
         views.assign_tasks,
         name='appointed_tasks'),

    path('recalculate_demand/',
         views.recalculate_demand,
         name='recalculate_demand'),

    path('companies/',
         views.CompanyListView.as_view(),
         name='companies_list'),

    path('recalculate_history_demand/',
         views.recalculate_history_demand,
         name='recalculate_history_demand'),

    path('availability_templates/',
         views.availability_template_list,
         name='availability_template_list'),
    path('availability_templates/<int:pk>/',
         views.availability_template_detail,
         name='availability_template_detail'),
    path('availability_template_data_details/<int:pk>/',
         views.availability_template_data_detail,
         name='availability_template_data_detail'),

    path('assign_availability_template/',
         views.assign_employee_availability_template,
         name='assign_availability_template'),

    path('employee_availability_templates/',
         views.EmployeeAvailabilityTemplatesView.as_view(),
         name='employee_availability_templates'),

    path('recalculate_availability/',
         views.recalculate_availability,
         name='recalculate_availability'),

    path('plan_shifts/',
         views.plan_shifts,
         name='plan_shifts'),

    path('planning_method/',
         views.PlanningMethodView.as_view(),
         name='planning_method'),

    path('working_hours_rate/',
         views.WorkingHoursRateView.as_view(),
         name='working_hours_rate'),

    path('work_shift_planning_rule/',
         views.WorkShiftPlanningRuleView.as_view(),
         name='work_shift_planning_rule'),

    path('breaking_rule/',
         views.BreakingRuleView.as_view(),
         name='breaking_rule'),

    path('employee_planning_rules/',
         views.EmployeePlanningRuleView.as_view(),
         name='employee_planning_rules'),

    path('assign_employee_planning_rules/',
         views.assign_employee_planning_rules,
         name='assign_employee_planning_rules'),

    path('employee_availability/',
         views.EmployeeAvailabilityView.as_view(),
         name='employee_availability'),
]
