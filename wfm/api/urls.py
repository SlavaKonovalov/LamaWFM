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

    path('subdivision/',
         views.SubdivisionListView.as_view(),
         name='subdiv_list'),
    path('subdivision/<int:pk>/',
         views.SubdivisionDetailView.as_view(),
         name='subdiv_detail'),

    path('employee/',
         views.EmployeeListView.as_view(),
         name='employee_list'),
    path('employee/<int:pk>/',
         views.EmployeeDetailView.as_view(),
         name='employee_detail'),
]