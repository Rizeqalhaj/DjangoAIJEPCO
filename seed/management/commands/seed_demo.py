"""
Seed demo data: 5 subscribers with 90 days of synthetic meter readings.

Usage:
    python manage.py seed_demo
    python manage.py seed_demo --days 30
    python manage.py seed_demo --clear
"""

from django.core.management.base import BaseCommand
from accounts.models import Subscriber
from meter.models import MeterReading
from meter.generator import generate_meter_data


DEMO_SUBSCRIBERS = [
    {
        "subscription_number": "01-100001-01",
        "phone_number": "+962791000001",
        "name": "\u0623\u062d\u0645\u062f \u0627\u0644\u062e\u0627\u0644\u062f\u064a",
        "area": "\u0639\u0628\u062f\u0648\u0646",
        "household_size": 4,
        "has_ev": True,
        "home_size_sqm": 180,
        "profile": "ev_peak_charger",
    },
    {
        "subscription_number": "01-100002-01",
        "phone_number": "+962791000002",
        "name": "\u0633\u0627\u0631\u0629 \u0627\u0644\u0645\u0635\u0631\u064a",
        "area": "\u0627\u0644\u0635\u0648\u064a\u0641\u064a\u0629",
        "household_size": 5,
        "has_ev": False,
        "home_size_sqm": 200,
        "profile": "ac_heavy_summer",
    },
    {
        "subscription_number": "01-100003-01",
        "phone_number": "+962791000003",
        "name": "\u0645\u062d\u0645\u062f \u0627\u0644\u0639\u0628\u0627\u062f\u064a",
        "area": "\u062e\u0644\u062f\u0627",
        "household_size": 3,
        "has_ev": False,
        "home_size_sqm": 120,
        "profile": "water_heater_peak",
    },
    {
        "subscription_number": "01-100004-01",
        "phone_number": "+962791000004",
        "name": "\u0644\u064a\u0646\u0627 \u062d\u062f\u0627\u062f",
        "area": "\u0627\u0644\u062c\u0628\u064a\u0647\u0629",
        "household_size": 6,
        "has_ev": False,
        "home_size_sqm": 220,
        "profile": "baseline_creep",
    },
    {
        "subscription_number": "01-100005-01",
        "phone_number": "+962791000005",
        "name": "\u0639\u0645\u0631 \u0627\u0644\u0632\u0639\u0628\u064a",
        "area": "\u062f\u0627\u0628\u0648\u0642",
        "household_size": 3,
        "has_ev": True,
        "home_size_sqm": 160,
        "profile": "efficient_user",
    },
]


class Command(BaseCommand):
    help = "Create 5 demo subscribers with 90 days of synthetic meter data each."

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=90,
            help='Number of days of historical data to generate (default: 90)',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete existing demo data before creating new data',
        )

    def handle(self, *args, **options):
        days = options['days']

        if options['clear']:
            demo_numbers = [s['subscription_number'] for s in DEMO_SUBSCRIBERS]
            deleted = Subscriber.objects.filter(
                subscription_number__in=demo_numbers
            ).delete()
            self.stdout.write(self.style.WARNING(
                f"Cleared existing demo data ({deleted[0]} objects deleted)."
            ))

        for sub_data in DEMO_SUBSCRIBERS:
            profile = sub_data['profile']
            subscriber, created = Subscriber.objects.get_or_create(
                subscription_number=sub_data['subscription_number'],
                defaults={
                    'phone_number': sub_data['phone_number'],
                    'name': sub_data['name'],
                    'area': sub_data['area'],
                    'governorate': 'Amman',
                    'household_size': sub_data['household_size'],
                    'has_ev': sub_data['has_ev'],
                    'home_size_sqm': sub_data['home_size_sqm'],
                    'tariff_category': 'residential',
                    'is_verified': True,
                }
            )

            if not created:
                self.stdout.write(
                    f"  Subscriber {subscriber.subscription_number} already exists, skipping."
                )
                continue

            self.stdout.write(
                f"  Created: {subscriber.subscription_number} ({profile})"
            )

            readings = generate_meter_data(subscriber, profile, days=days)
            MeterReading.objects.bulk_create(readings, batch_size=1000)
            self.stdout.write(
                f"    -> {len(readings)} readings ({days} days)"
            )

        total_subs = Subscriber.objects.count()
        total_readings = MeterReading.objects.filter(is_simulated=True).count()
        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {total_subs} subscribers, {total_readings} meter readings."
        ))
