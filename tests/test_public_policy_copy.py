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
