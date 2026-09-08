"""
Automated Security & Tenancy Isolation Tests.
Verifies that client-supplied X-Workspace-ID headers and session states cannot bypass tenancy boundaries.
"""

from django.test import TestCase, Client, RequestFactory
from django.db import models
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.test import APIClient

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import (
    Workspace,
    WorkspaceMembership,
    WorkspaceType,
    WorkspaceScopedModel,
)
from apps.workspaces.middleware import WorkspaceMiddleware
from apps.workspaces.permissions import IsWorkspaceMember, IsWorkspaceAdmin
from apps.workspaces.services import validate_workspace_access, resolve_active_workspace


class DummyTenantEntity(WorkspaceScopedModel):
    """Temporary concrete model for testing WorkspaceScopedModel and manager filtering."""

    name = models.CharField(max_length=50)

    class Meta:
        app_label = "workspaces"


class SecureTenantProtectedAPIView(APIView):
    """Test API view protected by IsWorkspaceMember."""

    permission_classes = [IsWorkspaceMember]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "success": True,
                "workspace_id": str(request.active_workspace.id),
                "message": "Access granted to tenant data.",
            }
        )


class WorkspaceIsolationSecurityTestCase(TestCase):
    """Test suite ensuring absolute tenancy isolation and anti-tampering defenses."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from django.db import connection
        with connection.schema_editor() as editor:
            editor.create_model(DummyTenantEntity)

    @classmethod
    def tearDownClass(cls):
        from django.db import connection
        with connection.schema_editor() as editor:
            editor.delete_model(DummyTenantEntity)
        super().tearDownClass()

    def setUp(self):
        self.factory = RequestFactory()
        self.api_client = APIClient()

        # Create Workspaces
        self.ws_a = Workspace.objects.create(
            name="Tenant Alpha",
            code="tenant-alpha",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.ws_b = Workspace.objects.create(
            name="Tenant Beta",
            code="tenant-beta",
            workspace_type=WorkspaceType.SERVICE,
        )

        # Create Roles
        self.role_admin = Role.objects.create(name="ADMIN")
        self.role_employee = Role.objects.create(name="EMPLOYEE")

        # Create Users
        self.user_a = User.objects.create_user(
            username="user_alpha",
            email="user_alpha@example.com",
            password="Password123!",
        )
        self.user_b = User.objects.create_user(
            username="user_beta",
            email="user_beta@example.com",
            password="Password123!",
        )

        # Memberships: user_a in ws_a ONLY; user_b in ws_b ONLY
        self.m_a = WorkspaceMembership.objects.create(
            user=self.user_a,
            workspace=self.ws_a,
            role=self.role_admin,
            is_default=True,
        )
        self.m_b = WorkspaceMembership.objects.create(
            user=self.user_b,
            workspace=self.ws_b,
            role=self.role_admin,
            is_default=True,
        )

    def test_x_workspace_id_forged_header_rejected_by_middleware(self):
        """Verify that a user providing a forged X-Workspace-ID for an unassigned workspace is denied access."""
        # user_a attempts to access ws_b by spoofing the header
        request = self.factory.get("/", HTTP_X_WORKSPACE_ID=str(self.ws_b.id))
        request.user = self.user_a

        middleware = WorkspaceMiddleware(lambda req: req)
        middleware(request)

        # active_workspace MUST be None and workspace_access_denied MUST be True
        self.assertIsNone(request.active_workspace)
        self.assertTrue(request.workspace_access_denied)

        # Verify DRF IsWorkspaceMember permission denies access
        permission_checker = IsWorkspaceMember()
        self.assertFalse(permission_checker.has_permission(request, None))

    def test_valid_x_workspace_id_header_accepted(self):
        """Verify that a valid X-Workspace-ID for a workspace the user belongs to is accepted."""
        request = self.factory.get("/", HTTP_X_WORKSPACE_ID=str(self.ws_a.id))
        request.user = self.user_a

        middleware = WorkspaceMiddleware(lambda req: req)
        middleware(request)

        self.assertEqual(request.active_workspace, self.ws_a)
        self.assertEqual(request.active_membership, self.m_a)
        self.assertFalse(request.workspace_access_denied)

        permission_checker = IsWorkspaceMember()
        self.assertTrue(permission_checker.has_permission(request, None))

    def test_legacy_workspace_code_requires_active_membership(self):
        request = self.factory.get("/", HTTP_X_WORKSPACE=self.ws_b.code)
        request.user = self.user_a

        WorkspaceMiddleware(lambda req: req)(request)

        self.assertIsNone(request.active_workspace)
        self.assertTrue(request.workspace_access_denied)
        self.assertFalse(IsWorkspaceMember().has_permission(request, None))

    def test_legacy_workspace_code_accepts_authorized_member(self):
        request = self.factory.get("/", HTTP_X_WORKSPACE=self.ws_a.code)
        request.user = self.user_a

        WorkspaceMiddleware(lambda req: req)(request)

        self.assertEqual(request.active_workspace, self.ws_a)
        self.assertEqual(request.active_membership, self.m_a)
        self.assertFalse(request.workspace_access_denied)

    def test_workspace_id_is_authoritative_when_headers_conflict(self):
        request = self.factory.get(
            "/",
            HTTP_X_WORKSPACE_ID=str(self.ws_a.id),
            HTTP_X_WORKSPACE=self.ws_b.code,
        )
        request.user = self.user_a

        WorkspaceMiddleware(lambda req: req)(request)

        self.assertEqual(request.active_workspace, self.ws_a)
        self.assertFalse(request.workspace_access_denied)

    def test_unauthorized_explicit_header_never_falls_back_to_default(self):
        request = self.factory.get("/", HTTP_X_WORKSPACE_ID=str(self.ws_b.id))
        request.user = self.user_a
        request.session = {"active_workspace_id": str(self.ws_a.id)}

        workspace, membership = resolve_active_workspace(request, self.user_a)

        self.assertIsNone(workspace)
        self.assertIsNone(membership)

    def test_authenticated_user_without_membership_cannot_select_legacy_workspace(self):
        customer = User.objects.create_user(
            username="public_customer",
            email="public_customer@example.com",
            password="Password123!",
        )
        request = self.factory.get("/", HTTP_X_WORKSPACE=self.ws_a.code)
        request.user = customer

        WorkspaceMiddleware(lambda req: req)(request)

        self.assertIsNone(request.active_workspace)
        self.assertTrue(request.workspace_access_denied)

    def test_inactive_membership_blocks_workspace_access(self):
        """Verify that deactivating a membership prevents access even with valid workspace_id."""
        self.m_a.is_active = False
        self.m_a.save()

        is_valid, membership, workspace = validate_workspace_access(self.user_a, str(self.ws_a.id))
        self.assertFalse(is_valid)
        self.assertIsNone(membership)

        request = self.factory.get("/")
        request.user = self.user_a

        middleware = WorkspaceMiddleware(lambda req: req)
        middleware(request)

        self.assertIsNone(request.active_workspace)

    def test_inactive_workspace_blocks_all_members(self):
        """Verify that deactivating a workspace prevents all members from accessing it."""
        self.ws_a.is_active = False
        self.ws_a.save()

        is_valid, membership, workspace = validate_workspace_access(self.user_a, str(self.ws_a.id))
        self.assertFalse(is_valid)

    def test_workspace_scoped_manager_partitioning(self):
        """Verify WorkspaceScopedManager strictly isolates querysets by workspace."""
        # Create test records
        entity_a1 = DummyTenantEntity.objects.create(name="Record Alpha 1", workspace=self.ws_a)
        entity_a2 = DummyTenantEntity.objects.create(name="Record Alpha 2", workspace=self.ws_a)
        entity_b1 = DummyTenantEntity.objects.create(name="Record Beta 1", workspace=self.ws_b)

        # Query for Tenant Alpha
        alpha_qs = DummyTenantEntity.objects.for_workspace(self.ws_a)
        self.assertEqual(alpha_qs.count(), 2)
        self.assertIn(entity_a1, alpha_qs)
        self.assertIn(entity_a2, alpha_qs)
        self.assertNotIn(entity_b1, alpha_qs)

        # Query for Tenant Beta
        beta_qs = DummyTenantEntity.objects.for_workspace(self.ws_b)
        self.assertEqual(beta_qs.count(), 1)
        self.assertEqual(beta_qs.first(), entity_b1)
        self.assertNotIn(entity_a1, beta_qs)
