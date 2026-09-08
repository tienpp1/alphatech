"""
Automated unit and integration tests for Identity & Authentication (Session & Token).
"""

from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType


class AuthenticationAPITestCase(TestCase):
    """Test suite for login, logout, session auth, token auth, and current user profile."""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()

        # Create Workspace
        self.workspace = Workspace.objects.create(
            name="Alpha Retail",
            code="alpha-retail",
            workspace_type=WorkspaceType.RETAIL,
        )

        # Create Role & Permissions
        self.perm = Permission.objects.create(
            codename="retail.view_order",
            name="View Orders",
            module="retail",
        )
        self.role = Role.objects.create(name="MANAGER", description="Store Manager")
        self.role.permissions.add(self.perm)

        # Create Test User
        self.password = "StrongPassword123!"
        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@example.com",
            password=self.password,
            first_name="Test",
            last_name="User",
        )

        # Create Membership
        self.membership = WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace,
            role=self.role,
            is_default=True,
        )

    def test_login_success_session_and_token(self):
        """Verify successful login returns user profile, DRF token, and default active workspace."""
        response = self.client.post(
            reverse("auth_login"),
            data={"username": "testuser", "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user"]["username"], "testuser")
        self.assertIsNotNone(data["data"]["token"])
        self.assertEqual(data["data"]["active_workspace"]["id"], str(self.workspace.id))
        self.assertEqual(data["data"]["active_workspace"]["role"], "MANAGER")

        # Verify Django session contains active_workspace_id
        session = self.client.session
        self.assertEqual(session.get("active_workspace_id"), str(self.workspace.id))

    def test_login_invalid_password(self):
        """Verify login fails with HTTP 401 when given incorrect password."""
        response = self.client.post(
            reverse("auth_login"),
            data={"username": "testuser", "password": "WrongPassword!"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "AUTHENTICATION_FAILED")

    def test_login_invalid_payload(self):
        """Verify login fails with HTTP 400 when missing required fields."""
        response = self.client.post(
            reverse("auth_login"),
            data={"username": "testuser"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_me_endpoint_with_session_auth(self):
        """Verify /api/v1/auth/me/ works using standard Session Authentication."""
        self.client.login(username="testuser", password=self.password)
        response = self.client.get(reverse("auth_me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user"]["username"], "testuser")
        self.assertEqual(data["data"]["active_workspace"]["id"], str(self.workspace.id))
        self.assertIn("retail.view_order", data["data"]["permissions"])

    def test_me_endpoint_with_token_auth(self):
        """Verify /api/v1/auth/me/ works using DRF Token Authentication."""
        token, _ = Token.objects.get_or_create(user=self.user)
        self.api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.api_client.get(reverse("auth_me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["user"]["username"], "testuser")

    def test_me_endpoint_unauthenticated(self):
        """Verify unauthenticated requests to /api/v1/auth/me/ are rejected with 401."""
        response = self.api_client.get(reverse("auth_me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        session_response = self.client.get(reverse("auth_me"))
        self.assertEqual(session_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_flushes_session_and_deletes_token(self):
        """Verify logout flushes session and revokes DRF token."""
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.login(username="testuser", password=self.password)

        response = self.client.post(reverse("auth_logout"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify token is deleted
        self.assertFalse(Token.objects.filter(user=self.user).exists())

        # Verify subsequent request fails with 401 Unauthorized
        me_response = self.client.get(reverse("auth_me"))
        self.assertEqual(me_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_reused_without_churn_on_repeated_login(self):
        """Verify that multiple logins for the same user reuse the existing token rather than churning keys."""
        token_initial, _ = Token.objects.get_or_create(user=self.user)

        res1 = self.client.post(
            reverse("auth_login"),
            data={"username": "testuser", "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        token_first_login = res1.json()["data"]["token"]
        self.assertEqual(token_first_login, token_initial.key)

        res2 = self.client.post(
            reverse("auth_login"),
            data={"username": "testuser", "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        token_second_login = res2.json()["data"]["token"]
        self.assertEqual(token_second_login, token_initial.key)

    def test_invalid_token_rejected_with_401(self):
        """Verify request with a forged or invalid DRF token header is rejected with 401 Unauthorized."""
        self.api_client.credentials(HTTP_AUTHORIZATION="Token invalid_fake_token_key_12345")
        response = self.api_client.get(reverse("auth_me"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
