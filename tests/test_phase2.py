"""
Phase 2 — Integration Tests.
Tests API endpoints, seed command, and data generator.
"""

import json
from datetime import timedelta
from django.test import TestCase, Client
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from accounts.models import Subscriber
from meter.models import MeterReading
from meter.generator import generate_meter_data, PROFILES


class TariffAPITest(TestCase):
    """Test tariff API endpoints."""

    def setUp(self):
        self.client = Client()

    def test_tariff_current_returns_200(self):
        response = self.client.get('/api/tariff/current/')
        self.assertEqual(response.status_code, 200)

    def test_tariff_current_has_period(self):
        response = self.client.get('/api/tariff/current/')
        data = response.json()
        self.assertIn(data['period'], ['off_peak', 'partial_peak', 'peak'])
        self.assertIn('period_name_ar', data)
        self.assertIn('period_name_en', data)
        self.assertIn('minutes_remaining', data)

    def test_tariff_calculate_returns_200(self):
        response = self.client.post(
            '/api/tariff/calculate/',
            data=json.dumps({"monthly_kwh": 500}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)

    def test_tariff_calculate_has_breakdown(self):
        response = self.client.post(
            '/api/tariff/calculate/',
            data=json.dumps({"monthly_kwh": 500}),
            content_type='application/json',
        )
        data = response.json()
        self.assertIn('total_fils', data)
        self.assertIn('total_jod', data)
        self.assertIn('tier_breakdown', data)
        self.assertEqual(len(data['tier_breakdown']), 4)  # 500 kWh = 4 tiers

    def test_tariff_calculate_missing_kwh(self):
        response = self.client.post(
            '/api/tariff/calculate/',
            data=json.dumps({}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_tariff_calculate_three_phase(self):
        response = self.client.post(
            '/api/tariff/calculate/',
            data=json.dumps({"monthly_kwh": 100, "phase": "three_phase"}),
            content_type='application/json',
        )
        data = response.json()
        self.assertEqual(data['fixed_charge_fils'], 1500)


class MeterAPITest(TestCase):
    """Test meter data API endpoints."""

    def setUp(self):
        self.client = Client()
        self.sub = Subscriber.objects.create(
            subscription_number='01-300001-01',
            phone_number='+962793000001',
            name='API Test User',
        )
        # Generate 7 days of data
        readings = generate_meter_data(self.sub, 'ev_peak_charger', days=7)
        MeterReading.objects.bulk_create(readings, batch_size=1000)

    def test_summary_returns_200(self):
        response = self.client.get('/api/meter/01-300001-01/summary/')
        self.assertEqual(response.status_code, 200)

    def test_summary_has_required_keys(self):
        response = self.client.get('/api/meter/01-300001-01/summary/?days=7')
        data = response.json()
        self.assertIn('total_kwh', data)
        self.assertIn('avg_daily_kwh', data)
        self.assertIn('trend', data)
        self.assertGreater(data['total_kwh'], 0)

    def test_daily_returns_200(self):
        # Use a date we know has data
        now = timezone.now()
        day = (now - timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.get(f'/api/meter/01-300001-01/daily/{day}/')
        self.assertEqual(response.status_code, 200)

    def test_daily_has_total_kwh(self):
        now = timezone.now()
        day = (now - timedelta(days=3)).strftime('%Y-%m-%d')
        response = self.client.get(f'/api/meter/01-300001-01/daily/{day}/')
        data = response.json()
        self.assertIn('total_kwh', data)

    def test_daily_invalid_date(self):
        response = self.client.get('/api/meter/01-300001-01/daily/not-a-date/')
        self.assertEqual(response.status_code, 400)

    def test_spikes_returns_200(self):
        response = self.client.get('/api/meter/01-300001-01/spikes/')
        self.assertEqual(response.status_code, 200)

    def test_spikes_has_structure(self):
        response = self.client.get('/api/meter/01-300001-01/spikes/')
        data = response.json()
        self.assertIn('spikes', data)
        self.assertIn('count', data)

    def test_forecast_returns_200(self):
        response = self.client.get('/api/meter/01-300001-01/forecast/')
        self.assertEqual(response.status_code, 200)

    def test_forecast_has_projection(self):
        response = self.client.get('/api/meter/01-300001-01/forecast/')
        data = response.json()
        self.assertIn('projected_monthly_kwh', data)
        self.assertIn('projected_bill', data)

    def test_nonexistent_subscriber_returns_404(self):
        response = self.client.get('/api/meter/99-999999-99/summary/')
        self.assertEqual(response.status_code, 404)


class SeedCommandTest(TestCase):
    """Test the seed_demo management command."""

    def test_seed_creates_subscribers(self):
        out = StringIO()
        call_command('seed_demo', days=3, stdout=out)
        self.assertEqual(Subscriber.objects.count(), 5)

    def test_seed_creates_readings(self):
        out = StringIO()
        call_command('seed_demo', days=3, stdout=out)
        # 5 subscribers * 3 days * 96 intervals = 1440
        expected = 5 * 3 * 96
        actual = MeterReading.objects.count()
        self.assertEqual(actual, expected)

    def test_seed_idempotent(self):
        out = StringIO()
        call_command('seed_demo', days=3, stdout=out)
        call_command('seed_demo', days=3, stdout=out)
        # Second run should skip existing subscribers
        self.assertEqual(Subscriber.objects.count(), 5)

    def test_seed_clear_flag(self):
        out = StringIO()
        call_command('seed_demo', days=3, stdout=out)
        self.assertEqual(Subscriber.objects.count(), 5)
        # Clear and recreate
        call_command('seed_demo', days=2, clear=True, stdout=out)
        self.assertEqual(Subscriber.objects.count(), 5)
        # New data should be 2 days worth
        expected = 5 * 2 * 96
        self.assertEqual(MeterReading.objects.count(), expected)


class GeneratorTest(TestCase):
    """Test the meter data generator."""

    def setUp(self):
        self.sub = Subscriber.objects.create(
            subscription_number='01-400001-01',
            phone_number='+962794000001',
            name='Generator Test',
        )

    def test_correct_count_1_day(self):
        readings = generate_meter_data(self.sub, 'ev_peak_charger', days=1)
        self.assertEqual(len(readings), 96)

    def test_correct_count_7_days(self):
        readings = generate_meter_data(self.sub, 'water_heater_peak', days=7)
        self.assertEqual(len(readings), 7 * 96)

    def test_valid_tou_periods(self):
        readings = generate_meter_data(self.sub, 'efficient_user', days=1)
        valid_periods = {'off_peak', 'partial_peak', 'peak'}
        for reading in readings:
            self.assertIn(reading.tou_period, valid_periods)

    def test_kwh_non_negative(self):
        readings = generate_meter_data(self.sub, 'ev_peak_charger', days=3)
        for reading in readings:
            self.assertGreaterEqual(reading.kwh, 0)

    def test_power_kw_matches_kwh(self):
        readings = generate_meter_data(self.sub, 'water_heater_peak', days=1)
        for reading in readings:
            # power_kw = kwh * 4 (approximately, due to rounding)
            self.assertAlmostEqual(reading.power_kw, reading.kwh * 4, delta=0.1)

    def test_all_profiles_generate(self):
        for profile_name in PROFILES:
            readings = generate_meter_data(self.sub, profile_name, days=1)
            self.assertEqual(len(readings), 96, f"Profile {profile_name} failed")

    def test_readings_are_unsaved(self):
        readings = generate_meter_data(self.sub, 'ev_peak_charger', days=1)
        self.assertIsNone(readings[0].pk)
        self.assertEqual(MeterReading.objects.count(), 0)

    def test_bulk_create_works(self):
        readings = generate_meter_data(self.sub, 'ev_peak_charger', days=1)
        MeterReading.objects.bulk_create(readings)
        self.assertEqual(MeterReading.objects.count(), 96)
