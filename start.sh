#!/bin/bash
set -e

echo "=== Railway Startup ==="
echo "PORT=$PORT"

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput || true

echo "=== Starting gunicorn on port ${PORT:-8000} ==="
exec gunicorn config.wsgi --bind "0.0.0.0:${PORT:-8000}" --log-level info --timeout 120
