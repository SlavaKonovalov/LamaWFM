from django.urls import path
from . import views

app_name = 'wfm'

urlpatterns = [
    path('business_indicator_dowload/',
         views.business_indicator_dowload,
         name='business_indicator_dowload'),
    path('demand_by_history_calculate/',
         views.demand_by_history_calculate,
         name='demand_by_history_calculate')
]