"""
Comprehensive Automated Test Suite for Internal Notification Center & Bell System.
Covers:
- Event triggers: Customer registration, Retail order, Service request, Public contact
- Transaction safety (no notifications on rollback)
- Workspace isolation (Workspace A vs Workspace B)
- Strict IDOR and multi-tenant security
- Customer / unauthenticated access denial
- Deduplication of notifications
- Unread count queries, mark single read, mark all read
- Retention management command (purge_old_notifications)
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase, Client
from django.utils import timezone
from django.db import transaction

from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Product, Category, Customer, Order, OrderStatus, PaymentMethod
from apps.service_ops.models import Service, ServiceCategory, ServiceRequest
from apps.notifications.models import Notification, NotificationEventType
from apps.notifications.services import (
    get_unread_count,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    create_notification,
)


class InternalNotificationsTestCase(TestCase):
    """
    Test suite validating the internal notification center, bell system APIs,
    event triggers, transaction safety, and workspace scoping.
    """

    def setUp(self):
        self.client = Client()

        # 1. Workspaces
        self.ws_retail = Workspace.objects.create(
            name="ABC Tech Store Retail",
            code="WS-RETAIL-NOTIF",
            workspace_type=WorkspaceType.RETAIL,
            is_active=True,
        )
        self.ws_service = Workspace.objects.create(
            name="XYZ IT Services",
            code="WS-SERVICE-NOTIF",
            workspace_type=WorkspaceType.SERVICE,
            is_active=True,
        )
        self.ws_other = Workspace.objects.create(
            name="Other Isolated Workspace",
            code="WS-OTHER-NOTIF",
            workspace_type=WorkspaceType.RETAIL,
            is_active=True,
        )

        # 2. Roles
        self.role_admin, _ = Role.objects.get_or_create(name="ADMIN")
        self.role_manager, _ = Role.objects.get_or_create(name="MANAGER")
        self.role_employee, _ = Role.objects.get_or_create(name="EMPLOYEE")
        self.role_viewer, _ = Role.objects.get_or_create(name="VIEWER")

        # 3. Internal Users
        # Retail Admin
        self.user_retail_admin = User.objects.create_user(
            username="retail_admin@test.vn",
            email="retail_admin@test.vn",
            password="Password123!",
            first_name="Quản trị",
            last_name="Bán lẻ",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.user_retail_admin,
            role=self.role_admin,
            is_default=True,
            is_active=True,
        )

        # Retail Employee
        self.user_retail_staff = User.objects.create_user(
            username="retail_staff@test.vn",
            email="retail_staff@test.vn",
            password="Password123!",
            first_name="Nhân viên",
            last_name="Bán lẻ",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.user_retail_staff,
            role=self.role_employee,
            is_default=True,
            is_active=True,
        )

        # Service Manager
        self.user_service_mgr = User.objects.create_user(
            username="service_mgr@test.vn",
            email="service_mgr@test.vn",
            password="Password123!",
            first_name="Quản lý",
            last_name="Dịch vụ",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_service,
            user=self.user_service_mgr,
            role=self.role_manager,
            is_default=True,
            is_active=True,
        )

        # Other Workspace Admin
        self.user_other_admin = User.objects.create_user(
            username="other_admin@test.vn",
            email="other_admin@test.vn",
            password="Password123!",
            first_name="Admin",
            last_name="Khác",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_other,
            user=self.user_other_admin,
            role=self.role_admin,
            is_default=True,
            is_active=True,
        )

        # Public Customer (No internal membership)
        self.user_customer = User.objects.create_user(
            username="customer_public@test.vn",
            email="customer_public@test.vn",
            password="Password123!",
            first_name="Khách",
            last_name="Hàng",
        )

        # 4. Catalog Sample Data
        self.cat = Category.objects.create(
            workspace=self.ws_retail,
            name="Laptop",
            code="CAT-NOTIF-TEST",
        )
        self.product = Product.objects.create(
            workspace=self.ws_retail,
            category=self.cat,
            name="MacBook Pro M3",
            sku="MBP-M3-NOTIF",
            unit_price=Decimal("45000000.00"),
            is_active=True,
        )
        self.service = Service.objects.create(
            workspace=self.ws_service,
            category=ServiceCategory.MAINTENANCE,
            name="Bảo trì máy chủ định kỳ",
            code="SRV-MAINT-01",
            base_fee=Decimal("2000000.00"),
            is_active=True,
        )

    # =========================================================================
    # A. EVENT: CUSTOMER REGISTRATION
    # =========================================================================

    def test_public_customer_registration_creates_new_customer_notification(self):
        """Successful public registration triggers NEW_CUSTOMER notification for retail admin/manager."""
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                "/dang-ky/",
                {
                    "name": "Nguyễn Văn Đăng Ký",
                    "email": "dangky.moi@testmail.vn",
                    "phone": "0988776655",
                    "password": "SecurePassword123!",
                    "confirm_password": "SecurePassword123!",
                    "terms": "on",
                },
            )
        self.assertEqual(resp.status_code, 302)

        # Check notification received by retail admin
        notif = Notification.objects.filter(
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_CUSTOMER,
        ).first()

        self.assertIsNotNone(notif)
        self.assertIn("Khách hàng mới đăng ký", notif.title)
        self.assertIn("Nguyễn Văn Đăng Ký", notif.message)
        self.assertEqual(notif.workspace, self.ws_retail)
        self.assertFalse(notif.is_read)

        # Ensure employee did not receive (role rules: ADMIN / MANAGER only)
        staff_notif = Notification.objects.filter(
            recipient=self.user_retail_staff,
            event_type=NotificationEventType.NEW_CUSTOMER,
        ).first()
        self.assertIsNone(staff_notif)

    def test_failed_customer_registration_does_not_create_notification(self):
        """Failed customer registration (e.g. mismatched passwords) creates no notification."""
        resp = self.client.post(
            "/dang-ky/",
            {
                "name": "Lỗi Mật Khẩu",
                "email": "loi@testmail.vn",
                "phone": "0988776655",
                "password": "SecurePassword123!",
                "confirm_password": "WrongPassword!",
                "terms": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Notification.objects.filter(message__icontains="Lỗi Mật Khẩu").exists())

    # =========================================================================
    # B. EVENT: RETAIL ORDER & TRANSACTION SAFETY
    # =========================================================================

    def test_public_order_placement_creates_new_order_notification(self):
        """Successful public checkout generates NEW_ORDER notification for retail staff and admins."""
        # 1. Add product to cart
        self.client.post(f"/gio-hang/them/{self.product.id}/", {"quantity": "1"})

        # 2. Place Order with on_commit execution
        with self.captureOnCommitCallbacks(execute=True):
            order_resp = self.client.post(
                "/thanh-toan/dat-hang/",
                {
                    "name": "Trần Đặt Hàng",
                    "phone": "0912345678",
                    "email": "trandathang@testmail.vn",
                    "address": "45 Lê Duẩn, Quận 1",
                    "delivery_method": "HOME_DELIVERY",
                },
            )
        self.assertEqual(order_resp.status_code, 302)

        # Verify notification created for retail admin
        admin_notif = Notification.objects.filter(
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
        ).first()
        self.assertIsNotNone(admin_notif)
        self.assertIn("Đơn hàng mới", admin_notif.title)
        self.assertIn("45.000.000", admin_notif.message)
        self.assertEqual(admin_notif.workspace, self.ws_retail)

        # Verify notification created for retail employee
        staff_notif = Notification.objects.filter(
            recipient=self.user_retail_staff,
            event_type=NotificationEventType.NEW_ORDER,
        ).first()
        self.assertIsNotNone(staff_notif)

        # Verify Service Manager in different workspace did NOT receive retail order notification
        service_notif = Notification.objects.filter(
            recipient=self.user_service_mgr,
            event_type=NotificationEventType.NEW_ORDER,
        ).first()
        self.assertIsNone(service_notif)

    def test_order_transaction_rollback_safety(self):
        """If order creation encounters an exception / rollback, NO notification is committed."""
        count_before = Notification.objects.filter(event_type=NotificationEventType.NEW_ORDER).count()

        customer = Customer.objects.create(
            workspace=self.ws_retail,
            code="CUST-ROLLBACK-TEST",
            name="Khách Rollback",
            email="rollback@test.vn",
        )

        # Force a database transaction rollback
        try:
            with transaction.atomic():
                # Fake temporary order
                fake_order = Order.objects.create(
                    workspace=self.ws_retail,
                    customer=customer,
                    order_number="ORD-FAIL-ROLLBACK",
                    order_date=timezone.now().date(),
                    order_timestamp=timezone.now(),
                    total_amount=Decimal("1000000.00"),
                    payment_method=PaymentMethod.CASH,
                )
                # Register on_commit handler inside transaction
                transaction.on_commit(
                    lambda: create_notification(
                        workspace=self.ws_retail,
                        recipient=self.user_retail_admin,
                        event_type=NotificationEventType.NEW_ORDER,
                        title="Đơn hàng rollback",
                        message="Không bao giờ xuất hiện",
                    )
                )
                # Intentionally trigger an exception to force rollback
                raise ValueError("Simulated database failure during checkout")
        except ValueError:
            pass

        count_after = Notification.objects.filter(event_type=NotificationEventType.NEW_ORDER).count()
        self.assertEqual(count_before, count_after)

    # =========================================================================
    # C. EVENT: SERVICE REQUEST
    # =========================================================================

    def test_public_service_request_creates_service_notification(self):
        """Public service request creates NEW_SERVICE_REQUEST notification for service workspace staff."""
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                "/yeu-cau-dich-vu/",
                {
                    "customer_name": "Lê Văn Server",
                    "phone": "0933221100",
                    "email": "le.server@testmail.vn",
                    "service_id": str(self.service.id),
                    "description": "Cần kiểm tra hệ thống máy chủ bị quá tải nhiệt.",
                },
            )
        self.assertEqual(resp.status_code, 200)

        # Service manager receives notification
        notif = Notification.objects.filter(
            recipient=self.user_service_mgr,
            event_type=NotificationEventType.NEW_SERVICE_REQUEST,
        ).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.workspace, self.ws_service)
        self.assertIn("Yêu cầu dịch vụ mới", notif.title)
        self.assertIn("Bảo trì máy chủ", notif.message)

        # Retail admin should NOT receive service request notification
        retail_notif = Notification.objects.filter(
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_SERVICE_REQUEST,
        ).first()
        self.assertIsNone(retail_notif)

    # =========================================================================
    # D. EVENT: PUBLIC CONTACT SUBMISSION
    # =========================================================================

    def test_public_contact_submission_creates_contact_notification(self):
        """Public visitor contact form submission generates NEW_CONTACT notification."""
        resp = self.client.post(
            "/lien-he/",
            {
                "name": "Bùi Văn Khách",
                "phone": "0944556677",
                "email": "bui.khach@testmail.vn",
                "message": "Tôi muốn báo giá gói 20 máy trạm trọn gói.",
            },
        )
        self.assertEqual(resp.status_code, 200)

        notif = Notification.objects.filter(
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_CONTACT,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIn("Có liên hệ mới", notif.title)
        self.assertIn("Bùi Văn Khách", notif.message)

    # =========================================================================
    # E. UNREAD COUNT, READ & READ ALL APIS
    # =========================================================================

    def test_unread_count_api_and_mark_read_flow(self):
        """Test GET unread-count, POST mark single read, and POST mark all read."""
        # Create 3 unread notifications for retail admin
        n1 = create_notification(self.ws_retail, self.user_retail_admin, NotificationEventType.NEW_ORDER, "Đơn 1", "Tin 1", "Order", "1")
        n2 = create_notification(self.ws_retail, self.user_retail_admin, NotificationEventType.NEW_ORDER, "Đơn 2", "Tin 2", "Order", "2")
        n3 = create_notification(self.ws_retail, self.user_retail_admin, NotificationEventType.NEW_ORDER, "Đơn 3", "Tin 3", "Order", "3")

        self.client.force_login(self.user_retail_admin)

        # 1. Check unread count = 3
        count_resp = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(count_resp.status_code, 200)
        self.assertEqual(count_resp.json()["unread_count"], 3)

        # 2. Mark n1 as read
        read_resp = self.client.post(f"/api/v1/notifications/{n1.id}/read/")
        self.assertEqual(read_resp.status_code, 200)
        self.assertTrue(read_resp.json()["is_read"])
        self.assertEqual(read_resp.json()["unread_count"], 2)

        n1.refresh_from_db()
        self.assertTrue(n1.is_read)
        self.assertIsNotNone(n1.read_at)

        # 3. Mark all as read
        all_resp = self.client.post("/api/v1/notifications/read-all/")
        self.assertEqual(all_resp.status_code, 200)
        self.assertEqual(all_resp.json()["unread_count"], 0)

        # Verify in DB
        self.assertEqual(get_unread_count(self.user_retail_admin, self.ws_retail), 0)

    def test_latest_notifications_api_payload(self):
        """GET /api/v1/notifications/latest/ returns structured notifications with Vietnamese labels."""
        create_notification(
            self.ws_retail,
            self.user_retail_admin,
            NotificationEventType.NEW_ORDER,
            "Đơn hàng mới",
            "Có đơn hàng mới #ORD-101.",
            "Order",
            "101",
            "/retail/orders/101/",
        )

        self.client.force_login(self.user_retail_admin)
        resp = self.client.get("/api/v1/notifications/latest/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(len(data["notifications"]), 1)
        item = data["notifications"][0]
        self.assertEqual(item["event_label"], "Đơn hàng mới")
        self.assertEqual(item["event_icon"], "🛒")
        self.assertEqual(item["title"], "Đơn hàng mới")
        self.assertIn("vừa xong", item["time_ago"])

    # =========================================================================
    # F. WORKSPACE ISOLATION & STRICT IDOR PROTECTION
    # =========================================================================

    def test_workspace_isolation_and_idor_protection(self):
        """
        Notification of Workspace A CANNOT be viewed or marked as read by user in Workspace B.
        API returns 404 for cross-workspace or cross-recipient access.
        """
        # Create notification in Retail Workspace for Retail Admin
        notif_retail = create_notification(
            self.ws_retail,
            self.user_retail_admin,
            NotificationEventType.NEW_ORDER,
            "Đơn Retail",
            "Nội dung bí mật bán lẻ",
            "Order",
            "999",
        )

        # Login as Other Workspace Admin
        self.client.force_login(self.user_other_admin)

        # 1. Other admin's unread count must be 0
        count_resp = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(count_resp.json()["unread_count"], 0)

        # 2. Other admin attempting to mark Retail Admin's notification as read -> 404
        read_attempt = self.client.post(f"/api/v1/notifications/{notif_retail.id}/read/")
        self.assertEqual(read_attempt.status_code, 404)

        # 3. Direct detail access attempt -> 404
        detail_attempt = self.client.get(f"/noibo/thong-bao/{notif_retail.id}/")
        self.assertEqual(detail_attempt.status_code, 404)

        # Notification remains unread in database
        notif_retail.refresh_from_db()
        self.assertFalse(notif_retail.is_read)

    # =========================================================================
    # G. CUSTOMER & UNAUTHENTICATED PROTECTION
    # =========================================================================

    def test_public_customer_cannot_access_internal_notifications(self):
        """Public customer accounts are denied access to internal notification APIs and pages."""
        # Unauthenticated request
        anon_resp = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(anon_resp.status_code, 302)  # Redirects to login

        # Customer account logged in (no internal membership)
        self.client.force_login(self.user_customer)
        cust_api_resp = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(cust_api_resp.status_code, 403)

        cust_ui_resp = self.client.get("/noibo/thong-bao/")
        self.assertEqual(cust_ui_resp.status_code, 302)
        self.assertIn("customer_only", cust_ui_resp.url)

    # =========================================================================
    # H. DEDUPLICATION
    # =========================================================================

    def test_notification_deduplication_prevention(self):
        """Calling create_notification repeatedly for the same entity does not duplicate notifications."""
        n1 = create_notification(
            workspace=self.ws_retail,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
            title="Đơn lặp",
            message="Nội dung",
            entity_type="Order",
            entity_id="9999",
        )
        n2 = create_notification(
            workspace=self.ws_retail,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
            title="Đơn lặp",
            message="Nội dung",
            entity_type="Order",
            entity_id="9999",
        )
        self.assertEqual(n1.id, n2.id)

        matching_count = Notification.objects.filter(
            recipient=self.user_retail_admin,
            entity_type="Order",
            entity_id="9999",
        ).count()
        self.assertEqual(matching_count, 1)

    # =========================================================================
    # I. RETENTION MANAGEMENT COMMAND (purge_old_notifications)
    # =========================================================================

    def test_purge_old_notifications_command(self):
        """Management command purges read notifications older than threshold."""
        from django.core.management import call_command
        import io

        now = timezone.now()
        # Old read notification (100 days ago)
        old_notif = Notification.objects.create(
            workspace=self.ws_retail,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
            title="Cũ",
            message="Rất cũ",
            is_read=True,
        )
        Notification.objects.filter(id=old_notif.id).update(
            created_at=now - timedelta(days=100)
        )

        # Recent notification (2 days ago)
        recent_notif = Notification.objects.create(
            workspace=self.ws_retail,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
            title="Mới",
            message="Rất mới",
            is_read=True,
        )

        # 1. Run dry-run
        out = io.StringIO()
        call_command("purge_old_notifications", "--days=90", "--dry-run", stdout=out)
        self.assertIn("[DRY-RUN]", out.getvalue())
        self.assertTrue(Notification.objects.filter(id=old_notif.id).exists())

        # 2. Run real purge
        out_real = io.StringIO()
        call_command("purge_old_notifications", "--days=90", stdout=out_real)
        self.assertIn("Successfully purged", out_real.getvalue())

        # Old notification deleted, recent notification kept
        self.assertFalse(Notification.objects.filter(id=old_notif.id).exists())
        self.assertTrue(Notification.objects.filter(id=recent_notif.id).exists())

    # =========================================================================
    # J. UNIFIED NOTIFICATION CENTER & CROSS-WORKSPACE AGGREGATION
    # =========================================================================

    def test_multi_workspace_admin_receives_both_retail_and_service_notifications_without_switching(self):
        """
        Unified Bell System: Administrator authorized for both Retail & Service workspaces
        receives and aggregates unread notifications across BOTH domains simultaneously.
        """
        # Give retail_admin membership in service workspace as ADMIN too
        WorkspaceMembership.objects.create(
            workspace=self.ws_service,
            user=self.user_retail_admin,
            role=self.role_admin,
            is_active=True,
        )

        # Create 1 Retail notification
        notif_retail = Notification.objects.create(
            workspace=self.ws_retail,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
            title="Đơn hàng ABC-001 mới",
            message="Khách hàng vừa đặt đơn",
            entity_type="Order",
            entity_id="101",
            target_url="/retail/orders/101/",
        )

        # Create 1 Service notification
        notif_service = Notification.objects.create(
            workspace=self.ws_service,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_SERVICE_REQUEST,
            title="Yêu cầu sự cố XYZ-001",
            message="Khách hàng báo lỗi máy chủ",
            entity_type="ServiceRequest",
            entity_id="202",
            target_url="/services/requests/202/",
        )

        # API unread count should return 2 (aggregated across all authorized workspaces)
        self.client.force_login(self.user_retail_admin)
        resp_count = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(resp_count.status_code, 200)
        self.assertEqual(resp_count.json()["unread_count"], 2)

        # Bell dropdown API should return both notifications with their workspace metadata
        resp_latest = self.client.get("/api/v1/notifications/latest/")
        self.assertEqual(resp_latest.status_code, 200)
        items = resp_latest.json()["notifications"]
        self.assertEqual(len(items), 2)
        item_workspaces = {item["workspace_code"] for item in items}
        self.assertIn("WS-RETAIL-NOTIF", item_workspaces)
        self.assertIn("WS-SERVICE-NOTIF", item_workspaces)

    def test_single_domain_manager_receives_only_authorized_workspace_notifications(self):
        """
        Domain Isolation: A manager with access only to Service workspace sees only
        Service notifications, and Retail notifications are completely isolated.
        """
        Notification.objects.create(
            workspace=self.ws_retail,
            recipient=self.user_service_mgr,
            event_type=NotificationEventType.NEW_ORDER,
            title="Đơn hàng lẻ",
            message="Đơn hàng",
        )
        Notification.objects.create(
            workspace=self.ws_service,
            recipient=self.user_service_mgr,
            event_type=NotificationEventType.NEW_SERVICE_REQUEST,
            title="Yêu cầu dịch vụ IT",
            message="Yêu cầu dịch vụ",
        )

        # user_service_mgr only has membership in ws_service
        self.client.force_login(self.user_service_mgr)
        resp_count = self.client.get("/api/v1/notifications/unread-count/")
        self.assertEqual(resp_count.status_code, 200)
        # Should only see 1 notification (from ws_service)
        self.assertEqual(resp_count.json()["unread_count"], 1)

        resp_latest = self.client.get("/api/v1/notifications/latest/")
        items = resp_latest.json()["notifications"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["workspace_code"], "WS-SERVICE-NOTIF")

    def test_notification_redirect_marks_read_and_navigates_to_target(self):
        """
        Clicking a notification marks it as read and safely redirects to target entity URL.
        """
        notif = Notification.objects.create(
            workspace=self.ws_retail,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
            title="Đơn hàng mới",
            message="Chi tiết đơn",
            target_url="/retail/orders/",
        )
        self.assertFalse(notif.is_read)

        self.client.force_login(self.user_retail_admin)
        resp = self.client.get(f"/noibo/thong-bao/{notif.id}/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/retail/orders/")

        notif.refresh_from_db()
        self.assertTrue(notif.is_read)
        self.assertIsNotNone(notif.read_at)

    def test_notification_redirect_gracefully_handles_deleted_entity(self):
        """
        If the related entity was deleted, redirect safely to notification center with warning.
        """
        notif = Notification.objects.create(
            workspace=self.ws_retail,
            recipient=self.user_retail_admin,
            event_type=NotificationEventType.NEW_ORDER,
            title="Đơn đã xóa",
            message="Chi tiết",
            entity_type="Order",
            entity_id="99999999",  # Non-existent ID
            target_url="/retail/orders/99999999/",
        )
        self.client.force_login(self.user_retail_admin)
        resp = self.client.get(f"/noibo/thong-bao/{notif.id}/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/noibo/thong-bao/")

        # Notification was still safely marked as read
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_unified_noibo_dashboard_displays_dual_domains_and_no_broken_switcher(self):
        """
        Unified /noibo/ Dashboard:
        - Accessible by authorized admin.
        - Renders dual business domain summaries (Retail + Service).
        - Does NOT contain broken workspace switcher link '/workspaces/switch-ui/'.
        - Features neutral internal management branding.
        """
        self.client.force_login(self.user_retail_admin)
        resp = self.client.get("/noibo/")
        self.assertEqual(resp.status_code, 200)

        content = resp.content.decode("utf-8")
        # Neutral branding
        self.assertIn("Trung tâm Quản trị", content)
        self.assertIn("Điều hành Nội bộ", content)
        # Dual domains
        self.assertIn("ABC Tech Store", content)
        self.assertIn("XYZ IT Technical Services", content)
        # No broken workspace switcher link in internal header
        self.assertNotIn("/workspaces/switch-ui/", content)
