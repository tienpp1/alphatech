"""
Automated tests for Role-Based Access Control (RBAC) across Service Operations endpoints.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.service_ops.models import Service


class ServiceRBACTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace = Workspace.objects.create(
            name="Service WS",
            code="svc-ws",
            workspace_type=WorkspaceType.SERVICE,
        )

        # Permissions
        self.perm_view = Permission.objects.create(codename="service.view_service", name="View Service", module="service_ops")
        self.perm_manage = Permission.objects.create(codename="service.manage_service", name="Manage Service", module="service_ops")
        self.perm_request_create = Permission.objects.create(codename="service.create_request", name="Create Request", module="service_ops")

        # Roles
        self.role_manager = Role.objects.create(name="MANAGER")
        self.role_manager.permissions.add(self.perm_view, self.perm_manage, self.perm_request_create)

        self.role_viewer = Role.objects.create(name="VIEWER")
        self.role_viewer.permissions.add(self.perm_view)

        # Users
        self.manager_user = User.objects.create_user(
            username="svc_manager",
            email="svc_manager@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.manager_user, workspace=self.workspace, role=self.role_manager, is_default=True)

        self.viewer_user = User.objects.create_user(
            username="svc_viewer",
            email="svc_viewer@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.viewer_user, workspace=self.workspace, role=self.role_viewer, is_default=True)

        self.service = Service.objects.create(workspace=self.workspace, code="HVAC-01", name="HVAC Maintenance")

    def test_viewer_can_read_services_but_cannot_create(self):
        self.client.force_authenticate(user=self.viewer_user)
        url = reverse("service_api_services")

        # GET is permitted
        get_res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)

        # POST is forbidden
        post_res = self.client.post(
            url,
            {"code": "NEW-SVC", "name": "New Service"},
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )
        self.assertEqual(post_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_create_and_manage_services(self):
        self.client.force_authenticate(user=self.manager_user)
        url = reverse("service_api_services")

        post_res = self.client.post(
            url,
            {"code": "NEW-MGR", "name": "Manager Service", "standard_duration_minutes": 60, "base_fee": "200000.00"},
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
