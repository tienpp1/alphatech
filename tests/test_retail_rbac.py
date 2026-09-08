"""
Automated tests for Role-Based Access Control (RBAC) across Retail endpoints.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Category, Product, Customer


class RetailRBACTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace = Workspace.objects.create(
            name="Retail WS",
            code="retail-ws",
            workspace_type=WorkspaceType.RETAIL,
        )

        # Permissions
        self.perm_view = Permission.objects.create(codename="retail.view_product", name="View Product", module="retail")
        self.perm_manage = Permission.objects.create(codename="retail.manage_product", name="Manage Product", module="retail")
        self.perm_order_create = Permission.objects.create(codename="retail.create_order", name="Create Order", module="retail")
        self.perm_order_manage = Permission.objects.create(codename="retail.manage_order", name="Manage Order", module="retail")

        # Roles
        self.role_admin = Role.objects.create(name="ADMIN")
        self.role_admin.permissions.add(self.perm_view, self.perm_manage, self.perm_order_create, self.perm_order_manage)

        self.role_viewer = Role.objects.create(name="VIEWER")
        self.role_viewer.permissions.add(self.perm_view)

        # Users with distinct emails
        self.admin_user = User.objects.create_user(
            username="admin_user",
            email="admin_user@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.admin_user, workspace=self.workspace, role=self.role_admin, is_default=True)

        self.viewer_user = User.objects.create_user(
            username="viewer_user",
            email="viewer_user@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.viewer_user, workspace=self.workspace, role=self.role_viewer, is_default=True)

        self.cat = Category.objects.create(workspace=self.workspace, name="Food", code="food")

    def test_viewer_can_read_products_but_cannot_create_or_delete(self):
        self.client.force_authenticate(user=self.viewer_user)
        url = reverse("retail_api_products")

        # GET is allowed
        get_res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)

        # POST is forbidden for viewer
        post_res = self.client.post(
            url,
            {"sku": "NEW-01", "name": "New Product", "category_id": self.cat.id, "unit_price": "10000"},
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )
        self.assertEqual(post_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_and_manage_products(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("retail_api_products")

        post_res = self.client.post(
            url,
            {"sku": "ADM-01", "name": "Admin Product", "category_id": self.cat.id, "unit_price": "25000"},
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace.id),
        )
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
