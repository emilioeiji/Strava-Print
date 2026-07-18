"""WSGI application for production servers."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "strava_print_web.settings")
application = get_wsgi_application()
