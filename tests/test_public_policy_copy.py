"""Public defaults must not turn demo SOPs into commercial assurances."""
from types import SimpleNamespace
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import SimpleTestCase

from apps.public_web.email_service import send_contact_confirmation_email


class PublicPolicyCopyTests(SimpleTestCase):
    def test_public_templates_render_without_unverified_default_promises(self):
        context = {"product": SimpleNamespace(id=1, name="Thiết bị thử", sku="TEST",
                    description="", unit_price=100, images=SimpleNamespace(count=0))}
        prohibited = ("ISO 27001", "bảo mật tuyệt đối", "xuất VAT tức thì",
                      "thiết bị công nghệ chính hãng", "bán lẻ thiết bị chính hãng",
                      "Đã bao gồm VAT", "12-24 tháng", "100% CO/CQ",
                      "1 đổi 1 trong 30 ngày", "99.8%", "10,000+", "2,400+",
                      "15 - 30 phút", "phản hồi trong 24 giờ")
        for page in ("home", "about", "products", "product_detail", "contact"):
            with self.subTest(page=page):
                html = render_to_string(f"public/{page}.html", context)
                self.assertTrue(html.strip())
                for phrase in prohibited:
                    self.assertNotIn(phrase, html)

    def test_product_description_is_preserved_not_replaced_by_generic_copy(self):
        html = render_to_string("public/product_detail.html", {"product": SimpleNamespace(
            id=1, name="Thiết bị thử", sku="TEST", unit_price=100,
            description="Thông số riêng của sản phẩm", images=SimpleNamespace(count=0))})
        self.assertIn("Thông số riêng của sản phẩm", html)

    def test_contact_receipt_keeps_customer_content_without_deadline(self):
        with patch("apps.public_web.email_service.queue_and_deliver_email") as queue:
            send_contact_confirmation_email("Khách thử", "test@example.test", "0900000000", "Cần tư vấn thiết bị")
        payload = queue.call_args.kwargs
        self.assertEqual(payload["recipient"], "test@example.test")
        for body in (payload["plain_body"], payload["html_body"]):
            self.assertIn("Cần tư vấn thiết bị", body)
            self.assertIn("0900000000", body)
            self.assertIn("Thời gian xử lý cần được xác nhận", body)
            self.assertNotIn("24 giờ làm việc", body)

    def test_populated_cart_does_not_promise_unverified_warranty_or_vat(self):
        product = SimpleNamespace(id=1, name="Thiết bị thử", sku="TEST")
        html = render_to_string("public/cart.html", {
            "items": [SimpleNamespace(product=product, quantity=1, unit_price=100,
                                      line_total=100, image_url="")],
            "summary": SimpleNamespace(total_quantity=1, subtotal=100,
                shipping_fee=30000, total_amount=30100, is_free_shipping=False),
        })
        for claim in ("Đã bao gồm trong giá", "12 - 24 tháng", "30 ngày"):
            self.assertNotIn(claim, html)
        for notice in ("Cần xác nhận theo đơn hàng", "Thời hạn bảo hành theo từng sản phẩm",
                       "Điều kiện đổi trả cần được xác nhận"):
            self.assertIn(notice, html)
        self.assertIn("30100 VNĐ", html)

    def test_product_default_copy_requires_policy_and_stock_confirmation(self):
        html = render_to_string("public/product_detail.html", {"product": SimpleNamespace(
            id=1, name="Thiết bị thử", sku="TEST", unit_price=100,
            description="Thông số riêng", images=SimpleNamespace(count=0))})
        for claim in ("Sẵn sàng giao hỏa tốc", "Đổi mới 30 ngày", "Giao hàng hỏa tốc toàn quốc"):
            self.assertNotIn(claim, html)
        self.assertIn("Tình trạng hàng được xác nhận khi xử lý đơn", html)
        self.assertIn("Điều kiện đổi trả cần được xác nhận", html)

    def test_checkout_does_not_promise_unimplemented_invoice_or_tracking(self):
        html = render_to_string("public/checkout.html", {})
        self.assertNotIn("Mã vận đơn và hóa đơn điện tử sẽ được gửi", html)
        self.assertNotIn("Giao nhanh toàn quốc", html)
        self.assertIn("Vận chuyển và hóa đơn cần được xác nhận riêng", html)
        self.assertIn("phí tiêu chuẩn 30.000đ (Miễn phí từ 5 triệu)", html)

    def test_order_receipt_keeps_totals_without_default_vat_assurance(self):
        html = render_to_string("public/order_success.html", {"order": SimpleNamespace(
            order_number="TEST", status="PENDING", subtotal_amount=100, total_amount=30100)})
        self.assertNotIn("Đã bao gồm trong giá", html)
        self.assertIn("Cần xác nhận theo đơn hàng", html)
        self.assertIn("30100 VNĐ", html)

    def test_staff_banner_does_not_claim_unconditional_permissions(self):
        html = render_to_string("public/customer_account.html", {"can_access_internal": True, "request": SimpleNamespace(
            user=SimpleNamespace(is_staff=True, is_superuser=False, is_authenticated=True,
                                 username="Staff", first_name="Staff", email="staff@example.test"))})
        self.assertNotIn("Bạn có toàn quyền truy cập", html)
        self.assertIn("Quyền truy cập được kiểm tra theo vai trò và workspace", html)

    def test_customer_order_detail_matches_receipt_tax_boundary(self):
        html = render_to_string("public/customer_order_detail.html", {
            "order": SimpleNamespace(order_number="TEST", status="PENDING",
                                     payment_method="COD", subtotal_amount=100,
                                     total_amount=30100),
        })
        self.assertNotIn("Đã bao gồm trong giá", html)
        self.assertIn("Cần xác nhận theo đơn hàng", html)
        self.assertIn("30100 VNĐ", html)

    def test_service_discovery_does_not_publish_unapproved_support_terms(self):
        service = SimpleNamespace(id=1, name="Bảo trì thử", code="TEST",
            category="MAINTENANCE", description="Kiểm tra máy chủ",
            standard_duration_minutes=120, base_fee=100)
        for template in ("public/services.html", "public/service_detail.html"):
            with self.subTest(template=template):
                html = render_to_string(template, {"service": service})
                for claim in ("30 ngày", "24/7", "chứng chỉ hành nghề", "cam kết SLA minh bạch"):
                    self.assertNotIn(claim, html)
        detail = render_to_string("public/service_detail.html", {"service": service})
        self.assertIn("Điều kiện bảo hành dịch vụ cần được xác nhận riêng", detail)
        self.assertIn("Kiểm tra máy chủ", detail)
