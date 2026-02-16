"""
WSGI config for config project.
"""

import os
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Auto-seed demo data on first deploy (when AUTO_SEED=1)
if os.environ.get('AUTO_SEED') == '1':
    try:
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            logging.info('AUTO_SEED: Seeding demo data...')
            from django.core.management import call_command
            call_command('seed_demo')
            call_command('seed_washer')
            logging.info('AUTO_SEED: Done.')
        else:
            logging.info('AUTO_SEED: Data exists, skipping.')
    except Exception as e:
        logging.error('AUTO_SEED failed: %s', e)
