"""
Seed a subscriber with a clear daily washing machine pattern at 20:00-21:00.

Usage:
    python manage.py seed_washer
    python manage.py seed_washer --clear
"""

import random
import numpy as np
from datetime import timedelta
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.models import Subscriber
from meter.models import MeterReading
from tariff.engine import get_tou_period, JORDAN_TZ
from core.clock import now as clock_now


SUB_NUMBER = "01-100006-01"
PHONE = "+962791000006"
NAME = "رنا الحسيني"
USERNAME = "rana"


class Command(BaseCommand):
    help = "Create subscriber #6 with daily 8-9pm washing machine pattern."

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=90,
            help='Days of data to generate (default 90)',
        )
        parser.add_argument(
            '--clear', action='store_true',
            help='Delete this subscriber first, then recreate',
        )

    def handle(self, *args, **options):
        days = options['days']

        if options['clear']:
            deleted = Subscriber.objects.filter(
                subscription_number=SUB_NUMBER
            ).delete()
            self.stdout.write(self.style.WARNING(
                f"Cleared: {deleted[0]} objects deleted."
            ))

        subscriber, created = Subscriber.objects.get_or_create(
            subscription_number=SUB_NUMBER,
            defaults={
                'phone_number': PHONE,
                'name': NAME,
                'area': 'طبربور',
                'governorate': 'Amman',
                'household_size': 3,
                'has_ev': False,
                'has_solar': False,
                'home_size_sqm': 110,
                'tariff_category': 'residential',
                'is_verified': True,
                'language': 'ar',
            },
        )

        # Create Django user
        if not subscriber.user:
            user, u_created = User.objects.get_or_create(
                username=USERNAME,
                defaults={"first_name": NAME},
            )
            if u_created:
                user.set_password("demo123")
                user.save()
                self.stdout.write(f"  Created user: {USERNAME} / demo123")
            subscriber.user = user
            subscriber.save(update_fields=["user"])

        if not created:
            existing = subscriber.readings.count()
            if existing > 0:
                self.stdout.write(
                    f"Subscriber {SUB_NUMBER} already has {existing} readings. "
                    f"Use --clear to recreate."
                )
                return

        self.stdout.write(f"{'Created' if created else 'Using existing'}: {subscriber}")

        readings = self._generate_data(subscriber, days)
        MeterReading.objects.bulk_create(readings, batch_size=1000)

        self.stdout.write(self.style.SUCCESS(
            f"Done! {len(readings)} readings ({days} days) for {SUB_NUMBER}.\n"
            f"Pattern: washing machine ~2 kW spike every day 20:00-21:00 (peak TOU)."
        ))

    def _generate_data(self, subscriber, days: int) -> list:
        """Generate realistic residential data with a clear 8-9pm washing machine spike."""
        now = clock_now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days)
        readings = []

        for day_offset in range(days):
            current_day = start + timedelta(days=day_offset)

            # Washing machine runs almost every day (95%)
            washer_today = random.random() < 0.95

            for interval in range(96):  # 96 x 15min = 24 hours
                ts = current_day + timedelta(minutes=15 * interval)
                hour = ts.hour

                # --- Base load (fridge, standby, etc.) ---
                load_kw = 0.35 + np.random.normal(0, 0.04)

                # --- Morning routine (6-8am): lights, breakfast, water heater ---
                if 6 <= hour < 8:
                    load_kw += 1.0 + np.random.normal(0, 0.2)

                # --- Evening cooking (17-19) ---
                if 17 <= hour < 19:
                    load_kw += 1.5 + np.random.normal(0, 0.3)

                # --- Evening lights, TV, normal activity (18-23) ---
                if 18 <= hour < 23:
                    load_kw += 1.0 + np.random.normal(0, 0.2)

                # --- WASHING MACHINE: 20:00-21:00 every day ---
                if washer_today and 20 <= hour < 21:
                    # Washing machine: ~2.0 kW, very consistent
                    load_kw += 2.0 + np.random.normal(0, 0.15)

                load_kw = max(0.05, load_kw)
                kwh = load_kw / 4.0
                tou = get_tou_period(ts)

                readings.append(MeterReading(
                    subscriber=subscriber,
                    timestamp=ts,
                    kwh=round(kwh, 4),
                    power_kw=round(load_kw, 2),
                    tou_period=tou["period"],
                    is_simulated=True,
                ))

        return readings
