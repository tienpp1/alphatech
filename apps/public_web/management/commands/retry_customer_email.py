from django.core.management.base import BaseCommand, CommandError

from apps.public_web.email_service import deliver_outbox_record
from apps.public_web.models import CustomerEmailDelivery


class Command(BaseCommand):
    help = "Retry a bounded number of pending or failed customer emails."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--public-id")

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit < 1 or limit > 100:
            raise CommandError("--limit must be between 1 and 100")

        queryset = CustomerEmailDelivery.objects.filter(
            status__in=(CustomerEmailDelivery.Status.PENDING, CustomerEmailDelivery.Status.FAILED)
        ).order_by("created_at")
        if options["public_id"]:
            queryset = queryset.filter(public_id=options["public_id"])

        sent = failed = 0
        for delivery in queryset[:limit]:
            result = deliver_outbox_record(delivery)
            if result:
                sent += 1
            else:
                failed += 1
        self.stdout.write(f"processed={sent + failed} sent={sent} failed={failed}")
