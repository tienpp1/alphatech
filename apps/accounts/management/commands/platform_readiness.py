"""Redacted production-readiness diagnostics."""

import json
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


def _configured(value):
    return bool(str(value or "").strip())


class Command(BaseCommand):
    help = "Report redacted application, security, OAuth, email and migration readiness."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--production", action="store_true", help="Evaluate production configuration even when DEBUG is enabled.")
        parser.add_argument("--strict", action="store_true", help="Exit non-zero when production gates are blocked.")

    def handle(self, *args, **options):
        db_ok = True
        db_error = None
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception as exc:  # pragma: no cover - depends on deployment DB
            db_ok = False
            db_error = exc.__class__.__name__

        try:
            migration_plan = MigrationExecutor(connection).migration_plan(
                MigrationExecutor(connection).loader.graph.leaf_nodes()
            )
            migrations_pending = len(migration_plan)
        except Exception as exc:  # pragma: no cover - depends on deployment DB
            migrations_pending = None
            db_error = db_error or exc.__class__.__name__

        production = options["production"] or not settings.DEBUG
        checks = {
            "database": {"ok": db_ok, "pending_migrations": migrations_pending, "error": db_error},
            "email": {
                "backend": settings.EMAIL_BACKEND,
                "host": settings.EMAIL_HOST,
                "port": settings.EMAIL_PORT,
                "tls": settings.EMAIL_USE_TLS,
                "ssl": settings.EMAIL_USE_SSL,
                "username_present": _configured(settings.EMAIL_HOST_USER),
                "password_present": _configured(settings.EMAIL_HOST_PASSWORD),
                "tls_ssl_conflict": bool(settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL),
            },
            "oauth": {
                "client_id_present": _configured(settings.GOOGLE_CLIENT_ID),
                "client_secret_present": _configured(settings.GOOGLE_CLIENT_SECRET),
                "redirect_uri": settings.GOOGLE_REDIRECT_URI or None,
                "https_required": production,
                "https_redirect": bool((settings.GOOGLE_REDIRECT_URI or "").lower().startswith("https://")),
            },
            "security": {
                "debug": settings.DEBUG,
                "ssl_redirect": settings.SECURE_SSL_REDIRECT,
                "session_cookie_secure": settings.SESSION_COOKIE_SECURE,
                "csrf_cookie_secure": settings.CSRF_COOKIE_SECURE,
                "hsts_seconds": settings.SECURE_HSTS_SECONDS,
                "content_type_nosniff": settings.SECURE_CONTENT_TYPE_NOSNIFF,
                "csp_report_only": getattr(settings, "CSP_REPORT_ONLY", False),
                "csp_enforce": getattr(settings, "CSP_ENFORCE", False),
                "public_base_url": settings.PUBLIC_BASE_URL or None,
            },
            "observability": {
                "sentry_configured": _configured(getattr(settings, "SENTRY_DSN", "")),
                "otlp_configured": _configured(getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "")),
                "service_name": getattr(settings, "OTEL_SERVICE_NAME", "ai-business-platform"),
            },
        }
        blockers = []
        if not db_ok or migrations_pending is None or migrations_pending:
            blockers.append("database")
        if production and settings.DEBUG:
            blockers.append("debug_enabled")
        if production and settings.EMAIL_BACKEND != "django.core.mail.backends.smtp.EmailBackend":
            blockers.append("smtp_backend_required")
        if settings.EMAIL_USE_TLS and settings.EMAIL_USE_SSL:
            blockers.append("email_tls_ssl_conflict")
        if production and (not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD):
            blockers.append("smtp_credentials")
        if production and (not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET):
            blockers.append("google_credentials")
        if production and not checks["oauth"]["https_redirect"]:
            blockers.append("https_oauth_redirect")
        if production and not (settings.SECURE_SSL_REDIRECT and settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE):
            blockers.append("secure_transport_cookies")
        if production and not (_configured(getattr(settings, "SENTRY_DSN", "")) or _configured(getattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", ""))):
            blockers.append("observability")

        result = {
            "status": "READY" if not blockers else "BLOCKED",
            "scope": "production_configuration" if production else "local_configuration",
            "live_verification": "NOT_VERIFIED_BY_THIS_COMMAND",
            "blockers": blockers, "checks": checks,
        }
        if options["as_json"]:
            self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            self.stdout.write(f"status={result['status']}")
            self.stdout.write(f"blockers={','.join(blockers) if blockers else 'none'}")
            self.stdout.write(f"email_backend={settings.EMAIL_BACKEND}")
            self.stdout.write(f"oauth_redirect={settings.GOOGLE_REDIRECT_URI or 'unset'}")
            self.stdout.write(f"pending_migrations={migrations_pending}")
        if options["strict"] and blockers:
            raise SystemExit(1)
