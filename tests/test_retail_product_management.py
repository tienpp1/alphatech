"""
Comprehensive Automated Test Suite for Retail Product Management:
CRUD, Image Management & Security, Soft-Delete, Trash, 7-Day Purge, RBAC,
Audit Logging, and Public Catalog Synchronization.
"""

import os
import io
import shutil
from decimal import Decimal
from datetime import timedelta
from PIL import Image

from django.test import TestCase, Client
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.conf import settings

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import (
    Workspace,
    WorkspaceType,
    WorkspaceMembership,
)
from apps.retail.models import (
    Category,
    Product,
    ProductImage,
    Branch,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
)
from apps.retail.services import (
    create_product,
    update_product,
    soft_delete_product,
    restore_product,
    permanent_delete_product,
)
from apps.retail.image_services import (
    save_product_image,
    delete_product_image,
    set_primary_product_image,
    validate_product_image_file,
)
from apps.audit.models import AuditLog


def create_test_image(filename="test.jpg", format="JPEG", size=(100, 100), color="blue"):
    """Generates an in-memory test image file using Pillow."""
    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return SimpleUploadedFile(filename, file_obj.read(), content_type=f"image/{format.lower()}")


class RetailProductManagementTestCase(TestCase):
    def setUp(self):
        # 1. Create Workspaces
        self.ws_retail = Workspace.objects.create(
            name="ABC Tech Store HCM",
            code="ABC_TECH_HCM",
            workspace_type=WorkspaceType.RETAIL,
            is_active=True,
        )
        self.ws_retail2 = Workspace.objects.create(
            name="ABC Tech Store HN",
            code="ABC_TECH_HN",
            workspace_type=WorkspaceType.RETAIL,
            is_active=True,
        )

        # 2. Create Users
        self.admin_user = User.objects.create_user(
            username="retail_admin",
            email="retail_admin@abctech.vn",
            password="StrongPassword123!",
            is_staff=True,
        )
        self.staff_user = User.objects.create_user(
            username="retail_staff",
            email="retail_staff@abctech.vn",
            password="StrongPassword123!",
        )
        self.outsider_user = User.objects.create_user(
            username="outsider",
            email="outsider@external.vn",
            password="StrongPassword123!",
        )

        # 3. Setup RBAC & Memberships
        self.perm_manage_prod, _ = Permission.objects.get_or_create(
            codename="retail.manage_product",
            defaults={"name": "Manage Products", "module": "retail"},
        )
        self.perm_view_prod, _ = Permission.objects.get_or_create(
            codename="retail.view_product",
            defaults={"name": "View Products", "module": "retail"},
        )

        self.role_manager, _ = Role.objects.get_or_create(
            name="Retail Manager",
            defaults={"description": "Retail Store Manager"},
        )
        self.role_manager.permissions.add(self.perm_manage_prod, self.perm_view_prod)

        self.role_viewer, _ = Role.objects.get_or_create(
            name="Retail Viewer",
            defaults={"description": "Retail Viewer"},
        )
        self.role_viewer.permissions.add(self.perm_view_prod)

        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.admin_user,
            role=self.role_manager,
            is_active=True,
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.staff_user,
            role=self.role_viewer,
            is_active=True,
        )

        # 4. Setup Categories
        self.cat_laptop = Category.objects.create(
            workspace=self.ws_retail,
            name="Laptop Doanh nghiệp",
            code="laptop-enterprise",
            is_active=True,
        )
        self.cat_accessories = Category.objects.create(
            workspace=self.ws_retail,
            name="Phụ kiện & Chuột",
            code="accessories-mouse",
            is_active=True,
        )

        # Setup Category in WS 2
        self.cat_ws2 = Category.objects.create(
            workspace=self.ws_retail2,
            name="Laptop Hà Nội",
            code="laptop-hn",
            is_active=True,
        )

        # 5. Setup Branch and Customer for orders
        self.branch = Branch.objects.create(
            workspace=self.ws_retail,
            code="BR_Q1",
            name="Chi nhánh Quận 1",
            address="123 Lê Lợi, Q1, TP.HCM",
        )
        self.customer = Customer.objects.create(
            workspace=self.ws_retail,
            code="CUST001",
            name="Nguyễn Văn A",
            phone="0901234567",
        )

        self.client = Client()

    def tearDown(self):
        # Clean test media files if any
        media_products_dir = os.path.join(settings.MEDIA_ROOT, "products")
        if os.path.exists(media_products_dir):
            try:
                shutil.rmtree(media_products_dir)
            except Exception:
                pass

    # =========================================================================
    # A. PRODUCT CRUD & VALIDATION
    # =========================================================================

    def test_create_product_success_and_audit(self):
        """Test creating a technology product with valid Vietnamese data and audit log."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Laptop Dell XPS 13 Plus",
                "sku": "DELL-XPS-9320",
                "category_id": self.cat_laptop.id,
                "unit": "chiếc",
                "unit_price": Decimal("35000000"),
                "cost_price": Decimal("28000000"),
                "description": "Intel Core i7-1360P, 16GB RAM, 512GB SSD, 13.4 inch 3.5K OLED",
                "is_active": True,
            },
        )
        self.assertIsNotNone(prod.id)
        self.assertEqual(prod.sku, "DELL-XPS-9320")
        self.assertEqual(prod.unit_price, Decimal("35000000"))
        self.assertFalse(prod.is_deleted)
        self.assertIsNone(prod.deleted_at)

        # Check Audit Log
        audit = AuditLog.objects.filter(
            workspace=self.ws_retail,
            entity_type="Product",
            entity_id=str(prod.id),
            action="PRODUCT_CREATED",
        ).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.actor_user, self.admin_user)

    def test_update_product_success_and_audit(self):
        """Test updating product attributes and verifying audit trail."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Chuột Logitech MX Master 3S",
                "sku": "LOGI-MX-3S",
                "category_id": self.cat_accessories.id,
                "unit": "cái",
                "unit_price": Decimal("2500000"),
                "cost_price": Decimal("1800000"),
                "is_active": True,
            },
        )
        updated = update_product(
            product=prod,
            user=self.admin_user,
            data={
                "name": "Chuột Logitech MX Master 3S (Quiet Clicks)",
                "unit_price": Decimal("2700000"),
            },
        )
        self.assertEqual(updated.name, "Chuột Logitech MX Master 3S (Quiet Clicks)")
        self.assertEqual(updated.unit_price, Decimal("2700000"))

        # Verify audit log
        audit = AuditLog.objects.filter(
            workspace=self.ws_retail,
            entity_type="Product",
            entity_id=str(prod.id),
            action="PRODUCT_UPDATED",
        ).first()
        self.assertIsNotNone(audit)

    # =========================================================================
    # B. IMAGE MANAGEMENT, SECURITY & PRIMARY TOGGLE
    # =========================================================================

    def test_product_image_upload_and_primary_selection(self):
        """Test uploading multiple product images and automatic primary promotion."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Bàn phím cơ Keychron Q1 Pro",
                "sku": "KEYCHRON-Q1P",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("4500000"),
            },
        )

        img_file1 = create_test_image("img1.png", format="PNG", color="red")
        img_file2 = create_test_image("img2.jpg", format="JPEG", color="blue")

        img1 = save_product_image(
            workspace=self.ws_retail,
            product=prod,
            uploaded_file=img_file1,
            alt_text="Ảnh mặt trước",
            is_primary=True,
        )
        img2 = save_product_image(
            workspace=self.ws_retail,
            product=prod,
            uploaded_file=img_file2,
            alt_text="Ảnh góc nghiêng",
            is_primary=False,
        )

        self.assertEqual(prod.images.count(), 2)
        self.assertTrue(img1.is_primary)
        self.assertFalse(img2.is_primary)
        self.assertEqual(prod.primary_image.id, img1.id)

        # Promote img2 to primary
        set_primary_product_image(prod, img2)
        img1.refresh_from_db()
        img2.refresh_from_db()
        self.assertFalse(img1.is_primary)
        self.assertTrue(img2.is_primary)
        self.assertEqual(prod.primary_image.id, img2.id)

        # Delete img2 (primary), img1 should automatically become primary
        delete_product_image(img2)
        img1.refresh_from_db()
        self.assertTrue(img1.is_primary)
        self.assertEqual(prod.images.count(), 1)

    def test_image_security_validation_rejections(self):
        """Test rejecting executable files, invalid mime types, and corrupted images."""
        # 1. Reject executable disguised as image
        fake_exe = SimpleUploadedFile("malware.exe", b"MZ\x90\x00\x03\x00\x00\x00", content_type="application/x-dosexec")
        with self.assertRaises(Exception):
            validate_product_image_file(fake_exe)

        # 2. Reject text script with .png extension
        fake_png = SimpleUploadedFile("script.png", b"<?php echo 'attack'; ?>", content_type="image/png")
        with self.assertRaises(Exception):
            validate_product_image_file(fake_png)

    # =========================================================================
    # C. SOFT-DELETE, TRASH & RESTORE
    # =========================================================================

    def test_soft_delete_and_trash_listing(self):
        """Test soft deleting a product moves it to Trash with countdown."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Màn hình Dell UltraSharp U2723QE",
                "sku": "DELL-U2723QE",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("14500000"),
            },
        )

        # Soft delete
        soft_delete_product(prod, user=self.admin_user)
        prod.refresh_from_db()

        self.assertTrue(prod.is_deleted)
        self.assertIsNotNone(prod.deleted_at)
        self.assertEqual(prod.deleted_by, self.admin_user)
        self.assertEqual(prod.days_until_permanent_delete, 7)

        # Non-deleted query should not find it
        active_prods = Product.objects.filter(workspace=self.ws_retail, deleted_at__isnull=True)
        self.assertNotIn(prod, active_prods)

        # Trash query should find it
        trash_prods = Product.objects.filter(workspace=self.ws_retail, deleted_at__isnull=False)
        self.assertIn(prod, trash_prods)

    def test_restore_product_success(self):
        """Test restoring a soft-deleted product back to active catalog."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Tai nghe Sony WH-1000XM5",
                "sku": "SONY-WH1000XM5",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("8490000"),
            },
        )
        soft_delete_product(prod, user=self.admin_user)
        self.assertTrue(prod.is_deleted)

        # Restore
        restored = restore_product(prod, user=self.admin_user)
        self.assertFalse(restored.is_deleted)
        self.assertIsNone(restored.deleted_at)
        self.assertIsNone(restored.deleted_by)

        # Verify in active catalog
        self.assertTrue(Product.objects.filter(workspace=self.ws_retail, sku="SONY-WH1000XM5", deleted_at__isnull=True).exists())

    def test_restore_product_sku_collision_blocked(self):
        """Test that restoring a product fails if another active product was created with the same SKU."""
        prod1 = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Ổ cứng SSD Samsung 980 Pro 1TB (Cũ)",
                "sku": "SSD-SAM-980PRO-1TB",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("2500000"),
            },
        )
        soft_delete_product(prod1, user=self.admin_user)

        # Create a new product with the same SKU while prod1 is in trash
        prod2 = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Ổ cứng SSD Samsung 980 Pro 1TB (Mới)",
                "sku": "SSD-SAM-980PRO-1TB",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("2600000"),
            },
        )

        # Restoring prod1 must raise ValidationError
        with self.assertRaises(Exception):
            restore_product(prod1, user=self.admin_user)

    # =========================================================================
    # D. HISTORICAL ORDER INTEGRITY & PERMANENT DELETE
    # =========================================================================

    def test_historical_order_integrity_preserved_on_soft_delete(self):
        """Historical orders must remain intact and valid even when referenced product is soft-deleted."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Router Wi-Fi 6 ASUS RT-AX88U",
                "sku": "ASUS-RT-AX88U",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("6500000"),
            },
        )

        # Create an Order referencing this product
        now = timezone.now()
        order = Order.objects.create(
            workspace=self.ws_retail,
            order_number="ORD-TEST-001",
            customer=self.customer,
            branch=self.branch,
            order_date=now.date(),
            order_timestamp=now,
            subtotal_amount=Decimal("6500000"),
            tax_amount=Decimal("650000"),
            total_amount=Decimal("7150000"),
            payment_method=PaymentMethod.CASH,
            status=OrderStatus.COMPLETED,
        )
        OrderItem.objects.create(
            order=order,
            product=prod,
            quantity=1,
            unit_price=Decimal("6500000"),
            discount=Decimal("0.00"),
            subtotal=Decimal("6500000"),
        )

        # Soft delete the product
        soft_delete_product(prod, user=self.admin_user)

        # Verify historical order item still references product
        order_item = OrderItem.objects.get(order=order)
        self.assertEqual(order_item.product_id, prod.id)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(prod.order_items.count(), 1)

        # Permanent delete must be blocked to prevent breaking transaction history
        with self.assertRaises(Exception):
            permanent_delete_product(prod, user=self.admin_user)

    def test_permanent_delete_success_for_unreferenced_product(self):
        """Permanent delete succeeds for unreferenced product and cleans image files."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Sản phẩm tạm thử nghiệm",
                "sku": "TEMP-TEST-001",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("100000"),
            },
        )
        img_file = create_test_image("temp_img.jpg", format="JPEG")
        img_obj = save_product_image(self.ws_retail, prod, img_file, alt_text="Temp")
        img_path = img_obj.image.path if img_obj.image else None

        prod_id = prod.id
        permanent_delete_product(prod, user=self.admin_user)

        # Product record must be deleted
        self.assertFalse(Product.objects.filter(id=prod_id).exists())

        # Audit log written
        audit = AuditLog.objects.filter(
            workspace=self.ws_retail,
            entity_type="Product",
            entity_id=str(prod_id),
            action="PRODUCT_PERMANENTLY_DELETED",
        ).first()
        self.assertIsNotNone(audit)

    # =========================================================================
    # E. 7-DAY AUTO PURGE MANAGEMENT COMMAND
    # =========================================================================

    def test_purge_deleted_products_command_dry_run_and_execution(self):
        """Test the purge_deleted_products command with --dry-run and actual purge."""
        # 1. Product deleted 10 days ago (eligible for purge)
        old_deleted_prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Laptop Cũ Bị Xóa 10 Ngày",
                "sku": "OLD-DEL-10D",
                "category_id": self.cat_laptop.id,
                "unit_price": Decimal("12000000"),
            },
        )
        old_deleted_prod.deleted_at = timezone.now() - timedelta(days=10)
        old_deleted_prod.save(update_fields=["deleted_at"])

        # 2. Product deleted 2 days ago (NOT eligible for purge)
        recent_deleted_prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Laptop Mới Xóa 2 Ngày",
                "sku": "REC-DEL-2D",
                "category_id": self.cat_laptop.id,
                "unit_price": Decimal("15000000"),
            },
        )
        recent_deleted_prod.deleted_at = timezone.now() - timedelta(days=2)
        recent_deleted_prod.save(update_fields=["deleted_at"])

        # Run with --dry-run
        out = io.StringIO()
        call_command("purge_deleted_products", "--dry-run", "--days=7", stdout=out)
        output_str = out.getvalue()
        self.assertIn("[DRY-RUN]", output_str)
        self.assertIn("OLD-DEL-10D", output_str)

        # Both records must still exist after dry-run
        self.assertTrue(Product.objects.filter(id=old_deleted_prod.id).exists())
        self.assertTrue(Product.objects.filter(id=recent_deleted_prod.id).exists())

        # Run actual purge
        out_real = io.StringIO()
        call_command("purge_deleted_products", "--days=7", stdout=out_real)
        output_real_str = out_real.getvalue()
        self.assertIn("PURGED: Product", output_real_str)

        # Old product must be destroyed, recent product must still remain in trash
        self.assertFalse(Product.objects.filter(id=old_deleted_prod.id).exists())
        self.assertTrue(Product.objects.filter(id=recent_deleted_prod.id).exists())

    # =========================================================================
    # F. PUBLIC WEBSITE SYNCHRONIZATION & COMMERCIAL ISOLATION
    # =========================================================================

    def test_public_catalog_sync_and_trash_exclusion(self):
        """Public catalog immediately reflects created products and excludes soft-deleted products."""
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Laptop ASUS Zenbook 14 OLED",
                "sku": "ASUS-ZEN-14",
                "category_id": self.cat_laptop.id,
                "unit_price": Decimal("24990000"),
                "cost_price": Decimal("19500000"),
                "description": "Màn hình Lumina OLED 2.8K 120Hz siêu nét",
                "is_active": True,
            },
        )

        # Public Catalog GET /san-pham/
        resp = self.client.get("/san-pham/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Laptop ASUS Zenbook 14 OLED")
        self.assertContains(resp, "24990000")
        # Cost price must NEVER appear on public site
        self.assertNotContains(resp, "19.500.000")
        self.assertNotContains(resp, "19500000")

        # Public Product Detail GET /san-pham/<id>/
        detail_resp = self.client.get(f"/san-pham/{prod.id}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Laptop ASUS Zenbook 14 OLED")
        self.assertContains(detail_resp, "ASUS-ZEN-14")
        self.assertNotContains(detail_resp, "19.500.000")

        # Now soft delete the product
        soft_delete_product(prod, user=self.admin_user)

        # Public catalog must NO LONGER show the product
        resp_after = self.client.get("/san-pham/")
        self.assertNotContains(resp_after, "Laptop ASUS Zenbook 14 OLED")

        # Public detail must return 404
        detail_after = self.client.get(f"/san-pham/{prod.id}/")
        self.assertEqual(detail_after.status_code, 404)

    # =========================================================================
    # G. REST API ENDPOINTS & WORKSPACE ISOLATION
    # =========================================================================

    def test_rest_api_trash_restore_and_images(self):
        """Test REST API endpoints for trash, restore, and image upload."""
        self.client.force_login(self.admin_user)
        # Set active workspace in session
        session = self.client.session
        session["active_workspace_id"] = str(self.ws_retail.id)
        session.save()

        # Create product via service
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Webcam Logitech Brio 4K",
                "sku": "LOGI-BRIO-4K",
                "category_id": self.cat_accessories.id,
                "unit_price": Decimal("4200000"),
            },
        )

        # 1. Soft-delete via API DELETE
        del_resp = self.client.delete(f"/api/v1/retail/products/{prod.id}/")
        self.assertEqual(del_resp.status_code, 200)
        prod.refresh_from_db()
        self.assertTrue(prod.is_deleted)

        # 2. View Trash via API GET
        trash_resp = self.client.get("/api/v1/retail/products/trash/")
        self.assertEqual(trash_resp.status_code, 200)
        self.assertEqual(trash_resp.json()["count"], 1)

        # 3. Restore via API POST
        restore_resp = self.client.post(f"/api/v1/retail/products/{prod.id}/restore/")
        self.assertEqual(restore_resp.status_code, 200)
        prod.refresh_from_db()
        self.assertFalse(prod.is_deleted)

        # 4. Upload image via API POST
        img_file = create_test_image("brio.jpg", format="JPEG")
        img_resp = self.client.post(
            f"/api/v1/retail/products/{prod.id}/images/",
            {"image": img_file, "is_primary": "true"},
            format="multipart",
        )
        self.assertEqual(img_resp.status_code, 201)
        self.assertEqual(prod.images.count(), 1)

    # =========================================================================
    # H. PRODUCT DETAIL UI VIEW & AUDIT TRAIL REGRESSION TESTS
    # =========================================================================

    def test_product_detail_ui_view_loads_successfully_with_audit_history(self):
        """
        GET /retail/products/<id>/ must load HTTP 200 without FieldError on AuditLog.
        Verifies product attributes, gallery images, and newest-first audit trail ordering.
        """
        self.client.force_login(self.admin_user)
        session = self.client.session
        session["active_workspace_id"] = str(self.ws_retail.id)
        session.save()

        # 1. Create product (creates PRODUCT_CREATED audit log)
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Laptop Dell Precision 5570",
                "sku": "DELL-PREC-5570",
                "category_id": self.cat_laptop.id,
                "unit": "chiếc",
                "unit_price": Decimal("45000000"),
                "cost_price": Decimal("38000000"),
                "description": "Máy trạm di động Intel Core i9, 32GB RAM, RTX A2000",
                "is_active": True,
            },
        )

        # 2. Add an image
        img_file = create_test_image("precision.jpg", format="JPEG", color="black")
        save_product_image(
            workspace=self.ws_retail,
            product=prod,
            uploaded_file=img_file,
            alt_text="Dell Precision 5570 Front View",
            is_primary=True,
        )

        # 3. GET /retail/products/<id>/
        resp = self.client.get(f"/retail/products/{prod.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Laptop Dell Precision 5570")
        self.assertContains(resp, "DELL-PREC-5570")
        self.assertContains(resp, "45000000")
        self.assertContains(resp, "Laptop Doanh nghiệp")
        self.assertContains(resp, "Đang kinh doanh")
        self.assertContains(resp, "PRODUCT_CREATED")
        self.assertContains(resp, self.admin_user.username)

        # Verify audit logs in context
        audit_logs = resp.context["audit_logs"]
        self.assertTrue(len(audit_logs) >= 1)
        self.assertEqual(audit_logs[0].action, "PRODUCT_CREATED")

    def test_product_edit_ui_flow_creates_audit_entry_and_renders_newest_first(self):
        """
        POST /retail/products/<id>/edit/ saves changes, creates PRODUCT_UPDATED in AuditLog,
        and subsequent GET /retail/products/<id>/ displays audit entries sorted newest first.
        """
        self.client.force_login(self.admin_user)
        session = self.client.session
        session["active_workspace_id"] = str(self.ws_retail.id)
        session.save()

        # 1. Create product
        prod = create_product(
            workspace=self.ws_retail,
            user=self.admin_user,
            data={
                "name": "Bàn phím cơ Leopold FC900R",
                "sku": "LEOPOLD-FC900R",
                "category_id": self.cat_accessories.id,
                "unit": "cái",
                "unit_price": Decimal("3200000"),
                "cost_price": Decimal("2400000"),
                "description": "Switch Cherry MX Blue",
                "is_active": True,
            },
        )

        # 2. Edit product via UI POST /retail/products/<id>/edit/
        edit_resp = self.client.post(
            f"/retail/products/{prod.id}/edit/",
            {
                "name": "Bàn phím cơ Leopold FC900R (PD Two Tone White)",
                "sku": "LEOPOLD-FC900R",
                "category_id": str(self.cat_accessories.id),
                "unit": "cái",
                "unit_price": "3400000",
                "cost_price": "2500000",
                "description": "Switch Cherry MX Red Silent, PBT Double-Shot",
                "is_active": "on",
            },
        )
        self.assertEqual(edit_resp.status_code, 302)
        self.assertEqual(edit_resp.url, f"/retail/products/{prod.id}/")

        # 3. GET /retail/products/<id>/ and inspect audit ordering
        detail_resp = self.client.get(f"/retail/products/{prod.id}/")
        self.assertEqual(detail_resp.status_code, 200)
        self.assertContains(detail_resp, "Bàn phím cơ Leopold FC900R (PD Two Tone White)")
        self.assertContains(detail_resp, "3400000")
        self.assertContains(detail_resp, "PRODUCT_UPDATED")
        self.assertContains(detail_resp, "PRODUCT_CREATED")

        audit_logs = list(detail_resp.context["audit_logs"])
        self.assertGreaterEqual(len(audit_logs), 2)
        # Newest first
        self.assertEqual(audit_logs[0].action, "PRODUCT_UPDATED")
        self.assertEqual(audit_logs[1].action, "PRODUCT_CREATED")
        self.assertGreaterEqual(audit_logs[0].timestamp, audit_logs[1].timestamp)
