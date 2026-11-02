"""A public academic policy is not commercial approval of internal SOPs."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.public_web.alphatech_ai import process_alphatech_query, handle_privacy_and_data_security, handle_warranty_and_doa
from apps.public_web.email_service import _with_public_policy_reference, queue_and_deliver_email
from apps.public_web.models import CustomerEmailDelivery
from apps.public_web.policies import POLICIES, POLICY_VERSION, render_policy_markdown


class DemoPolicyPagesTests(SimpleTestCase):
    def test_restored_routes_are_public_get_pages(self):
        for path in ("/chinh-sach/", "/dieu-khoan/", "/chinh-sach-bao-mat/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_retention_distinguishes_guarded_snapshot_from_local_media_and_backup(self):
        retention = dict((key, paragraphs) for key, _title, paragraphs in POLICIES[1]["sections"])["retention"]
        content = " ".join(retention)
        for expected in ("Media và file model cũ", "ForecastRun", "JSON", "SHA", "không phải bản sao lưu đầy đủ",
                         "chưa có S3", "chưa có bản ngoài máy"):
            self.assertIn(expected, content)
        self.assertNotIn("Media/model hiện nghiệm thu bằng Local Storage", content)

    def test_public_pages_get_without_login_or_database_access(self):
        for name in ("public_policies", "public_terms", "public_privacy"):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, POLICY_VERSION)
                self.assertContains(response, "đồ án")
                self.assertContains(response, "không phải chính sách thương mại")
                self.assertContains(response, "Không thanh toán thật")

    def test_pages_are_read_only_and_head_supported(self):
        for name in ("public_policies", "public_terms", "public_privacy"):
            self.assertEqual(self.client.head(reverse(name)).status_code, 200)
            self.assertEqual(self.client.post(reverse(name), {"approve_sop": True}).status_code, 405)

    def test_master_shows_both_parts_and_individual_pages_are_scoped(self):
        master = self.client.get(reverse("public_policies"))
        self.assertContains(master, 'id="terms-order"')
        self.assertContains(master, 'id="privacy-retention"')
        self.assertNotContains(self.client.get(reverse("public_terms")), 'id="privacy-retention"')
        self.assertNotContains(self.client.get(reverse("public_privacy")), 'id="terms-order"')

    def test_markdown_artifact_exactly_matches_canonical_content(self):
        path = Path(settings.BASE_DIR) / "docs" / "CHINH_SACH_DO_AN_ALPHATECH_V1.md"
        self.assertEqual(path.read_text(encoding="utf-8"), render_policy_markdown())

    def test_section_ids_unique_and_toc_targets_exist(self):
        html = self.client.get(reverse("public_policies")).content.decode()
        ids = []
        for policy in POLICIES:
            for section_id, title, paragraphs in policy["sections"]:
                target = f"{policy['key']}-{section_id}"
                ids.append(target)
                self.assertEqual(html.count(f'id="{target}"'), 1)
                self.assertIn(f'href="#{target}"', html)
                self.assertTrue(title and paragraphs)
        self.assertEqual(len(ids), len(set(ids)))

    def test_documented_shipping_matches_current_cart_constants(self):
        from apps.public_web.cart import STANDARD_SHIPPING_FEE, FREE_SHIPPING_THRESHOLD
        text = render_policy_markdown()
        for value in (STANDARD_SHIPPING_FEE, FREE_SHIPPING_THRESHOLD):
            self.assertIn(f"{int(value):,}đ".replace(",", "."), text)

    def test_registration_checkout_and_both_footers_link_actual_policies(self):
        for template in ("auth_register", "checkout", "home", "about", "contact"):
            with self.subTest(template=template):
                html = render_to_string(f"public/{template}.html", {})
                self.assertIn('href="/dieu-khoan/"', html)
                self.assertIn('href="/chinh-sach-bao-mat/"', html)
                self.assertNotIn('href="/gioi-thieu/" class="hover:text-white transition-colors">Điều khoản', html)
        html = render_to_string("public/auth_register.html", {})
        self.assertIn('rel="noopener noreferrer"', html)

    def test_content_uses_actual_workflow_and_does_not_authorize_internal_sops(self):
        content = render_policy_markdown()
        for expected in ("30.000đ", "5.000.000đ", "CASH", "không đồng nghĩa hoàn tiền",
                         "SENT", "Không hồi tố", "không cấp quyền công bố", "chưa có S3",
                         "Chưa có thời hạn tự động xóa", "Brevo", "Nominatim", "OSRM",
                         "không phải huấn luyện lại Gemini", "P1, P2, P3"):
            self.assertIn(expected, content)
        for promise in ("bồi hoàn 200%", "hoàn tiền 100% trong vòng 24 giờ", "cam kết từ 07 đến 14 ngày"):
            self.assertNotIn(promise, content)

    def test_public_policy_request_requires_no_auth_or_knowledge_lookup(self):
        request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False), session={})
        with patch("apps.knowledge.services.get_grounded_policy_snippet", side_effect=AssertionError("No internal retrieval")):
            result = process_alphatech_query(request, "Cho tôi xem bộ chính sách của website")
        for expected in (POLICY_VERSION, "/chinh-sach/", "/dieu-khoan/", "/chinh-sach-bao-mat/"):
            self.assertIn(expected, result["reply"])

    def test_policy_lookup_does_not_bypass_existing_public_security_boundary(self):
        request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False), session={})
        result = process_alphatech_query(request, "bộ chính sách và mật khẩu admin")
        self.assertIn("không cung cấp bí mật", result["reply"])

    def test_topic_answers_link_policy_without_promising_warranty_or_iso(self):
        privacy = handle_privacy_and_data_security("chính sách bảo mật dữ liệu")
        warranty = handle_warranty_and_doa("chính sách bảo hành")
        self.assertIn("/chinh-sach-bao-mat/", privacy["reply"])
        self.assertIn("Tôi chưa có bằng chứng xác minh", privacy["reply"])
        self.assertIn("/dieu-khoan/", warranty["reply"])
        self.assertIn("Tôi chưa có chính sách đã xác minh để cam kết thời hạn", warranty["reply"])

    @override_settings(PUBLIC_BASE_URL="https://demo.example.test")
    def test_email_footer_uses_environment_url_and_is_inside_html_body(self):
        plain, html = _with_public_policy_reference("Receipt", "<html><body>Receipt</body></html>")
        for value in (POLICY_VERSION, "https://demo.example.test/dieu-khoan/", "https://demo.example.test/chinh-sach-bao-mat/"):
            self.assertIn(value, plain)
            self.assertIn(value, html)
        self.assertLess(html.index(POLICY_VERSION), html.index("</body>"))
        self.assertNotIn("localhost", html)

    @override_settings(PUBLIC_BASE_URL="")
    def test_missing_base_url_does_not_invent_localhost_email_links(self):
        plain, html = _with_public_policy_reference("Receipt", "<p>Receipt</p>")
        self.assertIn(POLICY_VERSION, plain)
        self.assertNotIn('href="', html)
        self.assertNotIn("localhost", plain)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", PUBLIC_BASE_URL="https://demo.example.test")
class DemoPolicyOutboxTests(TestCase):
    def test_new_snapshot_versioned_and_legacy_dedup_hash_preserved(self):
        args = dict(event_type="CONTACT", recipient="guest@example.test", subject="Test", plain_body="Original receipt")
        result = queue_and_deliver_email(**args)
        expected = hashlib.sha256("CONTACT|||guest@example.test|Test|Original receipt".encode()).hexdigest()
        record = CustomerEmailDelivery.objects.get(public_id=result.public_id)
        self.assertEqual(record.deduplication_key, expected)
        self.assertIn(POLICY_VERSION, record.plain_body)
        self.assertEqual(queue_and_deliver_email(**args).public_id, result.public_id)
        self.assertEqual(CustomerEmailDelivery.objects.count(), 1)
        record.refresh_from_db()
        self.assertEqual(record.attempt_count, 1)

    def test_existing_pending_snapshot_kept_on_retry(self):
        args = dict(event_type="CONTACT", recipient="guest@example.test", subject="Test", plain_body="Original receipt", deduplication_key="policy-existing")
        old = CustomerEmailDelivery.objects.create(event_type="CONTACT", recipient=args["recipient"], subject=args["subject"],
            plain_body=args["plain_body"], html_body="<p>Original</p>", deduplication_key=args["deduplication_key"])
        self.assertEqual(queue_and_deliver_email(**args).public_id, str(old.public_id))
        old.refresh_from_db()
        self.assertEqual(old.plain_body, "Original receipt")
        self.assertEqual(old.html_body, "<p>Original</p>")
        self.assertEqual(old.status, CustomerEmailDelivery.Status.SENT)
