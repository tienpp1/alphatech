"""Isolated local evidence tests; never reuse DATABASE_URL or a business DB.

Run only with manage.py test --settings=config.settings_evidence_test --noinput.
Each process uses a fresh randomized test database; no existing DB is reset.
Omit --keepdb so successful runs destroy their own temporary database.
"""
import os
import sys
import uuid
from django.core.exceptions import ImproperlyConfigured

# Disable telemetry before base settings initialize exporters (including .env).
os.environ['SENTRY_DSN'] = ''
os.environ['OTEL_EXPORTER_OTLP_ENDPOINT'] = ''
from .settings import *  # noqa: F403,F401

if 'test' not in sys.argv:
    raise ImproperlyConfigured('Evidence settings are restricted to the test command.')

_host = os.getenv('EVIDENCE_DB_HOST', os.getenv('DB_HOST', '127.0.0.1'))
if _host not in ('localhost', '127.0.0.1', '::1'):
    raise ImproperlyConfigured('Evidence tests require a loopback PostgreSQL host.')
_password = os.getenv('EVIDENCE_DB_PASSWORD', os.getenv('DB_PASSWORD', ''))
if not _password:
    raise ImproperlyConfigured('Configure a local database password; do not paste it into chat.')

EVIDENCE_RUN_ID = uuid.uuid4().hex[:16]
EVIDENCE_REPORT_DIR = BASE_DIR / 'output' / 'evidence_tests' / EVIDENCE_RUN_ID
DATABASES = {'default': {
    'ENGINE': 'django.contrib.gis.db.backends.postgis',
    'NAME': 'postgres',
    'USER': os.getenv('EVIDENCE_DB_USER', os.getenv('DB_USER', 'postgres')),
    'PASSWORD': _password,
    'HOST': _host,
    'PORT': os.getenv('EVIDENCE_DB_PORT', os.getenv('DB_PORT', '5432')),
    'CONN_MAX_AGE': 0,
    'OPTIONS': {'connect_timeout': 5},
    'TEST': {'NAME': 'test_alphatech_evidence_' + EVIDENCE_RUN_ID},
}}
DEBUG = True
FORECAST_ASYNC_ENABLED = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']
LLM_API_KEY = ''
GEMINI_API_KEY = ''
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
BREVO_API_KEY = ''
MEDIA_ROOT = EVIDENCE_REPORT_DIR / 'media'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
