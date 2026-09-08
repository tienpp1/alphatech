"""
Tests for Executive Operational Reporting and Enterprise AI & GIS Telemetry Studio.
Verifies security isolation (unauthorized/customer-only redirection),
HTTP 200 rendering, CSV export formatting, and PostGIS/AI telemetry metrics.
"""

from django.test import TestCase, Client
from django.urls import reverse
from decimal import Decimal

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Order, Customer, OrderStatus


class ExecutiveReportingAndTelemetryTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create Workspace
        self.workspace = Workspace.objects.create(
            name="Test Retail Workspace",
            code="test-retail",
            workspace_type=WorkspaceType.RETAIL,
        )

        # 2. Create Roles
        self.manager_role = Role.objects.create(name="MANAGER", description="Manager Role")
        for code in ("retail.view_analytics", "retail.view_order", "retail.view_customer", "retail.view_product", "retail.view_branch", "gis.view_spatial_layers", "forecasting.view_forecast", "knowledge.view_knowledge", "approvals.view_approval"):
            permission, _ = Permission.objects.get_or_create(codename=code, defaults={"name": code, "module": code.split(".")[0]})
            self.manager_role.permissions.add(permission)

        # 3. Create Users
        self.admin_user = User.objects.create_superuser(
            username="admin_test",
            email="admin@test.com",
            password="Password123!",
        )

        self.manager_user = User.objects.create_user(
            username="manager_test",
            email="manager@test.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.manager_user,
            role=self.manager_role,
            is_active=True,
        )

        self.customer_user = User.objects.create_user(
            username="customer_test",
            email="customer@test.com",
            password="Password123!",
        )

        # 4. Create sample customer & order
        self.customer = Customer.objects.create(
            workspace=self.workspace,
            name="Khach Hang Mau",
            phone="0901234567",
        )
        from django.utils import timezone
        now_dt = timezone.now()
        self.order = Order.objects.create(
            workspace=self.workspace,
            customer=self.customer,
            order_number="ORD-TEST-001",
            order_date=now_dt.date(),
            order_timestamp=now_dt,
            total_amount=Decimal("1500000.00"),
            status=OrderStatus.COMPLETED,
        )

    def test_anonymous_access_redirects_to_login(self):
        """Anonymous requests to reporting and telemetry must redirect to login."""
        res_report = self.client.get("/noibo/bao-cao-dieu-hanh/")
        self.assertEqual(res_report.status_code, 302)
        self.assertIn("/accounts/login/", res_report.url)

        res_csv = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(res_csv.status_code, 302)
        self.assertIn("/accounts/login/", res_csv.url)

        res_telemetry = self.client.get("/noibo/telemetry/")
        self.assertEqual(res_telemetry.status_code, 302)
        self.assertIn("/accounts/login/", res_telemetry.url)

    def test_dashboard_membership_does_not_grant_business_data(self):
        self.manager_role.permissions.clear()
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["retail"]["total_orders_count"], "—")
        self.assertEqual(response.context["recent_activities"], [])
        self.assertNotContains(response, self.customer.name)

    def test_dashboard_notifications_belong_to_recipient(self):
        from apps.notifications.models import Notification
        Notification.objects.create(workspace=self.workspace, recipient=self.admin_user,
            event_type="NEW_CONTACT", title="PRIVATE-CONTACT-TITLE", message="Private contact")
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/")
        self.assertEqual(response.context["retail"]["total_orders_count"], 1)
        self.assertNotContains(response, "PRIVATE-CONTACT-TITLE")
        self.assertContains(response, self.customer.name)

    def test_report_does_not_claim_sla_or_signature(self):
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/")
        self.assertIsNone(response.context["service"]["resolution_rate"])
        self.assertNotContains(response, "Tỷ lệ Tuân thủ SLA")
        self.assertNotContains(response, "Khóa xác thực số")
        self.assertNotContains(response, "el.innerHTML = data[key]")
        self.assertContains(response, "sessionStorage.setItem")

    def test_csv_neutralizes_formula_cells(self):
        self.customer.name = '=HYPERLINK("https://example.invalid")'
        self.customer.save(update_fields=["name"])
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        import csv
        import io
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
        self.assertEqual(rows[-1][2], "'" + self.customer.name)

    def test_copilot_rejects_non_text_and_oversized_messages(self):
        for payload in ([], {"message": 123}, {"message": "x" * 2001}):
            response = self.client.post("/api/v1/public/copilot/", data=payload, content_type="application/json")
            self.assertEqual(response.status_code, 400)

    def test_role_name_without_permissions_does_not_grant_reporting(self):
        self.manager_role.permissions.clear()
        self.client.force_login(self.manager_user)
        for path in ("/noibo/bao-cao-dieu-hanh/", "/noibo/bao-cao-dieu-hanh/export-csv/", "/noibo/telemetry/"):
            self.assertEqual(self.client.get(path).status_code, 403)

    def test_membership_without_permissions_does_not_leak_second_workspace(self):
        other = Workspace.objects.create(code="private-report", name="Private report", workspace_type=WorkspaceType.RETAIL)
        role = Role.objects.create(name="NO_REPORT")
        WorkspaceMembership.objects.create(workspace=other, user=self.manager_user, role=role)
        customer = Customer.objects.create(workspace=other, code="PRIVATE", name="Hidden customer")
        Order.objects.create(workspace=other, customer=customer, order_number="HIDDEN-ORDER", order_date=self.order.order_date, order_timestamp=self.order.order_timestamp)
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "HIDDEN-ORDER")

    def test_customer_only_access_is_fenced(self):
        """Customer without internal workspace membership must be redirected safely."""
        self.client.force_login(self.customer_user)

        res_report = self.client.get("/noibo/bao-cao-dieu-hanh/")
        self.assertEqual(res_report.status_code, 302)
        self.assertIn("/tai-khoan/?notice=customer_only", res_report.url)

        res_csv = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(res_csv.status_code, 302)
        self.assertIn("/tai-khoan/?notice=customer_only", res_csv.url)

        res_telemetry = self.client.get("/noibo/telemetry/")
        self.assertEqual(res_telemetry.status_code, 302)
        self.assertIn("/tai-khoan/?notice=customer_only", res_telemetry.url)

    def test_manager_can_access_executive_report(self):
        """Internal manager can access executive operational report with HTTP 200."""
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BÁO CÁO VẬN HÀNH DOANH NGHIỆP")
        self.assertContains(response, "REP-HCMUNRE-")
        self.assertContains(response, "Mã tham chiếu:")
        self.assertContains(response, "không phải chữ ký số")
        self.assertContains(response, "window.print()")
        self.assertContains(response, "1500000")

    def test_manager_can_export_report_csv(self):
        """Internal manager can export CSV with UTF-8 BOM and order content."""
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        content = response.content.decode("utf-8-sig")
        self.assertIn("BAO CAO TONG HOP DON HANG VA VAN HANH DOANH NGHIEP", content)
        self.assertIn("ORD-TEST-001", content)
        self.assertIn("1,500,000", content)

    def test_manager_can_access_telemetry_studio(self):
        """Internal manager can access telemetry studio with PostGIS and AI model stats."""
        self.client.force_login(self.manager_user)
        response = self.client.get("/noibo/telemetry/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bảng Giám sát Hiệu năng Mô hình AI & Hạ tầng Không gian GIS")
        self.assertContains(response, "PostGIS")
        self.assertContains(response, "SRID 4326")
        self.assertContains(response, "XGBoost Time-Series Engine")
        self.assertContains(response, "Grounded RAG & pgvector")
        self.assertContains(response, "Human-in-the-loop & RBAC")
        self.assertNotIn("inference_latency_ms", response.context["ml"])
        self.assertNotIn("vector_search_latency_ms", response.context["rag"])
        self.assertEqual(response.context["rag"]["retrieval_hit_rate"], "Chưa đo trong phiên này")
        self.assertGreaterEqual(response.context["ml"]["count_query_latency_ms"], 0)
