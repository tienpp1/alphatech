"""
Automated unit tests for Role-Based Access Control (RBAC) and permissions.
"""

from django.test import TestCase, RequestFactory
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.accounts.services import (
    has_workspace_permission,
    get_user_permissions,
    assign_role_to_user_in_workspace,
)
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.workspaces.permissions import (
    IsWorkspaceMember,
    IsWorkspaceAdmin,
    IsWorkspaceManager,
    require_permission,
)


class RBACTestCase(TestCase):
    """Test suite for Role and Permission models, services, and DRF permission classes."""

    def setUp(self):
        self.factory = RequestFactory()

        # Create Workspaces
        self.retail_ws = Workspace.objects.create(
            name="Retail Store",
            code="retail-ws",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.service_ws = Workspace.objects.create(
            name="Field Service",
            code="service-ws",
            workspace_type=WorkspaceType.SERVICE,
        )

        # Create Permissions
        self.p_view_order = Permission.objects.create(
            codename="retail.view_order",
            name="View Order",
            module="retail",
        )
        self.p_create_order = Permission.objects.create(
            codename="retail.create_order",
            name="Create Order",
            module="retail",
        )
        self.p_assign_task = Permission.objects.create(
            codename="service.assign_task",
            name="Assign Task",
            module="service_ops",
        )

        # Create Roles
        self.admin_role = Role.objects.create(name="ADMIN", description="Administrator")
        self.admin_role.permissions.add(self.p_view_order, self.p_create_order, self.p_assign_task)

        self.manager_role = Role.objects.create(name="MANAGER", description="Manager")
        self.manager_role.permissions.add(self.p_view_order, self.p_create_order)

        self.employee_role = Role.objects.create(name="EMPLOYEE", description="Employee")
        self.employee_role.permissions.add(self.p_view_order)

        self.viewer_role = Role.objects.create(name="VIEWER", description="Viewer")

        # Create Users
        self.user = User.objects.create_user(
            username="multirole_user",
            email="multirole@example.com",
            password="Password123!",
        )
        self.superuser = User.objects.create_superuser(
            username="super_user",
            email="super@example.com",
            password="Password123!",
        )

        # Assign user different roles in different workspaces
        # Manager in Retail, Employee in Service
        assign_role_to_user_in_workspace(self.user, self.retail_ws, self.manager_role)
        assign_role_to_user_in_workspace(self.user, self.service_ws, self.employee_role)

    def test_role_has_permission_method(self):
        """Verify Role.has_permission returns correct boolean."""
        self.assertTrue(self.admin_role.has_permission("retail.view_order"))
        self.assertTrue(self.manager_role.has_permission("retail.create_order"))
        self.assertFalse(self.employee_role.has_permission("retail.create_order"))
        self.assertFalse(self.viewer_role.has_permission("retail.view_order"))

    def test_permission_variance_across_workspaces(self):
        """Verify the same user has different permissions in different workspaces."""
        # In Retail Workspace (Manager): has create_order and view_order
        self.assertTrue(has_workspace_permission(self.user, self.retail_ws, "retail.create_order"))
        self.assertTrue(has_workspace_permission(self.user, self.retail_ws, "retail.view_order"))
        self.assertFalse(has_workspace_permission(self.user, self.retail_ws, "service.assign_task"))

        # In Service Workspace (Employee): only has view_order, does NOT have create_order
        self.assertFalse(has_workspace_permission(self.user, self.service_ws, "retail.create_order"))
        self.assertTrue(has_workspace_permission(self.user, self.service_ws, "retail.view_order"))

    def test_superuser_inherits_all_permissions(self):
        """Verify superusers have all permissions across any workspace."""
        self.assertTrue(has_workspace_permission(self.superuser, self.retail_ws, "retail.create_order"))
        self.assertTrue(has_workspace_permission(self.superuser, self.service_ws, "service.assign_task"))
        self.assertTrue(has_workspace_permission(self.superuser, self.retail_ws, "nonexistent.perm"))

    def test_drf_permission_is_workspace_admin(self):
        """Verify IsWorkspaceAdmin permission class."""
        permission_checker = IsWorkspaceAdmin()

        # Admin user
        admin_user = User.objects.create_user(username="admin_user", email="adm@ex.com", password="P1")
        assign_role_to_user_in_workspace(admin_user, self.retail_ws, self.admin_role)

        request = self.factory.get("/")
        request.user = admin_user
        request.active_workspace = self.retail_ws
        request.active_membership = WorkspaceMembership.objects.get(user=admin_user, workspace=self.retail_ws)

        self.assertTrue(permission_checker.has_permission(request, None))

        # Manager user in same workspace should fail IsWorkspaceAdmin
        request.user = self.user
        request.active_membership = WorkspaceMembership.objects.get(user=self.user, workspace=self.retail_ws)
        self.assertFalse(permission_checker.has_permission(request, None))

    def test_drf_dynamic_permission_factory(self):
        """Verify require_permission factory verifies specific codename."""
        perm_class = require_permission("retail.create_order")()

        request = self.factory.post("/")
        request.user = self.user
        request.active_workspace = self.retail_ws
        request.active_membership = WorkspaceMembership.objects.get(user=self.user, workspace=self.retail_ws)

        # In Retail WS (Manager), has retail.create_order -> True
        self.assertTrue(perm_class.has_permission(request, None))

        # In Service WS (Employee), does not have retail.create_order -> False
        request.active_workspace = self.service_ws
        request.active_membership = WorkspaceMembership.objects.get(user=self.user, workspace=self.service_ws)
        self.assertFalse(perm_class.has_permission(request, None))
