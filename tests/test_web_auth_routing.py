"""
Tests for Web UI Authentication Flow and Protected Route Redirection.
Verifies login page accessibility, unauthenticated redirects, authenticated session returns,
logout invalidation, and next-url preservation.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.accounts.models import Permission, Role

User = get_user_model()


class WebAuthRoutingTestCase(TestCase):
    """Test suite for Web UI authentication and route protection."""

    def setUp(self):
        self.client = Client()
        self.username = "test_manager"
        self.password = "ManagerPass123!"
        self.user = User.objects.create_user(
            username=self.username,
            email="manager@example.com",
            password=self.password,
            is_active=True,
        )

        self.workspace = Workspace.objects.create(
            name="Retail Test Workspace",
            code="ws-retail-test",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.role = Role.objects.create(
            name="Manager",
            description="Operations Manager",
        )
        self.gis_permission, _ = Permission.objects.get_or_create(
            codename="gis.view_spatial_layers",
            defaults={"name": "View spatial layers", "module": "gis"},
        )
        self.service_analytics_permission, _ = Permission.objects.get_or_create(
            codename="service.view_analytics",
            defaults={"name": "View service analytics", "module": "service_ops"},
        )
        self.retail_analytics_permission, _ = Permission.objects.get_or_create(
            codename="retail.view_analytics",
            defaults={"name": "View retail analytics", "module": "retail"},
        )
        self.internal_read_permissions = []
        for codename, name, module in [
            ("integration.view_datasource", "View data sources", "integration"),
            ("mapping.view_mapping", "View mappings", "mapping"),
            ("knowledge.view_knowledge", "View knowledge", "knowledge"),
            ("ai.chat", "Use AI assistant", "ai"),
            ("forecasting.view_forecast", "View forecasts", "forecasting"),
            ("recommendations.view_recommendation", "View recommendations", "recommendations"),
            ("approvals.view_approval", "View approvals", "approvals"),
        ]:
            permission, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={"name": name, "module": module},
            )
            self.internal_read_permissions.append(permission)
        self.role.permissions.set([
            self.gis_permission,
            self.service_analytics_permission,
            self.retail_analytics_permission,
            *self.internal_read_permissions,
        ])

        self.membership = WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace,
            role=self.role,
            is_default=True,
            is_active=True,
        )

    def test_login_page_renders_successfully(self):
        """GET /accounts/login/ returns 200 OK and renders the sign-in template in Vietnamese."""
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "\u0110\u0103ng nh\u1eadp")
        self.assertContains(response, "username")
        self.assertContains(response, "password")
        self.assertContains(response, "btn-login-submit")

    def test_unauthenticated_protected_page_redirects_to_login(self):
        """Unauthenticated GET /retail/gis/ redirects to /accounts/login/?next=/retail/gis/."""
        response = self.client.get("/retail/gis/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        self.assertIn("next=/retail/gis/", response.url)

    def test_login_success_and_next_redirect(self):
        """Valid credentials log the user in and redirect to the requested ?next= page."""
        response = self.client.post(
            "/accounts/login/",
            {
                "username": self.username,
                "password": self.password,
                "next": "/retail/gis/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/retail/gis/")

        # Follow redirect and verify page loads for the authenticated session
        follow_response = self.client.get("/retail/gis/")
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, "retail-map")
        self.assertContains(follow_response, "B\u00e1n l\u1ebb (GIS)")

    def test_login_failure_shows_error_message(self):
        """Invalid credentials re-render login page with localized error message."""
        response = self.client.post(
            "/accounts/login/",
            {
                "username": self.username,
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "kh\u00f4ng ch\u00ednh x\u00e1c")

    def test_authenticated_user_visiting_login_redirects(self):
        """Already authenticated user accessing /accounts/login/ is redirected away to /noibo/."""
        self.client.login(username=self.username, password=self.password)
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/noibo/")

    def test_logout_flushes_session_and_protects_routes(self):
        """GET /accounts/logout/ logs out user, revokes token, and redirects to public website root (/)."""
        self.client.login(username=self.username, password=self.password)
        Token.objects.create(user=self.user)

        # Logout
        logout_response = self.client.get("/accounts/logout/")
        self.assertEqual(logout_response.status_code, 302)
        self.assertEqual(logout_response.url, "/")

        # Token is deleted
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        # Protected page requires login again
        reopen_response = self.client.get("/retail/gis/")
        self.assertEqual(reopen_response.status_code, 302)
        self.assertIn("/accounts/login/?next=/retail/gis/", reopen_response.url)

    def test_logout_post_flushes_session_and_redirects(self):
        """POST /accounts/logout/ terminates session, revokes DRF token, and redirects to public website root (/)."""
        self.client.login(username=self.username, password=self.password)
        Token.objects.create(user=self.user)

        post_logout = self.client.post("/accounts/logout/")
        self.assertEqual(post_logout.status_code, 302)
        self.assertEqual(post_logout.url, "/")


        # Token is revoked
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        # Cannot access protected route without re-authenticating
        reopen_response = self.client.get("/retail/")
        self.assertEqual(reopen_response.status_code, 302)
        self.assertIn("/accounts/login/?next=/retail/", reopen_response.url)

    def test_role_independent_visible_logout_and_vietnamese_badges(self):
        """Verify visible 'Đăng xuất' button and Vietnamese role badges for all 4 roles."""
        role_configs = [
            ("ADMIN", "Qu\u1ea3n tr\u1ecb vi\u00ean"),
            ("MANAGER", "Qu\u1ea3n l\u00fd"),
            ("EMPLOYEE", "Nh\u00e2n vi\u00ean"),
            ("VIEWER", "Ng\u01b0\u1eddi xem"),
        ]

        for role_name, expected_badge in role_configs:
            user = User.objects.create_user(
                username=f"user_{role_name.lower()}",
                email=f"user_{role_name.lower()}@testcorp.vn",
                password="TestPassword123!",
                is_active=True,
            )
            role_obj, _ = Role.objects.get_or_create(name=role_name)
            role_obj.permissions.add(self.gis_permission)
            WorkspaceMembership.objects.create(
                user=user,
                workspace=self.workspace,
                role=role_obj,
                is_default=True,
                is_active=True,
            )

            client = Client()
            client.login(username=f"user_{role_name.lower()}", password="TestPassword123!")

            # Set active workspace in session
            session = client.session
            session["active_workspace_id"] = str(self.workspace.id)
            session.save()

            response = client.get("/retail/gis/")
            self.assertEqual(
                response.status_code,
                200,
                f"Role {role_name} failed to load protected page /retail/gis/",
            )

            # Assert logout button is clearly visible and localized
            self.assertContains(
                response,
                "btn-logout",
                msg_prefix=f"Role {role_name} missing .btn-logout in navigation header",
            )
            self.assertContains(
                response,
                "\u0110\u0103ng xu\u1ea5t",
                msg_prefix=f"Role {role_name} missing '\u0110\u0103ng xu\u1ea5t' text in navigation header",
            )

            # Assert Vietnamese role badge
            self.assertContains(
                response,
                expected_badge,
                msg_prefix=f"Role {role_name} missing Vietnamese role badge '{expected_badge}'",
            )

    def test_vietnamese_navigation_labels_in_header(self):
        """Verify top-level domain navigation tabs are rendered with Vietnamese labels."""
        self.client.login(username=self.username, password=self.password)
        session = self.client.session
        session["active_workspace_id"] = str(self.workspace.id)
        session.save()

        response = self.client.get("/retail/")
        self.assertEqual(response.status_code, 200)

        vietnamese_nav_labels = [
            "B\u00e1n l\u1ebb",
            "T\u00edch h\u1ee3p",
            "\u00c1nh x\u1ea1",
            "Kho tri th\u1ee9c",
            "Tr\u1ee3 l\u00fd AI",
            "D\u1ef1 b\u00e1o",
            "Khuy\u1ebfn ngh\u1ecb",
            "Ph\u00ea duy\u1ec7t",
        ]
        for label in vietnamese_nav_labels:
            self.assertContains(
                response,
                label,
                msg_prefix=f"Navigation header missing Vietnamese label '{label}'",
            )

    def test_anonymous_get_noibo_redirects_to_login(self):
        """1. Anonymous GET /noibo/ redirects to valid login page with next=/noibo/ parameter."""
        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        self.assertIn("next=/noibo/", response.url)

    def test_login_page_http_200(self):
        """2. Login page GET /accounts/login/ returns HTTP 200."""
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "\u0110\u0103ng nh\u1eadp")
        self.assertContains(response, "username")
        self.assertContains(response, "password")

    def test_login_page_standalone_has_no_authenticated_navigation(self):
        """Verify Login page is a standalone screen with zero global navigation or authenticated UI."""
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)

        # Must contain clean standalone login elements
        self.assertContains(response, "N\u1ec1n t\u1ea3ng Doanh nghi\u1ec7p AI")
        self.assertContains(response, "\u0110\u0103ng nh\u1eadp h\u1ec7 th\u1ed1ng")
        self.assertContains(response, "Truy c\u1eadp kh\u00f4ng gian l\u00e0m vi\u1ec7c doanh nghi\u1ec7p")
        self.assertContains(response, "btn-login-submit")

        # Must NOT contain authenticated global navigation, menus, or badges
        forbidden_snippets = [
            "app-header",
            "header-nav",
            "app-footer",
            "btn-logout",
            "\u0110\u0103ng xu\u1ea5t",
            "btn-ws-toggle",
            "ws-dropdown-list",
            "\u0110\u1ed5i kh\u00f4ng gian",
            "Phase 0\u201312",
            "B\u00e1n l\u1ebb (GIS)",
            "D\u1ef1 b\u00e1o",
            "Khuy\u1ebfn ngh\u1ecb",
            "Ph\u00ea duy\u1ec7t",
            "T\u00edch h\u1ee3p",
            "\u00c1nh x\u1ea1",
            "Kho tri th\u1ee9c",
            "Tr\u1ee3 l\u00fd AI",
            "Qu\u1ea3n tr\u1ecb \u2197",
        ]
        for snippet in forbidden_snippets:
            self.assertNotContains(
                response,
                snippet,
                msg_prefix=f"Login page must not contain '{snippet}'",
            )

    def test_successful_login_loads_authenticated_dashboard(self):
        """3. Successful login redirects to and loads authenticated main dashboard at /noibo/."""
        response = self.client.post(
            "/accounts/login/",
            {
                "username": self.username,
                "password": self.password,
                "next": "/noibo/",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/noibo/")

        # Follow redirect and verify authenticated dashboard loads
        dashboard_response = self.client.get("/noibo/")
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, "Trung t\u00e2m Qu\u1ea3n tr\u1ecb & \u0110i\u1ec1u h\u00e0nh N\u1ed9i b\u1ed9 T\u1eadp trung")
        self.assertContains(dashboard_response, "ABC Tech Store")
        self.assertContains(dashboard_response, "XYZ IT Technical Services")

    def test_authenticated_get_noibo_http_200(self):
        """4. Authenticated GET /noibo/ returns HTTP 200 and renders main dashboard."""
        self.client.login(username=self.username, password=self.password)
        session = self.client.session
        session["active_workspace_id"] = str(self.workspace.id)
        session.save()

        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trung t\u00e2m Qu\u1ea3n tr\u1ecb & \u0110i\u1ec1u h\u00e0nh N\u1ed9i b\u1ed9 T\u1eadp trung")
        self.assertNotContains(response, "Phase 1 Gate")
        self.assertNotContains(response, "Ready for Phase 2")
        self.assertNotContains(response, "Phase 4 \u2014 Service Operations")

    def test_logout_session_terminated(self):
        """5. Logout terminates session, revokes tokens, and redirects to public website root /."""
        self.client.login(username=self.username, password=self.password)
        Token.objects.create(user=self.user)

        response = self.client.get("/accounts/logout/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        self.assertFalse(Token.objects.filter(user=self.user).exists())
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_anonymous_get_noibo_after_logout_requires_login(self):
        """6. Anonymous GET /noibo/ after logout requires login again."""
        self.client.login(username=self.username, password=self.password)
        self.client.get("/accounts/logout/")

        response = self.client.get("/noibo/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
        self.assertIn("next=/noibo/", response.url)

    def test_protected_routes_without_auth_redirect_to_login(self):
        """7. Protected routes without authentication redirect to login."""
        protected_routes = [
            "/noibo/",
            "/retail/",
            "/retail/products/",
            "/retail/gis/",
            "/services/",
            "/services/gis/",
            "/services/labor-cost/",
            "/integration/",
            "/mapping/",
            "/knowledge/",
            "/ai/",
            "/forecasting/",
            "/recommendations/",
            "/approvals/",
        ]
        for route in protected_routes:
            res = self.client.get(route)
            self.assertEqual(res.status_code, 302, f"{route} did not redirect")
            self.assertIn("/accounts/login/", res.url)

    def test_next_parameter_preserved_safely_and_rejects_open_redirect(self):
        """8. Next parameter preserves original destination safely and rejects open redirect."""
        # Safe internal next
        res = self.client.post(
            "/accounts/login/",
            {"username": self.username, "password": self.password, "next": "/retail/products/"},
        )
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, "/retail/products/")

        # Malicious external next -> defaults safely to /noibo/
        res_unsafe = self.client.post(
            "/accounts/login/",
            {"username": self.username, "password": self.password, "next": "https://evil.com/phishing"},
        )
        self.assertEqual(res_unsafe.status_code, 302)
        self.assertEqual(res_unsafe.url, "/noibo/")

    def test_routing_audit_protected_vs_public_pages(self):
        """Verify unauthenticated access across all major web routes."""
        protected_routes = [
            "/noibo/",
            "/retail/",
            "/retail/gis/",
            "/services/",
            "/services/gis/",
            "/services/labor-cost/",
            "/integration/",
            "/mapping/",
            "/knowledge/",
            "/ai/",
            "/forecasting/",
            "/recommendations/",
            "/approvals/",
        ]

        # 1. Unauthenticated: all protected routes redirect to /accounts/login/
        for route in protected_routes:
            res = self.client.get(route)
            self.assertEqual(
                res.status_code,
                302,
                f"Route {route} did not redirect when unauthenticated",
            )
            self.assertIn(
                "/accounts/login/",
                res.url,
                f"Route {route} did not redirect to /accounts/login/",
            )

        # 2. Public routes return 200 OK without login
        public_routes = [
            "/",
            "/san-pham/",
            "/dich-vu/",
            "/chi-nhanh/",
            "/gioi-thieu/",
            "/lien-he/",
            "/status/",
            "/health/",
            "/api/health/",
        ]
        for p_route in public_routes:
            self.assertEqual(
                self.client.get(p_route).status_code,
                200,
                f"Public route {p_route} failed to return 200 OK",
            )

        # 3. Authenticated: protected routes load successfully
        self.client.login(username=self.username, password=self.password)
        session = self.client.session
        session["active_workspace_id"] = str(self.workspace.id)
        session.save()

        service_only_routes = {"/services/", "/services/gis/", "/services/labor-cost/"}
        for route in protected_routes:
            res = self.client.get(route)
            if route in service_only_routes:
                self.assertEqual(
                    res.status_code,
                    403,
                    f"Retail-only member unexpectedly accessed Service route {route}",
                )
                continue
            self.assertEqual(
                res.status_code,
                200,
                f"Route {route} failed to load for authenticated user (status: {res.status_code})",
            )
