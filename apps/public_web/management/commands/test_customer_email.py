"""
Management command to test customer email delivery.
Usage:
    python manage.py test_customer_email recipient@gmail.com
"""

import uuid

from django.core.management.base import BaseCommand
from django.conf import settings
from apps.public_web.email_service import send_customer_welcome_email


class Command(BaseCommand):
    help = "Test customer email sending via configured EMAIL_BACKEND / SMTP"

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Recipient email address (e.g. your_email@gmail.com)")

    def handle(self, *args, **options):
        recipient = options["email"].strip()
        backend = getattr(settings, "EMAIL_BACKEND", "")
        host = getattr(settings, "EMAIL_HOST", "")
        port = getattr(settings, "EMAIL_PORT", "")

        self.stdout.write("--- CURRENT EMAIL CONFIGURATION ---")
        self.stdout.write(f"EMAIL_BACKEND   : {backend}")
        self.stdout.write(f"EMAIL_HOST      : {host}")
        self.stdout.write(f"EMAIL_PORT      : {port}")
        self.stdout.write(f"EMAIL_HOST_USER_PRESENT : {bool(getattr(settings, 'EMAIL_HOST_USER', ''))}")
        self.stdout.write(f"Sending test email to: {recipient}\n")

        success = send_customer_welcome_email(
            user_email=recipient,
            name="Khach Hang Thu Nghiem",
            customer_code="CUST-TEST-EMAIL",
            phone="0912345678",
            deduplication_key=f"diagnostic:{uuid.uuid4().hex}",
        )

        if success:
            self.stdout.write(
                "\n[ACCEPTED]: The configured email backend accepted one message. "
                "This does not prove inbox delivery; confirm Inbox/Spam separately."
            )
        else:
            self.stdout.write(
                f"\n[FAILED]: Delivery was not accepted (code={success.error_code}). "
                "Check the redacted integration diagnostic and retry after correcting configuration."
            )
