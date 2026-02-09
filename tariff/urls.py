from django.urls import path
from . import views

app_name = 'tariff'

urlpatterns = [
    path('current/', views.TouCurrentView.as_view(), name='current'),
    path('calculate/', views.BillCalculateView.as_view(), name='calculate'),
]
