"""
Automated Test Suite for Google OAuth 2.0 Integration and Customer Email Notifications.
Covers:
- Google Sign-In authorization redirect and state CSRF protection
- Google OAuth callback flow (Token exchange, UserInfo, User & Customer creation, Session login)
- Verification that public customers created via Google OAuth receive ZERO internal memberships (Rule 4)
- Automated Customer Email Notifications (Welcome, Login Alert, Order Receipt, Service Ticket, Contact Inquiry)
"""

import json
from decimal import Decimal
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, Client, override_settings
from django.utils import timezone

from apps.retail.models import Product, Category, Branch, Customer, Order, OrderItem, OrderStatus
from apps.service_ops.models import Service, ServiceCategory, ServiceRequest
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.public_web.models import CustomerEmailDelivery
from apps.public_web.views import _email_verification_token

User = get_user_model()


class MockHTTPResponse:
    """Mock HTTP response object for urllib.request.urlopen."""
    def __init__(self, json_data, status_code=200):
        self.data = json.dumps(json_data).encode("utf-8")
        self.status = status_code

    def read(self):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@override_settings(
    GOOGLE_CLIENT_ID="test-google-client-id",
    GOOGLE_CLIENT_SECRET="test-google-client-secret",
    GOOGLE_REDIRECT_URI="https://testserver/accounts/google/callback/",
    PUBLIC_BASE_URL="https://testserver",
)
class GoogleOAuthAndEmailNotificationsTestCase(TestCase):
    """
    Validates end-to-end Google OAuth 2.0 workflows and all automated customer email dispatches.
    """

    def setUp(self):
        self.client = Client()

        # 1. Setup Retail & Service Workspaces
        self.retail_ws = Workspace.objects.create(
            name="ABC Tech Retail",
            code="abc-retail-test",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.service_ws = Workspace.objects.create(
            name="XYZ IT Services",
            code="xyz-services-test",
            workspace_type=WorkspaceType.SERVICE,
        )

        # 2. Setup Retail Branch & Product
        self.branch = Branch.objects.create(
            workspace=self.retail_ws,
            name="Chi nhánh Quận 1",
            code="BR-Q1",
            address="123 Lê Lợi, Bến Nghé, Quận 1, TP.HCM",
            is_active=True,
        )
        self.category = Category.objects.create(
            workspace=self.retail_ws,
            name="Laptop Doanh Nhân",
            code="LAPTOP-BIZ",
            is_active=True,
        )
        self.product = Product.objects.create(
            workspace=self.retail_ws,
            category=self.category,
            name="Dell Latitude 7440 Ultrabook",
            sku="DELL-LAT-7440",
            unit_price=Decimal("24500000.00"),
            is_active=True,
        )

        # 3. Setup IT Service
        self.service = Service.objects.create(
            workspace=self.service_ws,
            code="SRV-SRV-MAINT",
            category=ServiceCategory.MAINTENANCE,
            name="Bảo trì hạ tầng máy chủ",
            base_fee=Decimal("3500000.00"),
            is_active=True,
        )

        # 4. Setup Existing Customer User
        self.existing_user = User.objects.create_user(
            username="existing_customer@gmail.com",
            email="existing_customer@gmail.com",
            password="SecureCustomerPass123!",
            first_name="Đặng Văn Khách",
        )
        self.existing_customer = Customer.objects.create(
            workspace=self.retail_ws,
            code="CUST-EXIST-01",
            name="Đặng Văn Khách",
            email="existing_customer@gmail.com",
            phone="0918112233",
            address="456 Hai Bà Trưng, Quận 3, TP.HCM",
        )

        # Clear mail outbox before every test
        mail.outbox.clear()

    # =========================================================================
    # A. Google OAuth 2.0 Auth Redirect & Status Endpoint
    # =========================================================================

    def test_google_auth_endpoint_returns_status_200(self):
        """GET /accounts/google/ returns 200 with configured Google OAuth state and action button."""
        response = self.client.get("/accounts/google/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Google", content)
        self.assertIn("OAuth 2.0 Sẵn sàng", content)
        self.assertIn("/accounts/google/?auth=1", content)

    def test_google_auth_redirect_to_google_authorization_endpoint(self):
        """GET /accounts/google/?auth=1 redirects to Google OAuth 2.0 authorization endpoint."""
        response = self.client.get("/accounts/google/?auth=1")
        self.assertEqual(response.status_code, 302)
        redirect_url = response.url
        self.assertTrue(redirect_url.startswith("https://accounts.google.com/o/oauth2/v2/auth"))
        self.assertIn("client_id=test-google-client-id", redirect_url)
        self.assertIn("response_type=code", redirect_url)
        self.assertIn("scope=openid+email+profile", redirect_url)
        self.assertIn("state=", redirect_url)

        # State must be securely stored in user session
        session = self.client.session
        self.assertTrue(len(session.get("google_oauth_state", "")) > 10)

    def test_google_auth_preserves_next_url_in_session(self):
        """GET /accounts/google/?auth=1&next=/san-pham/ stores next_url safely in session."""
        response = self.client.get("/accounts/google/?auth=1&next=/san-pham/")
        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertEqual(session.get("google_oauth_next"), "/san-pham/")

    # =========================================================================
    # B. Google OAuth 2.0 Callback Flow & Invariant Enforcement
    # =========================================================================

    @patch("apps.public_web.views._google_urlopen")
    def test_google_callback_first_time_user_creates_account_and_dispatches_emails(self, mock_urlopen):
        """
        New customer signs in via Google:
        1. Creates public User and Customer record.
        2. Logs customer in.
        3. Strictly prevents WorkspaceMembership or staff role (Rule 4).
        4. Dispatches Welcome email and Security Login Alert email to Gmail account.
        """
        # Set session state
        session = self.client.session
        session["google_oauth_state"] = "secure_test_state_12345"
        session["google_oauth_state_issued_at"] = timezone.now().timestamp()
        session["google_oauth_next"] = "/tai-khoan/"
        session.save()

        # Mock Google Token exchange response & Google UserInfo response
        mock_token_resp = MockHTTPResponse({"access_token": "mock_google_access_token_abc"})
        mock_userinfo_resp = MockHTTPResponse({
            "sub": "google-sub-998877",
            "email": "new_google_customer@gmail.com",
            "email_verified": True,
            "name": "Nguyễn Hoàng Google",
            "given_name": "Hoàng",
            "picture": "https://lh3.googleusercontent.com/a/test",
        })
        mock_urlopen.side_effect = [mock_token_resp, mock_userinfo_resp]

        callback_url = "/accounts/google/callback/?code=mock_auth_code_xyz&state=secure_test_state_12345"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.get(callback_url)

        # Should redirect to next_url (/tai-khoan/)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/tai-khoan/")

        # Verify User was created
        created_user = User.objects.filter(email="new_google_customer@gmail.com").first()
        self.assertIsNotNone(created_user)
        self.assertEqual(created_user.first_name, "Nguyễn Hoàng Google")

        # Verify Customer was created in Retail workspace
        customer_profile = Customer.objects.filter(email="new_google_customer@gmail.com").first()
        self.assertIsNotNone(customer_profile)
        self.assertEqual(customer_profile.name, "Nguyễn Hoàng Google")
        self.assertEqual(customer_profile.workspace, self.retail_ws)

        # CRITICAL RULE 4 CHECK: Public customer must NEVER have internal memberships
        memberships_count = WorkspaceMembership.objects.filter(user=created_user).count()
        self.assertEqual(memberships_count, 0)
        self.assertFalse(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)

        # Verify authenticated session
        self.assertEqual(int(self.client.session["_auth_user_id"]), created_user.pk)

        # Verify Emails dispatched (Welcome Email + Login Alert Email)
        self.assertEqual(len(mail.outbox), 2)
        subjects = [m.subject for m in mail.outbox]
        recipients = [m.to[0] for m in mail.outbox]

        self.assertTrue(any("Chào mừng" in s for s in subjects))
        self.assertTrue(any("đăng nhập thành công" in s for s in subjects))
        self.assertTrue(all(r == "new_google_customer@gmail.com" for r in recipients))

    @patch("apps.public_web.views._google_urlopen")
    def test_google_callback_existing_user_logs_in_and_dispatches_login_alert(self, mock_urlopen):
        """
        Existing customer signs in with Google:
        1. Logs into existing user.
        2. Dispatches Security Login Alert email (no duplicate welcome email).
        """
        session = self.client.session
        session["google_oauth_state"] = "existing_state_token"
        session["google_oauth_state_issued_at"] = timezone.now().timestamp()
        session.save()

        mock_token_resp = MockHTTPResponse({"access_token": "mock_google_access_token_def"})
        mock_userinfo_resp = MockHTTPResponse({
            "sub": "google-sub-112233",
            "email": "existing_customer@gmail.com",
            "email_verified": True,
            "name": "Đặng Văn Khách",
        })
        mock_urlopen.side_effect = [mock_token_resp, mock_userinfo_resp]

        callback_url = "/accounts/google/callback/?code=valid_code&state=existing_state_token"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.get(callback_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/tai-khoan/?login=google")

        # Verify authenticated session
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.existing_user.pk)

        # Verify only 1 email dispatched (Security Login Alert, no welcome email)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("đăng nhập thành công", mail.outbox[0].subject)
        self.assertIn("Google Sign-In", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["existing_customer@gmail.com"])

    def test_google_callback_invalid_csrf_state_rejected(self):
        """Callback with tampered or mismatched state parameter redirects with security error."""
        session = self.client.session
        session["google_oauth_state"] = "legitimate_state"
        session["google_oauth_state_issued_at"] = timezone.now().timestamp()
        session.save()

        callback_url = "/accounts/google/callback/?code=anycode&state=tampered_state"
        response = self.client.get(callback_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("error=google_csrf_invalid", response.url)

    # =========================================================================
    # C. Standard Customer Registration & Login Email Notifications
    # =========================================================================

    def test_standard_customer_registration_verifies_email_then_sends_welcome(self):
        """Password registration stays inactive until the mailbox link is opened."""
        payload = {
            "name": "Vũ Minh Khách",
            "email": "vuminh@gmail.com",
            "phone": "0987654321",
            "address": "789 Điện Biên Phủ, Bình Thạnh, TP.HCM",
            "password": "CustomerSecure2026!",
            "confirm_password": "CustomerSecure2026!",
            "terms": "on",
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/dang-ky/", payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dang-ky/?verification_sent=1")

        created_user = User.objects.get(email="vuminh@gmail.com")
        self.assertFalse(created_user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        email_msg = mail.outbox[0]
        self.assertIn("Xác minh email", email_msg.subject)
        self.assertEqual(email_msg.to, ["vuminh@gmail.com"])
        self.assertEqual(
            CustomerEmailDelivery.objects.get(user=created_user).event_type,
            CustomerEmailDelivery.EventType.EMAIL_VERIFICATION,
        )

        token = _email_verification_token(created_user)
        with self.captureOnCommitCallbacks(execute=True):
            verified = self.client.get(f"/xac-minh-email/{token}/")
        self.assertEqual(verified.url, "/tai-khoan/?registered=1&email_verified=1")
        created_user.refresh_from_db()
        self.assertTrue(created_user.is_active)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Chào mừng", mail.outbox[1].subject)

    def test_standard_customer_login_dispatches_security_alert_email(self):
        """POST /dang-nhap/ dispatches login security alert email with IP and timestamp."""
        payload = {
            "username_or_email": "existing_customer@gmail.com",
            "password": "SecureCustomerPass123!",
        }
        response = self.client.post("/dang-nhap/", payload)
        self.assertEqual(response.status_code, 302)

        # Verify Login Security Alert in outbox
        self.assertEqual(len(mail.outbox), 1)
        alert_email = mail.outbox[0]
        self.assertIn("đăng nhập thành công", alert_email.subject)
        self.assertEqual(alert_email.to, ["existing_customer@gmail.com"])
        self.assertIn("Mật khẩu tài khoản", alert_email.body)

    # =========================================================================
    # D. E-Commerce Order Placement Email Receipt Notification
    # =========================================================================

    def test_checkout_order_placement_dispatches_itemized_email_receipt(self):
        """Placing an order sends itemized receipt with SKU, quantities, and totals to customer email."""
        # 1. Add product to cart
        self.client.post(f"/gio-hang/them/{self.product.id}/", {"quantity": 2, "action": "add_to_cart"})

        # 2. Place Order
        order_payload = {
            "name": "Trần Thị Mua Hàng",
            "phone": "0933445566",
            "email": "customer_order@gmail.com",
            "address": "12 Nguyễn Văn Trỗi",
            "district": "Phú Nhuận",
            "city": "TP.HCM",
            "notes": "Giao giờ hành chính",
            "delivery_method": "HOME_DELIVERY",
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/thanh-toan/dat-hang/", order_payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/dat-hang-thanh-cong/"))

        # Verify Order Receipt in outbox
        self.assertEqual(len(mail.outbox), 1)
        order_email = mail.outbox[0]
        self.assertIn("Xác nhận đơn hàng", order_email.subject)
        self.assertEqual(order_email.to, ["customer_order@gmail.com"])
        self.assertIn("Dell Latitude 7440 Ultrabook", order_email.body)
        self.assertIn("DELL-LAT-7440", order_email.body)
        self.assertIn("x 2", order_email.body)

    def test_authenticated_checkout_sends_separate_account_and_form_messages(self):
        self.client.force_login(self.existing_user)
        self.client.post(f"/gio-hang/them/{self.product.id}/", {"quantity": 1})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/thanh-toan/dat-hang/", {
                "name": "Người nhận", "phone": "0933445566", "email": "recipient@example.com",
                "address": "12 Nguyễn Văn Trỗi", "district": "Phú Nhuận", "city": "TP.HCM",
                "delivery_method": "HOME_DELIVERY",
            })
        self.assertEqual(response.status_code, 302)
        self.assertEqual({tuple(message.to) for message in mail.outbox}, {
            ("existing_customer@gmail.com",), ("recipient@example.com",),
        })

    # =========================================================================
    # E. Technical Service Request Submission Email Notification
    # =========================================================================

    def test_service_request_submission_dispatches_confirmation_email(self):
        """Submitting a service request sends confirmation email with ticket number and SLA."""
        payload = {
            "customer_name": "Lê Kỹ Thuật",
            "email": "lekythuat@gmail.com",
            "phone": "0909123456",
            "service_id": str(self.service.id),
            "description": "Hệ thống server phòng máy chi nhánh hoạt động quá tải và ngắt đột ngột lúc 09h sáng.",
            "address": "Phòng máy chi nhánh 2",
            "preferred_time": "Trong ngày",
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/yeu-cau-dich-vu/", payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("tiếp nhận thành công", response.content.decode("utf-8").lower())

        # Verify Service Ticket Confirmation Email
        self.assertEqual(len(mail.outbox), 1)
        service_email = mail.outbox[0]
        self.assertIn("Tiếp nhận yêu cầu kỹ thuật", service_email.subject)
        self.assertEqual(service_email.to, ["lekythuat@gmail.com"])
        self.assertIn("Bảo trì hạ tầng máy chủ", service_email.body)
        self.assertIn("Mã phiếu:", service_email.body)

    def test_authenticated_service_request_sends_account_and_form_messages(self):
        self.client.force_login(self.existing_user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/yeu-cau-dich-vu/", {
                "customer_name": "Khách", "email": "service-form@example.com", "phone": "0909123456",
                "service_id": str(self.service.id), "description": "Máy chủ cần kiểm tra.",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual({tuple(message.to) for message in mail.outbox}, {
            ("existing_customer@gmail.com",), ("service-form@example.com",),
        })

    # =========================================================================
    # F. Contact Inquiry Submission Email Notification
    # =========================================================================

    def test_contact_form_submission_dispatches_confirmation_email(self):
        """Submitting contact form sends inquiry receipt email to sender with 24-hour turnaround notice."""
        payload = {
            "name": "Phạm Doanh Nghiệp",
            "email": "phamdoanhnghiep@gmail.com",
            "phone": "0912999888",
            "subject": "Tư vấn gói chuyển đổi số toàn diện",
            "message": "Doanh nghiệp chúng tôi muốn tìm hiểu giải pháp AI và hạ tầng mạng.",
        }
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/lien-he/", payload)
        self.assertEqual(response.status_code, 200)

        # Verify Contact Inquiry Confirmation Email
        self.assertEqual(len(mail.outbox), 1)
        contact_email = mail.outbox[0]
        self.assertIn("Xác nhận tiếp nhận tin nhắn liên hệ", contact_email.subject)
        self.assertEqual(contact_email.to, ["phamdoanhnghiep@gmail.com"])
        self.assertIn("Doanh nghiệp chúng tôi muốn tìm hiểu giải pháp AI và hạ tầng mạng.", contact_email.body)
        self.assertIn("24 giờ", contact_email.body)

    def test_authenticated_contact_sends_separate_account_and_form_messages(self):
        self.client.force_login(self.existing_user)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/lien-he/", {
                "name": "Khách", "email": "contact-form@example.com", "phone": "0912999888",
                "message": "Tôi cần tư vấn.",
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual({tuple(message.to) for message in mail.outbox}, {
            ("existing_customer@gmail.com",), ("contact-form@example.com",),
        })
