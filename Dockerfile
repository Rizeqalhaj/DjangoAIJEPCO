FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput 2>/dev/null || true

CMD python manage.py migrate --noinput && gunicorn config.wsgi --bind 0.0.0.0:$PORT --log-level info --access-logfile - --error-logfile -
