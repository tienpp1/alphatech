"""
tests.test_policy_and_claim_consistency
Empirical verification of Policy, SOP, Web, Chatbot, and Email Harmonization (Batch 47).
Validates closure of Checklist 97 Gates 43, 44, 45, 46, and 48.
"""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils import timezone

from apps.public_web.alphatech_ai import (
    handle_authenticity_and_cocq,
    handle_installment_procedure,
    handle_privacy_and_data_security,
    handle_shipping_payment_vat,
    handle_warranty_and_doa,
    handle_onsite_booking_guide,
    handle_b2b_corporate_quotation,
    handle_return_and_refund,
)
from apps.public_web.email_service import (
    send_contact_confirmation_email,
    send_order_confirmation_email,
    send_service_request_confirmation_email,
)


class PolicyAndClaimConsistencyTests(SimpleTestCase):
    """
    Validates published templates, chatbot handlers and email policy boundaries.
    """

    def test_homepage_does_not_reintroduce_unmeasured_production_claims(self):
        html = render_to_string('public/home.html', {})
        for claim in ('99.98%', '&lt; 1.2ms', '100% Chính hãng / Đầy đủ CO-CQ',
                      'Cam kết phản hồi SLA:', 'SLA &lt; 15 PHÚT', 'triệt tiêu lỗi lan truyền'):
            self.assertNotIn(claim, html)
        for notice in ('ví dụ giả định', 'không phải báo giá hay cam kết SLA thực tế',
                       'Chỉ số minh họa', 'Mốc thời gian giả định:'):
            self.assertIn(notice, html)

    def test_service_inquiry_countdown_is_not_a_response_commitment(self):
        html = render_to_string('public/service_request.html', {})
        for claim in ('Phản hồi xác nhận trong vòng', 'Cam kết phản hồi SLA',
                      '(Phản hồi &lt; 15 phút)', 'thuật toán điều phối kỹ sư phù hợp nhất'):
            self.assertNotIn(claim, html)
        for notice in ('không phải cam kết SLA', 'ĐẾM NGƯỢC MÔ PHỎNG',
                       'chưa đồng nghĩa lịch hẹn hoặc kỹ sư đã được phân công'):
            self.assertIn(notice, html)

    # -------------------------------------------------------------------------
    # 1. Gate 43 & 44: Web Templates Free of Unverified / Hyperbolic Claims
    # -------------------------------------------------------------------------
    def test_public_templates_clean_of_hyperbolic_claims(self):
        context = {
            "product": SimpleNamespace(
                id=1,
                name="Laptop ThinkPad Test",
                sku="THINKPAD-01",
                description="Thông số kỹ thuật chính thức từ nhà sản xuất",
                unit_price=Decimal("25000000.00"),
                images=SimpleNamespace(count=0),
            ),
            "service": SimpleNamespace(
                id=1,
                name="Bảo trì máy chủ",
                code="SRV-MAINT",
                category="MAINTENANCE",
                standard_duration_minutes=120,
                base_fee=Decimal("1500000.00"),
                description="Dịch vụ kiểm tra và bảo trì phần cứng máy chủ",
            ),
        }

        forbidden_phrases = (
            "bồi hoàn 200%",
            "trả góp 0%",
            "liên kết 24 ngân hàng",
            "ISO 27001",
            "ISO27001",
            "bảo mật tuyệt đối",
            "xuất VAT tức thì",
            "Đã bao gồm VAT",
            "12-24 tháng",
            "100% CO/CQ",
            "1 đổi 1 trong 30 ngày",
            "99.8%",
            "10,000+",
            "2,400+",
            "15 - 30 phút",
            "phản hồi trong 24 giờ",
        )

        pages = [
            "home",
            "about",
            "products",
            "product_detail",
            "contact",
            "services",
            "service_detail",
        ]

        for page in pages:
            with self.subTest(page=page):
                html = render_to_string(f"public/{page}.html", context)
                self.assertTrue(len(html.strip()) > 0, f"Template public/{page}.html must not render empty")
                for phrase in forbidden_phrases:
                    self.assertNotIn(
                        phrase,
                        html,
                        f"Template public/{page}.html contains forbidden unverified phrase: '{phrase}'",
                    )

    # -------------------------------------------------------------------------
    # 2. Gate 43, 44 & 48: Chatbot Handlers Strictly Reject / Qualify Claims
    # -------------------------------------------------------------------------
    def test_chatbot_authenticity_handler_rejects_unverified_refund_claims(self):
        query = "máy tính này có chính hãng và bồi hoàn 200% nếu là hàng giả không?"
        res = handle_authenticity_and_cocq(query.lower())
        self.assertIsNotNone(res)
        reply = res["reply"]
        self.assertIn("Tôi chưa có hồ sơ đã xác minh để cam kết xuất xứ, CO/CQ hoặc mức bồi hoàn", reply)
        self.assertNotIn("bồi hoàn 200%", reply)
        self.assertNotIn("cam kết 100%", reply)

    def test_chatbot_installment_handler_refuses_fake_checkout_guarantee(self):
        query = "tôi muốn mua trả góp 0% qua cccd duyệt hồ sơ 15 phút"
        res = handle_installment_procedure(query.lower())
        self.assertIsNotNone(res)
        reply = res["reply"]
        self.assertIn("Tôi chưa có chính sách trả góp đã xác minh", reply)
        self.assertIn("Không thể xác nhận trả góp có sẵn tại bước thanh toán", reply)
        self.assertIn("Không gửi ảnh CCCD, số thẻ, mật khẩu hay mã OTP", reply)

    def test_chatbot_security_handler_denies_unverified_iso27001_certification(self):
        query = "hệ thống công ty có chứng nhận ISO 27001 và an toàn dữ liệu tuyệt đối không?"
        res = handle_privacy_and_data_security(query.lower())
        self.assertIsNotNone(res)
        reply = res["reply"]
        self.assertIn("Tôi chưa có bằng chứng xác minh chứng nhận ISO 27001", reply)
        self.assertIn("các cam kết bảo mật tuyệt đối", reply)
        self.assertIn("Không gửi mật khẩu, mã OTP hoặc tài liệu nhạy cảm", reply)

    def test_chatbot_vat_shipping_handler_clarifies_invoice_boundary(self):
        query = "tôi cần xuất hóa đơn đỏ vat tức thì và giao hàng hỏa tốc trong 2 giờ"
        res = handle_shipping_payment_vat(query.lower())
        self.assertIsNotNone(res)
        reply = res["reply"]
        self.assertIn("Tôi chưa có bằng chứng về dịch vụ phát hành hóa đơn VAT tự động", reply)
        self.assertIn("Email xác nhận đơn hàng không thay thế hóa đơn VAT", reply)
        self.assertIn("gửi đơn cũng không đồng nghĩa tiền đã được nhận", reply)

    def test_chatbot_warranty_and_return_handlers_avoid_fabricated_timelines(self):
        # Warranty / DOA
        w_query = "chính sách bảo hành 1 đổi 1 trong 30 ngày và cho mượn máy như thế nào?"
        w_res = handle_warranty_and_doa(w_query.lower())
        self.assertIsNotNone(w_res)
        self.assertIn("Tôi chưa có chính sách đã xác minh để cam kết thời hạn", w_res["reply"])

        # Return / Refund
        r_query = "tôi mua nhầm cấu hình muốn đổi trả hàng và hoàn tiền ngay"
        r_res = handle_return_and_refund(r_query.lower())
        self.assertIsNotNone(r_res)
        self.assertIn("Tôi chưa có chính sách đã xác minh để xác nhận thời hạn đổi trả", r_res["reply"])

    def test_chatbot_b2b_handler_refuses_unverified_credit_terms(self):
        query = "chúng tôi là doanh nghiệp cần mua sỉ 50 laptop công nợ 60 ngày"
        res = handle_b2b_corporate_quotation(query.lower())
        self.assertIsNotNone(res)
        self.assertIn("Tôi chưa có chính sách đã xác minh về chiết khấu, công nợ", res["reply"])

    # -------------------------------------------------------------------------
    # 3. Gate 48: Advisory Chatbot Content vs Executed Transactional Reality
    # -------------------------------------------------------------------------
    def test_onsite_booking_advisory_does_not_assert_confirmed_execution(self):
        query = "đặt lịch kỹ thuật viên đến tận nơi sửa chữa máy chủ phòng lab"
        res = handle_onsite_booking_guide(query.lower())
        self.assertIsNotNone(res)
        reply = res["reply"]
        # Explicit warning that chatbot advice is not transaction execution
        self.assertIn("Gửi biểu mẫu chưa đồng nghĩa lịch hẹn đã được duyệt", reply)
        self.assertIn("Phạm vi phục vụ, chi phí và thời gian đến cần được nhân viên xác nhận", reply)
        self.assertIn("/yeu-cau-dich-vu/", reply)

    # -------------------------------------------------------------------------
    # 4. Gate 46: Cross-Channel Policy Consistency in Customer Emails
    # -------------------------------------------------------------------------
    def test_contact_confirmation_email_omits_unverified_sla(self):
        with patch("apps.public_web.email_service.queue_and_deliver_email") as mock_queue:
            send_contact_confirmation_email(
                "Trần Văn Thử",
                "tranvanthu@test.com",
                "0912345678",
                "Tôi muốn tìm hiểu thêm về dịch vụ bảo trì định kỳ.",
            )
        self.assertTrue(mock_queue.called)
        kwargs = mock_queue.call_args.kwargs
        for body in (kwargs["plain_body"], kwargs["html_body"]):
            self.assertIn("Thời gian xử lý cần được xác nhận", body)
            self.assertNotIn("24 giờ làm việc", body)
            self.assertNotIn("phản hồi trong 24 giờ", body)

    def test_order_confirmation_email_strictly_avoids_exporting_sop_or_vat_claims(self):
        customer = SimpleNamespace(name="Nguyễn Văn A", email="nguyenvana@test.com")
        items = MagicMock()
        items.select_related.return_value.all.return_value = [
            SimpleNamespace(
                product=SimpleNamespace(name="Laptop Dell XPS 13", sku="DELL-XPS13"),
                quantity=1,
                unit_price=Decimal("32000000.00"),
                subtotal=Decimal("32000000.00"),
            )
        ]
        order = SimpleNamespace(
            pk=101,
            customer=customer,
            order_number="ORD-TEST-00101",
            order_timestamp=timezone.now(),
            items=items,
            subtotal_amount=Decimal("32000000.00"),
            total_amount=Decimal("32000000.00"),
            branch=None,
            notes="Giao hàng tiêu chuẩn",
        )

        with patch("apps.public_web.email_service.queue_and_deliver_email") as mock_queue:
            send_order_confirmation_email(order)

        self.assertTrue(mock_queue.called)
        kwargs = mock_queue.call_args.kwargs
        for body in (kwargs["plain_body"], kwargs["html_body"]):
            self.assertIn("ORD-TEST-00101", body)
            self.assertIn("Laptop Dell XPS 13", body)
            self.assertIn("xác nhận điều kiện bảo hành", body)
            # Forbidden claims
            self.assertNotIn("Đã bao gồm VAT", body)
            self.assertNotIn("xuất hóa đơn đỏ tức thì", body)
            self.assertNotIn("ISO 27001", body)
            self.assertNotIn("bảo mật tuyệt đối", body)

    def test_service_request_email_omits_fabricated_sla_deadlines(self):
        customer = SimpleNamespace(name="Phạm Thị B", email="phamtib@test.com")
        service_req = SimpleNamespace(
            pk=202,
            customer=customer,
            request_number="SR-TEST-00202",
            service=SimpleNamespace(name="Khắc phục sự cố mạng nội bộ"),
            created_at=timezone.now(),
            priority="HIGH",
        )

        with patch("apps.public_web.email_service.queue_and_deliver_email") as mock_queue:
            send_service_request_confirmation_email(service_req)

        self.assertTrue(mock_queue.called)
        kwargs = mock_queue.call_args.kwargs
        for body in (kwargs["plain_body"], kwargs["html_body"]):
            self.assertIn("SR-TEST-00202", body)
            self.assertIn("Cao", body)
            self.assertIn("không xác lập cam kết SLA mới", body)
            self.assertNotIn("30 phút", body)
            self.assertNotIn("24/7", body)
            self.assertNotIn("Phản hồi trong ngày", body)
