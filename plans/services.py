"""Plan services for creating, retrieving, and checking optimization plans."""

from datetime import timedelta
from django.utils import timezone

from plans.models import OptimizationPlan
from meter.analyzer import MeterAnalyzer


def create_optimization_plan(subscriber, tool_input: dict) -> OptimizationPlan:
    """
    Create a new optimization plan for a subscriber.

    tool_input keys:
        - detected_pattern (str)
        - user_hypothesis (str)
        - plan_summary (str)
        - actions (list[dict])
        - monitoring_days (int, default 7)
    """
    analyzer = MeterAnalyzer(subscriber)
    summary = analyzer.get_consumption_summary(days=30)

    baseline_daily = summary.get('avg_daily_kwh', 0)
    peak_share = summary.get('peak_share_percent', 0)
    baseline_peak = round(baseline_daily * peak_share / 100, 2) if peak_share else 0

    forecast = analyzer.get_bill_forecast()
    baseline_monthly_cost = forecast.get('projected_bill', {}).get('total_fils', 0)

    monitoring_days = tool_input.get('monitoring_days', 7)

    plan = OptimizationPlan.objects.create(
        subscriber=subscriber,
        detected_pattern=tool_input['detected_pattern'],
        detection_data={},
        user_hypothesis=tool_input['user_hypothesis'],
        plan_summary=tool_input['plan_summary'],
        plan_details={"actions": tool_input.get('actions', [])},
        baseline_daily_kwh=baseline_daily,
        baseline_peak_kwh=baseline_peak,
        baseline_monthly_cost_fils=int(baseline_monthly_cost),
        status='active',
        verify_after_date=timezone.now().date() + timedelta(days=monitoring_days),
    )
    return plan


def get_active_plan(subscriber) -> OptimizationPlan | None:
    """Return the latest active or monitoring plan, or None."""
    return (
        OptimizationPlan.objects
        .filter(subscriber=subscriber, status__in=['active', 'monitoring'])
        .order_by('-created_at')
        .first()
    )


def check_progress(subscriber, plan_id: int) -> dict:
    """
    Compare current consumption vs plan's baseline.

    Returns dict with baseline_daily_kwh, current_daily_kwh,
    change_percent, and on_track flag.
    """
    try:
        plan = OptimizationPlan.objects.get(id=plan_id, subscriber=subscriber)
    except OptimizationPlan.DoesNotExist:
        return {"error": "Plan not found"}

    analyzer = MeterAnalyzer(subscriber)
    days_since = (timezone.now().date() - plan.created_at.date()).days
    if days_since < 1:
        days_since = 1

    summary = analyzer.get_consumption_summary(days=min(days_since, 30))
    current_daily = summary.get('avg_daily_kwh', 0)

    baseline = plan.baseline_daily_kwh
    if baseline > 0:
        change_percent = round((current_daily - baseline) / baseline * 100, 1)
    else:
        change_percent = 0

    return {
        "plan_id": plan.id,
        "plan_summary": plan.plan_summary,
        "status": plan.status,
        "baseline_daily_kwh": round(baseline, 2),
        "current_daily_kwh": round(current_daily, 2),
        "change_percent": change_percent,
        "on_track": change_percent <= 0,
        "days_monitored": days_since,
        "verify_after_date": str(plan.verify_after_date),
    }
