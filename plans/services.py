"""Plan services for creating, retrieving, and checking optimization plans."""

from datetime import timedelta
from django.utils import timezone

from plans.models import OptimizationPlan, PlanCheckpoint
from meter.analyzer import MeterAnalyzer
from tariff.engine import calculate_residential_bill


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
        plan_details={
            "actions": tool_input.get('actions', []),
            "monitoring_period_days": monitoring_days,
        },
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
    Compare current consumption vs plan's baseline and record a checkpoint.

    Creates a PlanCheckpoint record on each call for historical tracking.

    Returns dict with baseline_daily_kwh, current_daily_kwh,
    change_percent, on_track, is_improving, ready_for_verification,
    and estimated monthly savings.
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
    peak_share = summary.get('peak_share_percent', 0)
    off_peak_share = summary.get('off_peak_share_percent', 0)

    current_peak_kwh = round(current_daily * peak_share / 100, 2) if peak_share else 0
    current_offpeak_kwh = round(current_daily * off_peak_share / 100, 2) if off_peak_share else 0

    baseline = plan.baseline_daily_kwh
    if baseline > 0:
        change_percent = round((current_daily - baseline) / baseline * 100, 1)
    else:
        change_percent = 0

    # Estimate current daily cost
    current_monthly_bill = calculate_residential_bill(current_daily * 30)
    current_cost_fils_per_day = int(current_monthly_bill['total_fils'] / 30)

    # Calculate savings vs baseline
    baseline_cost_per_day = plan.baseline_monthly_cost_fils / 30 if plan.baseline_monthly_cost_fils else 0
    savings_per_day = baseline_cost_per_day - current_cost_fils_per_day
    estimated_monthly_savings_fils = int(savings_per_day * 30)
    estimated_monthly_savings_jod = round(estimated_monthly_savings_fils / 1000, 2)

    is_improving = change_percent < 0
    ready_for_verification = timezone.now().date() >= plan.verify_after_date

    # Record checkpoint
    PlanCheckpoint.objects.create(
        plan=plan,
        check_date=timezone.now().date(),
        avg_daily_kwh=round(current_daily, 2),
        avg_peak_kwh=current_peak_kwh,
        avg_offpeak_kwh=current_offpeak_kwh,
        estimated_cost_fils_per_day=current_cost_fils_per_day,
        change_vs_baseline_percent=change_percent,
    )

    return {
        "plan_id": plan.id,
        "plan_summary": plan.plan_summary,
        "status": plan.status,
        "baseline_daily_kwh": round(baseline, 2),
        "current_daily_kwh": round(current_daily, 2),
        "change_percent": change_percent,
        "on_track": change_percent <= 0,
        "is_improving": is_improving,
        "ready_for_verification": ready_for_verification,
        "estimated_monthly_savings_fils": estimated_monthly_savings_fils,
        "estimated_monthly_savings_jod": estimated_monthly_savings_jod,
        "days_monitored": days_since,
        "verify_after_date": str(plan.verify_after_date),
    }


def verify_plan(plan: OptimizationPlan) -> dict:
    """
    Verify an optimization plan by comparing current consumption to baseline.

    Updates the plan status to 'verified' and stores the verification result.

    Returns the progress dict from check_progress.
    """
    progress = check_progress(plan.subscriber, plan.id)

    if "error" in progress:
        return progress

    plan.status = 'verified'
    plan.verification_result = {
        "verified_at": timezone.now().isoformat(),
        "baseline_daily_kwh": progress["baseline_daily_kwh"],
        "final_daily_kwh": progress["current_daily_kwh"],
        "change_percent": progress["change_percent"],
        "improved": progress["is_improving"],
        "estimated_monthly_savings_fils": progress["estimated_monthly_savings_fils"],
        "estimated_monthly_savings_jod": progress["estimated_monthly_savings_jod"],
        "days_monitored": progress["days_monitored"],
    }
    plan.save()

    return progress
