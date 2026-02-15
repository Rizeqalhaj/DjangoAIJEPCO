from django.urls import path

from plans.views import PlanDetailView, SubscriberPlansView

app_name = "plans"

urlpatterns = [
    path(
        "<str:subscription_number>/",
        SubscriberPlansView.as_view(),
        name="subscriber-plans",
    ),
    path(
        "detail/<int:plan_id>/",
        PlanDetailView.as_view(),
        name="plan-detail",
    ),
]
