"""Management command to check and verify due optimization plans."""

from django.core.management.base import BaseCommand
from notifications.tasks import check_plan_verifications


class Command(BaseCommand):
    help = "Check optimization plans that are due for verification and notify subscribers via WhatsApp."

    def handle(self, *args, **options):
        self.stdout.write("Checking plan verifications...")
        verified = check_plan_verifications()
        self.stdout.write(self.style.SUCCESS(f"Done. {verified} plan(s) verified and notified."))
