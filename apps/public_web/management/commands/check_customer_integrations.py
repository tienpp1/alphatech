"""Report customer OAuth/email configuration without exposing credentials."""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Show redacted Google OAuth and customer email configuration status"

    def handle(self, *args, **options):
        configured_redirect = settings.GOOGLE_REDIRECT_URI
        redirect_valid = bool(configured_redirect) and (
            configured_redirect.startswith("https://")
            or (
                settings.DEBUG
                and configured_redirect.startswith(("http://localhost", "http://127.0.0.1"))
            )
        )
        active_redirect = configured_redirect if redirect_valid else ""
        rows = {
            "EMAIL_BACKEND": settings.EMAIL_BACKEND,
            "EMAIL_HOST": settings.EMAIL_HOST,
            "EMAIL_PORT": settings.EMAIL_PORT,
            "EMAIL_USE_TLS": settings.EMAIL_USE_TLS,
            "EMAIL_USE_SSL": settings.EMAIL_USE_SSL,
            "EMAIL_HOST_USER_PRESENT": bool(settings.EMAIL_HOST_USER),
            "EMAIL_HOST_PASSWORD_PRESENT": bool(settings.EMAIL_HOST_PASSWORD),
            "DEFAULT_FROM_EMAIL": settings.DEFAULT_FROM_EMAIL,
            "PUBLIC_BASE_URL": getattr(settings, "PUBLIC_BASE_URL", ""),
            "GOOGLE_CLIENT_ID_PRESENT": bool(settings.GOOGLE_CLIENT_ID),
            "GOOGLE_CLIENT_SECRET_PRESENT": bool(settings.GOOGLE_CLIENT_SECRET),
            "ACTIVE_GOOGLE_REDIRECT_URI": active_redirect,
            "GOOGLE_REDIRECT_URI_VALID": redirect_valid,
        }
        for key, value in rows.items():
            self.stdout.write(f"{key}={value}")

        smtp_ready = bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)
        oauth_ready = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET and redirect_valid)
        self.stdout.write(self.style.SUCCESS(f"SMTP_CONFIGURED={smtp_ready}"))
        self.stdout.write(self.style.SUCCESS(f"GOOGLE_OAUTH_CONFIGURED={oauth_ready}"))
