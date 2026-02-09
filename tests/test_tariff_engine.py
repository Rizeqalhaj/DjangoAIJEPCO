"""
Phase 2 — Tariff Engine Tests.
Tests for get_tou_period(), calculate_residential_bill(), and estimate_cost_by_period().
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from django.test import TestCase
from tariff.engine import (
    get_tou_period,
    calculate_residential_bill,
    estimate_cost_by_period,
    JORDAN_TZ,
    RESIDENTIAL_TIERS,
    RESIDENTIAL_FIXED_CHARGE_FILS,
    TOU_RATES,
)


class TouPeriodTest(TestCase):
    """Test TOU period determination."""

    def test_off_peak_morning(self):
        dt = datetime(2026, 2, 7, 10, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'off_peak')
        self.assertEqual(result['start_time'], '05:00')
        self.assertEqual(result['end_time'], '14:00')
        self.assertEqual(result['next_period'], 'partial_peak')

    def test_partial_peak_afternoon(self):
        dt = datetime(2026, 2, 7, 15, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'partial_peak')
        self.assertEqual(result['start_time'], '14:00')
        self.assertEqual(result['end_time'], '17:00')
        self.assertEqual(result['next_period'], 'peak')

    def test_peak_evening(self):
        dt = datetime(2026, 2, 7, 20, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'peak')
        self.assertEqual(result['start_time'], '17:00')
        self.assertEqual(result['end_time'], '23:00')
        self.assertEqual(result['next_period'], 'partial_peak')

    def test_partial_peak_night(self):
        dt = datetime(2026, 2, 7, 2, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'partial_peak')
        self.assertEqual(result['start_time'], '23:00')
        self.assertEqual(result['end_time'], '05:00')
        self.assertEqual(result['next_period'], 'off_peak')

    def test_partial_peak_late_night(self):
        dt = datetime(2026, 2, 7, 23, 30, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'partial_peak')
        # 23:30 to 05:00 = 5.5 hours = 330 minutes
        self.assertEqual(result['minutes_remaining'], 330)

    def test_boundary_5am_is_off_peak(self):
        dt = datetime(2026, 2, 7, 5, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'off_peak')

    def test_boundary_14pm_is_partial_peak(self):
        dt = datetime(2026, 2, 7, 14, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'partial_peak')

    def test_boundary_17pm_is_peak(self):
        dt = datetime(2026, 2, 7, 17, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'peak')

    def test_boundary_23pm_is_partial_peak(self):
        dt = datetime(2026, 2, 7, 23, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'partial_peak')

    def test_minutes_remaining_mid_period(self):
        dt = datetime(2026, 2, 7, 13, 30, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'off_peak')
        self.assertEqual(result['minutes_remaining'], 30)

    def test_minutes_remaining_at_start(self):
        dt = datetime(2026, 2, 7, 17, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertEqual(result['minutes_remaining'], 360)  # 6 hours

    def test_default_uses_now(self):
        result = get_tou_period()
        self.assertIn(result['period'], ['off_peak', 'partial_peak', 'peak'])
        self.assertIn('period_name_ar', result)
        self.assertIn('period_name_en', result)
        self.assertIn('minutes_remaining', result)

    def test_naive_datetime_gets_tz(self):
        dt = datetime(2026, 2, 7, 10, 0)  # no tzinfo
        result = get_tou_period(dt)
        self.assertEqual(result['period'], 'off_peak')

    def test_arabic_names_present(self):
        dt = datetime(2026, 2, 7, 10, 0, tzinfo=JORDAN_TZ)
        result = get_tou_period(dt)
        self.assertTrue(len(result['period_name_ar']) > 0)
        self.assertTrue(len(result['next_period_name_ar']) > 0)

    def test_all_keys_present(self):
        result = get_tou_period(datetime(2026, 2, 7, 12, 0, tzinfo=JORDAN_TZ))
        expected_keys = [
            'period', 'period_name_ar', 'period_name_en',
            'start_time', 'end_time', 'minutes_remaining',
            'next_period', 'next_period_name_ar', 'next_period_name_en',
        ]
        for key in expected_keys:
            self.assertIn(key, result, f"Missing key: {key}")


class ResidentialBillTest(TestCase):
    """Test residential tiered bill calculation."""

    def test_small_usage_tier1_only(self):
        bill = calculate_residential_bill(100)
        self.assertEqual(bill['energy_charge_fils'], 100 * 33)
        self.assertEqual(bill['fixed_charge_fils'], 500)
        self.assertEqual(bill['total_fils'], 100 * 33 + 500)
        self.assertEqual(bill['total_jod'], round((100 * 33 + 500) / 1000, 2))
        self.assertEqual(len(bill['tier_breakdown']), 1)

    def test_crosses_tiers(self):
        # 500 kWh: tier1=160x33, tier2=160x72, tier3=160x86, tier4=20x114
        bill = calculate_residential_bill(500)
        expected_energy = (160 * 33) + (160 * 72) + (160 * 86) + (20 * 114)
        self.assertEqual(bill['energy_charge_fils'], expected_energy)
        self.assertEqual(len(bill['tier_breakdown']), 4)
        self.assertEqual(bill['tier_breakdown'][0]['kwh'], 160)
        self.assertEqual(bill['tier_breakdown'][3]['kwh'], 20)

    def test_large_usage_all_tiers(self):
        # 1200 kWh: hits all 7 tiers, last tier = 200 kwh at 265
        bill = calculate_residential_bill(1200)
        self.assertEqual(len(bill['tier_breakdown']), 7)
        self.assertEqual(bill['tier_breakdown'][6]['rate_fils'], 265)
        self.assertEqual(bill['tier_breakdown'][6]['kwh'], 200)

    def test_zero_usage(self):
        bill = calculate_residential_bill(0)
        self.assertEqual(bill['energy_charge_fils'], 0)
        self.assertEqual(bill['total_fils'], 500)  # fixed only
        self.assertEqual(bill['avg_rate_fils'], 0)
        self.assertEqual(len(bill['tier_breakdown']), 0)

    def test_three_phase_fixed_charge(self):
        bill = calculate_residential_bill(100, phase="three_phase")
        self.assertEqual(bill['fixed_charge_fils'], 1500)
        self.assertEqual(bill['total_fils'], 100 * 33 + 1500)

    def test_avg_rate_increases_with_usage(self):
        bill_low = calculate_residential_bill(100)
        bill_high = calculate_residential_bill(800)
        self.assertGreater(bill_high['avg_rate_fils'], bill_low['avg_rate_fils'])

    def test_total_jod_is_total_fils_divided_by_1000(self):
        bill = calculate_residential_bill(300)
        self.assertAlmostEqual(bill['total_jod'], bill['total_fils'] / 1000, places=2)

    def test_monthly_kwh_in_output(self):
        bill = calculate_residential_bill(456.789)
        self.assertAlmostEqual(bill['monthly_kwh'], 456.8, places=1)

    def test_tier_breakdown_sums_to_energy_charge(self):
        bill = calculate_residential_bill(750)
        tier_total = sum(t['cost_fils'] for t in bill['tier_breakdown'])
        self.assertEqual(tier_total, bill['energy_charge_fils'])

    def test_exact_tier_boundary(self):
        # Exactly 160 kWh — should be all tier 1
        bill = calculate_residential_bill(160)
        self.assertEqual(len(bill['tier_breakdown']), 1)
        self.assertEqual(bill['energy_charge_fils'], 160 * 33)

    def test_one_kwh_over_tier_boundary(self):
        # 161 kWh — tier 1 full + 1 kWh in tier 2
        bill = calculate_residential_bill(161)
        self.assertEqual(len(bill['tier_breakdown']), 2)
        self.assertEqual(bill['tier_breakdown'][1]['kwh'], 1)


class EstimateCostByPeriodTest(TestCase):
    """Test cost estimation by TOU period."""

    def test_residential_structure(self):
        result = estimate_cost_by_period(
            {"off_peak": 150, "partial_peak": 80, "peak": 120},
            tariff_type="residential",
        )
        self.assertIn('total_kwh', result)
        self.assertIn('cost_at_current_pattern', result)
        self.assertIn('cost_if_shifted_to_offpeak', result)
        self.assertIn('potential_savings_jod', result)
        self.assertAlmostEqual(result['total_kwh'], 350)

    def test_ev_home_savings_positive(self):
        # Peak is more expensive than off-peak, so shifting should save money
        result = estimate_cost_by_period(
            {"off_peak": 50, "partial_peak": 50, "peak": 200},
            tariff_type="ev_home",
        )
        self.assertGreater(result['potential_savings_jod'], 0)

    def test_ev_home_all_offpeak_no_savings(self):
        result = estimate_cost_by_period(
            {"off_peak": 300, "partial_peak": 0, "peak": 0},
            tariff_type="ev_home",
        )
        self.assertEqual(result['potential_savings_jod'], 0)

    def test_total_kwh_matches_input(self):
        kwh = {"off_peak": 100, "partial_peak": 50, "peak": 75}
        result = estimate_cost_by_period(kwh)
        self.assertAlmostEqual(result['total_kwh'], 225)
