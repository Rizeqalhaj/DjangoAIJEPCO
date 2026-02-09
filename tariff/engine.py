"""
TOU Tariff Engine for JEPCO / EMRC rates.

Provides:
- get_tou_period(): Determine current Time-of-Use period
- calculate_residential_bill(): Calculate tiered residential electricity bill
- estimate_cost_by_period(): Compare current consumption pattern vs shifted-to-offpeak
"""

from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Optional

JORDAN_TZ = ZoneInfo("Asia/Amman")

# EMRC TOU Rates (effective July 2025) — fils per kWh
TOU_RATES = {
    "ev_home": {
        "off_peak": 108,
        "partial_peak": 118,
        "peak": 160,
    },
    "ev_public": {
        "off_peak": 103,
        "partial_peak": 113,
        "peak": 133,
    },
}

# JEPCO Residential Tiered Tariff — (max_kwh_in_tier, fils_per_kwh)
RESIDENTIAL_TIERS = [
    (160, 33),       # First 160 kWh
    (160, 72),       # 161–320 kWh
    (160, 86),       # 321–480 kWh
    (160, 114),      # 481–640 kWh
    (160, 158),      # 641–800 kWh
    (200, 200),      # 801–1000 kWh
    (float('inf'), 265),  # Above 1000 kWh
]

# Fixed monthly charges (fils)
RESIDENTIAL_FIXED_CHARGE_FILS = {
    "single_phase": 500,    # 0.5 JOD/month
    "three_phase": 1500,    # 1.5 JOD/month
}

# Period display names
_PERIOD_NAMES = {
    "off_peak": {"ar": "خارج الذروة", "en": "Off-Peak"},
    "partial_peak": {"ar": "ذروة جزئية", "en": "Partial Peak"},
    "peak": {"ar": "وقت الذروة", "en": "Peak"},
}


def get_tou_period(dt: Optional[datetime] = None) -> dict:
    """
    Determine the Time-of-Use period for a given datetime.

    TOU schedule (Jordan):
        Off-Peak:      05:00 – 14:00
        Partial Peak:  14:00 – 17:00  AND  23:00 – 05:00
        Peak:          17:00 – 23:00

    Returns dict with period info, names in ar/en, timing, and next period.
    """
    if dt is None:
        dt = datetime.now(JORDAN_TZ)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=JORDAN_TZ)

    hour = dt.hour
    minute = dt.minute

    if 5 <= hour < 14:
        period = "off_peak"
        start_time = "05:00"
        end_time = "14:00"
        minutes_remaining = (14 - hour) * 60 - minute
        next_period = "partial_peak"
    elif 14 <= hour < 17:
        period = "partial_peak"
        start_time = "14:00"
        end_time = "17:00"
        minutes_remaining = (17 - hour) * 60 - minute
        next_period = "peak"
    elif 17 <= hour < 23:
        period = "peak"
        start_time = "17:00"
        end_time = "23:00"
        minutes_remaining = (23 - hour) * 60 - minute
        next_period = "partial_peak"
    else:
        # 23:00–05:00 (partial peak overnight)
        period = "partial_peak"
        start_time = "23:00"
        end_time = "05:00"
        if hour >= 23:
            minutes_remaining = (5 + 24 - hour) * 60 - minute
        else:
            minutes_remaining = (5 - hour) * 60 - minute
        next_period = "off_peak"

    minutes_remaining = max(0, minutes_remaining)

    return {
        "period": period,
        "period_name_ar": _PERIOD_NAMES[period]["ar"],
        "period_name_en": _PERIOD_NAMES[period]["en"],
        "start_time": start_time,
        "end_time": end_time,
        "minutes_remaining": minutes_remaining,
        "next_period": next_period,
        "next_period_name_ar": _PERIOD_NAMES[next_period]["ar"],
        "next_period_name_en": _PERIOD_NAMES[next_period]["en"],
    }


def calculate_residential_bill(monthly_kwh: float, phase: str = "single_phase") -> dict:
    """
    Calculate residential electricity bill using JEPCO tiered tariff.

    Args:
        monthly_kwh: Total monthly consumption in kWh.
        phase: "single_phase" or "three_phase" (affects fixed charge).

    Returns dict with total_fils, total_jod, tier_breakdown, etc.
    """
    remaining = monthly_kwh
    tier_breakdown = []
    total_energy = 0

    for i, (tier_kwh, rate) in enumerate(RESIDENTIAL_TIERS):
        used_in_tier = min(remaining, tier_kwh)
        if used_in_tier <= 0:
            break
        cost = int(used_in_tier * rate)
        tier_breakdown.append({
            "tier": i + 1,
            "kwh": round(used_in_tier, 1),
            "rate_fils": rate,
            "cost_fils": cost,
        })
        total_energy += cost
        remaining -= used_in_tier

    fixed = RESIDENTIAL_FIXED_CHARGE_FILS.get(phase, 500)
    total = total_energy + fixed

    if monthly_kwh > 0:
        avg_rate = round(total_energy / monthly_kwh, 1)
    else:
        avg_rate = 0

    return {
        "total_fils": total,
        "total_jod": round(total / 1000, 2),
        "fixed_charge_fils": fixed,
        "energy_charge_fils": total_energy,
        "tier_breakdown": tier_breakdown,
        "avg_rate_fils": avg_rate,
        "monthly_kwh": round(monthly_kwh, 1),
    }


def estimate_cost_by_period(kwh_by_period: dict, tariff_type: str = "residential") -> dict:
    """
    Compare current consumption pattern vs all-off-peak scenario.

    Args:
        kwh_by_period: {"off_peak": 150, "partial_peak": 80, "peak": 120}
        tariff_type: "residential" or "ev_home"

    Returns dict with current cost, shifted cost, and potential savings.
    """
    total_kwh = sum(kwh_by_period.values())

    if tariff_type == "residential":
        # Residential is tiered (not TOU) — bill is the same regardless of period
        residential_bill = calculate_residential_bill(total_kwh)
        current_cost_fils = residential_bill["total_fils"]
        shifted_cost_fils = residential_bill["total_fils"]

        # Also show what it would cost under EV TOU rates for comparison
        ev_current = sum(
            kwh * TOU_RATES["ev_home"][period]
            for period, kwh in kwh_by_period.items()
        )
        ev_shifted = int(total_kwh * TOU_RATES["ev_home"]["off_peak"])

        return {
            "total_kwh": round(total_kwh, 1),
            "cost_at_current_pattern": {
                "residential_bill": residential_bill,
                "ev_tou_cost_fils": ev_current,
            },
            "cost_if_shifted_to_offpeak": {
                "residential_bill": calculate_residential_bill(total_kwh),
                "ev_tou_cost_fils": ev_shifted,
            },
            "potential_savings_jod": round((ev_current - ev_shifted) / 1000, 2),
        }
    else:
        # EV TOU tariff — savings come from shifting
        rates = TOU_RATES.get(tariff_type, TOU_RATES["ev_home"])
        current_cost_fils = sum(
            kwh * rates[period]
            for period, kwh in kwh_by_period.items()
        )
        shifted_cost_fils = int(total_kwh * rates["off_peak"])
        savings_fils = current_cost_fils - shifted_cost_fils

        return {
            "total_kwh": round(total_kwh, 1),
            "cost_at_current_pattern": {
                "total_fils": current_cost_fils,
                "total_jod": round(current_cost_fils / 1000, 2),
            },
            "cost_if_shifted_to_offpeak": {
                "total_fils": shifted_cost_fils,
                "total_jod": round(shifted_cost_fils / 1000, 2),
            },
            "potential_savings_jod": round(savings_fils / 1000, 2),
        }
