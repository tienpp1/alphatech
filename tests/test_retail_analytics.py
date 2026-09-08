"""
Automated tests for Sales Analytics and Revenue Selectors.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Category, Product, Branch, Customer, Order, OrderItem, OrderStatus
from apps.retail.selectors import (
    get_revenue_summary,
    get_revenue_timeseries,
    get_branch_revenue_breakdown,
    get_top_products,
    get_customer_sales_summary,
)


class RetailAnalyticsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace1 = Workspace.objects.create(
            name="Retail WS 1",
            code="retail-1",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.perm_view = Permission.objects.create(codename="retail.view_order", name="View", module="retail")
        self.perm_analytics = Permission.objects.create(codename="retail.view_analytics", name="Analytics", module="retail")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_analytics)

        self.user = User.objects.create_user(
            username="analytics_user",
            email="analytics_user@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace1,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

        self.cat = Category.objects.create(workspace=self.workspace1, name="Beverages", code="bev")
        self.prod1 = Product.objects.create(
            workspace=self.workspace1, category=self.cat, sku="P1", name="Product 1", unit_price=Decimal("10000")
        )
        self.prod2 = Product.objects.create(
            workspace=self.workspace1, category=self.cat, sku="P2", name="Product 2", unit_price=Decimal("20000")
        )
        self.branch1 = Branch.objects.create(
            workspace=self.workspace1, code="B1", name="Branch 1", address="A1", region="R1"
        )
        self.branch2 = Branch.objects.create(
            workspace=self.workspace1, code="B2", name="Branch 2", address="A2", region="R2"
        )
        self.customer = Customer.objects.create(workspace=self.workspace1, code="C1", name="Customer 1")

        # Create 3 orders: 2 completed (100k and 40k), 1 cancelled (50k)
        o1 = Order.objects.create(
            workspace=self.workspace1,
            order_number="ORD-01",
            customer=self.customer,
            branch=self.branch1,
            order_date=date(2026, 8, 1),
            order_timestamp="2026-08-01T10:00:00Z",
            status=OrderStatus.COMPLETED,
            subtotal_amount=Decimal("100000"),
            total_amount=Decimal("100000"),
        )
        OrderItem.objects.create(order=o1, product=self.prod1, quantity=10, unit_price=Decimal("10000"), subtotal=Decimal("100000"))

        o2 = Order.objects.create(
            workspace=self.workspace1,
            order_number="ORD-02",
            customer=self.customer,
            branch=self.branch2,
            order_date=date(2026, 8, 2),
            order_timestamp="2026-08-02T10:00:00Z",
            status=OrderStatus.CONFIRMED,
            subtotal_amount=Decimal("40000"),
            total_amount=Decimal("40000"),
        )
        OrderItem.objects.create(order=o2, product=self.prod2, quantity=2, unit_price=Decimal("20000"), subtotal=Decimal("40000"))

        o3 = Order.objects.create(
            workspace=self.workspace1,
            order_number="ORD-03",
            customer=self.customer,
            branch=self.branch1,
            order_date=date(2026, 8, 3),
            order_timestamp="2026-08-03T10:00:00Z",
            status=OrderStatus.CANCELLED,
            subtotal_amount=Decimal("50000"),
            total_amount=Decimal("50000"),
        )
        OrderItem.objects.create(order=o3, product=self.prod1, quantity=5, unit_price=Decimal("10000"), subtotal=Decimal("50000"))

    def test_revenue_summary_excludes_cancelled_orders(self):
        summary = get_revenue_summary(self.workspace1)
        # Expected: 100,000 + 40,000 = 140,000 (excluding 50,000 cancelled)
        self.assertEqual(summary["total_revenue"], Decimal("140000.00"))
        self.assertEqual(summary["order_count"], 2)
        self.assertEqual(summary["cancelled_order_count"], 1)
        self.assertEqual(summary["average_order_value"], Decimal("70000.00"))
        self.assertEqual(summary["total_items_sold"], 12)

    def test_top_products_ranking(self):
        top_prods = get_top_products(self.workspace1, limit=5)
        self.assertEqual(len(top_prods), 2)
        # Product 1 has 100k revenue (excluding cancelled order), Product 2 has 40k
        self.assertEqual(top_prods[0]["sku"], "P1")
        self.assertEqual(top_prods[0]["revenue"], 100000.0)
        self.assertEqual(top_prods[0]["quantity_sold"], 10)

    def test_branch_revenue_breakdown(self):
        breakdown = get_branch_revenue_breakdown(self.workspace1)
        self.assertEqual(len(breakdown), 2)
        self.assertEqual(breakdown[0]["branch_code"], "B1")
        self.assertEqual(breakdown[0]["revenue"], 100000.0)
        self.assertEqual(breakdown[1]["branch_code"], "B2")
        self.assertEqual(breakdown[1]["revenue"], 40000.0)

    def test_analytics_api_endpoints(self):
        url = reverse("retail_api_analytics_revenue")
        res = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(str(res.data["data"]["total_revenue"])), Decimal("140000.00"))
