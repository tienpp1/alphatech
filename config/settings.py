"""
Django settings for AI Business Operations Platform project.
"""

from pathlib import Path
import os
import sys
import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

DATABASES = {
    'default': dj_database_url.config(
        default=f"postgres://{os.getenv('DB_USER', 'postgres')}:{os.getenv('DB_PASSWORD', 'postgres')}@{os.getenv('DB_HOST', '127.0.0.1')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'ai_business_platform_db')}",
        conn_max_age=600
    )
}
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add apps folder to Python path
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Windows PostGIS GDAL / GEOS Path Configuration
if sys.platform == "win32":
    _pg_bin = os.getenv("POSTGRES_BIN_PATH", r"C:\Program Files\PostgreSQL\18\bin")
    if os.path.exists(_pg_bin):
        try:
            os.add_dll_directory(_pg_bin)
        except AttributeError:
            pass
        if _pg_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = _pg_bin + os.pathsep + os.environ.get("PATH", "")
        _gdal_dll = os.path.join(_pg_bin, "libgdal-35.dll")
        _geos_dll = os.path.join(_pg_bin, "libgeos_c.dll")
        if os.path.exists(_gdal_dll):
            os.environ.setdefault("GDAL_LIBRARY_PATH", _gdal_dll)
            GDAL_LIBRARY_PATH = _gdal_dll
        if os.path.exists(_geos_dll):
            os.environ.setdefault("GEOS_LIBRARY_PATH", _geos_dll)
            GEOS_LIBRARY_PATH = _geos_dll

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-ai-business-platform-default-key-change-in-production-2026",
)

DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver").split(",")
    if host.strip()
]

# Application definition

INSTALLED_APPS = [
    # Django built-in & GIS apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    # Third-party apps
    "rest_framework",
    "rest_framework.authtoken",
    # Platform Core (Phase 2)
    "apps.accounts",
    "apps.workspaces",
    # Audit & Security Foundation
    "apps.audit",
    # Retail Business Operations (Phase 3)
    "apps.retail",
    # Service Operations (Phase 4)
    "apps.service_ops",
    # Spatial GIS & GeoDjango Analytics (Phase 5)
    "apps.gis",
    # Data Integration & Ingestion (Phase 6)
    "apps.integration",
    # Data Mapping Engine & Standard Data Model (Phase 7)
    "apps.mapping",
    # RAG + Knowledge Base + Grounded LLM Assistant (Phase 8)
    "apps.knowledge",
    # Predictive Analytics & XGBoost Forecasting (Phase 9)
    "apps.forecasting",
    # Decision Support & Recommendations (Phase 10)
    "apps.recommendations",
    # Controlled Tool Calling & Approvals (Phase 10)
    "apps.approvals",
    # Public Business Website & Customer Experience
    "apps.public_web",
    # Internal Notification Center & Bell System
    "apps.notifications",
]


AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "/dang-nhap/"
LOGIN_REDIRECT_URL = "/tai-khoan/"
LOGOUT_REDIRECT_URL = "/"

# Email Configuration (SMTP / Console)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "").strip()

# When real SMTP credentials (EMAIL_HOST_USER & EMAIL_HOST_PASSWORD) are provided, activate SMTP backend
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
else:
    EMAIL_BACKEND = os.getenv(
        "EMAIL_BACKEND",
        "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
    )

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True").lower() in ("true", "1", "t")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False").lower() in ("true", "1", "t")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER or "noreply@abctech.vn")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000" if DEBUG else "").strip().rstrip("/")

if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("EMAIL_USE_TLS and EMAIL_USE_SSL cannot both be enabled.")

# Google Identity Services / OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "").strip()
GOOGLE_OAUTH_USE_ENV_PROXY = os.getenv("GOOGLE_OAUTH_USE_ENV_PROXY", "False").lower() in ("true", "1", "t")



MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "config.middleware.RequestCorrelationIdMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.workspaces.middleware.WorkspaceMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# Production security posture is opt-in so local development and test clients
# continue to use HTTP.  The readiness command reports missing production
# values without ever printing secrets.
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ("true", "1", "t")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "t")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() in ("true", "1", "t")
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() in ("true", "1", "t")
SECURE_HSTS_PRELOAD = os.getenv("SECURE_HSTS_PRELOAD", "False").lower() in ("true", "1", "t")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = os.getenv("SECURE_REFERRER_POLICY", "same-origin")
SECURE_CROSS_ORIGIN_OPENER_POLICY = os.getenv("SECURE_CROSS_ORIGIN_OPENER_POLICY", "same-origin")

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.workspaces.context_processors.workspace_context",
                "apps.public_web.context_processors.cart_context",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database Configuration
# Uses PostGIS by default with configuration parameters from .env
DB_ENGINE = os.getenv("DB_ENGINE", "django.contrib.gis.db.backends.postgis")
DB_NAME = os.getenv("DB_NAME", "ai_business_platform_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASES = {
    "default": {
        "ENGINE": DB_ENGINE,
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
    }
}

# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Ho_Chi_Minh"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework Settings
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(os.getenv("DEFAULT_PAGE_SIZE", "20")),
}

# Platform Custom Settings
WORKSPACE_DEFAULT = os.getenv("WORKSPACE_DEFAULT", "retail")

# Phase 8: RAG, Embedding & Knowledge Assistant Settings
RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "100"))
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.70"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "768"))
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))

# Phase 9: Predictive Analytics & XGBoost Forecasting
FORECASTING_ARTIFACTS_DIR = BASE_DIR / "ml_models" / "forecasting"
FORECASTING_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
FORECAST_DEFAULT_HORIZON_DAYS = int(os.getenv("FORECAST_DEFAULT_HORIZON_DAYS", "14"))
FORECAST_DEFAULT_TEST_SIZE = float(os.getenv("FORECAST_DEFAULT_TEST_SIZE", "0.20"))
FORECAST_DEFAULT_ESTIMATORS = int(os.getenv("FORECAST_DEFAULT_ESTIMATORS", "100"))
FORECAST_DEFAULT_MAX_DEPTH = int(os.getenv("FORECAST_DEFAULT_MAX_DEPTH", "4"))
FORECAST_DEFAULT_LEARNING_RATE = float(os.getenv("FORECAST_DEFAULT_LEARNING_RATE", "0.05"))

# ==============================================================================
# Phase 11: Production Security Hardening & Logging
# ==============================================================================

# Authentication URL Routing
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Session & CSRF Cookie Security
SESSION_COOKIE_HTTPONLY = True
# CSRF_COOKIE_HTTPONLY = False is intentionally configured to allow browser JavaScript/AJAX
# fetch handlers (Leaflet maps, Chart.js filters, AI Knowledge Chat, Approval actions) to read
# the 'csrftoken' cookie and supply it via the standard 'X-CSRFToken' request header.
CSRF_COOKIE_HTTPONLY = False
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# LEGACY / DEPRECATED: SECURE_BROWSER_XSS_FILTER sets the 'X-XSS-Protection: 1; mode=block' header.
# Modern browsers (Chrome, Firefox, Edge, Safari) have deprecated/removed this header because
# it can introduce client-side vulnerabilities. It is NOT the primary XSS defense.
# The primary XSS defenses in this project are Django's automatic HTML template escaping,
# safe parameter binding in queries, and Content Security Policy (CSP).
SECURE_BROWSER_XSS_FILTER = True

# Content Security Policy (CSP) Evaluation:
# Evaluated conservatively in Report-Only mode to avoid breaking Leaflet (OpenStreetMap tiles),
# Chart.js, and template AJAX components. Full enforcement can be scheduled as a future hardening step.
CSP_REPORT_ONLY = os.getenv("CSP_REPORT_ONLY", "True").lower() in ("true", "1", "t")
CSP_ENFORCE = os.getenv("CSP_ENFORCE", "False").lower() in ("true", "1", "t")

SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "ai-business-platform").strip()

# Production SSL / HTTPS flags (Configurable via env; defaults safe for local development/tests)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ("true", "1", "t")
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "t")
CSRF_COOKIE_SECURE = os.getenv("CSRF_COOKIE_SECURE", "False").lower() in ("true", "1", "t")

# Standard Structured Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}
