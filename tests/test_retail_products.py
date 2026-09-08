"""
Automated tests for Product catalog, validation, SKU uniqueness, and safe deletion.
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Category, Product, Customer, Order, OrderItem
from apps.retail.services import create_product, update_product, delete_product


class RetailProductTests(TestCase):
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
            username="prod_admin",
            email="prod_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace1,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

        self.cat1 = Category.objects.create(workspace=self.workspace1, name="Drinks", code="drinks")
        self.cat2 = Category.objects.create(workspace=self.workspace2, name="Drinks 2", code="drinks")

    def test_create_product_service(self):
        prod = create_product(
            workspace=self.workspace1,
            user=self.user,
            data={
                "category_id": self.cat1.id,
                "sku": "DRK-001",
                "name": "Mineral Water 500ml",
                "unit": "chai",
                "unit_price": Decimal("7000"),
                "cost_price": Decimal("4500"),
            },
        )
        self.assertEqual(prod.sku, "DRK-001")
        self.assertEqual(prod.unit_price, Decimal("7000"))
        self.assertEqual(prod.workspace, self.workspace1)

    def test_negative_unit_price_rejected(self):
        with self.assertRaises(ValidationError):
            create_product(
                workspace=self.workspace1,
                user=self.user,
                data={
                    "category_id": self.cat1.id,
                    "sku": "DRK-NEG",
                    "name": "Invalid Price Drink",
                    "unit_price": Decimal("-5000"),
                },
            )

    def test_cross_workspace_category_rejected(self):
        # Trying to create product in WS1 using a category belonging to WS2
        with self.assertRaises(ValidationError):
            create_product(
                workspace=self.workspace1,
                user=self.user,
                data={
                    "category_id": self.cat2.id,
                    "sku": "DRK-CROSS",
                    "name": "Cross WS Product",
                    "unit_price": Decimal("10000"),
                },
            )

    def test_product_safe_delete_prevented_when_order_items_exist(self):
        prod = create_product(
            workspace=self.workspace1,
            user=self.user,
            data={
                "category_id": self.cat1.id,
                "sku": "DRK-ORDS",
                "name": "Ordered Drink",
                "unit_price": Decimal("12000"),
            },
        )
        customer = Customer.objects.create(
            workspace=self.workspace1,
            code="CUST-001",
            name="Test Customer",
        )
        order = Order.objects.create(
            workspace=self.workspace1,
            order_number="ORD-TEST-01",
            customer=customer,
            order_date="2026-08-01",
            order_timestamp="2026-08-01T10:00:00Z",
            total_amount=Decimal("12000"),
        )
        OrderItem.objects.create(
            order=order,
            product=prod,
            quantity=1,
            unit_price=Decimal("12000"),
            subtotal=Decimal("12000"),
        )

        with self.assertRaises(ValidationError):
            delete_product(prod, self.user)

        self.assertTrue(Product.objects.filter(id=prod.id).exists())

    def test_product_api_list_and_create(self):
        url = reverse("retail_api_products")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        post_res = self.client.post(
            url,
            {
                "sku": "API-PROD",
                "name": "API Created Product",
                "category_id": self.cat1.id,
                "unit_price": "25000",
            },
            format="json",
            HTTP_X_WORKSPACE_ID=str(self.workspace1.id),
        )
        self.assertEqual(post_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(post_res.data["data"]["sku"], "API-PROD")
