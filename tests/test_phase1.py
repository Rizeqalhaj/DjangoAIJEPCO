"""
Phase 1 Foundation Tests
Tests that verify: models, health check endpoint, admin registration, and settings.
"""

from datetime import date
from django.test import TestCase, Client
from django.contrib.admin.sites import site as admin_site
from django.conf import settings
from accounts.models import Subscriber
from meter.models import MeterReading
from plans.models import OptimizationPlan, PlanCheckpoint
from django.utils import timezone


class HealthCheckTest(TestCase):
    """Test the /api/health/ endpoint."""

    def test_health_check_returns_200(self):
        client = Client()
        response = client.get('/api/health/')
        self.assertEqual(response.status_code, 200)

    def test_health_check_returns_correct_json(self):
        client = Client()
        response = client.get('/api/health/')
        data = response.json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['service'], 'kahrabaai')


class SettingsTest(TestCase):
    """Test that Django settings are configured correctly."""

    def test_timezone_is_amman(self):
        self.assertEqual(settings.TIME_ZONE, 'Asia/Amman')

    def test_use_tz_is_true(self):
        self.assertTrue(settings.USE_TZ)

    def test_rest_framework_is_installed(self):
        self.assertIn('rest_framework', settings.INSTALLED_APPS)

    def test_all_project_apps_installed(self):
        expected_apps = [
            'core', 'accounts', 'meter', 'tariff', 'agent',
            'plans', 'whatsapp', 'rag', 'notifications', 'seed',
        ]
        for app in expected_apps:
            self.assertIn(app, settings.INSTALLED_APPS, f"App '{app}' not in INSTALLED_APPS")


class SubscriberModelTest(TestCase):
    """Test the Subscriber model."""

    def setUp(self):
        self.subscriber = Subscriber.objects.create(
            subscription_number='01-123456-01',
            phone_number='+962791234567',
            name='Test User',
            language='ar',
            tariff_category='residential',
            governorate='Amman',
            area='Abdoun',
            household_size=4,
            has_ev=True,
            has_solar=False,
            home_size_sqm=180,
            is_verified=True,
        )

    def test_subscriber_creation(self):
        self.assertEqual(Subscriber.objects.count(), 1)

    def test_subscriber_str(self):
        self.assertEqual(str(self.subscriber), 'Test User (01-123456-01)')

    def test_subscriber_str_no_name(self):
        sub = Subscriber.objects.create(
            subscription_number='01-999999-01',
            phone_number='+962790000000',
        )
        self.assertEqual(str(sub), 'Unknown (01-999999-01)')

    def test_subscriber_defaults(self):
        sub = Subscriber.objects.create(
            subscription_number='01-888888-01',
            phone_number='+962790000001',
        )
        self.assertEqual(sub.language, 'ar')
        self.assertEqual(sub.tariff_category, 'residential')
        self.assertEqual(sub.governorate, 'Amman')
        self.assertFalse(sub.has_ev)
        self.assertFalse(sub.has_solar)
        self.assertFalse(sub.is_verified)
        self.assertTrue(sub.wants_weekly_report)
        self.assertTrue(sub.wants_spike_alerts)
        self.assertTrue(sub.wants_plan_checkups)

    def test_subscription_number_unique(self):
        with self.assertRaises(Exception):
            Subscriber.objects.create(
                subscription_number='01-123456-01',  # duplicate
                phone_number='+962790000002',
            )

    def test_phone_number_unique(self):
        with self.assertRaises(Exception):
            Subscriber.objects.create(
                subscription_number='01-111111-01',
                phone_number='+962791234567',  # duplicate
            )

    def test_timestamps_auto_set(self):
        self.assertIsNotNone(self.subscriber.created_at)
        self.assertIsNotNone(self.subscriber.updated_at)

    def test_ordering_is_newest_first(self):
        sub2 = Subscriber.objects.create(
            subscription_number='01-222222-01',
            phone_number='+962790000003',
        )
        subs = list(Subscriber.objects.all())
        self.assertEqual(subs[0], sub2)  # newest first
        self.assertEqual(subs[1], self.subscriber)


class MeterReadingModelTest(TestCase):
    """Test the MeterReading model."""

    def setUp(self):
        self.subscriber = Subscriber.objects.create(
            subscription_number='01-100001-01',
            phone_number='+962791000001',
            name='Ahmad',
        )
        self.reading = MeterReading.objects.create(
            subscriber=self.subscriber,
            timestamp=timezone.now(),
            kwh=1.25,
            power_kw=5.0,
            tou_period='peak',
            is_simulated=True,
        )

    def test_reading_creation(self):
        self.assertEqual(MeterReading.objects.count(), 1)

    def test_reading_str(self):
        result = str(self.reading)
        self.assertIn('01-100001-01', result)
        self.assertIn('1.25 kWh', result)

    def test_reading_subscriber_relation(self):
        self.assertEqual(self.reading.subscriber, self.subscriber)
        self.assertEqual(self.subscriber.readings.count(), 1)

    def test_reading_tou_choices(self):
        for period in ['off_peak', 'partial_peak', 'peak']:
            reading = MeterReading.objects.create(
                subscriber=self.subscriber,
                timestamp=timezone.now() + timezone.timedelta(hours=MeterReading.objects.count()),
                kwh=0.5,
                power_kw=2.0,
                tou_period=period,
            )
            self.assertEqual(reading.tou_period, period)

    def test_reading_optional_fields(self):
        self.assertIsNone(self.reading.voltage)
        self.assertIsNone(self.reading.current_amps)
        self.assertIsNone(self.reading.power_factor)

    def test_reading_with_optional_fields(self):
        reading = MeterReading.objects.create(
            subscriber=self.subscriber,
            timestamp=timezone.now() + timezone.timedelta(hours=10),
            kwh=0.8,
            power_kw=3.2,
            tou_period='off_peak',
            voltage=230.5,
            current_amps=14.0,
            power_factor=0.95,
        )
        self.assertAlmostEqual(reading.voltage, 230.5)
        self.assertAlmostEqual(reading.current_amps, 14.0)
        self.assertAlmostEqual(reading.power_factor, 0.95)

    def test_cascade_delete(self):
        """Deleting subscriber should delete all readings."""
        self.subscriber.delete()
        self.assertEqual(MeterReading.objects.count(), 0)


class OptimizationPlanModelTest(TestCase):
    """Test the OptimizationPlan and PlanCheckpoint models."""

    def setUp(self):
        self.subscriber = Subscriber.objects.create(
            subscription_number='01-100002-01',
            phone_number='+962791000002',
            name='Sara',
        )
        self.plan = OptimizationPlan.objects.create(
            subscriber=self.subscriber,
            detected_pattern='3 kW spike every day at 7 PM for 4 hours',
            detection_data={'spike_hour': 19, 'avg_power_kw': 7.5},
            user_hypothesis='EV charging when I get home',
            plan_summary='Shift EV charging to 1 AM off-peak',
            plan_details={
                'actions': [
                    {'action': 'Set EV timer to 1 AM', 'expected_savings_fils_per_day': 200}
                ],
                'monitoring_period_days': 7,
            },
            baseline_daily_kwh=28.5,
            baseline_peak_kwh=12.3,
            baseline_monthly_cost_fils=45000,
            status='active',
            verify_after_date=date(2026, 2, 14),
        )

    def test_plan_creation(self):
        self.assertEqual(OptimizationPlan.objects.count(), 1)

    def test_plan_str(self):
        result = str(self.plan)
        self.assertIn('01-100002-01', result)
        self.assertIn('Shift EV charging', result)

    def test_plan_defaults(self):
        self.assertEqual(self.plan.status, 'active')
        self.assertIsNone(self.plan.verification_result)

    def test_plan_json_fields(self):
        self.assertEqual(self.plan.detection_data['spike_hour'], 19)
        self.assertEqual(len(self.plan.plan_details['actions']), 1)

    def test_plan_subscriber_relation(self):
        self.assertEqual(self.subscriber.plans.count(), 1)

    def test_checkpoint_creation(self):
        checkpoint = PlanCheckpoint.objects.create(
            plan=self.plan,
            check_date=date(2026, 2, 10),
            avg_daily_kwh=25.0,
            avg_peak_kwh=9.5,
            avg_offpeak_kwh=10.2,
            estimated_cost_fils_per_day=1500,
            change_vs_baseline_percent=-12.3,
            notes='Good progress',
        )
        self.assertEqual(PlanCheckpoint.objects.count(), 1)
        self.assertEqual(self.plan.checkpoints.count(), 1)
        self.assertAlmostEqual(checkpoint.change_vs_baseline_percent, -12.3)

    def test_plan_cascade_delete(self):
        """Deleting subscriber should delete plans and checkpoints."""
        PlanCheckpoint.objects.create(
            plan=self.plan,
            check_date=date(2026, 2, 10),
            avg_daily_kwh=25.0,
            avg_peak_kwh=9.5,
            avg_offpeak_kwh=10.2,
            estimated_cost_fils_per_day=1500,
            change_vs_baseline_percent=-12.3,
        )
        self.subscriber.delete()
        self.assertEqual(OptimizationPlan.objects.count(), 0)
        self.assertEqual(PlanCheckpoint.objects.count(), 0)


class AdminRegistrationTest(TestCase):
    """Test that all models are registered in Django admin."""

    def test_subscriber_registered(self):
        self.assertIn(Subscriber, admin_site._registry)

    def test_meter_reading_registered(self):
        self.assertIn(MeterReading, admin_site._registry)

    def test_optimization_plan_registered(self):
        self.assertIn(OptimizationPlan, admin_site._registry)

    def test_plan_checkpoint_registered(self):
        self.assertIn(PlanCheckpoint, admin_site._registry)

    def test_admin_accessible(self):
        from django.contrib.auth.models import User
        User.objects.create_superuser('testadmin', 'test@test.com', 'testpass')
        client = Client()
        client.login(username='testadmin', password='testpass')
        response = client.get('/admin/')
        self.assertEqual(response.status_code, 200)
