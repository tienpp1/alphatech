import json
from io import StringIO
from unittest.mock import Mock, patch

import requests
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from apps.public_web.email_backends import BrevoEmailBackend, EmailTransportError
from apps.public_web.email_service import queue_and_deliver_email, deliver_outbox_record
from apps.public_web.models import CustomerEmailDelivery

BACKEND = "apps.public_web.email_backends.BrevoEmailBackend"


def response(status=201, body=None):
    result = Mock(status_code=status)
    result.json.return_value = body if body is not None else {"messageId": "provider-test-id"}
    return result


@override_settings(EMAIL_BACKEND=BACKEND, BREVO_API_KEY="test-only-key",
                   DEFAULT_FROM_EMAIL="AlphaTech <sender@example.com>")
class BrevoBackendTests(SimpleTestCase):
    def message(self, recipient="one@example.com"):
        msg = EmailMultiAlternatives("Xác minh", "Nội dung", to=[recipient])
        msg.attach_alternative("<p>Nội dung</p>", "text/html")
        return msg

    @patch("requests.post")
    def test_two_messages_are_private_and_preserve_html(self, post):
        post.return_value = response()
        messages = [self.message(), self.message("two@example.com")]
        self.assertEqual(BrevoEmailBackend().send_messages(messages), 2)
        for call, recipient in zip(post.call_args_list, ("one@example.com", "two@example.com")):
            self.assertEqual(call.args[0], "https://api.brevo.com/v3/smtp/email")
            payload = call.kwargs["json"]
            self.assertEqual(payload["to"], [{"email": recipient}])
            self.assertNotIn("cc", payload)
            self.assertEqual(payload["htmlContent"], "<p>Nội dung</p>")
            self.assertFalse(call.kwargs["allow_redirects"])
            self.assertEqual(call.kwargs["timeout"], (5, 15))
        self.assertEqual(messages[0].provider_message_id, "provider-test-id")

    @patch("requests.post")
    def test_errors_never_count_as_accepted_or_expose_body(self, post):
        for status in (200, 302, 400, 401, 403, 429, 500):
            post.return_value = response(status, {"message": "private-provider-error"})
            with self.assertRaises(EmailTransportError) as error:
                BrevoEmailBackend().send_messages([self.message()])
            self.assertNotIn("private", str(error.exception))
            self.assertEqual(BrevoEmailBackend(fail_silently=True).send_messages([self.message()]), 0)
        for payload in ({}, [], {"messageId": ""}):
            post.return_value = response(body=payload)
            with self.assertRaisesMessage(EmailTransportError, "BREVO_INVALID_RESPONSE"):
                BrevoEmailBackend().send_messages([self.message()])

    @patch("requests.post", side_effect=requests.Timeout("secret"))
    def test_timeout_has_unknown_delivery_status_and_no_implicit_retry(self, post):
        with self.assertRaisesMessage(EmailTransportError, "BREVO_TIMEOUT_UNKNOWN_DELIVERY"):
            BrevoEmailBackend().send_messages([self.message()])
        post.assert_called_once()

    @patch("requests.post")
    def test_missing_key_or_multiple_recipients_fails_before_network(self, post):
        with override_settings(BREVO_API_KEY=""):
            with self.assertRaisesMessage(EmailTransportError, "BREVO_CONFIG_MISSING"):
                BrevoEmailBackend().send_messages([self.message()])
        message = self.message()
        message.to.append("two@example.com")
        with self.assertRaisesMessage(EmailTransportError, "BREVO_UNSUPPORTED_MESSAGE"):
            BrevoEmailBackend().send_messages([message])
        post.assert_not_called()

    def test_readiness_does_not_require_smtp_for_https_backend(self):
        with override_settings(EMAIL_HOST_USER="", EMAIL_HOST_PASSWORD=""), patch(
            "apps.accounts.management.commands.platform_readiness.connection"
        ), patch("apps.accounts.management.commands.platform_readiness.MigrationExecutor") as executor:
            executor.return_value.migration_plan.return_value = []
            output = StringIO()
            call_command("platform_readiness", "--production", "--json", stdout=output)
            payload = json.loads(output.getvalue())
            self.assertNotIn("smtp_credentials", payload["blockers"])
            self.assertNotIn("delivery_backend_required", payload["blockers"])
            self.assertNotIn("test-only-key", output.getvalue())


@override_settings(EMAIL_BACKEND=BACKEND, BREVO_API_KEY="test-only-key",
                   DEFAULT_FROM_EMAIL="sender@example.com")
class BrevoOutboxTests(TestCase):
    @patch("requests.post")
    def test_failed_record_can_retry_then_remains_idempotent(self, post):
        post.return_value = response(429)
        result = queue_and_deliver_email(event_type="CONTACT", recipient="one@example.com",
            subject="Liên hệ", plain_body="Đã ghi nhận", deduplication_key="brevo-contact-test")
        self.assertEqual(result.status, "FAILED")
        self.assertEqual(result.error_code, "BREVO_RATE_LIMIT")
        delivery = CustomerEmailDelivery.objects.get(public_id=result.public_id)
        post.return_value = response()
        self.assertEqual(deliver_outbox_record(delivery).status, "SENT")
        self.assertEqual(delivery.attempt_count, 2)
        deliver_outbox_record(delivery)
        self.assertEqual(post.call_count, 2)
