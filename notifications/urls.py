from django.urls import path
from notifications.views import trigger_check_plans

urlpatterns = [
    path("check-plans/", trigger_check_plans, name="check-plans"),
]
