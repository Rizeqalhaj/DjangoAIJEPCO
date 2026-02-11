"""Celery tasks for scheduled notifications (weekly reports, spike alerts, plan verifications)."""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.models import Subscriber
from meter.analyzer import MeterAnalyzer
from plans.models import OptimizationPlan
from plans.services import check_progress
from whatsapp.sender import send_text

from notifications.message_templates import (
    WEEKLY_REPORT_AR, WEEKLY_REPORT_EN,
    WEEKLY_IMPROVED_AR, WEEKLY_IMPROVED_EN,
    WEEKLY_INCREASED_AR, WEEKLY_INCREASED_EN,
    WEEKLY_STABLE_AR, WEEKLY_STABLE_EN,
    SPIKE_ALERT_AR, SPIKE_ALERT_EN,
    PLAN_RESULT_IMPROVED_AR, PLAN_RESULT_IMPROVED_EN,
    PLAN_RESULT_NOT_IMPROVED_AR, PLAN_RESULT_NOT_IMPROVED_EN,
)

logger = logging.getLogger("notifications")


@shared_task
def send_weekly_reports():
    """Send weekly consumption reports to opted-in verified subscribers."""
    subscribers = Subscriber.objects.filter(
        wants_weekly_report=True,
        is_verified=True,
    )

    sent = 0
    for sub in subscribers:
        try:
            _send_weekly_report_to(sub)
            sent += 1
        except Exception:
            logger.exception("Weekly report failed for %s", sub.phone_number)

    logger.info("Weekly reports sent: %d/%d", sent, subscribers.count())
    return sent


def _send_weekly_report_to(subscriber):
    """Build and send a weekly report to one subscriber."""
    analyzer = MeterAnalyzer(subscriber)

    summary = analyzer.get_consumption_summary(days=7)
    now = timezone.now()

    # Compare this week vs last week
    this_week_start = (now - timedelta(days=7)).date()
    this_week_end = now.date()
    last_week_start = (now - timedelta(days=14)).date()
    last_week_end = (now - timedelta(days=8)).date()

    comparison = analyzer.compare_periods(
        last_week_start, last_week_end,
        this_week_start, this_week_end,
    )

    change_percent = abs(comparison["change_percent"])
    is_ar = subscriber.language == "ar"

    if comparison["improved"]:
        change_line = (WEEKLY_IMPROVED_AR if is_ar else WEEKLY_IMPROVED_EN).format(
            change_percent=change_percent,
        )
    elif comparison["change_percent"] > 2:
        change_line = (WEEKLY_INCREASED_AR if is_ar else WEEKLY_INCREASED_EN).format(
            change_percent=change_percent,
        )
    else:
        change_line = WEEKLY_STABLE_AR if is_ar else WEEKLY_STABLE_EN

    template = WEEKLY_REPORT_AR if is_ar else WEEKLY_REPORT_EN
    message = template.format(
        avg_daily_kwh=summary["avg_daily_kwh"],
        total_kwh=summary["total_kwh"],
        avg_daily_cost_fils=summary["avg_daily_cost_fils"],
        change_line=change_line,
    )

    send_text(subscriber.phone_number, message)


@shared_task
def check_spike_alerts():
    """Check for spikes in the last day and alert opted-in subscribers."""
    subscribers = Subscriber.objects.filter(
        wants_spike_alerts=True,
        is_verified=True,
    )

    sent = 0
    for sub in subscribers:
        try:
            if _send_spike_alert_to(sub):
                sent += 1
        except Exception:
            logger.exception("Spike alert failed for %s", sub.phone_number)

    logger.info("Spike alerts sent: %d/%d checked", sent, subscribers.count())
    return sent


def _send_spike_alert_to(subscriber) -> bool:
    """Check for spikes and send alert if found. Returns True if alert sent."""
    analyzer = MeterAnalyzer(subscriber)
    spikes = analyzer.detect_spikes(days=1, threshold_factor=2.5)

    if not spikes:
        return False

    biggest = max(spikes, key=lambda s: s["spike_factor"])
    is_ar = subscriber.language == "ar"

    template = SPIKE_ALERT_AR if is_ar else SPIKE_ALERT_EN
    message = template.format(
        power_kw=biggest["power_kw"],
        time=biggest["timestamp"],
        factor=biggest["spike_factor"],
    )

    send_text(subscriber.phone_number, message)
    return True


@shared_task
def check_plan_verifications():
    """Check and verify plans that have reached their verification date."""
    today = timezone.now().date()

    plans = OptimizationPlan.objects.filter(
        status__in=["active", "monitoring"],
        verify_after_date__lte=today,
    ).select_related("subscriber")

    verified = 0
    for plan in plans:
        try:
            if not plan.subscriber.is_verified:
                continue

            _verify_and_notify(plan)
            verified += 1
        except Exception:
            logger.exception("Plan verification failed for plan %d", plan.id)

    logger.info("Plans verified: %d/%d eligible", verified, plans.count())
    return verified


def _verify_and_notify(plan):
    """Verify a plan and send the result to the subscriber."""
    progress = check_progress(plan.subscriber, plan.id)

    if "error" in progress:
        logger.warning("check_progress error for plan %d: %s", plan.id, progress["error"])
        return

    plan.status = "verified"
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

    subscriber = plan.subscriber
    is_ar = subscriber.language == "ar"
    improved = progress["is_improving"]

    if improved:
        template = PLAN_RESULT_IMPROVED_AR if is_ar else PLAN_RESULT_IMPROVED_EN
    else:
        template = PLAN_RESULT_NOT_IMPROVED_AR if is_ar else PLAN_RESULT_NOT_IMPROVED_EN

    message = template.format(
        plan_summary=plan.plan_summary[:100],
        change_percent=abs(progress["change_percent"]),
        savings_jod=progress["estimated_monthly_savings_jod"],
    )

    send_text(subscriber.phone_number, message)
