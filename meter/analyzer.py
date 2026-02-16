"""
Meter data analyzer for consumption insights.

Provides daily summaries, hourly profiles, spike detection,
recurring pattern detection, period comparison, bill forecasting,
and consumption summaries.
"""

from datetime import date, datetime, timedelta
from collections import defaultdict
from django.db.models import Sum, Avg, Max, Min, Count, F, Q
from django.db.models.functions import TruncDate, ExtractHour

from core.clock import now as clock_now
from tariff.engine import calculate_residential_bill, JORDAN_TZ


class MeterAnalyzer:
    def __init__(self, subscriber):
        self.subscriber = subscriber
        self.readings = subscriber.readings  # RelatedManager

    def get_daily_summary(self, target_date: date) -> dict:
        """Summarize a single day's consumption."""
        qs = self.readings.filter(timestamp__date=target_date)

        if not qs.exists():
            return {
                "date": str(target_date),
                "no_data": True,
                "message": f"No meter readings found for {target_date}. Data may not exist for this date.",
                "total_kwh": 0,
                "peak_kwh": 0,
                "off_peak_kwh": 0,
                "partial_peak_kwh": 0,
                "max_power_kw": 0,
                "max_power_hour": 0,
                "estimated_cost_fils": 0,
                "cost_breakdown_by_period": {},
            }

        # Aggregate by TOU period
        period_data = qs.values('tou_period').annotate(
            total_kwh=Sum('kwh')
        )
        kwh_by_period = {row['tou_period']: round(row['total_kwh'], 2) for row in period_data}
        total_kwh = sum(kwh_by_period.values())

        # Max power reading
        max_reading = qs.order_by('-power_kw').first()
        max_power_kw = round(max_reading.power_kw, 2) if max_reading else 0
        max_power_hour = max_reading.timestamp.astimezone(JORDAN_TZ).hour if max_reading else 0

        # Estimate daily cost: project to monthly, divide back
        projected_monthly = total_kwh * 30
        monthly_bill = calculate_residential_bill(projected_monthly)
        estimated_cost_fils = int(monthly_bill['total_fils'] / 30)

        # Cost breakdown by period
        cost_breakdown = {}
        for period, kwh in kwh_by_period.items():
            period_monthly = kwh * 30
            period_bill = calculate_residential_bill(period_monthly)
            cost_breakdown[period] = {
                "kwh": round(kwh, 2),
                "cost_fils": int(period_bill['total_fils'] / 30),
            }

        return {
            "date": str(target_date),
            "total_kwh": round(total_kwh, 2),
            "peak_kwh": round(kwh_by_period.get('peak', 0), 2),
            "off_peak_kwh": round(kwh_by_period.get('off_peak', 0), 2),
            "partial_peak_kwh": round(kwh_by_period.get('partial_peak', 0), 2),
            "max_power_kw": max_power_kw,
            "max_power_hour": max_power_hour,
            "estimated_cost_fils": estimated_cost_fils,
            "cost_breakdown_by_period": cost_breakdown,
        }

    def get_hourly_profile(self, start_date: date, end_date: date) -> dict:
        """Average consumption by hour of day over a date range."""
        qs = self.readings.filter(
            timestamp__date__gte=start_date,
            timestamp__date__lte=end_date,
        )

        hourly = qs.annotate(
            hour=ExtractHour('timestamp', tzinfo=JORDAN_TZ)
        ).values('hour').annotate(
            avg_kw=Avg('power_kw')
        ).order_by('hour')

        hourly_avg_kw = [0.0] * 24
        for row in hourly:
            hourly_avg_kw[row['hour']] = round(row['avg_kw'], 2)

        peak_hour = max(range(24), key=lambda h: hourly_avg_kw[h])
        lowest_hour = min(range(24), key=lambda h: hourly_avg_kw[h])

        return {
            "period": {"start": str(start_date), "end": str(end_date)},
            "hourly_avg_kw": hourly_avg_kw,
            "peak_hour": peak_hour,
            "peak_avg_kw": hourly_avg_kw[peak_hour],
            "lowest_hour": lowest_hour,
            "lowest_avg_kw": hourly_avg_kw[lowest_hour],
        }

    def detect_spikes(self, days: int = 7, threshold_factor: float = 1.5,
                       start_date=None, end_date=None) -> list:
        """Find unusual consumption spikes in last N days or a specific date range."""
        now = clock_now()
        if start_date and end_date:
            recent_start = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=JORDAN_TZ)
            recent_end = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=JORDAN_TZ)
            range_days = (end_date - start_date).days + 1
            baseline_start = recent_start - timedelta(days=30)
        else:
            recent_start = now - timedelta(days=days)
            recent_end = now
            range_days = days
            baseline_start = now - timedelta(days=30 + days)

        # Baseline: average power_kw by hour, EXCLUDING the recent period
        baseline_qs = self.readings.filter(
            timestamp__gte=baseline_start,
            timestamp__lt=recent_start,
        ).annotate(
            hour=ExtractHour('timestamp', tzinfo=JORDAN_TZ)
        ).values('hour').annotate(
            avg_kw=Avg('power_kw')
        )
        baseline = {row['hour']: row['avg_kw'] for row in baseline_qs}

        # Fallback: if not enough historical data, use all available data
        if not baseline:
            baseline_qs = self.readings.filter(
                timestamp__gte=now - timedelta(days=30),
                timestamp__lte=now,
            ).annotate(
                hour=ExtractHour('timestamp', tzinfo=JORDAN_TZ)
            ).values('hour').annotate(
                avg_kw=Avg('power_kw')
            )
            baseline = {row['hour']: row['avg_kw'] for row in baseline_qs}

        if not baseline:
            return []

        # Recent readings
        recent = self.readings.filter(
            timestamp__gte=recent_start,
            timestamp__lte=recent_end if start_date else now,
        ).order_by('timestamp')

        # Find spike readings
        spike_readings = []
        for reading in recent:
            hour = reading.timestamp.astimezone(JORDAN_TZ).hour
            base_kw = baseline.get(hour, 0)
            if base_kw > 0 and reading.power_kw > threshold_factor * base_kw:
                spike_readings.append({
                    "timestamp": reading.timestamp,
                    "power_kw": round(reading.power_kw, 2),
                    "baseline_kw": round(base_kw, 2),
                    "spike_factor": round(reading.power_kw / base_kw, 2),
                    "tou_period": reading.tou_period,
                })

        if not spike_readings:
            return []

        # Group consecutive spikes into events
        events = []
        current_event = None

        for spike in spike_readings:
            if current_event is None:
                current_event = {
                    "timestamp": spike["timestamp"].isoformat(),
                    "power_kw": spike["power_kw"],
                    "baseline_kw": spike["baseline_kw"],
                    "spike_factor": spike["spike_factor"],
                    "tou_period": spike["tou_period"],
                    "duration_minutes": 15,
                    "_last_ts": spike["timestamp"],
                }
            elif (spike["timestamp"] - current_event["_last_ts"]).total_seconds() <= 900:
                # Consecutive (within 15 min)
                current_event["duration_minutes"] += 15
                current_event["power_kw"] = max(current_event["power_kw"], spike["power_kw"])
                current_event["spike_factor"] = max(current_event["spike_factor"], spike["spike_factor"])
                current_event["_last_ts"] = spike["timestamp"]
            else:
                # New event
                extra_kwh = (current_event["power_kw"] - current_event["baseline_kw"]) * current_event["duration_minutes"] / 60
                current_event["estimated_extra_cost_fils"] = int(extra_kwh * 100)  # rough estimate
                del current_event["_last_ts"]
                events.append(current_event)
                current_event = {
                    "timestamp": spike["timestamp"].isoformat(),
                    "power_kw": spike["power_kw"],
                    "baseline_kw": spike["baseline_kw"],
                    "spike_factor": spike["spike_factor"],
                    "tou_period": spike["tou_period"],
                    "duration_minutes": 15,
                    "_last_ts": spike["timestamp"],
                }

        if current_event:
            extra_kwh = (current_event["power_kw"] - current_event["baseline_kw"]) * current_event["duration_minutes"] / 60
            current_event["estimated_extra_cost_fils"] = int(extra_kwh * 100)
            del current_event["_last_ts"]
            events.append(current_event)

        return events

    def detect_recurring_pattern(self, days: int = 14) -> list:
        """Find patterns that repeat daily or weekly."""
        now = clock_now()
        start = now - timedelta(days=days)

        qs = self.readings.filter(timestamp__gte=start, timestamp__lte=now)
        if not qs.exists():
            return []

        # Compute average power by (date, hour) to find high-power blocks
        daily_hourly = qs.annotate(
            day=TruncDate('timestamp'),
            hour=ExtractHour('timestamp', tzinfo=JORDAN_TZ),
        ).values('day', 'hour').annotate(
            avg_kw=Avg('power_kw')
        )

        # Organize by hour: {hour: [(date, avg_kw), ...]}
        hour_data = defaultdict(list)
        for row in daily_hourly:
            hour_data[row['hour']].append({
                'date': row['day'],
                'avg_kw': row['avg_kw'],
                'weekday': row['day'].weekday() < 5,
            })

        # Overall average power for threshold
        overall_avg = qs.aggregate(avg=Avg('power_kw'))['avg'] or 0
        threshold = overall_avg * 1.5

        # Find hours with consistently high power
        high_hours = []
        for hour in range(24):
            entries = hour_data.get(hour, [])
            if not entries:
                continue

            high_entries = [e for e in entries if e['avg_kw'] > threshold]
            total_days = len(entries)
            high_days = len(high_entries)

            if high_days < 3:
                continue

            consistency = high_days / total_days if total_days > 0 else 0
            avg_kw = sum(e['avg_kw'] for e in high_entries) / high_days

            # Determine pattern type
            weekday_highs = sum(1 for e in high_entries if e['weekday'])
            weekend_highs = high_days - weekday_highs

            weekday_total = sum(1 for e in entries if e['weekday'])
            weekend_total = total_days - weekday_total

            if weekday_total > 0 and weekend_total > 0:
                weekday_rate = weekday_highs / weekday_total
                weekend_rate = weekend_highs / weekend_total if weekend_total > 0 else 0
                if weekday_rate > 0.6 and weekend_rate < 0.3:
                    pattern_type = "weekday"
                elif weekend_rate > 0.6 and weekday_rate < 0.3:
                    pattern_type = "weekend"
                else:
                    pattern_type = "daily"
            else:
                pattern_type = "daily"

            high_hours.append({
                "hour": hour,
                "avg_kw": round(avg_kw, 1),
                "occurrences": high_days,
                "total_days": total_days,
                "consistency": round(consistency, 2),
                "pattern_type": pattern_type,
            })

        if not high_hours:
            return []

        # Group consecutive hours into blocks
        high_hours.sort(key=lambda x: x["hour"])
        patterns = []
        current_block = None

        for hh in high_hours:
            if current_block is None:
                current_block = {
                    "pattern_type": hh["pattern_type"],
                    "start_hour": hh["hour"],
                    "end_hour": hh["hour"] + 1,
                    "avg_power_kw": hh["avg_kw"],
                    "occurrences": hh["occurrences"],
                    "consistency": hh["consistency"],
                    "_count": 1,
                    "_total_kw": hh["avg_kw"],
                }
            elif hh["hour"] == current_block["end_hour"]:
                current_block["end_hour"] = hh["hour"] + 1
                current_block["_count"] += 1
                current_block["_total_kw"] += hh["avg_kw"]
                current_block["avg_power_kw"] = round(current_block["_total_kw"] / current_block["_count"], 1)
                current_block["occurrences"] = min(current_block["occurrences"], hh["occurrences"])
                current_block["consistency"] = min(current_block["consistency"], hh["consistency"])
            else:
                self._finalize_pattern(current_block, patterns)
                current_block = {
                    "pattern_type": hh["pattern_type"],
                    "start_hour": hh["hour"],
                    "end_hour": hh["hour"] + 1,
                    "avg_power_kw": hh["avg_kw"],
                    "occurrences": hh["occurrences"],
                    "consistency": hh["consistency"],
                    "_count": 1,
                    "_total_kw": hh["avg_kw"],
                }

        if current_block:
            self._finalize_pattern(current_block, patterns)

        patterns.sort(key=lambda p: p["estimated_daily_cost_fils"], reverse=True)
        return patterns

    def _finalize_pattern(self, block, patterns):
        """Convert a raw block into a pattern dict."""
        from tariff.engine import get_tou_period, JORDAN_TZ
        from datetime import datetime

        mid_hour = (block["start_hour"] + block["end_hour"]) // 2
        dt = datetime(2026, 1, 1, mid_hour, 0, tzinfo=JORDAN_TZ)
        tou = get_tou_period(dt)["period"]

        hours = block["end_hour"] - block["start_hour"]
        daily_kwh = block["avg_power_kw"] * hours
        monthly_kwh = daily_kwh * 30
        monthly_bill = calculate_residential_bill(monthly_kwh)
        estimated_daily = int(monthly_bill['total_fils'] / 30)

        patterns.append({
            "pattern_type": block["pattern_type"],
            "start_hour": block["start_hour"],
            "end_hour": block["end_hour"],
            "avg_power_kw": block["avg_power_kw"],
            "occurrences": block["occurrences"],
            "consistency": block["consistency"],
            "estimated_daily_cost_fils": estimated_daily,
            "tou_period": tou,
        })

    def compare_periods(self, period1_start: date, period1_end: date,
                        period2_start: date, period2_end: date) -> dict:
        """Compare two time periods."""
        def _period_stats(start, end):
            qs = self.readings.filter(
                timestamp__date__gte=start,
                timestamp__date__lte=end,
            )
            agg = qs.aggregate(total_kwh=Sum('kwh'))
            total_kwh = agg['total_kwh'] or 0

            num_days = (end - start).days + 1
            daily_dates = qs.annotate(day=TruncDate('timestamp')).values('day').distinct()
            actual_days = daily_dates.count() or 1

            avg_daily = total_kwh / actual_days
            monthly_bill = calculate_residential_bill(avg_daily * 30)
            avg_cost = int(monthly_bill['total_fils'] / 30)

            return {
                "start": str(start),
                "end": str(end),
                "avg_daily_kwh": round(avg_daily, 1),
                "avg_cost_fils_per_day": avg_cost,
            }

        p1 = _period_stats(period1_start, period1_end)
        p2 = _period_stats(period2_start, period2_end)

        change_kwh = round(p2["avg_daily_kwh"] - p1["avg_daily_kwh"], 1)
        change_percent = round(
            (change_kwh / p1["avg_daily_kwh"] * 100) if p1["avg_daily_kwh"] else 0, 1
        )
        change_cost = p2["avg_cost_fils_per_day"] - p1["avg_cost_fils_per_day"]

        return {
            "period1": p1,
            "period2": p2,
            "change_kwh": change_kwh,
            "change_percent": change_percent,
            "change_cost_fils": change_cost,
            "change_cost_jod": round(change_cost / 1000, 2),
            "improved": change_kwh < 0,
        }

    def get_bill_forecast(self, days_in_month: int = 30) -> dict:
        """Forecast end-of-month bill based on current month's data."""
        now = clock_now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Current month data
        qs = self.readings.filter(timestamp__gte=month_start, timestamp__lte=now)
        agg = qs.aggregate(total_kwh=Sum('kwh'))
        actual_kwh = agg['total_kwh'] or 0

        # Days with data this month
        days_with_data = qs.annotate(
            day=TruncDate('timestamp')
        ).values('day').distinct().count()

        if days_with_data == 0:
            return {
                "days_elapsed": 0,
                "days_remaining": days_in_month,
                "actual_kwh_so_far": 0,
                "projected_monthly_kwh": 0,
                "projected_bill": calculate_residential_bill(0),
                "last_month_kwh": 0,
                "last_month_bill_fils": 0,
                "change_vs_last_month_percent": 0,
            }

        days_elapsed = days_with_data
        days_remaining = max(0, days_in_month - days_elapsed)
        daily_avg = actual_kwh / days_elapsed
        projected_monthly_kwh = round(daily_avg * days_in_month, 1)
        projected_bill = calculate_residential_bill(projected_monthly_kwh)

        # Determine tier reached
        tier_reached = len(projected_bill['tier_breakdown'])

        # Last month data
        last_month_start = (month_start - timedelta(days=1)).replace(day=1)
        last_month_end = month_start - timedelta(seconds=1)
        last_month_qs = self.readings.filter(
            timestamp__gte=last_month_start,
            timestamp__lte=last_month_end,
        )
        last_month_agg = last_month_qs.aggregate(total_kwh=Sum('kwh'))
        last_month_kwh = round(last_month_agg['total_kwh'] or 0, 1)
        last_month_bill = calculate_residential_bill(last_month_kwh)

        change_vs_last = round(
            ((projected_monthly_kwh - last_month_kwh) / last_month_kwh * 100)
            if last_month_kwh > 0 else 0, 1
        )

        # Warning
        warning = ""
        if last_month_kwh > 0:
            last_tier = len(last_month_bill['tier_breakdown'])
            if tier_reached > last_tier:
                warning = f"You're on track to hit tier {tier_reached}. Last month was tier {last_tier}."

        result = {
            "days_elapsed": days_elapsed,
            "days_remaining": days_remaining,
            "actual_kwh_so_far": round(actual_kwh, 1),
            "projected_monthly_kwh": projected_monthly_kwh,
            "projected_bill": {
                "total_fils": projected_bill['total_fils'],
                "total_jod": projected_bill['total_jod'],
                "tier_reached": tier_reached,
            },
            "last_month_kwh": last_month_kwh,
            "last_month_bill_fils": last_month_bill['total_fils'],
            "change_vs_last_month_percent": change_vs_last,
        }
        if warning:
            result["projected_bill"]["warning"] = warning

        return result

    def get_consumption_summary(self, days: int = 30, start_date: date = None, end_date: date = None) -> dict:
        """High-level consumption summary for agent context.

        If start_date and end_date are provided, uses those exact boundaries
        (e.g. for a specific calendar month). Otherwise falls back to
        rolling last N days.
        """
        now = clock_now()

        if start_date and end_date:
            qs = self.readings.filter(
                timestamp__date__gte=start_date,
                timestamp__date__lte=end_date,
            )
            period_days = (end_date - start_date).days + 1
            period_label = f"{start_date} to {end_date}"
        else:
            start = now - timedelta(days=days)
            qs = self.readings.filter(timestamp__gte=start, timestamp__lte=now)
            period_days = days
            period_label = f"last {days} days"

        if not qs.exists():
            return {
                "period_days": period_days,
                "period_label": period_label,
                "no_data": True,
                "message": f"No meter readings found for {period_label}.",
                "total_kwh": 0,
                "avg_daily_kwh": 0,
                "avg_daily_cost_fils": 0,
                "peak_share_percent": 0,
                "off_peak_share_percent": 0,
                "partial_peak_share_percent": 0,
                "highest_day": None,
                "lowest_day": None,
                "trend": "stable",
                "trend_percent_per_week": 0,
            }

        # Total and period breakdown
        total_agg = qs.aggregate(total_kwh=Sum('kwh'))
        total_kwh = total_agg['total_kwh'] or 0

        period_agg = qs.values('tou_period').annotate(period_kwh=Sum('kwh'))
        period_kwh = {row['tou_period']: row['period_kwh'] for row in period_agg}

        peak_share = round((period_kwh.get('peak', 0) / total_kwh * 100) if total_kwh else 0, 1)
        off_peak_share = round((period_kwh.get('off_peak', 0) / total_kwh * 100) if total_kwh else 0, 1)
        partial_peak_share = round((period_kwh.get('partial_peak', 0) / total_kwh * 100) if total_kwh else 0, 1)

        # Daily totals
        daily_totals = qs.annotate(
            day=TruncDate('timestamp')
        ).values('day').annotate(
            day_kwh=Sum('kwh')
        ).order_by('day')

        daily_list = list(daily_totals)
        actual_days = len(daily_list)
        avg_daily_kwh = round(total_kwh / actual_days, 1) if actual_days else 0

        # Cost estimate
        monthly_bill = calculate_residential_bill(avg_daily_kwh * 30)
        avg_daily_cost = round(monthly_bill['total_fils'] / 30, 1) if avg_daily_kwh else 0

        # Highest and lowest day
        if daily_list:
            highest = max(daily_list, key=lambda d: d['day_kwh'])
            lowest = min(daily_list, key=lambda d: d['day_kwh'])
            highest_day = {"date": str(highest['day']), "kwh": round(highest['day_kwh'], 1)}
            lowest_day = {"date": str(lowest['day']), "kwh": round(lowest['day_kwh'], 1)}
        else:
            highest_day = None
            lowest_day = None

        # Trend detection: compare first half vs second half
        trend = "stable"
        trend_percent_per_week = 0.0
        if actual_days >= 4:
            mid = actual_days // 2
            first_half = daily_list[:mid]
            second_half = daily_list[mid:]

            first_avg = sum(d['day_kwh'] for d in first_half) / len(first_half)
            second_avg = sum(d['day_kwh'] for d in second_half) / len(second_half)

            if first_avg > 0:
                change_pct = ((second_avg - first_avg) / first_avg) * 100
                if change_pct > 5:
                    trend = "increasing"
                elif change_pct < -5:
                    trend = "decreasing"

                # Weekly rate
                weeks = actual_days / 7
                if weeks > 0:
                    trend_percent_per_week = round(change_pct / (weeks / 2), 1)

        return {
            "period_days": period_days,
            "period_label": period_label,
            "total_kwh": round(total_kwh, 1),
            "avg_daily_kwh": avg_daily_kwh,
            "avg_daily_cost_fils": avg_daily_cost,
            "peak_share_percent": peak_share,
            "off_peak_share_percent": off_peak_share,
            "partial_peak_share_percent": partial_peak_share,
            "highest_day": highest_day,
            "lowest_day": lowest_day,
            "trend": trend,
            "trend_percent_per_week": trend_percent_per_week,
        }
