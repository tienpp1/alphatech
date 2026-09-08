"""
Management command to purge soft-deleted products that have exceeded their retention period (default 7 days).
"""

import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from apps.retail.models import Product, ProductImage
from apps.audit.services import log_action
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = "Purge soft-deleted products older than the retention threshold (default: 7 days)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the purge without modifying the database or removing files.",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Retention period in days (default: 7). Products deleted prior to this will be purged.",
        )
        parser.add_argument(
            "--workspace",
            type=str,
            default=None,
            help="Optional workspace code or UUID to restrict the purge operation.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        retention_days = options["days"]
        workspace_param = options["workspace"]

        now = timezone.now()
        cutoff_date = now - timedelta(days=retention_days)

        qs = Product.objects.filter(deleted_at__lte=cutoff_date).select_related("workspace", "category")

        if workspace_param:
            ws = Workspace.objects.filter(code=workspace_param).first()
            if not ws:
                try:
                    ws = Workspace.objects.filter(id=workspace_param).first()
                except Exception:
                    ws = None
            if ws:
                qs = qs.filter(workspace=ws)
            else:
                self.stderr.write(self.style.ERROR(f"Workspace '{workspace_param}' not found."))
                return

        total_eligible = qs.count()

        mode_str = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            self.style.NOTICE(
                f"{mode_str}Searching for soft-deleted products deleted on or before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')} (Retention: {retention_days} days)..."
            )
        )
        self.stdout.write(f"Found {total_eligible} eligible product(s) for permanent purge.")

        purged_count = 0
        skipped_count = 0
        images_cleaned_count = 0

        for product in qs:
            prod_id = product.id
            prod_sku = product.sku
            prod_name = product.name
            ws = product.workspace
            has_orders = product.order_items.exists()

            if has_orders:
                # To preserve historical order data integrity, do not hard-delete referenced products
                self.stdout.write(
                    self.style.WARNING(
                        f"  - SKIPPED: Product #{prod_id} [{prod_sku}] '{prod_name}' has {product.order_items.count()} historical order item(s). Preserved for transaction integrity."
                    )
                )
                skipped_count += 1
                continue

            if dry_run:
                img_count = product.images.count()
                self.stdout.write(
                    f"  - [WOULD PURGE]: Product #{prod_id} [{prod_sku}] '{prod_name}' (Deleted: {product.deleted_at.strftime('%Y-%m-%d')}, Images: {img_count})"
                )
                purged_count += 1
                images_cleaned_count += img_count
            else:
                try:
                    with transaction.atomic():
                        # 1. Clean physical image files safely
                        for img in product.images.all():
                            try:
                                if img.image and hasattr(img.image, "path") and os.path.isfile(img.image.path):
                                    img.image.delete(save=False)
                                    images_cleaned_count += 1
                            except Exception:
                                pass

                        # 2. Delete database record
                        product.delete()

                        # 3. Log Audit Event
                        log_action(
                            workspace=ws,
                            actor_user=None,
                            action="PRODUCT_PURGED_AUTO",
                            entity_type="Product",
                            entity_id=prod_id,
                            changes={
                                "sku": prod_sku,
                                "name": prod_name,
                                "retention_days": retention_days,
                                "deleted_at": str(product.deleted_at),
                            },
                        )
                        purged_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"  - PURGED: Product #{prod_id} [{prod_sku}] '{prod_name}' successfully.")
                        )
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"  - ERROR purging Product #{prod_id} [{prod_sku}]: {str(e)}"))
                    skipped_count += 1

        summary_msg = (
            f"\n{mode_str}Purge Summary:\n"
            f"  - Total eligible: {total_eligible}\n"
            f"  - Successfully purged: {purged_count}\n"
            f"  - Skipped (historical orders/errors): {skipped_count}\n"
            f"  - Associated image files cleaned: {images_cleaned_count}"
        )
        self.stdout.write(self.style.SUCCESS(summary_msg) if not dry_run else self.style.NOTICE(summary_msg))
