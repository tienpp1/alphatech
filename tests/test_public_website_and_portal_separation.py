"""
Comprehensive Automated Test Suite for Public Website & Internal Management Portal Separation.
Verifies:
- Public routes accessibility without authentication (/, /san-pham/, /dich-vu/, /chi-nhanh/, /gioi-thieu/, /lien-he/, /yeu-cau-dich-vu/).
- Technology product catalog, search, category filter, price sorting, and detail views.
- 4 IT Technical service categories, service detail, and safe inquiry submission.
- Public data security (no leaked cost prices, labor rates, customer data, revenue, or workload scores).
- Internal portal (/noibo/) protection with login redirection.
- Login and logout routing.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from apps.retail.models import Product, Category, Branch
from apps.service_ops.models import Service, ServiceCategory, ServiceRequest
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.accounts.models import Role

User = get_user_model()


class PublicWebsiteAndPortalSeparationTestCase(TestCase):
    """Test suite for public-facing business website and internal admin portal separation."""

    def setUp(self):
        self.client = Client()

        # 1. Create Retail & Service Workspaces
        self.retail_ws = Workspace.objects.create(
            name="ABC Tech Store Workspace",
            code="ws-retail-abc",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.service_ws = Workspace.objects.create(
            name="XYZ IT Services Workspace",
            code="ws-service-xyz",
            workspace_type=WorkspaceType.SERVICE,
        )

        # 2. Create Categories & Products for ABC Tech Store
        self.cat_laptop = Category.objects.create(
            workspace=self.retail_ws,
            name="Laptop",
            code="laptop",
            description="Máy tính xách tay chính hãng",
            is_active=True,
        )

        self.cat_mouse = Category.objects.create(
            workspace=self.retail_ws,
            name="Chuột",
            code="mouse",
            description="Chuột máy tính không dây và gaming",
            is_active=True,
        )

        self.prod_laptop = Product.objects.create(
            workspace=self.retail_ws,
            category=self.cat_laptop,
            sku="LAP-DELL-01",
            name="Laptop Dell Latitude 7420",
            description="Laptop doanh nghiệp Intel Core i7 16GB 512GB SSD",
            unit="chiếc",
            unit_price=Decimal("22500000.00"),
            cost_price=Decimal("18000000.00"),  # Sensitive internal data
            is_active=True,
        )

        self.prod_mouse = Product.objects.create(
            workspace=self.retail_ws,
            category=self.cat_mouse,
            sku="MOU-LOGI-MX3",
            name="Chuột Logitech MX Master 3S",
            description="Chuột công thái học cao cấp",
            unit="cái",
            unit_price=Decimal("2450000.00"),
            cost_price=Decimal("1700000.00"),  # Sensitive internal data
            is_active=True,
        )

        self.prod_inactive = Product.objects.create(
            workspace=self.retail_ws,
            category=self.cat_mouse,
            sku="MOU-OLD-01",
            name="Chuột Cũ Ngừng Kinh Doanh",
            description="Hết hàng",
            unit="cái",
            unit_price=Decimal("100000.00"),
            cost_price=Decimal("50000.00"),
            is_active=False,
        )

        # 3. Create Branches
        self.branch = Branch.objects.create(
            workspace=self.retail_ws,
            code="BR-Q1",
            name="Chi nhánh Quận 1 - Flagship Store",
            address="123 Nguyễn Thị Minh Khai, Phường Bến Thành, Quận 1, TP.HCM",
            phone="028 3822 6868",
            latitude=Decimal("10.772500"),
            longitude=Decimal("106.698000"),
            is_active=True,
        )

        # 4. Create Services for XYZ IT Services
        self.srv_install = Service.objects.create(
            workspace=self.service_ws,
            code="INST-OS-01",
            name="Cài đặt hệ điều hành và phần mềm bảo mật",
            category=ServiceCategory.INSTALLATION,
            description="Cài đặt Windows 11 Enterprise, cấu hình bảo mật và sao lưu",
            standard_duration_minutes=90,
            base_fee=Decimal("350000.00"),
            is_active=True,
        )

        self.srv_maint = Service.objects.create(
            workspace=self.service_ws,
            code="MAIN-SRV-01",
            name="Bảo trì định kỳ hệ thống máy chủ",
            category=ServiceCategory.MAINTENANCE,
            description="Vệ sinh phần cứng máy chủ, kiểm tra nhật ký lỗi RAID",
            standard_duration_minutes=180,
            base_fee=Decimal("1200000.00"),
            is_active=True,
        )

        self.srv_db = Service.objects.create(
            workspace=self.service_ws,
            code="DB-OPT-01",
            name="Tư vấn tối ưu hóa cơ sở dữ liệu PostgreSQL",
            category=ServiceCategory.DATABASE_CONSULTING,
            description="Phân tích câu truy vấn chậm, đánh chỉ mục và tinh chỉnh tham số",
            standard_duration_minutes=240,
            base_fee=Decimal("3000000.00"),
            is_active=True,
        )

        self.srv_repair = Service.objects.create(
            workspace=self.service_ws,
            code="REP-LAP-01",
            name="Sửa chữa phần cứng và thay thế linh kiện Laptop",
            category=ServiceCategory.DEVICE_REPAIR,
            description="Chẩn đoán lỗi bo mạch, thay màn hình và bàn phím",
            standard_duration_minutes=120,
            base_fee=Decimal("500000.00"),
            is_active=True,
        )

        # 5. Internal Admin / Manager User
        self.manager_user = User.objects.create_user(
            username="portal_manager",
            email="manager@abctech.vn",
            password="ManagerPass123!",
            is_active=True,
        )
        self.role_manager = Role.objects.create(name="Manager", description="Operations Manager")
        self.membership = WorkspaceMembership.objects.create(
            user=self.manager_user,
            workspace=self.retail_ws,
            role=self.role_manager,
            is_default=True,
            is_active=True,
        )

    # =========================================================================
    # SECTION 1: PUBLIC HOMEPAGE TESTS (GET /)
    # =========================================================================

    def test_public_homepage_renders_unauthenticated(self):
        """GET / returns 200 OK without authentication and displays ABC Tech Store & XYZ IT Services."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Verify page branding
        self.assertContains(response, "Nền tảng Doanh nghiệp AI")
        self.assertContains(response, "ABC Tech Store")
        self.assertContains(response, "XYZ IT Technical Services")

        # Verify Hero headline and CTAs
        self.assertContains(response, "Thiết bị công nghệ và dịch vụ kỹ thuật cho doanh nghiệp")
        self.assertContains(response, "Xem sản phẩm")
        self.assertContains(response, "Khám phá dịch vụ")

        # Verify public login CTA button exists pointing to /dang-nhap/
        self.assertContains(response, "/dang-nhap/")
        self.assertContains(response, "Đăng nhập")

        # Verify internal workspace switcher and roles are NOT exposed on public homepage
        self.assertNotContains(response, "btn-ws-toggle")
        self.assertNotContains(response, "Đổi không gian")
        self.assertNotContains(response, "Quản trị viên")

    # =========================================================================
    # SECTION 2: PUBLIC RETAIL CATALOG & DETAIL (GET /san-pham/ & /san-pham/<id>/)
    # =========================================================================

    def test_public_products_catalog_listing(self):
        """GET /san-pham/ lists active products and categories without requiring auth."""
        response = self.client.get("/san-pham/")
        self.assertEqual(response.status_code, 200)

        # Active products are shown
        self.assertContains(response, "Laptop Dell Latitude 7420")
        self.assertContains(response, "Chuột Logitech MX Master 3S")
        self.assertContains(response, "22500000")

        # Inactive products are strictly excluded
        self.assertNotContains(response, "Chuột Cũ Ngừng Kinh Doanh")

    def test_public_products_filter_by_category(self):
        """GET /san-pham/?category=laptop filters products by category code."""
        response = self.client.get("/san-pham/?category=laptop")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Laptop Dell Latitude 7420")
        self.assertNotContains(response, "Chuột Logitech MX Master 3S")

    def test_public_products_search_query(self):
        """GET /san-pham/?q=Logitech searches products by keyword."""
        response = self.client.get("/san-pham/?q=Logitech")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chuột Logitech MX Master 3S")
        self.assertNotContains(response, "Laptop Dell Latitude 7420")

    def test_public_products_price_sorting(self):
        """GET /san-pham/?sort=price_asc sorts products from lowest to highest price."""
        response = self.client.get("/san-pham/?sort=price_asc")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Mouse (2.45M) should appear before Laptop (22.5M)
        idx_mouse = content.find("Chuột Logitech MX Master 3S")
        idx_laptop = content.find("Laptop Dell Latitude 7420")
        self.assertTrue(idx_mouse < idx_laptop)

    def test_public_product_detail_view(self):
        """GET /san-pham/<id>/ shows product details, specifications, and contact CTA."""
        response = self.client.get(f"/san-pham/{self.prod_laptop.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Laptop Dell Latitude 7420")
        self.assertContains(response, "LAP-DELL-01")
        self.assertContains(response, "22500000")
        self.assertContains(response, "Mua ngay")
        self.assertContains(response, "Còn hàng")

    def test_public_product_detail_inactive_returns_404(self):
        """GET /san-pham/<id>/ on an inactive product returns 404."""
        response = self.client.get(f"/san-pham/{self.prod_inactive.id}/")
        self.assertEqual(response.status_code, 404)

    # =========================================================================
    # SECTION 3: PUBLIC SERVICE CATALOG & DETAIL (GET /dich-vu/ & /dich-vu/<id>/)
    # =========================================================================

    def test_public_services_catalog_all_4_categories(self):
        """GET /dich-vu/ renders all 4 approved IT service categories with services."""
        response = self.client.get("/dich-vu/")
        self.assertEqual(response.status_code, 200)

        # Verify the 4 approved categories are displayed
        self.assertContains(response, "Cài đặt hệ thống")
        self.assertContains(response, "Bảo trì hệ thống")
        self.assertContains(response, "Tư vấn quản trị CSDL")
        self.assertContains(response, "Sửa chữa thiết bị")

        # Verify service items
        self.assertContains(response, "Cài đặt hệ điều hành và phần mềm bảo mật")
        self.assertContains(response, "Tư vấn tối ưu hóa cơ sở dữ liệu PostgreSQL")
        self.assertContains(response, "3000000")

    def test_public_services_filter_by_category(self):
        """GET /dich-vu/?category=DATABASE_CONSULTING filters services."""
        response = self.client.get("/dich-vu/?category=DATABASE_CONSULTING")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tư vấn tối ưu hóa cơ sở dữ liệu PostgreSQL")
        self.assertNotContains(response, "Sửa chữa phần cứng và thay thế linh kiện Laptop")

    def test_public_service_detail_view(self):
        """GET /dich-vu/<id>/ shows service scope, standard turnaround duration, and base fee."""
        response = self.client.get(f"/dich-vu/{self.srv_db.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tư vấn tối ưu hóa cơ sở dữ liệu PostgreSQL")
        self.assertContains(response, "3000000")
        self.assertContains(response, "240")
        self.assertContains(response, "Yêu cầu dịch vụ này ngay")

    # =========================================================================
    # SECTION 4: PUBLIC SERVICE REQUEST FORM (GET & POST /yeu-cau-dich-vu/)
    # =========================================================================

    def test_public_service_request_get(self):
        """GET /yeu-cau-dich-vu/ returns request submission form."""
        response = self.client.get("/yeu-cau-dich-vu/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "yêu cầu hỗ trợ kỹ thuật")
        self.assertContains(response, "customer_name")
        self.assertContains(response, "phone")
        self.assertContains(response, "description")

    def test_public_service_request_post_creates_safe_inquiry(self):
        """POST /yeu-cau-dich-vu/ creates a ServiceRequest safely without auto-dispatch."""
        initial_count = ServiceRequest.objects.count()

        post_data = {
            "customer_name": "Công ty Cổ phần Công nghệ X",
            "phone": "0987654321",
            "email": "contact@congnghex.vn",
            "service_id": str(self.srv_install.id),
            "address": "Tầng 5, Tòa nhà Landmark, Bình Thạnh, TP.HCM",
            "preferred_time": "Thứ 3 tuần sau lúc 09:00",
            "description": "Cần cài đặt hệ điều hành và thiết lập phân quyền bảo mật cho 10 máy trạm mới.",
        }

        response = self.client.post("/yeu-cau-dich-vu/", post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tiếp nhận thành công")

        # Verify a ServiceRequest record was safely created in the database
        self.assertEqual(ServiceRequest.objects.count(), initial_count + 1)
        created_req = ServiceRequest.objects.latest("created_at")
        self.assertEqual(created_req.status, "OPEN")
        self.assertEqual(created_req.priority, "MEDIUM")
        self.assertEqual(created_req.service, self.srv_install)
        self.assertEqual(created_req.customer.workspace, created_req.workspace)
        self.assertIn("Công ty Cổ phần Công nghệ X", created_req.description)
        self.assertIn("0987654321", created_req.description)

        # Verify safe ticket creation: NO auto-assigned technician, NO modified schedule
        self.assertFalse(hasattr(created_req, "technician") and created_req.technician is not None)

    # =========================================================================
    # SECTION 5: PUBLIC BRANCHES, ABOUT & CONTACT (GET /chi-nhanh/, /gioi-thieu/, /lien-he/)
    # =========================================================================

    def test_public_branches_view(self):
        """GET /chi-nhanh/ displays physical branches with GIS coordinates and address."""
        response = self.client.get("/chi-nhanh/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Chi nhánh Quận 1 - Flagship Store")
        self.assertContains(response, "123 Nguyễn Thị Minh Khai")
        self.assertContains(response, "028 3822 6868")
        self.assertContains(response, "10.7725")
        self.assertContains(response, "106.6980")

    def test_public_about_view(self):
        """GET /gioi-thieu/ returns 200 OK with business domain intros."""
        response = self.client.get("/gioi-thieu/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ABC Tech Store")
        self.assertContains(response, "XYZ IT Technical Services")

    def test_public_contact_view(self):
        """GET & POST /lien-he/ returns contact info and handles message submission."""
        get_response = self.client.get("/lien-he/")
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "1900 6868")

        post_response = self.client.post(
            "/lien-he/",
            {
                "name": "Nguyễn Văn Test",
                "contact": "test@example.com",
                "topic": "retail",
                "message": "Tôi muốn hỏi chính sách mua số lượng lớn laptop.",
            },
        )
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "thành công")

    # =========================================================================
    # SECTION 6: PUBLIC DATA SECURITY AUDIT (ZERO SENSITIVE DATA LEAKS)
    # =========================================================================

    def test_public_pages_do_not_leak_sensitive_internal_metrics(self):
        """Ensure cost price, profit margins, internal employee rates, and admin data never leak to public pages."""
        public_urls = [
            "/",
            "/san-pham/",
            f"/san-pham/{self.prod_laptop.id}/",
            "/dich-vu/",
            f"/dich-vu/{self.srv_install.id}/",
            "/chi-nhanh/",
            "/gioi-thieu/",
            "/lien-he/",
        ]

        sensitive_strings = [
            "cost_price",
            "18000000",  # Cost price of laptop
            "1700000",   # Cost price of mouse
            "hourly_labor_rate",
            "current_workload_score",
            "supplier",
            "total_revenue",
            "internal_margin",
        ]

        for url in public_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"URL {url} failed with {res.status_code}")
            content = res.content.decode("utf-8")
            for secret in sensitive_strings:
                self.assertNotIn(
                    secret,
                    content,
                    f"Security leak detected: '{secret}' found on public URL '{url}'",
                )

    # =========================================================================
    # SECTION 7: INTERNAL PORTAL ROUTING & AUTH FLOW (/noibo/)
    # =========================================================================

    def test_unauthenticated_noibo_redirects_to_login(self):
        """Unauthenticated GET /noibo/ redirects to /accounts/login/?next=/noibo/."""
        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        self.assertIn("next=/noibo/", response.url)

    def test_authenticated_noibo_loads_dashboard(self):
        """Authenticated user accessing /noibo/ loads the internal management dashboard."""
        self.client.login(username="portal_manager", password="ManagerPass123!")
        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nền tảng Doanh nghiệp AI")
        self.assertContains(response, "Bảng điều khiển")

    def test_login_redirects_to_noibo_by_default(self):
        """Valid credentials without next parameter redirect to /noibo/."""
        response = self.client.post(
            "/accounts/login/",
            {
                "username": "portal_manager",
                "password": "ManagerPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/noibo/")

    def test_logout_redirects_to_public_website_root(self):
        """GET /accounts/logout/ terminates internal session and returns to public website root /."""
        self.client.login(username="portal_manager", password="ManagerPass123!")
        Token.objects.create(user=self.manager_user)

        response = self.client.get("/accounts/logout/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

        # Unauthenticated /noibo/ after logout must require login
        after_logout_res = self.client.get("/noibo/")
        self.assertEqual(after_logout_res.status_code, 302)
        self.assertIn("/accounts/login/?next=/noibo/", after_logout_res.url)
