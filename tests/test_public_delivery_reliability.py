"""Commit-boundary public delivery regressions; providers are not contacted."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TransactionTestCase, override_settings

from apps.public_web.email_service import deliver_outbox_record
from apps.public_web.models import ContactSubmission, CustomerEmailDelivery
from apps.retail.models import Branch, Category, Order, Product, StockBalance
from apps.service_ops.models import Service, ServiceRequest
from apps.workspaces.models import Workspace


class ContactFormRetentionSafetyTests(SimpleTestCase):
    def test_retained_invalid_form_values_are_html_escaped(self):
        attack = '</textarea><script>alert("unsafe")</script>'
        html = render_to_string("public/contact.html", {
            "error_message": "Địa chỉ email không hợp lệ",
            "form_data": {"name": attack, "phone": "0900000000", "email": "bad-email", "message": attack},
        })
        self.assertIn("&lt;/textarea&gt;&lt;script&gt;", html)
        self.assertNotIn(attack, html)
        self.assertIn('role="alert"', html)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    HOME_DELIVERY_FULFILLMENT_POLICY="strict",
    HOME_DELIVERY_DEFAULT_BRANCH_CODE="BR-D1",
    HOME_DELIVERY_FALLBACK_BRANCH_CODES=(),
)
class PublicDeliveryReliabilityTests(TransactionTestCase):
    def setUp(self):
        self.retail = Workspace.objects.create(code="delivery-retail", name="Retail", workspace_type="RETAIL")
        self.service_ws = Workspace.objects.create(code="delivery-service", name="Service", workspace_type="SERVICE")
        self.service = Service.objects.create(workspace=self.service_ws, code="SUPPORT", name="TEST support")
        self.user = get_user_model().objects.create_user(username="delivery-owner", email="account@example.test")
        category = Category.objects.create(workspace=self.retail, code="TEST", name="TEST")
        self.product = Product.objects.create(workspace=self.retail, category=category,
                                             sku="TEST-DELIVERY", name="TEST product", unit_price=100)
        self.branch = Branch.objects.create(workspace=self.retail, code="BR-D1", name="TEST branch")
        self.stock = StockBalance.objects.create(workspace=self.retail, branch=self.branch,
                                                product=self.product, quantity_on_hand=10)

    def contact(self, **changes):
        return self.client.post("/lien-he/", {"name": "Tên nhập trong form", "phone": "0900000000",
                                               "email": "form@example.test", "message": "Nội dung TEST",
                                               **changes})

    def test_invalid_contact_email_is_rejected_before_any_event_or_send(self):
        for authenticated in (False, True):
            if authenticated:
                self.client.force_login(self.user)
            for email in ("not-an-email", "bad@@example.test"):
                with patch("apps.public_web.email_service.send_mail") as send:
                    response = self.contact(email=email)
                self.assertFalse(ContactSubmission.objects.exists())
                self.assertFalse(CustomerEmailDelivery.objects.exists())
                send.assert_not_called()
                self.assertContains(response, "Địa chỉ email không hợp lệ")
                self.assertContains(response, email)
                self.assertContains(response, "Nội dung TEST")
                self.assertContains(response, "0900000000")

    def test_invalid_legacy_contact_email_is_rejected(self):
        response = self.contact(email="", contact="bad@@example.test")
        self.assertFalse(ContactSubmission.objects.exists())
        self.assertFalse(CustomerEmailDelivery.objects.exists())
        self.assertContains(response, "Địa chỉ email không hợp lệ")

    def test_blank_form_email_keeps_account_delivery_and_does_not_change_identity(self):
        self.client.force_login(self.user)
        response = self.contact(email="")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["email_warning"])
        self.assertEqual([message.to for message in mail.outbox], [["account@example.test"]])
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "account@example.test")
        self.assertEqual(self.user.first_name, "")

    def test_contact_partial_failure_warns_and_duplicate_post_retries_only_failed_address(self):
        self.client.force_login(self.user)
        with patch("apps.public_web.email_service.send_mail", side_effect=[1, 0]) as send:
            response = self.contact()
        self.assertTrue(response.context["email_warning"])
        self.assertContains(response, "email xác nhận chưa gửi được")
        self.assertEqual([call.kwargs["recipient_list"] for call in send.call_args_list],
                         [["account@example.test"], ["form@example.test"]])
        self.assertEqual(ContactSubmission.objects.count(), 1)
        self.assertEqual(dict(CustomerEmailDelivery.objects.values_list("recipient", "status")),
                         {"account@example.test": "SENT", "form@example.test": "FAILED"})
        with patch("apps.public_web.email_service.send_mail", return_value=1) as send:
            response = self.contact()
        self.assertFalse(response.context["email_warning"])
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.kwargs["recipient_list"], ["form@example.test"])
        self.assertEqual(ContactSubmission.objects.count(), 1)
        self.assertEqual(CustomerEmailDelivery.objects.count(), 2)
        self.assertFalse(CustomerEmailDelivery.objects.exclude(status="SENT").exists())

    def test_service_partial_failure_survives_commit_and_prg_retry(self):
        self.client.force_login(self.user)
        token = self.client.get("/yeu-cau-dich-vu/").context["submission_token"]
        payload = {"customer_name": "TEST", "phone": "0900000000", "email": "form@example.test",
                   "service_id": str(self.service.pk), "description": "Nội dung TEST", "submission_token": token}
        with patch("apps.public_web.email_service.send_mail", side_effect=[0, 1]) as send:
            response = self.client.post("/yeu-cau-dich-vu/", payload, follow=True)
        self.assertTrue(response.context["email_warning"])
        self.assertEqual(send.call_count, 2)
        self.assertEqual(ServiceRequest.objects.count(), 1)
        with patch("apps.public_web.email_service.send_mail", return_value=1) as send:
            response = self.client.post("/yeu-cau-dich-vu/", payload, follow=True)
        self.assertFalse(response.context["email_warning"])
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.kwargs["recipient_list"], ["account@example.test"])
        self.assertEqual(ServiceRequest.objects.count(), 1)
        self.assertEqual(CustomerEmailDelivery.objects.count(), 2)
    def test_strict_checkout_commits_stock_and_order_when_one_email_fails(self):
        self.client.force_login(self.user)
        self.client.post(f"/gio-hang/them/{self.product.pk}/", {"quantity": "1"})
        with patch("apps.public_web.email_service.send_mail", side_effect=[0, 1]) as send:
            response = self.client.post("/thanh-toan/dat-hang/", {"name": "TEST", "phone": "0900000000",
                "email": "form@example.test", "address": "TEST address", "delivery_method": "HOME_DELIVERY"})
        order = Order.objects.get()
        self.assertEqual(response.url, f"/dat-hang-thanh-cong/{order.order_number}/")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, 9)
        self.assertTrue(order.fulfillment_stock_reserved)
        self.assertEqual([call.kwargs["recipient_list"] for call in send.call_args_list],
                         [["account@example.test"], ["form@example.test"]])
        self.assertContains(self.client.get(response.url), "email xác nhận chưa gửi được")
        failed = CustomerEmailDelivery.objects.get(status="FAILED")
        with patch("apps.public_web.email_service.send_mail", return_value=1) as send:
            deliver_outbox_record(failed)
            deliver_outbox_record(failed)
        self.assertEqual(send.call_count, 1)
        self.assertNotContains(self.client.get(response.url), "email xác nhận chưa gửi được")
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, 9)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CustomerEmailDelivery.objects.count(), 2)
