"""
Automated tests for Orders:
- Server-side price snapshot & total calculation
- Atomic transactions
- Controlled state transitions
- Audit logging emission
"""

from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.audit.models import AuditLog
from apps.retail.models import Category, Product, Branch, Customer, Order, OrderItem, OrderStatus, PaymentMethod
from apps.retail.services import create_order, transition_order_status


class RetailOrderTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace1 = Workspace.objects.create(
            name="Retail WS 1",
            code="retail-1",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.perm_view = Permission.objects.create(codename="retail.view_order", name="View", module="retail")
        self.perm_create = Permission.objects.create(codename="retail.create_order", name="Create", module="retail")
        self.perm_manage = Permission.objects.create(codename="retail.manage_order", name="Manage", module="retail")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_create, self.perm_manage)

        self.user = User.objects.create_user(
            username="order_admin",
            email="order_admin@example.com",
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
            workspace=self.workspace1,
            category=self.cat,
            sku="BEV-001",
            name="Coke",
            unit_price=Decimal("10000"),
        )
        self.prod2 = Product.objects.create(
            workspace=self.workspace1,
            category=self.cat,
            sku="BEV-002",
            name="Redbull",
            unit_price=Decimal("15000"),
        )
        self.customer = Customer.objects.create(
            workspace=self.workspace1,
            code="CUST-001",
            name="John Doe",
        )
        self.branch = Branch.objects.create(
            workspace=self.workspace1,
            code="BR-01",
            name="D1 Branch",
            address="Nguyen Hue",
            region="District 1",
        )

    def test_order_creation_calculates_server_side_totals_and_snapshots_price(self):
        # Create order with 2x Coke (10,000 each) and 3x Redbull (15,000 each)
        # Expected subtotal = 2*10,000 + 3*15,000 = 65,000
        # Discount = 5,000 -> Expected Total = 60,000
        order = create_order(
            workspace=self.workspace1,
            user=self.user,
            data={
                "customer_id": self.customer.id,
                "branch_id": self.branch.id,
                "discount_amount": Decimal("5000"),
                "items": [
                    {"product_id": self.prod1.id, "quantity": 2, "discount": Decimal("0.00")},
                    {"product_id": self.prod2.id, "quantity": 3, "discount": Decimal("0.00")},
                ],
            },
        )

        self.assertEqual(order.subtotal_amount, Decimal("65000.00"))
        self.assertEqual(order.discount_amount, Decimal("5000.00"))
        self.assertEqual(order.total_amount, Decimal("60000.00"))
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.items.count(), 2)

        # Verify historical price snapshot remains even if product price subsequently changes
        self.prod1.unit_price = Decimal("20000")
        self.prod1.save()

        item1 = order.items.get(product=self.prod1)
        self.assertEqual(item1.unit_price, Decimal("10000.00"))
        self.assertEqual(item1.subtotal, Decimal("20000.00"))

        # Verify audit log recorded
        audit = AuditLog.objects.filter(action="ORDER_CREATED", entity_id=str(order.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.workspace, self.workspace1)

    def test_order_creation_rejects_inactive_product(self):
        self.prod1.is_active = False
        self.prod1.save()

        with self.assertRaises(ValidationError):
            create_order(
                workspace=self.workspace1,
                user=self.user,
                data={
                    "customer_id": self.customer.id,
                    "items": [{"product_id": self.prod1.id, "quantity": 1}],
                },
            )

    def test_order_state_transitions(self):
        order = create_order(
            workspace=self.workspace1,
            user=self.user,
            data={
                "customer_id": self.customer.id,
                "items": [{"product_id": self.prod1.id, "quantity": 1}],
            },
        )
        self.assertEqual(order.status, OrderStatus.PENDING)

        # 1. PENDING -> CONFIRMED (Valid)
        order = transition_order_status(order, OrderStatus.CONFIRMED, self.user)
        self.assertEqual(order.status, OrderStatus.CONFIRMED)

        # 2. CONFIRMED -> COMPLETED (Valid)
        order = transition_order_status(order, OrderStatus.COMPLETED, self.user)
        self.assertEqual(order.status, OrderStatus.COMPLETED)

        # 3. COMPLETED -> CANCELLED (Invalid: terminal state)
        with self.assertRaises(ValidationError):
            transition_order_status(order, OrderStatus.CANCELLED, self.user)

    def test_order_cancel_from_pending(self):
        order = create_order(
            workspace=self.workspace1,
            user=self.user,
            data={
                "customer_id": self.customer.id,
                "items": [{"product_id": self.prod1.id, "quantity": 1}],
            },
        )
        order = transition_order_status(order, OrderStatus.CANCELLED, self.user)
        self.assertEqual(order.status, OrderStatus.CANCELLED)

        # Re-transitioning from CANCELLED is rejected
        with self.assertRaises(ValidationError):
            transition_order_status(order, OrderStatus.CONFIRMED, self.user)

    def test_order_rest_api_create_and_confirm(self):
        url = reverse("retail_api_orders")
        payload = {
            "customer_id": self.customer.id,
            "branch_id": self.branch.id,
            "payment_method": "CASH",
            "items": [
                {"product_id": self.prod1.id, "quantity": 2, "discount": "0.00"},
            ],
        }
        res = self.client.post(url, payload, format="json", HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        order_id = res.data["data"]["id"]
        self.assertEqual(Decimal(str(res.data["data"]["total_amount"])), Decimal("20000.00"))

        # Confirm via API
        confirm_url = reverse("retail_api_order_confirm", kwargs={"pk": order_id})
        confirm_res = self.client.post(confirm_url, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(confirm_res.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm_res.data["data"]["status"], "CONFIRMED")
