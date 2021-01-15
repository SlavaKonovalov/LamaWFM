from django.urls import path
from . import views

app_name = 'wfm'

urlpatterns = [
    path('productionTasks/',
         views.ProductionTaskListView.as_view(),
         name='task_list'),
    path('productionTasks/<pk>/',
         views.ProductionTaskDetailView.as_view(),
         name='task_detail'),
    path('organizations/',
         views.OrganizationListView.as_view(),
         name='org_list'),
    path('organizations/<pk>/',
         views.OrganizationDetailView.as_view(),
         name='org_detail'),
]
