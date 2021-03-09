from django.urls import path
from . import views

app_name = 'wfm'

urlpatterns = [
    path('business_indicator_download/',
         views.business_indicator_download,
         name='business_indicator_download'),
    path('demand_by_history_calculate/',
         views.demand_by_history_calculate,
         name='demand_by_history_calculate')
]