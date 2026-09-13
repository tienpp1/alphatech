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
        self.assertIn("AI AlphaTech", data["reply"])
        self.assertTrue(len(data.get("suggestions", [])) > 0)

    def test_public_copilot_get_status_and_identity(self):
        """GET /api/v1/public/copilot/ returns online status and AI AlphaTech assistant name."""
        resp = self.client.get("/api/v1/public/copilot/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["assistant"], "AI AlphaTech")
        self.assertIn("warranty_doa", data["capabilities"])

    def test_public_copilot_warranty_and_doa_policy(self):
        """POST /api/v1/public/copilot/ explains 72h DOA 1-to-1 replacement and official warranty."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "chính sách bảo hành và đổi trả 1 đổi 1 như thế nào"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("DOA", data["reply"])
        self.assertIn("72 giờ", data["reply"])
        self.assertIn("1 Đổi 1", data["reply"])
        self.assertIn("1900 6868", data["reply"])

    def test_public_copilot_shipping_payment_vat(self):
        """POST /api/v1/public/copilot/ explains payment methods, express shipping, and e-VAT."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "công ty có xuất hóa đơn VAT và giao hàng hỏa tốc không"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("VAT", data["reply"])
        self.assertIn("hỏa tốc", data["reply"])
        self.assertIn("5.000.000₫", data["reply"])
        self.assertIn("Trả góp 0%", data["reply"])

    def test_public_copilot_trade_in_upgrade(self):
        """POST /api/v1/public/copilot/ explains trade-in program, subsidies, and zero data leak."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "tôi muốn thu cũ đổi mới lên đời laptop"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Trade-In", data["reply"])
        self.assertIn("15%", data["reply"])
        self.assertIn("Zero Data Leak", data["reply"])

    def test_public_copilot_workflow_specific_laptop_consulting(self):
        """POST /api/v1/public/copilot/ provides tailored advice for design / architecture."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "tư vấn laptop làm đồ họa 3d và kiến trúc cad"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Đồ họa", data["reply"])
        self.assertIn("RTX", data["reply"])
        self.assertIn("RAM", data["reply"])

    def test_public_copilot_emergency_network_sla(self):
        """POST /api/v1/public/copilot/ emphasizes <15m SLA response for emergency network outage."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "công ty bị rớt mạng khẩn cấp cần kỹ thuật viên gấp"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("KHẨN CẤP", data["reply"])
        self.assertIn("15 phút", data["reply"])
        self.assertIn("30 – 45 phút", data["reply"])

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

    def test_public_copilot_authenticity_and_cocq(self):
        """POST /api/v1/public/copilot/ confirms 100% genuine CO/CQ and Service Tag check."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "hàng ở shop có chính hãng không có giấy tờ co cq không"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("CO (Certificate of Origin)", data["reply"])
        self.assertIn("CQ (Certificate of Quality)", data["reply"])
        self.assertIn("200%", data["reply"])
        self.assertIn("Service Tag", data["reply"])

    def test_public_copilot_installment_procedure(self):
        """POST /api/v1/public/copilot/ explains 0% credit card vs CCCD installment procedures."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "thủ tục mua trả góp qua cccd hoặc thẻ tín dụng như thế nào"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("CCCD gắn chip", data["reply"])
        self.assertIn("Lãi suất 0%", data["reply"])
        self.assertIn("15 – 20 phút", data["reply"])
        self.assertIn("10% – 30%", data["reply"])

    def test_public_copilot_return_and_refund(self):
        """POST /api/v1/public/copilot/ explains 7-day exchange and refund conditions."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "nếu mua về dùng không thích hoặc nhầm cấu hình có được đổi trả không"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("07 ngày", data["reply"])
        self.assertIn("Miễn phí phí đổi", data["reply"])
        self.assertIn("10% – 15%", data["reply"])
        self.assertIn("1 – 3 ngày làm việc", data["reply"])

    def test_public_copilot_hardware_upgrade_maintenance(self):
        """POST /api/v1/public/copilot/ explains RAM/SSD upgrades, thermal paste, and warranty safety."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "shop có nhận nâng cấp ram ssd và vệ sinh tra keo tản nhiệt lấy liền không"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("15 – 30 Phút", data["reply"])
        self.assertIn("Arctic MX-4", data["reply"])
        self.assertIn("không làm mất bảo hành chính hãng", data["reply"])
        self.assertIn("MIỄN PHÍ vệ sinh máy trọn đời", data["reply"])

    def test_public_copilot_software_and_remote_support(self):
        """POST /api/v1/public/copilot/ explains clean OS install, data migration, and remote support."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "mua máy có được cài sẵn win bản quyền và hỗ trợ chuyển dữ liệu không"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("Windows 11 Pro", data["reply"])
        self.assertIn("Data Migration", data["reply"])
        self.assertIn("UltraViewer / AnyDesk", data["reply"])

    def test_public_copilot_b2b_corporate_quotation(self):
        """POST /api/v1/public/copilot/ explains corporate volume discounts, quotations, and credit terms."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "công ty muốn xin bảng báo giá mua số lượng lớn cho nhân viên"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("5% đến 12%", data["reply"])
        self.assertIn("30 phút", data["reply"])
        self.assertIn("15 đến 30 ngày", data["reply"])
        self.assertIn("b2b@alphatech.vn", data["reply"])

    def test_public_copilot_privacy_and_data_security(self):
        """POST /api/v1/public/copilot/ guarantees ISO 27001 customer privacy and open glass bench."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "khi sửa máy dữ liệu cá nhân có bị lộ hay xem trộm không"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ISO 27001", data["reply"])
        self.assertIn("nghiêm cấm sao chép", data["reply"])
        self.assertIn("vách kính trong suốt", data["reply"])
        self.assertIn("camera", data["reply"])

    def test_public_copilot_onsite_booking_guide(self):
        """POST /api/v1/public/copilot/ explains 3-step on-site technician booking and transparent fees."""
        resp = self.client.post(
            "/api/v1/public/copilot/",
            data=json.dumps({"message": "tôi muốn đặt thợ kỹ thuật đến tận nhà sửa máy tính thì làm thế nào"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("On-Site IT Service", data["reply"])
        self.assertIn("150.000₫ – 350.000₫", data["reply"])
        self.assertIn("21:00", data["reply"])

