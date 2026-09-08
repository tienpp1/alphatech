"""
Automated unit and API tests for Workspaces and Tenancy Management.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.db import IntegrityError
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.workspaces.services import get_user_workspaces, switch_workspace


class WorkspaceTestCase(TestCase):
    """Test suite for Workspace models, services, and API endpoints."""

    def setUp(self):
        self.client = Client()

        # Create Roles
        self.role_admin = Role.objects.create(name="ADMIN")
        self.role_employee = Role.objects.create(name="EMPLOYEE")

        # Create Workspaces
        self.ws_retail = Workspace.objects.create(
            name="Retail One",
            code="retail-one",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.ws_service = Workspace.objects.create(
            name="Service One",
            code="service-one",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.ws_private = Workspace.objects.create(
            name="Private Operations",
            code="private-ops",
            workspace_type=WorkspaceType.RETAIL,
        )

        # Create Users
        self.user = User.objects.create_user(
            username="ws_user",
            email="ws_user@example.com",
            password="Password123!",
        )

        # Memberships: user belongs to ws_retail and ws_service, but NOT ws_private
        self.m_retail = WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.ws_retail,
            role=self.role_admin,
            is_default=True,
        )
        self.m_service = WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.ws_service,
            role=self.role_employee,
            is_default=False,
        )

    def test_unique_membership_constraint(self):
        """Verify duplicate membership creation for same user and workspace raises IntegrityError."""
        with self.assertRaises(IntegrityError):
            WorkspaceMembership.objects.create(
                user=self.user,
                workspace=self.ws_retail,
                role=self.role_employee,
            )

    def test_get_user_workspaces_service(self):
        """Verify get_user_workspaces returns only accessible workspaces."""
        workspaces = get_user_workspaces(self.user)
        self.assertEqual(workspaces.count(), 2)
        self.assertIn(self.ws_retail, workspaces)
        self.assertIn(self.ws_service, workspaces)
        self.assertNotIn(self.ws_private, workspaces)

    def test_workspace_list_api(self):
        """Verify GET /api/v1/workspaces/ returns user's accessible workspaces."""
        self.client.login(username="ws_user", password="Password123!")

        response = self.client.get(reverse("workspace_list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["count"], 2)

        workspace_ids = [w["id"] for w in data["data"]]
        self.assertIn(str(self.ws_retail.id), workspace_ids)
        self.assertIn(str(self.ws_service.id), workspace_ids)
        self.assertNotIn(str(self.ws_private.id), workspace_ids)

    def test_workspace_switch_api_success(self):
        """Verify POST /api/v1/workspaces/switch/ changes active workspace."""
        self.client.login(username="ws_user", password="Password123!")

        response = self.client.post(
            reverse("workspace_switch"),
            data={"workspace_id": str(self.ws_service.id)},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["active_workspace"]["id"], str(self.ws_service.id))
        self.assertEqual(data["data"]["active_workspace"]["role"], "EMPLOYEE")

        # Verify session is updated
        self.assertEqual(self.client.session.get("active_workspace_id"), str(self.ws_service.id))

    def test_workspace_switch_unauthorized_rejected(self):
        """Verify switching to an unassigned workspace is rejected with 403."""
        self.client.login(username="ws_user", password="Password123!")

        response = self.client.post(
            reverse("workspace_switch"),
            data={"workspace_id": str(self.ws_private.id)},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "PERMISSION_DENIED")

    def test_current_workspace_api(self):
        """Verify GET /api/v1/workspaces/current/ returns currently active workspace."""
        self.client.login(username="ws_user", password="Password123!")

        response = self.client.get(reverse("workspace_current"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        # Default workspace is ws_retail
        self.assertEqual(data["data"]["workspace"]["id"], str(self.ws_retail.id))
        self.assertEqual(data["data"]["role"], "ADMIN")
