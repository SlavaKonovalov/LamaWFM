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

    path('appointed_tasks/',
         views.AppointedTaskListView.as_view(),
         name='appointed_task_list'),

    path('recalculateDemand/',
         views.recalculate_demand_request,
         name='recalculate_demand'),
]
