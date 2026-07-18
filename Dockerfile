FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY strava_print ./strava_print
COPY strava_print_web ./strava_print_web
COPY studio ./studio
COPY templates ./templates
COPY web_templates ./web_templates
COPY manage.py ./

RUN pip install --no-cache-dir ".[production]" \
    && python manage.py collectstatic --noinput

RUN adduser --disabled-password --gecos "" appuser \
    && mkdir -p /app/media \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate && gunicorn strava_print_web.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 300"]
