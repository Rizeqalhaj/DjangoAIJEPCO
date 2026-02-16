import os
import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SeedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'seed'

    def ready(self):
        if os.environ.get('AUTO_SEED') != '1':
            return
        # Only run in the main process (not in migrate/collectstatic)
        if os.environ.get('RUN_MAIN') == 'true':
            return
        try:
            from django.contrib.auth.models import User
            if not User.objects.filter(username='admin').exists():
                logger.info('AUTO_SEED: No admin user found, running seed_demo...')
                from django.core.management import call_command
                call_command('seed_demo')
                call_command('seed_washer')
                logger.info('AUTO_SEED: Seeding complete.')
            else:
                logger.info('AUTO_SEED: Data already exists, skipping.')
        except Exception as e:
            logger.error('AUTO_SEED failed: %s', e)
