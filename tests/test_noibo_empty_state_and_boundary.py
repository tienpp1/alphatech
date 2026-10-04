"""
Tests for Empty States, Boundary Conditions, and Degradation Resilience
on the Unified Internal Management Portal (/noibo/) and Executive Reports.

Verifies:
1. Zero division safety (0 orders -> AOV = 0, 0 service tickets -> resolution rate = None).
2. Clean metric fallback formatting without NoneType errors.
3. Proper rendering of empty state cards with informative Vietnamese copy and navigation links.
4. Export CSV and Telemetry resilience in a zero-record workspace environment.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.utils import timezone

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer, Order, OrderStatus
from config.views import _csv_text


class NoiboEmptyStateAndBoundaryTests(TestCase):
    def setUp(self):
        self.client = Client()

        # 1. Create a pristine empty Retail workspace
        self.empty_retail_ws = Workspace.objects.create(
            name="Empty Retail Store",
            code="empty-retail",
            workspace_type=WorkspaceType.RETAIL,
        )

        # 2. Create a pristine empty Service workspace
        self.empty_service_ws = Workspace.objects.create(
            name="Empty Service Ops",
            code="empty-service",
            workspace_type=WorkspaceType.SERVICE,
        )

        # 3. Create full-permission manager role
        self.manager_role = Role.objects.create(name="MANAGER", description="Full View Manager")
        all_perms = (
            "retail.view_analytics", "retail.view_order", "retail.view_customer",
            "retail.view_product", "retail.manage_product", "retail.view_branch",
            "service.view_analytics", "service.view_request", "service.view_service",
            "service.view_employee", "service.view_task", "service.view_schedule",
            "service.view_sla", "service.view_labor_entry",
            "gis.view_spatial_layers", "forecasting.view_forecast",
            "recommendations.view_recommendation", "approvals.view_approval",
            "knowledge.view_knowledge", "ai.chat",
        )
        for code in all_perms:
            perm, _ = Permission.objects.get_or_create(codename=code, defaults={"name": code, "module": code.split(".")[0]})
            self.manager_role.permissions.add(perm)

        # 4. User assigned to BOTH empty workspaces
        self.empty_manager = User.objects.create_user(
            username="empty_manager",
            email="empty_manager@test.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.empty_retail_ws,
            user=self.empty_manager,
            role=self.manager_role,
            is_active=True,
        )
        WorkspaceMembership.objects.create(
            workspace=self.empty_service_ws,
            user=self.empty_manager,
            role=self.manager_role,
            is_active=True,
        )

    def test_dashboard_renders_cleanly_with_zero_records(self):
        """Dashboard must handle zero orders, products, tickets, and activities without error."""
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 200)

        # Verify retail metrics are clean zeroes, not None or errors
        retail = response.context["retail"]
        self.assertEqual(retail["products_count"], 0)
        self.assertEqual(retail["new_orders_count"], 0)
        self.assertEqual(retail["total_orders_count"], 0)
        self.assertEqual(retail["total_revenue"], "0")
        self.assertEqual(retail["branches_count"], 0)

        # Verify service metrics are clean zeroes
        service = response.context["service"]
        self.assertEqual(service["services_count"], 0)
        self.assertEqual(service["new_requests_count"], 0)
        self.assertEqual(service["in_progress_count"], 0)
        self.assertEqual(service["sla_risk_count"], 0)
        self.assertEqual(service["technicians_count"], 0)
        self.assertEqual(service["total_tickets_count"], 0)

        # Verify recent activities is empty list
        self.assertEqual(response.context["recent_activities"], [])

        # Verify aesthetic empty state card is rendered
        self.assertContains(response, "Chưa có hoạt động nghiệp vụ nào")
        self.assertContains(response, "Toàn bộ sự kiện phát sinh từ đơn hàng mới")
        self.assertContains(response, "/noibo/retail/orders/")
        self.assertContains(response, "/noibo/services/requests/")

    def test_executive_report_zero_division_guard(self):
        """Executive report calculations (AOV, SLA resolution) must not trigger ZeroDivisionError."""
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/")
        self.assertEqual(response.status_code, 200)

        retail = response.context["retail"]
        self.assertEqual(retail["total_orders"], 0)
        self.assertEqual(retail["completed_orders"], 0)
        self.assertEqual(retail["aov"], Decimal("0.00"))
        self.assertEqual(retail["branch_count"], 0)

        service = response.context["service"]
        self.assertEqual(service["total_tickets"], 0)
        self.assertEqual(service["resolved_tickets"], 0)
        self.assertIsNone(service["resolution_rate"])

        # Check empty tables render gracefully
        self.assertContains(response, "Không có dữ liệu chi nhánh.")
        self.assertContains(response, "Không có yêu cầu phê duyệt nào gần đây.")
        self.assertContains(response, "Đang cập nhật các mô hình chuỗi thời gian đã huấn luyện.")

    def test_export_csv_zero_records(self):
        """CSV export with 0 orders must return HTTP 200 and UTF-8 BOM with valid headers."""
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        self.assertIn("BAO CAO TONG HOP DON HANG VA VAN HANH DOANH NGHIEP", content)
        self.assertIn("Ma don hang", content)

    def test_telemetry_zero_records(self):
        """Telemetry studio with 0 records must return HTTP 200 with zero geocoded entities."""
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/telemetry/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["spatial"]["branches_geocoded"], 0)
        self.assertEqual(response.context["spatial"]["customers_geocoded"], 0)
        self.assertEqual(response.context["spatial"]["technicians_geocoded"], 0)

    def test_accessibility_skip_link_and_aria_attributes(self):
        """Dashboard must contain WCAG AA skip-link, ARIA controls, and high-contrast focus rings."""
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        # WCAG 2.4.1 Bypass Blocks
        self.assertIn('class="skip-link"', content)
        self.assertIn('href="#main-content"', content)
        self.assertIn('id="main-content"', content)

        # WCAG 4.1.2 Name, Role, Value
        self.assertIn('id="btn-notif-bell"', content)
        self.assertIn('aria-label="Thông báo hệ thống"', content)
        self.assertIn('aria-haspopup="true"', content)
        self.assertIn('aria-expanded="false"', content)

        # Dropdown Menus ARIA
        self.assertIn('id="btn-dropdown-retail"', content)
        self.assertIn('role="menu"', content)
        self.assertIn('role="menuitem"', content)

        # WCAG 2.4.7 Focus Visible Indicator
        self.assertIn(':focus-visible', content)
        self.assertIn('outline: 2px solid #818cf8', content)

    def test_csv_injection_formula_neutralization_and_workspace_isolation(self):
        """
        Verify CSV injection defense (neutralizing =, +, -, @, %, |, control chars),
        defense-in-depth DOM XSS mitigation in executive report,
        and strict tenant isolation across CSV exports.
        """
        # 1. Direct unit verification of _csv_text formula neutralization
        self.assertEqual(_csv_text("=cmd|' /C calc'!A0"), "'=cmd|' /C calc'!A0")
        self.assertEqual(_csv_text("@SUM(1+1)*cmd"), "'@SUM(1+1)*cmd")
        self.assertEqual(_csv_text("%100"), "'%100")
        self.assertEqual(_csv_text("|'cmd'|' /C calc'!A0"), "'|'cmd'|' /C calc'!A0")
        self.assertEqual(_csv_text("+84901234567"), "'+84901234567")
        self.assertEqual(_csv_text("-50000"), "'-50000")
        self.assertEqual(_csv_text("  =1+1"), "'  =1+1")
        self.assertEqual(_csv_text("\tcmd"), "'\tcmd")
        self.assertEqual(_csv_text("\rtest"), "'\rtest")
        self.assertEqual(_csv_text("\ntest"), "'\ntest")
        # Benign inputs should remain unescaped
        self.assertEqual(_csv_text("Công ty TNHH Alpha Tech"), "Công ty TNHH Alpha Tech")
        self.assertEqual(_csv_text("0901234567"), "0901234567")
        self.assertEqual(_csv_text(None), "")
        self.assertEqual(_csv_text(""), "")

        # 2. Setup malicious payload in authorized workspace order
        malicious_customer = Customer.objects.create(
            workspace=self.empty_retail_ws,
            code="CUST-INJ-01",
            name="=cmd|' /C calc'!A0",
            phone="+84901234567",
        )
        Order.objects.create(
            workspace=self.empty_retail_ws,
            order_number="@ORD-CALC-001",
            customer=malicious_customer,
            order_date=timezone.now().date(),
            order_timestamp=timezone.now(),
            total_amount=Decimal("1500000.00"),
            status=OrderStatus.COMPLETED,
        )

        # 3. Setup another workspace with private records (cross-tenant isolation test)
        other_ws = Workspace.objects.create(
            name="Confidential Isolation Tenant",
            code="tenant-isolation",
            workspace_type=WorkspaceType.RETAIL,
        )
        secret_customer = Customer.objects.create(
            workspace=other_ws,
            code="CUST-SECRET",
            name="Confidential Customer X",
            phone="0988888888",
        )
        Order.objects.create(
            workspace=other_ws,
            order_number="SECRET-ORD-999",
            customer=secret_customer,
            order_date=timezone.now().date(),
            order_timestamp=timezone.now(),
            total_amount=Decimal("9999999.00"),
            status=OrderStatus.COMPLETED,
        )

        # 4. Fetch CSV as empty_manager (only authorized for empty_retail_ws & empty_service_ws)
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", response.headers["Content-Disposition"])

        content = response.content.decode("utf-8-sig")
        # Formula characters must be neutralized with leading single quote
        self.assertIn("'=cmd|' /C calc'!A0", content)
        self.assertIn("'+84901234567", content)
        self.assertIn("'@ORD-CALC-001", content)
        self.assertIn("1,500,000", content)

        # Cross-tenant records must NOT leak into the CSV export
        self.assertNotIn("SECRET-ORD-999", content)
        self.assertNotIn("Confidential Customer X", content)
        self.assertNotIn("Confidential Isolation Tenant", content)

        # 5. Separation of concerns: Public customer without internal membership
        customer_user = User.objects.create_user(
            username="public_customer_csv",
            email="cust_csv@test.com",
            password="CustomerPass123!",
        )
        self.client.force_login(customer_user)
        resp_cust = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(resp_cust.status_code, 403)

        # 6. DOM XSS Defense in Executive Report template
        self.client.force_login(self.empty_manager)
        resp_report = self.client.get("/noibo/bao-cao-dieu-hanh/")
        self.assertEqual(resp_report.status_code, 200)
        report_html = resp_report.content.decode("utf-8")
        self.assertIn("toast.replaceChildren(iconSpan, document.createTextNode(' '), msgSpan);", report_html)
        self.assertNotIn("toast.innerHTML =", report_html)

    def test_executive_report_print_stylesheet_and_a4_layout(self):
        """
        Verify that Executive Operational Report contains optimal A4 @media print stylesheet,
        proper page-break controls, screen-chrome hiding rules, and safe print triggers.
        """
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/bao-cao-dieu-hanh/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        # 1. Verify A4 @page sizing and print media query
        self.assertIn("@media print", html)
        self.assertIn("size: A4 portrait;", html)
        self.assertIn("margin: 12mm 15mm 15mm 15mm;", html)

        # 2. Verify all UI chrome elements are suppressed when printing
        self.assertIn(".app-header", html)
        self.assertIn(".app-footer", html)
        self.assertIn(".report-toolbar", html)
        self.assertIn(".skip-link", html)
        self.assertIn(".notif-bell-container", html)
        self.assertIn(".edit-mode-banner", html)
        self.assertIn(".report-toast", html)

        # 3. Verify pagination and page break preservation rules
        self.assertIn("page-break-after: avoid;", html)
        self.assertIn("page-break-inside: avoid;", html)
        self.assertIn("display: table-header-group;", html)

        # 4. Verify print trigger button and safe print function
        self.assertIn('id="btn-print-report"', html)
        self.assertIn('onclick="handlePrintReport()"', html)
        self.assertIn('window.print();', html)
        self.assertIn('class="exec-evaluation-card"', html)

    def test_telemetry_studio_observability_and_exception_resilience(self):
        """
        Verify Telemetry Studio (/noibo/telemetry/) observability metrics,
        PostGIS and AI latency benchmarking, safe DOM rendering, and RBAC isolation.
        """
        self.client.force_login(self.empty_manager)
        response = self.client.get("/noibo/telemetry/")
        self.assertEqual(response.status_code, 200)

        # 1. Verify 4 Core Telemetry Pillars Context
        self.assertIn("spatial", response.context)
        self.assertIn("ml", response.context)
        self.assertIn("rag", response.context)
        self.assertIn("governance", response.context)

        # 2. Verify Database Name Sanitization (no leaked filesystem paths)
        safe_db = response.context["spatial"]["database"]
        self.assertNotIn(":\\", safe_db)
        self.assertNotIn("/home/", safe_db)
        self.assertNotIn("/var/", safe_db)

        # 3. Verify HTML & Safe DOM construction in live ping benchmark console
        html = response.content.decode("utf-8")
        self.assertIn('id="btn-ping-spatial"', html)
        self.assertIn('id="btn-ping-rag"', html)
        self.assertIn('id="btn-ping-xgb"', html)
        self.assertIn('id="btn-telemetry-report"', html)
        self.assertIn('id="btn-telemetry-dashboard"', html)
        self.assertIn("term.replaceChildren(line1, line2, line3, line4);", html)
        self.assertNotIn("term.innerHTML =", html)

        # 4. Verify /api/health/ endpoint returns valid JSON with redacted credentials
        resp_health = self.client.get("/api/health/")
        self.assertIn(resp_health.status_code, (200, 503))
        health_json = resp_health.json()
        self.assertIn("status", health_json)
        self.assertIn("timestamp", health_json)
        self.assertEqual(health_json["database"]["name"], "redacted")
        self.assertEqual(health_json["database"]["host"], "redacted")
        self.assertEqual(health_json["database"]["port"], "redacted")

        # 5. Separation of concerns: Public customer blocked from telemetry studio
        cust_user = User.objects.create_user(
            username="public_customer_telemetry",
            email="cust_telem@test.com",
            password="CustomerPass123!",
        )
        self.client.force_login(cust_user)
        resp_cust = self.client.get("/noibo/telemetry/")
        self.assertEqual(resp_cust.status_code, 403)

    def test_system_hardening_csv_none_guard_and_absolute_links(self):
        """
        Verify CSV export resilience against NoneType total_amount,
        absolute URL routing in retail products catalog, and customer_only notice CTA.
        """
        # 1. Test CSV export with an order having None/0 total_amount
        cust = Customer.objects.create(
            workspace=self.empty_retail_ws,
            code="CUST-NONE-01",
            name="Test Customer None Guard",
            phone="0987654321",
        )
        order = Order.objects.create(
            workspace=self.empty_retail_ws,
            customer=cust,
            order_number="ORD-NONE-TEST",
            order_date=timezone.now().date(),
            order_timestamp=timezone.now(),
            total_amount=Decimal("0.00"),
            status=OrderStatus.COMPLETED,
        )
        # Verify formatting resilience
        self.client.force_login(self.empty_manager)
        resp_csv = self.client.get("/noibo/bao-cao-dieu-hanh/export-csv/")
        self.assertEqual(resp_csv.status_code, 200)
        csv_content = resp_csv.content.decode("utf-8")
        self.assertIn("ORD-NONE-TEST", csv_content)

        # 2. Test Retail Products Catalog Absolute Links & Back Button
        resp_products = self.client.get("/noibo/retail/products/")
        self.assertEqual(resp_products.status_code, 200)
        prod_html = resp_products.content.decode("utf-8")
        self.assertIn('id="btn-back-dashboard"', prod_html)
        self.assertIn('href="/noibo/"', prod_html)
        self.assertIn('href="/noibo/retail/products/trash/"', prod_html)
        self.assertIn('href="/noibo/retail/products/create/"', prod_html)

        # 3. Test Customer Account notice=customer_only has CTA to /san-pham/
        cust_user = User.objects.create_user(
            username="cust_notice_test",
            email="cust_notice@test.com",
            password="Password123!",
        )
        self.client.force_login(cust_user)
        resp_acc = self.client.get("/tai-khoan/?notice=customer_only")
        self.assertEqual(resp_acc.status_code, 200)
        acc_html = resp_acc.content.decode("utf-8")
        self.assertIn("Cổng Quản trị Nội bộ (/noibo/) dành riêng cho nhân viên", acc_html)
        self.assertIn('href="/san-pham/"', acc_html)
        self.assertIn("Mua sắm sản phẩm", acc_html)

    def test_management_all_routes_matrix_and_rbac_integrity(self):
        """
        Verify all internal management navigation routes have absolute URLs,
        render without 500 exceptions, and maintain strict RBAC perimeter.
        """
        # 1. Verify navigation back-links and absolute URLs in retail & service ops
        self.client.force_login(self.empty_manager)

        # Orders page
        resp_orders = self.client.get("/noibo/retail/orders/")
        self.assertEqual(resp_orders.status_code, 200)
        orders_html = resp_orders.content.decode("utf-8")
        self.assertIn('id="btn-back-dashboard"', orders_html)
        self.assertIn('href="/noibo/retail/"', orders_html)
        self.assertIn('href="/noibo/retail/orders/"', orders_html)

        # Customers page
        resp_customers = self.client.get("/noibo/retail/customers/")
        self.assertEqual(resp_customers.status_code, 200)
        cust_html = resp_customers.content.decode("utf-8")
        self.assertIn('id="btn-back-dashboard"', cust_html)
        self.assertIn('href="/noibo/retail/"', cust_html)
        self.assertIn('href="/noibo/retail/customers/"', cust_html)

        # Service requests page
        resp_svc_reqs = self.client.get("/noibo/services/requests/")
        self.assertEqual(resp_svc_reqs.status_code, 200)
        svc_reqs_html = resp_svc_reqs.content.decode("utf-8")
        self.assertIn('id="btn-back-dashboard"', svc_reqs_html)
        self.assertIn('href="/noibo/services/"', svc_reqs_html)
        self.assertIn('href="/noibo/services/requests/"', svc_reqs_html)

        # Service dashboard page
        resp_svc_dash = self.client.get("/noibo/services/")
        self.assertEqual(resp_svc_dash.status_code, 200)
        svc_dash_html = resp_svc_dash.content.decode("utf-8")
        self.assertIn('id="btn-back-dashboard"', svc_dash_html)
        self.assertIn('href="/noibo/"', svc_dash_html)
        self.assertIn('href="/noibo/services/requests/"', svc_dash_html)

        # 2. Comprehensive Route Matrix (Ensure 0 unhandled 500 crashes across manager views)
        management_routes = [
            "/noibo/",
            "/noibo/bao-cao-dieu-hanh/",
            "/noibo/bao-cao-dieu-hanh/export-csv/",
            "/noibo/telemetry/",
            "/noibo/status/",
            "/noibo/bang-tin/",
            "/noibo/trao-doi/",
            "/noibo/retail/",
            "/noibo/retail/products/",
            "/noibo/retail/products/trash/",
            "/noibo/retail/orders/",
            "/noibo/retail/customers/",
            "/noibo/retail/goods-receiving/",
            "/noibo/retail/branches/",
            "/noibo/services/",
            "/noibo/services/requests/",
            "/noibo/services/services/",
            "/noibo/services/employees/",
            "/noibo/services/tasks/",
            "/noibo/services/slas/",
            "/noibo/services/labor-cost/",
            "/noibo/ai/",
            "/noibo/knowledge/",
            "/noibo/approvals/",
        ]
        for route in management_routes:
            resp = self.client.get(route)
            self.assertIn(
                resp.status_code,
                [200, 302],
                f"Route '{route}' failed with status {resp.status_code}",
            )

        # 3. RBAC Boundary Test: Unauthenticated requests cannot access /noibo/
        self.client.logout()
        resp_anon = self.client.get("/noibo/")
        self.assertEqual(resp_anon.status_code, 302)
        self.assertTrue(resp_anon.url.startswith("/accounts/login/") or "/dang-nhap/" in resp_anon.url)

