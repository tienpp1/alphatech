import re
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import Client, TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.public_web.models import RegistrationCode, SocialIdentity, CustomerEmailDelivery
from apps.public_web.views import _email_verification_token


class RegistrationCodeTests(TestCase):
    payload = dict(name="Khách hàng", email="new@example.com", phone="0900000000",
                   password="safe-password-123", confirm_password="safe-password-123", terms="on")

    def start(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/dang-ky/", self.payload)
        self.user = User.objects.get(email=self.payload["email"])
        self.code = re.search(r"Mã đăng ký AlphaTech của bạn: (\d{6})", mail.outbox[-1].body).group(1)

    def verify(self, code=None, client=None):
        with self.captureOnCommitCallbacks(execute=True):
            return (client or self.client).post("/dang-ky/xac-minh-ma/", {"code": code or self.code})

    def test_correct_code_activates_once_and_sends_welcome(self):
        self.start()
        self.assertFalse(self.user.is_active)
        self.assertNotEqual(RegistrationCode.objects.get(user=self.user).code_hash, self.code)
        self.assertContains(self.client.get("/dang-ky/"), 'autocomplete="one-time-code"')
        self.assertIn("registered=1", self.verify().url)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.workspace_memberships.exists())
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Chào mừng", mail.outbox[-1].subject)
        self.client.logout()
        self.verify()
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 2)

    def test_wrong_code_locks_after_five_and_resend_does_not_reset(self):
        self.start()
        wrong = "000000" if self.code != "000000" else "999999"
        for _ in range(5):
            self.verify(wrong)
        self.verify()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        RegistrationCode.objects.filter(user=self.user).update(sent_at=timezone.now()-timedelta(minutes=2))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/dang-ky/gui-lai-xac-minh/")
        self.assertEqual(len(mail.outbox), 1)

    def test_expired_code_and_signed_link_cannot_bypass(self):
        self.start()
        RegistrationCode.objects.filter(user=self.user).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.verify()
        self.client.get(f"/xac-minh-email/{_email_verification_token(self.user)}/")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_other_session_cannot_verify_or_resend_by_email(self):
        self.start()
        other = Client()
        self.verify(client=other)
        with self.captureOnCommitCallbacks(execute=True):
            other.post("/dang-ky/gui-lai-xac-minh/", {"email": self.user.email})
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("_auth_user_id", other.session)

    def test_wrong_password_cannot_claim_pending_session(self):
        self.start()
        other = Client()
        other.post("/dang-nhap/", {"username_or_email": self.user.email, "password": "wrong-password"})
        self.assertNotIn("pending_verification_user_id", other.session)
        other.post("/dang-ky/", {**self.payload, "password": "wrong-password", "confirm_password": "wrong-password"})
        self.assertNotIn("pending_verification_user_id", other.session)

    def test_correct_password_can_resume_verification_in_new_browser(self):
        self.start()
        other = Client()
        other.post("/dang-nhap/", {"username_or_email": self.user.email, "password": self.payload["password"]})
        self.assertEqual(other.session["pending_verification_user_id"], self.user.pk)
        self.assertIn("registered=1", self.verify(client=other).url)

    def test_send_limit_is_per_account_and_recovers_after_hour(self):
        self.start()
        RegistrationCode.objects.filter(user=self.user).update(sends=5, sent_at=timezone.now()-timedelta(minutes=2))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/dang-ky/gui-lai-xac-minh/")
        self.assertEqual(len(mail.outbox), 1)
        RegistrationCode.objects.filter(user=self.user).update(window_started_at=timezone.now()-timedelta(hours=2))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/dang-ky/gui-lai-xac-minh/")
        self.assertEqual(len(mail.outbox), 2)

    def test_resend_rotates_code_and_enforces_cooldown(self):
        self.start()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/dang-ky/gui-lai-xac-minh/")
        self.assertEqual(len(mail.outbox), 1)
        RegistrationCode.objects.filter(user=self.user).update(sent_at=timezone.now()-timedelta(minutes=2))
        with patch("apps.public_web.registration.secrets.randbelow", return_value=123456 if self.code != "123456" else 654321):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post("/dang-ky/gui-lai-xac-minh/")
        self.assertEqual(len(mail.outbox), 2)
        self.verify()
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        new_code = re.search(r"Mã đăng ký AlphaTech của bạn: (\d{6})", mail.outbox[-1].body).group(1)
        self.assertIn("registered=1", self.verify(new_code).url)

    def test_google_email_case_insensitive_rejected_without_mail(self):
        user = User.objects.create_user(username="google", email="new@example.com")
        SocialIdentity.objects.create(user=user, provider="GOOGLE", subject="sub", provider_email=user.email)
        response = self.client.post("/dang-ky/", {**self.payload, "email": "NEW@example.com"})
        self.assertContains(response, "Email này đã tồn tại")
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(RegistrationCode.objects.exists())
        self.assertFalse(CustomerEmailDelivery.objects.exists())

    def test_failed_delivery_retains_pending_and_shows_warning(self):
        with patch("apps.public_web.email_service.send_mail", return_value=0):
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post("/dang-ky/", self.payload)
        self.assertFalse(User.objects.get(email=self.payload["email"]).is_active)
        self.assertEqual(CustomerEmailDelivery.objects.get().status, "FAILED")
        self.assertContains(self.client.get("/dang-ky/?verification_sent=1"), "email chưa gửi được")

    def test_failed_code_persistence_rolls_back_pending_registration(self):
        with patch("apps.public_web.views.issue_registration_code", side_effect=RuntimeError("test failure")):
            response = self.client.post("/dang-ky/", self.payload)
        self.assertContains(response, "Đã xảy ra lỗi")
        self.assertFalse(User.objects.filter(email=self.payload["email"]).exists())
        self.assertFalse(CustomerEmailDelivery.objects.exists())

    def test_failed_welcome_keeps_verified_account_and_warns(self):
        self.start()
        with patch("apps.public_web.email_service.send_mail", return_value=0):
            self.verify()
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(CustomerEmailDelivery.objects.filter(user=self.user, event_type="WELCOME", status="FAILED").exists())
        response = self.client.get("/tai-khoan/?registered=1")
        self.assertTrue(response.context["email_warning"])

    def test_verify_requires_post_and_csrf(self):
        self.start()
        self.assertEqual(self.client.get("/dang-ky/xac-minh-ma/").status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        self.assertEqual(csrf_client.post("/dang-ky/xac-minh-ma/", {"code": self.code}).status_code, 403)
