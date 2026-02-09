from django.urls import path
from . import views

app_name = 'meter'

urlpatterns = [
    path('<str:subscription_number>/summary/', views.MeterSummaryView.as_view(), name='summary'),
    path('<str:subscription_number>/daily/<str:target_date>/', views.MeterDailyView.as_view(), name='daily'),
    path('<str:subscription_number>/spikes/', views.MeterSpikesView.as_view(), name='spikes'),
    path('<str:subscription_number>/forecast/', views.BillForecastView.as_view(), name='forecast'),
]
