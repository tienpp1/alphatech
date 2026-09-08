"""
Management command to purge old notifications based on retention policy.
Example usage:
    python manage.py purge_old_notifications --days=90
    python manage.py purge_old_notifications --days=30 --dry-run
"""

from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.models import Notification


class Command(BaseCommand):
    help = "Purges notifications older than specified number of days (default: 90 days)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Number of retention days to keep (default: 90 days).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the purge and output count without deleting rows.",
        )
        parser.add_argument(
            "--include-unread",
            action="store_true",
            help="Also purge unread notifications older than the threshold.",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        include_unread = options["include_unread"]

        cutoff_date = timezone.now() - timedelta(days=days)
        qs = Notification.objects.filter(created_at__lt=cutoff_date)

        if not include_unread:
            qs = qs.filter(is_read=True)

        count = qs.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY-RUN] Found {count} notifications older than {days} days to purge."
                )
            )
            return

        deleted_count, _ = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully purged {deleted_count} notifications older than {days} days."
            )
        )
