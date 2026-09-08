"""
Automated tests for Service catalog, validation, active filtering, and workspace isolation.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.service_ops.models import Service
from apps.service_ops.services import create_service, update_service, delete_service


class ServiceCatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace1 = Workspace.objects.create(
            name="Service WS 1",
            code="svc-ws-1",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.workspace2 = Workspace.objects.create(
            name="Service WS 2",
            code="svc-ws-2",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.perm_view = Permission.objects.create(codename="service.view_service", name="View", module="service_ops")
        self.perm_manage = Permission.objects.create(codename="service.manage_service", name="Manage", module="service_ops")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(
            username="svc_admin",
            email="svc_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace1,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_service_model_and_service(self):
        svc = create_service(
            workspace=self.workspace1,
            user=self.user,
            data={
                "code": "HVAC-101",
                "name": "HVAC Overhaul",
                "description": "Full compressor and refrigerant flush",
                "standard_duration_minutes": 180,
                "base_fee": "750000.00",
            },
        )
        self.assertEqual(svc.code, "HVAC-101")
        self.assertEqual(svc.base_fee, Decimal("750000.00"))
        self.assertEqual(svc.standard_duration_minutes, 180)
        self.assertEqual(svc.workspace, self.workspace1)

    def test_duplicate_service_code_per_workspace_rejected(self):
        create_service(self.workspace1, self.user, {"code": "FIBER-01", "name": "Fiber Splice"})
        with self.assertRaises(ValidationError):
            create_service(self.workspace1, self.user, {"code": "FIBER-01", "name": "Fiber Splice Duplicate"})

        # Same code in workspace 2 is allowed
        svc2 = create_service(self.workspace2, self.user, {"code": "FIBER-01", "name": "Fiber Splice WS2"})
        self.assertEqual(svc2.workspace, self.workspace2)

    def test_service_rest_api_list_and_create(self):
        url = reverse("service_api_services")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        post_res = self.client.post(
            url,
            {
                "code": "CCTV-NEW",
                "name": "CCTV Setup",
                "standard_duration_minutes": 90,
                "base_fee": "450000.00",
            },
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace1.id),
        )
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(post_res.data["data"]["code"], "CCTV-NEW")
