import json
import re
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.public_web.email_service import (
    deliver_outbox_record,
    queue_and_deliver_email,
    resolve_customer_recipients,
    send_contact_confirmation_email,
)
from apps.public_web.models import CustomerEmailDelivery, SocialIdentity
from apps.public_web.views import _email_verification_token


User = get_user_model()


class EmailVerificationRegistrationTests(TestCase):
    payload = {
        "name": "Verified Customer",
        "email": "verify@example.com",
        "phone": "0900000000",
        "password": "safe-password-123",
        "confirm_password": "safe-password-123",
        "terms": "on",
    }

    def test_password_registration_requires_mailbox_verification(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/dang-ky/", self.payload)
        self.assertEqual(response.url, "/dang-ky/?verification_sent=1")
        user = User.objects.get(email="verify@example.com")
        self.assertFalse(user.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)
        delivery = CustomerEmailDelivery.objects.get(
            user=user, event_type=CustomerEmailDelivery.EventType.EMAIL_VERIFICATION
        )
        self.assertEqual(delivery.status, CustomerEmailDelivery.Status.SENT)
        code = re.search(r"Mã đăng ký AlphaTech của bạn: (\d{6})", mail.outbox[0].body).group(1)

        with self.captureOnCommitCallbacks(execute=True):
            activated = self.client.post("/dang-ky/xac-minh-ma/", {"code": code})
        self.assertEqual(activated.url, "/tai-khoan/?registered=1&email_verified=1")
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)
        self.assertTrue(CustomerEmailDelivery.objects.filter(
            user=user, event_type=CustomerEmailDelivery.EventType.WELCOME,
            status=CustomerEmailDelivery.Status.SENT,
        ).exists())

        self.client.logout()
        replay = self.client.get(f"/xac-minh-email/{_email_verification_token(user)}/")
        self.assertEqual(replay.url, "/dang-nhap/?verified=already")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_duplicate_registration_never_creates_second_user(self):
        User.objects.create_user(
            username="verify@example.com", email="verify@example.com", password="existing-password"
        )
        response = self.client.post("/dang-ky/", self.payload)
        self.assertContains(response, "Email này đã tồn tại")
        self.assertEqual(User.objects.filter(email__iexact="VERIFY@example.com").count(), 1)

    def test_invalid_email_does_not_create_pending_account_or_delivery(self):
        for email in ("bad space@example.com", "two@@example.com"):
            response = self.client.post("/dang-ky/", {**self.payload, "email": email})
            self.assertContains(response, "Địa chỉ email không đúng định dạng")
            self.assertFalse(User.objects.filter(email=email).exists())
        self.assertFalse(CustomerEmailDelivery.objects.exists())

    def test_inactive_duplicate_can_request_one_throttled_resend(self):
        user = User.objects.create_user(
            username="verify@example.com", email="verify@example.com", password="existing-password",
            is_active=False,
        )
        response = self.client.post("/dang-ky/", self.payload)
        self.assertContains(response, "đã tồn tại nhưng chưa được xác minh")
        with self.captureOnCommitCallbacks(execute=True):
            first = self.client.post("/dang-ky/gui-lai-xac-minh/", {"email": user.email})
        self.assertEqual(first.url, "/dang-ky/?verification_sent=1")
        self.assertEqual(len(mail.outbox), 1)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/dang-ky/gui-lai-xac-minh/", {"email": user.email})
        self.assertEqual(len(mail.outbox), 1)

    def test_invalid_verification_link_does_not_activate_account(self):
        user = User.objects.create_user(
            username="verify@example.com", email="verify@example.com", is_active=False
        )
        response = self.client.get("/xac-minh-email/not-a-valid-token/")
        self.assertIn("verification_error=invalid", response.url)
        user.refresh_from_db()
        self.assertFalse(user.is_active)


class MockHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class CustomerEmailOutboxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="account@example.com", email="Account@Example.com", password="safe-password-123"
        )
        mail.outbox.clear()

    def test_recipient_matrix_normalizes_validates_and_deduplicates(self):
        self.assertEqual(
            resolve_customer_recipients(self.user, "form@example.com"),
            ["account@example.com", "form@example.com"],
        )
        self.assertEqual(resolve_customer_recipients(self.user, "ACCOUNT@example.com"), ["account@example.com"])
        self.assertEqual(resolve_customer_recipients(self.user, "not-an-email"), ["account@example.com"])
        self.assertEqual(resolve_customer_recipients(None, "guest@example.com"), ["guest@example.com"])
        self.assertEqual(resolve_customer_recipients(None, ""), [])

    def test_two_unique_recipients_receive_separate_messages(self):
        for recipient in resolve_customer_recipients(self.user, "form@example.com"):
            result = send_contact_confirmation_email(
                "Customer", recipient, message_body="Need help", user=self.user,
                deduplication_key=f"contact:test:{recipient}",
            )
            self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual({tuple(message.to) for message in mail.outbox}, {
            ("account@example.com",), ("form@example.com",),
        })

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
    )
    def test_missing_smtp_credentials_records_failure_without_raw_exception(self):
        result = queue_and_deliver_email(
            event_type=CustomerEmailDelivery.EventType.CONTACT,
            recipient="account@example.com",
            subject="Subject",
            plain_body="Body",
            user=self.user,
            deduplication_key="smtp-missing",
        )
        self.assertFalse(result)
        delivery = CustomerEmailDelivery.objects.get(deduplication_key="smtp-missing")
        self.assertEqual(delivery.status, CustomerEmailDelivery.Status.FAILED)
        self.assertEqual(delivery.last_error_code, "SMTP_CONFIG_MISSING")
        self.assertEqual(delivery.attempt_count, 1)

    @patch("apps.public_web.email_service.send_mail", return_value=0)
    def test_backend_zero_is_failure_then_retry_can_be_sent(self, mocked_send):
        result = queue_and_deliver_email(
            event_type=CustomerEmailDelivery.EventType.CONTACT,
            recipient="account@example.com", subject="Subject", plain_body="Body",
            user=self.user, deduplication_key="retry-zero",
        )
        self.assertFalse(result)
        delivery = CustomerEmailDelivery.objects.get(deduplication_key="retry-zero")
        self.assertEqual(delivery.status, CustomerEmailDelivery.Status.FAILED)
        mocked_send.return_value = 1
        self.assertTrue(deliver_outbox_record(delivery))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, CustomerEmailDelivery.Status.SENT)
        self.assertEqual(delivery.attempt_count, 2)

    def test_resend_enforces_owner_and_csrf_protected_post(self):
        delivery = CustomerEmailDelivery.objects.create(
            user=self.user, event_type=CustomerEmailDelivery.EventType.CONTACT,
            recipient=self.user.email.lower(), subject="Subject", plain_body="Body",
            status=CustomerEmailDelivery.Status.FAILED, deduplication_key="owned-resend",
        )
        other = User.objects.create_user(username="other@example.com", email="other@example.com", password="pw")
        self.client.force_login(other)
        url = f"/tai-khoan/email/{delivery.public_id}/gui-lai/"
        self.assertEqual(self.client.post(url).status_code, 404)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, CustomerEmailDelivery.Status.SENT)

    def test_bounded_retry_command_processes_failed_delivery(self):
        delivery = CustomerEmailDelivery.objects.create(
            user=self.user, event_type=CustomerEmailDelivery.EventType.CONTACT,
            recipient="account@example.com", subject="Subject", plain_body="Body",
            status=CustomerEmailDelivery.Status.FAILED, deduplication_key="command-retry",
        )
        output = StringIO()
        call_command("retry_customer_email", limit=1, stdout=output)
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, CustomerEmailDelivery.Status.SENT)
        self.assertIn("processed=1 sent=1 failed=0", output.getvalue())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
    )
    def test_registration_survives_smtp_failure_and_shows_truthful_warning(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/dang-ky/", {
                "name": "New Customer", "email": "new@example.com", "phone": "0900000000",
                "password": "safe-password-123", "confirm_password": "safe-password-123", "terms": "on",
            })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(email="new@example.com").exists())
        delivery = CustomerEmailDelivery.objects.get(recipient="new@example.com")
        self.assertEqual(delivery.status, CustomerEmailDelivery.Status.FAILED)
        warning = self.client.get("/dang-ky/")
        self.assertContains(warning, "email chưa gửi được")

    def test_guest_contact_without_email_is_recorded_with_delivery_warning(self):
        response = self.client.post("/lien-he/", {
            "name": "Guest", "phone": "0900000000", "email": "", "message": "Need help",
        })
        self.assertContains(response, "gửi tin nhắn liên hệ thành công")
        self.assertContains(response, "email xác nhận chưa gửi được")
        self.assertEqual(CustomerEmailDelivery.objects.count(), 0)


@override_settings(
    GOOGLE_CLIENT_ID="test-client",
    GOOGLE_CLIENT_SECRET="test-secret",
    GOOGLE_REDIRECT_URI="https://testserver/accounts/google/callback/",
    PUBLIC_BASE_URL="https://testserver",
)
class GoogleOAuthSecuritySimulationTests(TestCase):
    """Mocked provider responses are integration simulations, not live Google proof."""

    def setUp(self):
        self.client = Client()

    def _set_state(self, state="state-value"):
        session = self.client.session
        session["google_oauth_state"] = state
        session["google_oauth_state_issued_at"] = timezone.now().timestamp()
        session["google_oauth_redirect_uri"] = "https://testserver/accounts/google/callback/"
        session.save()

    def _responses(self, **userinfo):
        profile = {"sub": "subject-1", "email": "verified@example.com", "email_verified": True, "name": "Verified User"}
        profile.update(userinfo)
        return [MockHTTPResponse({"access_token": "test-access-token"}), MockHTTPResponse(profile)]

    @patch("apps.public_web.views._google_urlopen")
    def test_unverified_google_email_is_rejected(self, urlopen):
        self._set_state()
        urlopen.side_effect = self._responses(email_verified=False)
        response = self.client.get("/accounts/google/callback/?code=code&state=state-value")
        self.assertIn("google_email_unverified", response.url)
        self.assertFalse(User.objects.filter(email="verified@example.com").exists())
        notice = self.client.get(response.url)
        self.assertContains(notice, "Email Google chưa được xác minh")

    @patch("apps.public_web.views._google_urlopen")
    def test_subject_is_persisted_and_state_cannot_be_replayed(self, urlopen):
        self._set_state()
        urlopen.side_effect = self._responses()
        first = self.client.get("/accounts/google/callback/?code=code&state=state-value")
        self.assertEqual(first.status_code, 302)
        user = User.objects.get(email="verified@example.com")
        self.assertTrue(SocialIdentity.objects.filter(
            provider=SocialIdentity.Provider.GOOGLE, subject="subject-1", user=user
        ).exists())
        replay = self.client.get("/accounts/google/callback/?code=code&state=state-value")
        self.assertIn("google_csrf_invalid", replay.url)

    def test_expired_state_is_rejected_before_network_call(self):
        session = self.client.session
        session["google_oauth_state"] = "expired"
        session["google_oauth_state_issued_at"] = timezone.now().timestamp() - 601
        session.save()
        with patch("apps.public_web.views._google_urlopen") as urlopen:
            response = self.client.get("/accounts/google/callback/?code=code&state=expired")
        self.assertIn("google_csrf_invalid", response.url)
        urlopen.assert_not_called()

    @override_settings(GOOGLE_REDIRECT_URI="", DEBUG=False)
    def test_production_does_not_derive_redirect_from_host(self):
        response = self.client.get("/accounts/google/?auth=1")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "accounts.google.com/o/oauth2/v2/auth")

    @patch("apps.public_web.views._google_urlopen")
    def test_existing_user_with_another_google_subject_is_collision(self, urlopen):
        user = User.objects.create_user(username="verified@example.com", email="verified@example.com")
        SocialIdentity.objects.create(
            provider=SocialIdentity.Provider.GOOGLE, subject="old-subject", user=user,
            provider_email=user.email,
        )
        self._set_state()
        urlopen.side_effect = self._responses(sub="new-subject")
        response = self.client.get("/accounts/google/callback/?code=code&state=state-value")
        self.assertIn("google_identity_collision", response.url)
        self.assertEqual(SocialIdentity.objects.filter(user=user).count(), 1)

    @patch("apps.public_web.views._google_urlopen")
    def test_verified_google_activates_same_pending_user_without_duplicate(self, urlopen):
        pending = User.objects.create_user(
            username="verified@example.com", email="verified@example.com",
            password="password-registration", is_active=False,
        )
        self._set_state()
        urlopen.side_effect = self._responses()
        response = self.client.get("/accounts/google/callback/?code=code&state=state-value")
        self.assertEqual(response.status_code, 302)
        pending.refresh_from_db()
        self.assertTrue(pending.is_active)
        self.assertFalse(pending.has_usable_password())
        self.assertEqual(User.objects.filter(email__iexact="VERIFIED@example.com").count(), 1)
        self.assertTrue(SocialIdentity.objects.filter(user=pending, subject="subject-1").exists())

    @patch("apps.public_web.views._google_urlopen")
    def test_google_created_email_cannot_be_registered_again(self, urlopen):
        self._set_state()
        urlopen.side_effect = self._responses()
        self.client.get("/accounts/google/callback/?code=code&state=state-value")
        self.client.get("/dang-xuat/")
        response = self.client.post("/dang-ky/", {
            "name": "Duplicate", "email": "VERIFIED@example.com", "phone": "0900000000",
            "password": "another-password", "confirm_password": "another-password", "terms": "on",
        })
        self.assertContains(response, "Email này đã tồn tại")
        self.assertEqual(User.objects.filter(email__iexact="verified@example.com").count(), 1)
