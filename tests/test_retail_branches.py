"""
Automated tests for Branch model, services, GIS coordinate validation, and uniqueness.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Branch
from apps.retail.services import create_branch


class RetailBranchTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace1 = Workspace.objects.create(
            name="Retail WS 1",
            code="retail-1",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.perm_view = Permission.objects.create(codename="retail.view_branch", name="View", module="retail")
        self.perm_manage = Permission.objects.create(codename="retail.manage_branch", name="Manage", module="retail")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(
            username="branch_admin",
            email="branch_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace1,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_branch_with_valid_coordinates(self):
        branch = create_branch(
            workspace=self.workspace1,
            user=self.user,
            data={
                "code": "BR-01",
                "name": "District 1 Flagship",
                "address": "123 Nguyen Hue, D1, HCMC",
                "region": "District 1",
                "latitude": 10.7745,
                "longitude": 106.7032,
                "phone": "028-38210001",
            },
        )
        self.assertEqual(branch.code, "BR-01")
        self.assertIsNotNone(branch.location)
        self.assertAlmostEqual(float(branch.latitude), 10.7745, places=4)
        self.assertAlmostEqual(float(branch.longitude), 106.7032, places=4)

    def test_invalid_coordinates_rejected(self):
        with self.assertRaises(ValidationError):
            create_branch(
                workspace=self.workspace1,
                user=self.user,
                data={
                    "code": "BR-INV",
                    "name": "Invalid Branch",
                    "address": "Nowhere",
                    "region": "Unknown",
                    "latitude": 120.0,  # Invalid latitude (> 90)
                    "longitude": 106.7032,
                },
            )

    def test_branch_api_list(self):
        create_branch(
            workspace=self.workspace1,
            user=self.user,
            data={
                "code": "BR-02",
                "name": "D7 Outlet",
                "address": "Ton Dat Tien",
                "region": "District 7",
            },
        )
        url = reverse("retail_api_branches")
        response = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["data"][0]["code"], "BR-02")
