"""
Synthetic meter data generator for demo/testing.

Generates realistic 15-minute interval smart meter readings
for 5 predefined subscriber profiles.
"""

import logging
import random
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from meter.models import MeterReading
from tariff.engine import get_tou_period, JORDAN_TZ

logger = logging.getLogger(__name__)

PROFILES = {
    "ev_peak_charger": {
        "description": "EV owner who charges at peak every evening",
        "base_load_kw": 0.4,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.5, "variance": 0.3},
            {"name": "evening_cooking", "hours": (17, 19), "add_kw": 2.0, "variance": 0.5},
            {"name": "ev_charging", "hours": (19, 23), "add_kw": 7.0, "variance": 0.5,
             "weekday_only": True, "probability": 0.8},
            {"name": "evening_lights_tv", "hours": (18, 23), "add_kw": 1.0, "variance": 0.3},
        ],
    },
    "ac_heavy_summer": {
        "description": "Heavy AC user, bill shock in summer",
        "base_load_kw": 0.5,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.2, "variance": 0.3},
            {"name": "ac_afternoon", "hours": (14, 18), "add_kw": 3.5, "variance": 0.8,
             "summer_only": True},
            {"name": "ac_evening", "hours": (18, 23), "add_kw": 3.0, "variance": 0.7,
             "summer_only": True},
            {"name": "evening_normal", "hours": (18, 22), "add_kw": 1.5, "variance": 0.4},
        ],
    },
    "water_heater_peak": {
        "description": "Water heater at peak time - easy fix, big savings",
        "base_load_kw": 0.35,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.0, "variance": 0.2},
            {"name": "water_heater_evening", "hours": (18, 20), "add_kw": 2.5, "variance": 0.3,
             "probability": 0.9},
            {"name": "evening_normal", "hours": (18, 22), "add_kw": 1.2, "variance": 0.3},
        ],
    },
    "baseline_creep": {
        "description": "Slowly increasing consumption over months",
        "base_load_kw": 0.4,
        "monthly_increase_percent": 10,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.3, "variance": 0.3},
            {"name": "daytime_home", "hours": (10, 16), "add_kw": 0.8, "variance": 0.4},
            {"name": "evening_normal", "hours": (17, 22), "add_kw": 2.0, "variance": 0.5},
        ],
    },
    "efficient_user": {
        "description": "Energy-conscious user, mostly off-peak",
        "base_load_kw": 0.3,
        "patterns": [
            {"name": "morning_routine", "hours": (6, 8), "add_kw": 1.0, "variance": 0.2},
            {"name": "daytime_laundry", "hours": (9, 12), "add_kw": 1.5, "variance": 0.5,
             "probability": 0.3},
            {"name": "evening_light", "hours": (18, 22), "add_kw": 1.0, "variance": 0.3},
            {"name": "ev_night_charge", "hours": (1, 5), "add_kw": 7.0, "variance": 0.3,
             "probability": 0.6},
        ],
    },
}


def generate_meter_data(subscriber, profile_name: str, days: int = 90) -> list:
    """
    Generate synthetic 15-minute interval meter data.

    Args:
        subscriber: Subscriber model instance.
        profile_name: Key from PROFILES dict.
        days: Number of days of historical data to generate.

    Returns:
        List of unsaved MeterReading instances. Call bulk_create() on result.
    """
    profile = PROFILES[profile_name]
    base_load_kw = profile["base_load_kw"]
    monthly_increase_percent = profile.get("monthly_increase_percent", 0)
    patterns = profile["patterns"]

    now = datetime.now(JORDAN_TZ)
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)

    readings = []

    for day_offset in range(days):
        current_day = start_date + timedelta(days=day_offset)
        is_weekday = current_day.weekday() < 5
        is_summer = current_day.month in (6, 7, 8, 9)

        # Baseline creep multiplier
        month_offset = day_offset / 30.0
        if monthly_increase_percent:
            creep_multiplier = (1 + monthly_increase_percent / 100) ** month_offset
        else:
            creep_multiplier = 1.0

        # Roll probability once per pattern per day
        pattern_active_today = {}
        for pattern in patterns:
            prob = pattern.get("probability")
            if prob is not None:
                pattern_active_today[pattern["name"]] = random.random() < prob
            else:
                pattern_active_today[pattern["name"]] = True

        for interval in range(96):
            interval_time = current_day + timedelta(minutes=15 * interval)

            hour = interval_time.hour
            load_kw = base_load_kw

            for pattern in patterns:
                # Check weekday_only
                if pattern.get("weekday_only") and not is_weekday:
                    continue
                # Check summer_only
                if pattern.get("summer_only") and not is_summer:
                    continue
                # Check probability (rolled once per day)
                if not pattern_active_today[pattern["name"]]:
                    continue
                # Check hour range
                start_hour, end_hour = pattern["hours"]
                if start_hour <= hour < end_hour:
                    load_kw += pattern["add_kw"] + np.random.normal(0, pattern["variance"])

            # Apply creep
            load_kw *= creep_multiplier

            # Add small base noise
            load_kw += np.random.normal(0, 0.05)

            # Clamp to non-negative
            load_kw = max(0.0, load_kw)

            # kWh for 15-min interval
            kwh = load_kw / 4.0

            # TOU period
            tou_info = get_tou_period(interval_time)

            readings.append(MeterReading(
                subscriber=subscriber,
                timestamp=interval_time,
                kwh=round(kwh, 4),
                power_kw=round(load_kw, 2),
                tou_period=tou_info["period"],
                is_simulated=True,
            ))

    return readings


def generate_plan_improvement_data(subscriber, start_date, end_date, reduction_percent=15):
    """
    Generate reduced-consumption readings for the monitoring period of a plan.

    Copies the subscriber's existing consumption pattern but scales it down
    by reduction_percent (default 15%). Deletes any existing readings in the
    date range first, then inserts the reduced versions.

    Args:
        subscriber: Subscriber model instance.
        start_date: date object — first day of monitoring.
        end_date: date object — last day of monitoring (inclusive).
        reduction_percent: How much to reduce consumption (10-20 typical).
    """
    from core.clock import now as clock_now

    tz = JORDAN_TZ
    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=tz)
    # end is inclusive, so go to end of that day
    end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=tz)

    days = (end_date - start_date).days + 1
    if days < 1:
        return

    # Find a reference period of the same length BEFORE the plan start
    ref_start = start_dt - timedelta(days=days)
    ref_end = start_dt

    ref_readings = list(
        MeterReading.objects.filter(
            subscriber=subscriber,
            timestamp__gte=ref_start,
            timestamp__lt=ref_end,
        ).order_by("timestamp")
    )

    if not ref_readings:
        logger.warning("No reference readings found for subscriber %s", subscriber.phone_number)
        return

    # Delete existing readings in the monitoring period
    deleted, _ = MeterReading.objects.filter(
        subscriber=subscriber,
        timestamp__gte=start_dt,
        timestamp__lt=end_dt,
    ).delete()

    # Create new readings scaled down with some variance
    scale = 1 - (reduction_percent / 100)
    new_readings = []

    for ref in ref_readings:
        # Shift the timestamp forward by `days` days
        new_ts = ref.timestamp + timedelta(days=days)
        if new_ts >= end_dt:
            break

        # Apply reduction with small random variance (±3%)
        jitter = 1.0 + random.uniform(-0.03, 0.03)
        new_kwh = max(0.01, ref.kwh * scale * jitter)
        new_power = max(0.01, ref.power_kw * scale * jitter)

        tou_info = get_tou_period(new_ts)
        new_readings.append(MeterReading(
            subscriber=subscriber,
            timestamp=new_ts,
            kwh=round(new_kwh, 4),
            power_kw=round(new_power, 2),
            tou_period=tou_info["period"],
            is_simulated=True,
        ))

    if new_readings:
        MeterReading.objects.bulk_create(new_readings, ignore_conflicts=True)
        logger.info(
            "Generated %d improved readings for %s (-%d%%)",
            len(new_readings), subscriber.phone_number, reduction_percent,
        )
