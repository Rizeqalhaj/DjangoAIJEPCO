"""
Synthetic meter data generator for demo/testing.

Generates realistic 15-minute interval smart meter readings
for 5 predefined subscriber profiles.
"""

import random
import numpy as np
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from meter.models import MeterReading
from tariff.engine import get_tou_period, JORDAN_TZ

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
