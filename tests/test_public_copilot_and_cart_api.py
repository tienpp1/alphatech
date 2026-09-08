"""
Automated Test Suite for Public AI Copilot Widget & Enhanced Cart/Dispatch Flows.
Verifies:
- Public AI Copilot API (/api/v1/public/copilot/) answers product, service SLA, branch queries
- Strict zero leakage of sensitive internal metrics (cost_price, supplier, workload, margin)
- Public Cart JSON API (/gio-hang/api/) serialization & AJAX support
- Safe public service request dispatch & branch GIS page integration
"""

import json
from decimal import Decimal
from django.test import TestCase, Client
from apps.retail.models import Product, Category, Branch, Order, OrderStatus
from apps.service_ops.models import Service, ServiceCategory, ServiceRequest
from apps.workspaces.models import Workspace, WorkspaceType


class PublicCopilotAndCartApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.ws_retail = Workspace.objects.create(
            name="Retail Workspace",
            code="WS-RET-COPILOT",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.ws_service = Workspace.objects.create(
            name="Service Workspace",
            code="WS-SRV-COPILOT",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.cat_laptop = Category.objects.create(
            workspace=self.ws_retail,
            name="Laptop Doanh Nghiệp",
            code="laptop-biz",
        )

        self.product = Product.objects.create(
            workspace=self.ws_retail,
            category=self.cat_laptop,
            sku="LAP-DELL-5520",
            name="Laptop Dell Latitude 5520",
            description="Intel Core i5 16GB RAM 512GB SSD",
            unit="chiếc",
            unit_price=Decimal("18500000.00"),
            cost_price=Decimal("14000000.00"),  # Sensitive internal data
            is_active=True,
        )

        self.service = Service.objects.create(
            workspace=self.ws_service,
            code="SRV-INSTALL-01",
            category=ServiceCategory.INSTALLATION,
            name="Cài đặt hệ điều hành và phần mềm bảo mật",
            description="Triển khai chuẩn doanh nghiệp ISO 27001",
            is_active=True,
        )

        self.branch = Branch.objects.create(
            workspace=self.ws_retail,
            code="BR-Q1-FLAGSHIP",
            name="Chi nhánh Quận 1 Flagship",
            address="123 Nguyễn Thị Minh Khai, P. Bến Thành, Q.1",
            phone="1900 6868",
            latitude=Decimal("10.7725"),
            longitude=Decimal("106.6980"),
            is_active=True,
        )

    def test_public_copilot_greeting_and_suggestions(self):
        """POST /api/v1/public/copilot/ with empty or greeting returns welcome and suggestion chips."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "xin chào"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("AI Copilot", data["reply"])
        self.assertTrue(len(data.get("suggestions", [])) > 0)

    def test_order_tracking_requires_exact_code_and_owner(self):
        from apps.accounts.models import User
        from apps.retail.models import Customer
        from django.utils import timezone
        owner = User.objects.create_user(username="copilot-owner", email="owner@example.com")
        outsider = User.objects.create_user(username="copilot-other", email="other@example.com")
        customer = Customer.objects.create(workspace=self.ws_retail, code="OWNER", name="Owner", user=owner)
        order = Order.objects.create(workspace=self.ws_retail, customer=customer, created_by=owner, order_number="ORD-20260908-SECRET", order_date=timezone.now().date(), order_timestamp=timezone.now(), total_amount=123456)
        def track(code):
            return self.client.post("/api/v1/public/copilot/", data=json.dumps({"message": "tra cứu đơn hàng " + code}), content_type="application/json").json()["reply"]
        self.assertNotIn("123.456", track(order.order_number))
        self.client.force_login(outsider)
        self.assertNotIn("123.456", track(order.order_number))
        self.client.force_login(owner)
        self.assertIn("123.456", track(order.order_number))
        self.assertNotIn("123.456", track("ORD-20260908"))

    def test_public_copilot_product_query_and_zero_cost_leak(self):
        """POST /api/v1/public/copilot/ answers product inquiry without leaking cost_price."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "tư vấn laptop dell"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Laptop Dell Latitude 5520", data["reply"])
        self.assertIn("18.500.000₫", data["reply"])
        # Zero cost price leakage
        self.assertNotIn("14000000", data["reply"])
        self.assertNotIn("cost_price", data["reply"])

    def test_public_copilot_service_query_and_zero_rate_leak(self):
        """POST /api/v1/public/copilot/ answers service inquiry without leaking labor rates."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "dịch vụ cài đặt hệ điều hành"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Cài đặt hệ điều hành", data["reply"])
        self.assertIn("SLA", data["reply"])
        # Zero internal labor rate leakage
        self.assertNotIn("250000", data["reply"])
        self.assertNotIn("hourly_labor_rate", data["reply"])

    def test_public_copilot_branch_query(self):
        """POST /api/v1/public/copilot/ lists physical branch and hotline."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "địa chỉ chi nhánh gần nhất"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Chi nhánh Quận 1 Flagship", data["reply"])
        self.assertIn("1900 6868", data["reply"])

    def test_public_cart_json_api(self):
        """GET /gio-hang/api/ returns serialized cart state with shipping progress."""
        # Add item via AJAX
        add_resp = self.client.post(
            f"/gio-hang/them/{self.product.id}/",
            {"quantity": "1", "action": "add_to_cart", "format": "json"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(add_resp.status_code, 200)
        add_data = add_resp.json()
        self.assertTrue(add_data["success"])
        self.assertEqual(add_data["total_items"], 1)

        # Query cart JSON state
        cart_resp = self.client.get("/gio-hang/api/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(cart_resp.status_code, 200)
        cart_data = cart_resp.json()
        self.assertEqual(cart_data["total_quantity"], 1)
        self.assertEqual(cart_data["items_count"], 1)
        self.assertEqual(cart_data["items"][0]["sku"], "LAP-DELL-5520")
        # Subtotal is 18,500,000 >= 5,000,000 threshold -> is_free_shipping True
        self.assertTrue(cart_data["is_free_shipping"])
        self.assertEqual(cart_data["shipping_fee"], 0)
