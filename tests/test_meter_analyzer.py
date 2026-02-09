"""
Phase 2 — Meter Analyzer Tests.
Tests use deterministic data created in setUp for predictable assertions.
"""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from django.test import TestCase
from django.utils import timezone

from accounts.models import Subscriber
from meter.models import MeterReading
from meter.analyzer import MeterAnalyzer
from tariff.engine import JORDAN_TZ


def _make_reading(subscriber, ts, kwh, power_kw, tou_period):
    """Helper to create a MeterReading instance (unsaved)."""
    return MeterReading(
        subscriber=subscriber,
        timestamp=ts,
        kwh=kwh,
        power_kw=power_kw,
        tou_period=tou_period,
        is_simulated=True,
    )


def _bulk_day(subscriber, target_date, base_kw=1.0, peak_kw=None):
    """
    Create 96 readings for a single day with controlled values.
    Returns list of unsaved MeterReading objects.

    Hours 5-13 (off_peak): base_kw
    Hours 14-16 (partial_peak): base_kw
    Hours 17-22 (peak): peak_kw or base_kw
    Hours 23-4 (partial_peak): base_kw * 0.5
    """
    if peak_kw is None:
        peak_kw = base_kw

    readings = []
    for interval in range(96):
        ts = datetime(
            target_date.year, target_date.month, target_date.day,
            tzinfo=JORDAN_TZ
        ) + timedelta(minutes=15 * interval)
        hour = ts.hour

        if 5 <= hour < 14:
            kw = base_kw
            tou = 'off_peak'
        elif 14 <= hour < 17:
            kw = base_kw
            tou = 'partial_peak'
        elif 17 <= hour < 23:
            kw = peak_kw
            tou = 'peak'
        else:
            kw = base_kw * 0.5
            tou = 'partial_peak'

        kwh = kw / 4.0  # 15-min interval
        readings.append(_make_reading(subscriber, ts, round(kwh, 4), round(kw, 2), tou))

    return readings


class DailySummaryTest(TestCase):
    """Test MeterAnalyzer.get_daily_summary()."""

    def setUp(self):
        self.sub = Subscriber.objects.create(
            subscription_number='01-200001-01',
            phone_number='+962792000001',
            name='Test Daily',
        )
        self.target = date(2026, 1, 15)
        readings = _bulk_day(self.sub, self.target, base_kw=1.0, peak_kw=4.0)
        MeterReading.objects.bulk_create(readings)
        self.analyzer = MeterAnalyzer(self.sub)

    def test_reading_count(self):
        self.assertEqual(MeterReading.objects.filter(subscriber=self.sub).count(), 96)

    def test_total_kwh_positive(self):
        result = self.analyzer.get_daily_summary(self.target)
        self.assertGreater(result['total_kwh'], 0)

    def test_peak_kwh_higher_than_offpeak_per_hour(self):
        result = self.analyzer.get_daily_summary(self.target)
        # Peak hours (17-22) = 6 hours, 24 intervals at 4kW → peak_kwh = 24 * 1.0 = 24
        # Off-peak (5-13) = 9 hours, 36 intervals at 1kW → off_peak_kwh = 36 * 0.25 = 9
        self.assertGreater(result['peak_kwh'], result['off_peak_kwh'])

    def test_max_power_in_peak(self):
        result = self.analyzer.get_daily_summary(self.target)
        self.assertEqual(result['max_power_kw'], 4.0)
        self.assertGreaterEqual(result['max_power_hour'], 17)
        self.assertLess(result['max_power_hour'], 23)

    def test_cost_positive(self):
        result = self.analyzer.get_daily_summary(self.target)
        self.assertGreater(result['estimated_cost_fils'], 0)

    def test_empty_day_returns_zeros(self):
        result = self.analyzer.get_daily_summary(date(2020, 1, 1))
        self.assertEqual(result['total_kwh'], 0)

    def test_all_keys_present(self):
        result = self.analyzer.get_daily_summary(self.target)
        for key in ['date', 'total_kwh', 'peak_kwh', 'off_peak_kwh',
                     'partial_peak_kwh', 'max_power_kw', 'max_power_hour',
                     'estimated_cost_fils', 'cost_breakdown_by_period']:
            self.assertIn(key, result)


class HourlyProfileTest(TestCase):
    """Test MeterAnalyzer.get_hourly_profile()."""

    def setUp(self):
        self.sub = Subscriber.objects.create(
            subscription_number='01-200002-01',
            phone_number='+962792000002',
            name='Test Hourly',
        )
        # Create 7 days of data with peak at 4kW
        readings = []
        for i in range(7):
            day = date(2026, 1, 10 + i)
            readings.extend(_bulk_day(self.sub, day, base_kw=1.0, peak_kw=4.0))
        MeterReading.objects.bulk_create(readings)
        self.analyzer = MeterAnalyzer(self.sub)

    def test_hourly_profile_length(self):
        result = self.analyzer.get_hourly_profile(date(2026, 1, 10), date(2026, 1, 16))
        self.assertEqual(len(result['hourly_avg_kw']), 24)

    def test_peak_hour_in_peak_range(self):
        result = self.analyzer.get_hourly_profile(date(2026, 1, 10), date(2026, 1, 16))
        self.assertGreaterEqual(result['peak_hour'], 17)
        self.assertLess(result['peak_hour'], 23)
        self.assertAlmostEqual(result['peak_avg_kw'], 4.0, places=1)

    def test_lowest_hour_in_night(self):
        result = self.analyzer.get_hourly_profile(date(2026, 1, 10), date(2026, 1, 16))
        # Night hours have base_kw * 0.5 = 0.5
        self.assertLess(result['lowest_avg_kw'], 1.0)

    def test_period_in_output(self):
        result = self.analyzer.get_hourly_profile(date(2026, 1, 10), date(2026, 1, 16))
        self.assertIn('period', result)
        self.assertEqual(result['period']['start'], '2026-01-10')


class SpikeDetectionTest(TestCase):
    """Test MeterAnalyzer.detect_spikes()."""

    def setUp(self):
        self.sub = Subscriber.objects.create(
            subscription_number='01-200003-01',
            phone_number='+962792000003',
            name='Test Spikes',
        )
        now = timezone.now()
        # 30 days of baseline at 1kW ending today
        readings = []
        for i in range(30):
            day = (now - timedelta(days=30 - i)).date()
            readings.extend(_bulk_day(self.sub, day, base_kw=1.0, peak_kw=1.0))

        # Replace last 2 days with big spikes (8kW during peak)
        for i in range(2):
            day = (now - timedelta(days=2 - i)).date()
            readings = [r for r in readings if r.timestamp.date() != day]
            readings.extend(_bulk_day(self.sub, day, base_kw=1.0, peak_kw=8.0))

        MeterReading.objects.bulk_create(readings)
        self.analyzer = MeterAnalyzer(self.sub)

    def test_spikes_detected(self):
        spikes = self.analyzer.detect_spikes(days=7, threshold_factor=2.0)
        self.assertGreater(len(spikes), 0)

    def test_spike_has_required_keys(self):
        spikes = self.analyzer.detect_spikes(days=7, threshold_factor=2.0)
        if spikes:
            spike = spikes[0]
            for key in ['timestamp', 'power_kw', 'baseline_kw',
                         'spike_factor', 'tou_period', 'duration_minutes']:
                self.assertIn(key, spike)

    def test_spike_factor_above_threshold(self):
        spikes = self.analyzer.detect_spikes(days=7, threshold_factor=2.0)
        for spike in spikes:
            self.assertGreaterEqual(spike['spike_factor'], 2.0)

    def test_no_spikes_with_high_threshold(self):
        spikes = self.analyzer.detect_spikes(days=7, threshold_factor=100.0)
        self.assertEqual(len(spikes), 0)


class ComparePeriodsTest(TestCase):
    """Test MeterAnalyzer.compare_periods()."""

    def setUp(self):
        self.sub = Subscriber.objects.create(
            subscription_number='01-200004-01',
            phone_number='+962792000004',
            name='Test Compare',
        )
        # Week 1: high consumption (3kW base)
        readings = []
        for i in range(7):
            day = date(2026, 1, 1 + i)
            readings.extend(_bulk_day(self.sub, day, base_kw=3.0, peak_kw=3.0))
        # Week 2: low consumption (1kW base)
        for i in range(7):
            day = date(2026, 1, 8 + i)
            readings.extend(_bulk_day(self.sub, day, base_kw=1.0, peak_kw=1.0))
        MeterReading.objects.bulk_create(readings)
        self.analyzer = MeterAnalyzer(self.sub)

    def test_improvement_detected(self):
        result = self.analyzer.compare_periods(
            date(2026, 1, 1), date(2026, 1, 7),
            date(2026, 1, 8), date(2026, 1, 14),
        )
        self.assertTrue(result['improved'])
        self.assertLess(result['change_kwh'], 0)
        self.assertLess(result['change_percent'], 0)

    def test_all_keys_present(self):
        result = self.analyzer.compare_periods(
            date(2026, 1, 1), date(2026, 1, 7),
            date(2026, 1, 8), date(2026, 1, 14),
        )
        for key in ['period1', 'period2', 'change_kwh', 'change_percent',
                     'change_cost_fils', 'change_cost_jod', 'improved']:
            self.assertIn(key, result)


class BillForecastTest(TestCase):
    """Test MeterAnalyzer.get_bill_forecast()."""

    def setUp(self):
        self.sub = Subscriber.objects.create(
            subscription_number='01-200005-01',
            phone_number='+962792000005',
            name='Test Forecast',
        )
        # Create 10 days of data in current month
        now = timezone.now()
        readings = []
        for i in range(10):
            day = now.date().replace(day=1) + timedelta(days=i)
            if day > now.date():
                break
            readings.extend(_bulk_day(self.sub, day, base_kw=2.0, peak_kw=2.0))
        if readings:
            MeterReading.objects.bulk_create(readings)
        self.analyzer = MeterAnalyzer(self.sub)

    def test_forecast_structure(self):
        result = self.analyzer.get_bill_forecast()
        for key in ['days_elapsed', 'days_remaining', 'actual_kwh_so_far',
                     'projected_monthly_kwh', 'projected_bill',
                     'last_month_kwh', 'last_month_bill_fils']:
            self.assertIn(key, result)

    def test_projected_kwh_positive(self):
        result = self.analyzer.get_bill_forecast()
        self.assertGreater(result['projected_monthly_kwh'], 0)

    def test_projected_bill_has_total(self):
        result = self.analyzer.get_bill_forecast()
        self.assertIn('total_fils', result['projected_bill'])
        self.assertGreater(result['projected_bill']['total_fils'], 0)


class ConsumptionSummaryTest(TestCase):
    """Test MeterAnalyzer.get_consumption_summary()."""

    def setUp(self):
        self.sub = Subscriber.objects.create(
            subscription_number='01-200006-01',
            phone_number='+962792000006',
            name='Test Summary',
        )
        # 30 days: first 15 at 1kW, second 15 at 3kW (increasing trend)
        now = timezone.now()
        readings = []
        for i in range(30):
            day = (now - timedelta(days=30 - i)).date()
            if i < 15:
                readings.extend(_bulk_day(self.sub, day, base_kw=1.0, peak_kw=1.0))
            else:
                readings.extend(_bulk_day(self.sub, day, base_kw=3.0, peak_kw=3.0))
        MeterReading.objects.bulk_create(readings)
        self.analyzer = MeterAnalyzer(self.sub)

    def test_summary_structure(self):
        result = self.analyzer.get_consumption_summary(days=30)
        for key in ['period_days', 'total_kwh', 'avg_daily_kwh',
                     'avg_daily_cost_fils', 'peak_share_percent',
                     'off_peak_share_percent', 'partial_peak_share_percent',
                     'highest_day', 'lowest_day', 'trend',
                     'trend_percent_per_week']:
            self.assertIn(key, result)

    def test_total_kwh_positive(self):
        result = self.analyzer.get_consumption_summary(days=30)
        self.assertGreater(result['total_kwh'], 0)

    def test_increasing_trend(self):
        result = self.analyzer.get_consumption_summary(days=30)
        self.assertEqual(result['trend'], 'increasing')

    def test_shares_sum_near_100(self):
        result = self.analyzer.get_consumption_summary(days=30)
        total_share = (result['peak_share_percent'] +
                       result['off_peak_share_percent'] +
                       result['partial_peak_share_percent'])
        self.assertAlmostEqual(total_share, 100, delta=1)

    def test_highest_day_higher_than_lowest(self):
        result = self.analyzer.get_consumption_summary(days=30)
        self.assertGreater(
            result['highest_day']['kwh'],
            result['lowest_day']['kwh']
        )

    def test_empty_returns_zeros(self):
        sub2 = Subscriber.objects.create(
            subscription_number='01-200007-01',
            phone_number='+962792000007',
        )
        analyzer = MeterAnalyzer(sub2)
        result = analyzer.get_consumption_summary(days=30)
        self.assertEqual(result['total_kwh'], 0)
        self.assertEqual(result['trend'], 'stable')
