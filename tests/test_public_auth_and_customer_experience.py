"""
Automated Test Suite for Public Authentication, Customer Registration, Password Reset, Customer Account, and Light Theme Redesign.
"""

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase, Client
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

from apps.accounts.models import Role, Permission
from apps.retail.models import Product, Category, Branch, Customer, Order
from apps.service_ops.models import Service, ServiceCategory, ServiceRequest
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType

User = get_user_model()


class PublicAuthAndCustomerExperienceTestCase(TestCase):
    """
    Test suite covering customer login, customer registration, password reset,
    customer account portal, Google sign-in status, and light theme rendering.
    """

    def setUp(self):
        self.client = Client()

        # 1. Setup Workspaces
        self.retail_ws = Workspace.objects.create(
            name="ABC Tech Retail",
            code="abc-retail",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.service_ws = Workspace.objects.create(
            name="XYZ IT Services",
            code="xyz-services",
            workspace_type=WorkspaceType.SERVICE,
        )

        # 2. Setup Internal Staff & Public Customer Users
        self.manager_user = User.objects.create_user(
            username="manager_test",
            email="manager@abctech.vn",
            password="ManagerPassword123!",
            first_name="Quản Lý",
        )
        self.manager_role = Role.objects.create(name="MANAGER", description="Internal Manager")
        WorkspaceMembership.objects.create(
            user=self.manager_user,
            workspace=self.retail_ws,
            role=self.manager_role,
            is_active=True,
            is_default=True,
        )

        self.customer_user = User.objects.create_user(
            username="customer_test@example.com",
            email="customer_test@example.com",
            password="CustomerPassword123!",
            first_name="Nguyễn Văn Khách",
        )
        self.customer_profile = Customer.objects.create(
            workspace=self.retail_ws,
            user=self.customer_user,
            code="CUST-TEST-01",
            name="Nguyễn Văn Khách",
            email="customer_test@example.com",
            phone="0912345678",
            address="123 Nguyễn Huệ, Quận 1, TP.HCM",
        )

        # 3. Setup Test Product & Category
        self.category = Category.objects.create(
            workspace=self.retail_ws,
            name="Laptop",
            code="laptop",
            is_active=True,
        )
        self.product = Product.objects.create(
            workspace=self.retail_ws,
            category=self.category,
            name="Laptop Dell XPS 15",
            sku="LAP-DELL-XPS15",
            unit_price=Decimal("35000000.00"),
            cost_price=Decimal("28000000.00"),
            is_active=True,
        )

        # 4. Setup Test IT Service
        self.service = Service.objects.create(
            workspace=self.service_ws,
            name="Cài đặt hệ điều hành & phần mềm",
            code="SRV-INSTALL-01",
            category=ServiceCategory.INSTALLATION,
            standard_duration_minutes=60,
            base_fee=Decimal("250000.00"),
            is_active=True,
        )

    # =========================================================================
    # A. Public Customer Login Flow
    # =========================================================================

    def test_public_login_page_renders_light_theme(self):
        """GET /dang-nhap/ returns 200 with light auth template and Google button."""
        response = self.client.get("/dang-nhap/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Đăng nhập", content)
        self.assertIn("Đăng ký", content)
        self.assertIn("Đăng nhập bằng Google", content)
        self.assertIn("Quên mật khẩu?", content)

    def test_public_customer_login_success_redirects_to_account(self):
        """POST /dang-nhap/ with customer credentials redirects to /tai-khoan/."""
        response = self.client.post("/dang-nhap/", {
            "username_or_email": "customer_test@example.com",
            "password": "CustomerPassword123!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/tai-khoan/")

    def test_internal_staff_login_redirects_to_noibo(self):
        """POST /dang-nhap/ with manager credentials redirects to /noibo/."""
        response = self.client.post("/dang-nhap/", {
            "username_or_email": "manager@abctech.vn",
            "password": "ManagerPassword123!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/noibo/")

    def test_public_login_invalid_credentials(self):
        """POST /dang-nhap/ with incorrect credentials returns 200 with Vietnamese error."""
        response = self.client.post("/dang-nhap/", {
            "username_or_email": "customer_test@example.com",
            "password": "WrongPassword999!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Email hoặc mật khẩu không chính xác", response.content.decode("utf-8"))

    # =========================================================================
    # B. Public Customer Registration Flow
    # =========================================================================

    def test_public_register_page_renders(self):
        """GET /dang-ky/ returns 200 with registration form and terms checkbox."""
        response = self.client.get("/dang-ky/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Đăng ký tài khoản", content)
        self.assertIn("Họ và tên", content)
        self.assertIn("Số điện thoại liên hệ", content)
        self.assertIn("Tôi đồng ý với", content)
        self.assertIn("Đăng ký bằng Google", content)

    def test_public_register_success_creates_user_and_customer_profile(self):
        """POST /dang-ky/ creates User and linked Customer without internal roles."""
        payload = {
            "name": "Trần Thị Lan",
            "email": "lan.tran@example.com",
            "phone": "0988776655",
            "address": "456 Lê Duẩn, Quận 1, TP.HCM",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "terms": "on",
        }
        response = self.client.post("/dang-ky/", payload)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dang-ky/?verification_sent=1")

        # Check User created
        user = User.objects.filter(email="lan.tran@example.com").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, "Trần Thị Lan")
        self.assertTrue(user.check_password("SecurePassword123!"))
        self.assertFalse(user.is_active)

        # Check Customer profile created
        customer = Customer.objects.filter(email="lan.tran@example.com").first()
        self.assertIsNotNone(customer)
        self.assertEqual(customer.name, "Trần Thị Lan")
        self.assertEqual(customer.phone, "0988776655")

        # Crucial Security Check: Public customer must NOT have internal memberships
        memberships_count = WorkspaceMembership.objects.filter(user=user).count()
        self.assertEqual(memberships_count, 0)

    def test_public_register_duplicate_email_rejected(self):
        """POST /dang-ky/ with existing email returns friendly error message."""
        payload = {
            "name": "Duplicate User",
            "email": "customer_test@example.com",
            "phone": "0999888777",
            "password": "AnotherPassword123!",
            "confirm_password": "AnotherPassword123!",
            "terms": "on",
        }
        response = self.client.post("/dang-ky/", payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Email này đã tồn tại", response.content.decode("utf-8"))

    def test_public_register_password_mismatch_rejected(self):
        """POST /dang-ky/ with mismatched passwords returns error."""
        payload = {
            "name": "Mismatch User",
            "email": "mismatch@example.com",
            "phone": "0999888777",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
            "terms": "on",
        }
        response = self.client.post("/dang-ky/", payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Mật khẩu xác nhận không khớp", response.content.decode("utf-8"))

    def test_public_register_without_terms_rejected(self):
        """POST /dang-ky/ without checking terms checkbox returns error."""
        payload = {
            "name": "No Terms User",
            "email": "noterms@example.com",
            "phone": "0999888777",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        response = self.client.post("/dang-ky/", payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Điều khoản sử dụng", response.content.decode("utf-8"))

    # =========================================================================
    # C. Forgot Password & Password Reset Flow
    # =========================================================================

    def test_forgot_password_request_generates_token_and_safe_message(self):
        """POST /quen-mat-khau/ sends email and displays enumeration-safe message."""
        response = self.client.post("/quen-mat-khau/", {"email": "customer_test@example.com"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Nếu địa chỉ email tồn tại trong hệ thống", response.content.decode("utf-8"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("đặt lại mật khẩu", mail.outbox[0].subject.lower())

    def test_password_reset_confirm_and_complete(self):
        """Full reset token verification and new password establishment."""
        uid = urlsafe_base64_encode(force_bytes(self.customer_user.pk))
        token = default_token_generator.make_token(self.customer_user)

        # GET confirm form
        confirm_url = f"/quen-mat-khau/xac-nhan/{uid}/{token}/"
        response = self.client.get(confirm_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Thiết lập mật khẩu mới", response.content.decode("utf-8"))

        # POST new password
        post_response = self.client.post(confirm_url, {
            "password": "BrandNewPassword123!",
            "confirm_password": "BrandNewPassword123!",
        })
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(post_response.url, "/quen-mat-khau/hoan-tat/")

        # Verify password actually updated
        self.customer_user.refresh_from_db()
        self.assertTrue(self.customer_user.check_password("BrandNewPassword123!"))

    # =========================================================================
    # D. Public Customer Account Portal & Access Control
    # =========================================================================

    def test_customer_account_unauthenticated_redirects_to_login(self):
        """GET /tai-khoan/ unauthenticated redirects to /dang-nhap/?next=/tai-khoan/."""
        response = self.client.get("/tai-khoan/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue("/dang-nhap/" in response.url)

    def test_customer_account_authenticated_renders_profile_and_tickets(self):
        """GET /tai-khoan/ authenticated renders customer's profile and submitted service tickets."""
        # Create a sample service ticket for this customer
        service_customer = Customer.objects.create(
            workspace=self.service_ws, user=self.customer_user,
            code="CUST-SERVICE-99", name=self.customer_profile.name,
            email=self.customer_user.email,
        )
        ServiceRequest.objects.create(
            workspace=self.service_ws,
            request_number="REQ-CUST-99",
            customer=service_customer,
            service=self.service,
            title="Cần hỗ trợ cài đặt hệ thống",
            description="Yêu cầu từ customer_test",
            status="OPEN",
            priority="MEDIUM",
        )

        self.client.force_login(self.customer_user)
        response = self.client.get("/tai-khoan/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("Nguyễn Văn Khách", content)
        self.assertIn("customer_test@example.com", content)
        self.assertIn("REQ-CUST-99", content)
        self.assertIn("Cần hỗ trợ cài đặt hệ thống", content)

    def test_customer_user_cannot_access_internal_management_portal(self):
        """Customer without internal staff role attempting /noibo/ is redirected to /tai-khoan/."""
        self.client.force_login(self.customer_user)
        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/tai-khoan/"))

    # =========================================================================
    # E. Google Sign-In & Public Pages Light Theme Security Checks
    # =========================================================================

    def test_google_auth_endpoint_returns_status(self):
        """GET /accounts/google/ returns 200 with clear configuration status."""
        response = self.client.get("/accounts/google/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Google", response.content.decode("utf-8"))

    def test_public_pages_do_not_leak_sensitive_internal_metrics(self):
        """Ensure public product, service, and branch pages do not leak cost price or internal labor."""
        routes = ["/", "/san-pham/", f"/san-pham/{self.product.id}/", "/dich-vu/", f"/dich-vu/{self.service.id}/", "/chi-nhanh/", "/gioi-thieu/", "/lien-he/"]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            content = response.content.decode("utf-8")
            self.assertNotIn("cost_price", content)
            self.assertNotIn("28000000", content)  # internal cost price
            self.assertNotIn("workload_score", content)
            self.assertNotIn("hourly_labor_rate", content)
