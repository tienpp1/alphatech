"""OAuth transport is simulated; authorization is exercised through real views."""
from unittest.mock import patch
from django.test import TestCase, RequestFactory, override_settings
from django.utils import timezone
from apps.accounts.models import User, Role
from apps.accounts.internal_access import AUTH_METHOD_KEY
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.public_web.models import SocialIdentity
from rest_framework.authtoken.models import Token
from tests.test_google_oauth_and_email_notifications import MockHTTPResponse
from config.consumers import may_view_telemetry


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    GOOGLE_CLIENT_ID="test-client", GOOGLE_CLIENT_SECRET="test-secret",
    GOOGLE_REDIRECT_URI="https://testserver/accounts/google/callback/")
class GoogleInternalBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("boundary-admin", "boundary@example.test", "TestPassword123!")
        self.ws = Workspace.objects.create(name="Boundary", code="boundary", workspace_type="RETAIL")

    def google_session(self):
        self.client.force_login(self.user)
        session = self.client.session
        session[AUTH_METHOD_KEY] = "google"
        session.save()

    def test_google_superuser_denied_internal_ui_api_admin_and_token_disclosure(self):
        Token.objects.create(user=self.user)
        self.google_session()
        for path in ("/noibo/", "/retail/products/", "/status/", "/admin/",
                     "/api/v1/auth/me/", "/api/v1/retail/products/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 403)
        response = self.client.get("/tai-khoan/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="/noibo/"')
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_superuser)

    def test_password_reauthentication_restores_admin_access(self):
        self.google_session()
        self.assertEqual(self.client.get("/accounts/login/").status_code, 200)
        response = self.client.post("/accounts/login/", {"username": self.user.username, "password": "TestPassword123!"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[AUTH_METHOD_KEY], "password")
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)
        self.assertEqual(self.client.get("/noibo/").status_code, 200)

    def test_unknown_legacy_linked_session_is_public_only(self):
        SocialIdentity.objects.create(user=self.user, provider="GOOGLE", subject="legacy", provider_email=self.user.email)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/noibo/").status_code, 403)

    def test_linked_superuser_cannot_reauthenticate_into_internal_portal(self):
        SocialIdentity.objects.create(user=self.user, provider="GOOGLE",
            subject="linked-password", provider_email=self.user.email)
        response = self.client.post("/accounts/login/", {
            "username": self.user.username, "password": "TestPassword123!"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post("/api/v1/auth/login/", {
            "username": self.user.username, "password": "TestPassword123!"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_linked_identity_denied_old_password_session_token_and_socket(self):
        token = Token.objects.create(user=self.user)
        SocialIdentity.objects.create(user=self.user, provider="GOOGLE",
            subject="linked-old-credentials", provider_email=self.user.email)
        self.assertEqual(self.client.get("/api/v1/auth/me/",
            HTTP_AUTHORIZATION=f"Token {token.key}").status_code, 403)
        self.client.force_login(self.user)
        session = self.client.session
        session[AUTH_METHOD_KEY] = "password"
        session.save()
        for path in ("/noibo/", "/admin/", "/api/v1/retail/products/"):
            self.assertEqual(self.client.get(path).status_code, 403)
        self.assertNotContains(self.client.get("/tai-khoan/"), 'href="/noibo/"')
        self.assertFalse(may_view_telemetry.func(self.user.pk, session))

    def test_public_password_login_of_linked_identity_stays_public(self):
        SocialIdentity.objects.create(user=self.user, provider="GOOGLE",
            subject="linked-public-password", provider_email=self.user.email)
        response = self.client.post("/dang-nhap/?next=/noibo/", {
            "username_or_email": self.user.username, "password": "TestPassword123!"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/tai-khoan/"))
        self.assertEqual(self.client.get("/noibo/").status_code, 403)

    def test_sessionless_linked_request_never_resolves_workspace(self):
        from apps.workspaces.middleware import WorkspaceMiddleware
        SocialIdentity.objects.create(user=self.user, provider="GOOGLE",
            subject="sessionless", provider_email=self.user.email)
        request = RequestFactory().get("/", HTTP_X_WORKSPACE_ID=str(self.ws.pk))
        request.user = self.user
        WorkspaceMiddleware(lambda req: req)(request)
        self.assertTrue(request.workspace_access_denied)
        self.assertIsNone(request.active_workspace)

    def test_viewer_and_custom_roles_cannot_use_internal_ui_even_with_read_grants(self):
        from apps.accounts.models import Permission
        self.user.is_superuser = False
        self.user.save()
        permission = Permission.objects.create(codename="retail.view_product", name="Read products", module="retail")
        for name in ("VIEWER", "CUSTOM_MANAGER"):
            with self.subTest(role=name):
                role = Role.objects.create(name=name)
                role.permissions.add(permission)
                WorkspaceMembership.objects.update_or_create(user=self.user, workspace=self.ws, defaults={"role": role})
                self.client.force_login(self.user)
                for path in ("/retail/products/", "/noibo/retail/products/", "/admin/"):
                    self.assertEqual(self.client.get(path).status_code, 403)

    def test_internal_password_login_role_matrix(self):
        self.user.is_superuser = False
        self.user.is_staff = True  # Django staff alone is insufficient.
        self.user.save()
        for name, allowed in (("ADMIN", True), ("MANAGER", True), ("EMPLOYEE", True), ("VIEWER", False)):
            with self.subTest(role=name):
                role, _ = Role.objects.get_or_create(name=name)
                WorkspaceMembership.objects.update_or_create(user=self.user, workspace=self.ws, defaults={"role": role})
                self.client.logout()
                response = self.client.post("/api/v1/auth/login/", {"username": self.user.username, "password": "TestPassword123!"})
                self.assertEqual(response.status_code, 200 if allowed else 403)

    @patch("apps.public_web.views._google_urlopen")
    def test_callback_overwrites_password_session_and_rejects_legacy_next(self, transport):
        self.client.force_login(self.user)
        session = self.client.session
        session[AUTH_METHOD_KEY] = "password"
        session["google_oauth_state"] = "boundary-state"
        session["google_oauth_state_issued_at"] = timezone.now().timestamp()
        session["google_oauth_next"] = "/admin/"
        session.save()
        transport.side_effect = [MockHTTPResponse({"access_token": "test-token"}),
            MockHTTPResponse({"sub": "boundary-google", "email": self.user.email, "email_verified": True})]
        response = self.client.get("/accounts/google/callback/?code=test-code&state=boundary-state")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[AUTH_METHOD_KEY], "google")
        self.assertTrue(response.url.startswith("/tai-khoan/"))
        self.assertEqual(self.client.get("/noibo/").status_code, 403)

    def test_google_websocket_authorization_denied(self):
        # Exercise the real synchronous DB policy. The Channels adapter closes
        # old connections and must not run inside TestCase's atomic transaction.
        self.assertFalse(may_view_telemetry.func(self.user.pk, {AUTH_METHOD_KEY: "google"}))

    def test_revoked_role_token_denied(self):
        token = Token.objects.create(user=self.user)
        self.user.is_superuser = False
        self.user.save()
        self.assertEqual(self.client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Token {token.key}").status_code, 403)

    def test_existing_socket_reloads_changed_session_method(self):
        self.client.force_login(self.user)
        session = self.client.session
        session[AUTH_METHOD_KEY] = "password"
        session.save()
        self.assertTrue(may_view_telemetry.func(self.user.pk, session))
        changed = self.client.session
        changed[AUTH_METHOD_KEY] = "google"
        changed.save()
        self.assertFalse(may_view_telemetry.func(self.user.pk, session))
