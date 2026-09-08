"""
Automated tests for Category model, services, APIs, and safe deletion.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Category, Product
from apps.retail.services import create_category, update_category, delete_category


class RetailCategoryTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace1 = Workspace.objects.create(
            name="Retail WS 1",
            code="retail-1",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.workspace2 = Workspace.objects.create(
            name="Retail WS 2",
            code="retail-2",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.perm_view = Permission.objects.create(codename="retail.view_product", name="View", module="retail")
        self.perm_manage = Permission.objects.create(codename="retail.manage_product", name="Manage", module="retail")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(
            username="cat_admin",
            email="cat_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace1,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_category_service(self):
        cat = create_category(
            workspace=self.workspace1,
            user=self.user,
            data={"name": "Beverages", "code": "beverages", "description": "Soft drinks and juices"},
        )
        self.assertEqual(cat.name, "Beverages")
        self.assertEqual(cat.code, "beverages")
        self.assertEqual(cat.workspace, self.workspace1)

    def test_category_code_unique_per_workspace(self):
        create_category(self.workspace1, self.user, {"name": "Beverages", "code": "bev"})
        # Creating same code in workspace 2 is allowed
        cat2 = create_category(self.workspace2, self.user, {"name": "Beverages 2", "code": "bev"})
        self.assertEqual(cat2.workspace, self.workspace2)

    def test_safe_delete_category_blocked_if_products_exist(self):
        cat = create_category(self.workspace1, self.user, {"name": "Snacks", "code": "snk"})
        Product.objects.create(
            workspace=self.workspace1,
            category=cat,
            sku="SNK-001",
            name="Chips",
            unit_price=Decimal("15000"),
        )
        # Attempt to delete category should raise ValidationError
        with self.assertRaises(ValidationError):
            delete_category(cat, self.user)

        self.assertTrue(Category.objects.filter(id=cat.id).exists())

    def test_category_api_list_and_create(self):
        url = reverse("retail_api_categories")
        response = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Post new category
        post_resp = self.client.post(
            url,
            {"name": "Bakery", "code": "bakery", "description": "Bread and cakes"},
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace1.id),
        )
        self.assertEqual(post_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(post_resp.data["data"]["code"], "bakery")
