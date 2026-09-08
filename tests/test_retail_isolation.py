"""
Automated tests for Strict Multi-Tenant Isolation across Retail Domain Entities.
Ensures zero data leakage between distinct workspaces.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Category, Product, Branch, Customer, Order


class RetailIsolationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace_a = Workspace.objects.create(
            name="Retail A",
            code="retail-a",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.workspace_b = Workspace.objects.create(
            name="Retail B",
            code="retail-b",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.perm_view = Permission.objects.create(codename="retail.view_product", name="View Product", module="retail")
        self.perm_order_view = Permission.objects.create(codename="retail.view_order", name="View Order", module="retail")

        self.role = Role.objects.create(name="MANAGER")
        self.role.permissions.add(self.perm_view, self.perm_order_view)

        self.user_a = User.objects.create_user(
            username="user_a",
            email="user_a@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.user_a, workspace=self.workspace_a, role=self.role, is_default=True)

        self.user_b = User.objects.create_user(
            username="user_b",
            email="user_b@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(user=self.user_b, workspace=self.workspace_b, role=self.role, is_default=True)

        # Populate Workspace A
        self.cat_a = Category.objects.create(workspace=self.workspace_a, name="Cat A", code="cat-a")
        self.prod_a = Product.objects.create(workspace=self.workspace_a, category=self.cat_a, sku="SKU-A", name="Prod A", unit_price=Decimal("10000"))
        self.cust_a = Customer.objects.create(workspace=self.workspace_a, code="CUST-A", name="Cust A")
        self.order_a = Order.objects.create(
            workspace=self.workspace_a, order_number="ORD-A-01", customer=self.cust_a, order_date="2026-08-01", order_timestamp="2026-08-01T10:00:00Z", total_amount=Decimal("10000")
        )

        # Populate Workspace B
        self.cat_b = Category.objects.create(workspace=self.workspace_b, name="Cat B", code="cat-b")
        self.prod_b = Product.objects.create(workspace=self.workspace_b, category=self.cat_b, sku="SKU-B", name="Prod B", unit_price=Decimal("20000"))
        self.cust_b = Customer.objects.create(workspace=self.workspace_b, code="CUST-B", name="Cust B")
        self.order_b = Order.objects.create(
            workspace=self.workspace_b, order_number="ORD-B-01", customer=self.cust_b, order_date="2026-08-01", order_timestamp="2026-08-01T10:00:00Z", total_amount=Decimal("20000")
        )

    def test_user_a_cannot_see_products_from_workspace_b(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("retail_api_products")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        skus = [p["sku"] for p in res.data["data"]]
        self.assertIn("SKU-A", skus)
        self.assertNotIn("SKU-B", skus)

    def test_user_a_cannot_get_product_detail_from_workspace_b(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("retail_api_product_detail", kwargs={"pk": self.prod_b.id})
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_see_orders_from_workspace_b(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("retail_api_orders")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_a.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ord_nums = [o["order_number"] for o in res.data["data"]]
        self.assertIn("ORD-A-01", ord_nums)
        self.assertNotIn("ORD-B-01", ord_nums)

    def test_user_a_cannot_access_workspace_b_even_with_explicit_header(self):
        self.client.force_authenticate(user=self.user_a)
        url = reverse("retail_api_products")
        # Attempting to impersonate Workspace B header
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace_b.id))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
