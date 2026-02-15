from django.urls import path
from notifications.views import trigger_check_plans, trigger_check_plans_open

urlpatterns = [
    path("check-plans/", trigger_check_plans, name="check-plans"),
    path("check-plans-open/", trigger_check_plans_open, name="check-plans-open"),
]
