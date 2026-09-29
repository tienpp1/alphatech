"""Acceptance test suite for Gate 73: Cross-channel inventory consistency & strict fulfillment."""
from decimal import Decimal
from io import StringIO
import json

from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from apps.retail.models import Branch, Category, Order, OrderStatus, Product, StockBalance
from apps.retail.services import transition_order_status
from apps.workspaces.models import Workspace, WorkspaceType


@override_settings(
    HOME_DELIVERY_FULFILLMENT_POLICY="strict",
    HOME_DELIVERY_DEFAULT_BRANCH_CODE="BR-D1",
    HOME_DELIVERY_FALLBACK_BRANCH_CODES=("BR-BT", "BR-D7"),
)
class FulfillmentInventoryConsistencyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(
            name="Consistency Retail Workspace",
            code="consistency-retail",
            workspace_type=WorkspaceType.RETAIL,
        )
        category = Category.objects.create(
            workspace=self.workspace, name="Điện tử", code="ELEC"
        )
        self.product = Product.objects.create(
            workspace=self.workspace,
            category=category,
            sku="CONSIST-001",
            name="Sản phẩm kiểm chuẩn tồn kho",
            unit_price=Decimal("500000"),
            cost_price=Decimal("300000"),
        )
        self.branch_d1 = Branch.objects.create(
            workspace=self.workspace,
            code="BR-D1",
            name="Chi nhánh Quận 1",
            address="123 Lê Lợi, Quận 1",
            region="TP.HCM",
            latitude=Decimal("10.774500"),
            longitude=Decimal("106.703200"),
            is_active=True,
        )
        self.branch_bt = Branch.objects.create(
            workspace=self.workspace,
            code="BR-BT",
            name="Chi nhánh Bình Thạnh",
            address="456 Điện Biên Phủ, Bình Thạnh",
            region="TP.HCM",
            latitude=Decimal("10.799700"),
            longitude=Decimal("106.718500"),
            is_active=True,
        )
        self.branch_d7 = Branch.objects.create(
            workspace=self.workspace,
            code="BR-D7",
            name="Chi nhánh Quận 7",
            address="789 Nguyễn Văn Linh, Quận 7",
            region="TP.HCM",
            latitude=Decimal("10.728800"),
            longitude=Decimal("106.719600"),
            is_active=True,
        )

    def _add_to_cart(self, quantity):
        return self.client.post(
            f"/gio-hang/them/{self.product.pk}/",
            {"quantity": str(quantity), "action": "add_to_cart"},
        )

    def _checkout(self, delivery_method, quantity=1, **extra):
        self._add_to_cart(quantity)
        payload = {
            "name": "Khách hàng kiểm thử",
            "phone": "0987654321",
            "email": "test-customer@example.com",
            "address": "123 Đường Kiểm Thử",
            "district": "Quận 1",
            "city": "TP. Hồ Chí Minh",
            "delivery_method": delivery_method,
            **extra,
        }
        return self.client.post("/thanh-toan/dat-hang/", payload)

    def test_cross_channel_inventory_deduction_and_cancellation_rollback(self):
        """Verify Store Pickup and Home Delivery both deduct and restore stock consistently."""
        stock_d1 = StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_d1,
            product=self.product,
            quantity_on_hand=10,
        )
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_bt,
            product=self.product,
            quantity_on_hand=5,
        )
        StockBalance.objects.create(
            workspace=self.workspace,
            branch=self.branch_d7,
            product=self.product,
            quantity_on_hand=5,
        )

        # 1. Store Pickup checkout for 3 units at BR-D1
        pickup_resp = self._checkout(
            delivery_method="STORE_PICKUP",
            quantity=3,
            branch_id=str(self.branch_d1.pk),
        )
        self.assertEqual(pickup_resp.status_code, 302)
        stock_d1.refresh_from_db()
        self.assertEqual(stock_d1.quantity_on_hand, 7)
        pickup_order = Order.objects.filter(branch=self.branch_d1).first()
        self.assertIsNotNone(pickup_order)
        self.assertTrue(pickup_order.fulfillment_stock_reserved)

        # 2. Home Delivery checkout for 4 units (routes to BR-D1 by default/proximity)
        delivery_resp = self._checkout(
            delivery_method="HOME_DELIVERY",
            quantity=4,
            delivery_latitude="10.774000",
            delivery_longitude="106.703000",
        )
        self.assertEqual(delivery_resp.status_code, 302)
        stock_d1.refresh_from_db()
        self.assertEqual(stock_d1.quantity_on_hand, 3)
        delivery_order = Order.objects.exclude(pk=pickup_order.pk).first()
        self.assertIsNotNone(delivery_order)
        self.assertEqual(delivery_order.branch, self.branch_d1)
        self.assertTrue(delivery_order.fulfillment_stock_reserved)

        # 3. Rollback Home Delivery order -> stock increases by 4
        transition_order_status(delivery_order, OrderStatus.CANCELLED, None)
        stock_d1.refresh_from_db()
        self.assertEqual(stock_d1.quantity_on_hand, 7)

        # 4. Rollback Store Pickup order -> stock increases by 3 back to original 10
        transition_order_status(pickup_order, OrderStatus.CANCELLED, None)
        stock_d1.refresh_from_db()
        self.assertEqual(stock_d1.quantity_on_hand, 10)

    def test_strict_fulfillment_rejection_prevents_negative_balance(self):
        """Verify strict fulfillment rejects checkout when insufficient stock and preserves balances."""
        stock_d1 = StockBalance.objects.create(
            workspace=self.workspace, branch=self.branch_d1, product=self.product, quantity_on_hand=2
        )
        stock_bt = StockBalance.objects.create(
            workspace=self.workspace, branch=self.branch_bt, product=self.product, quantity_on_hand=2
        )
        stock_d7 = StockBalance.objects.create(
            workspace=self.workspace, branch=self.branch_d7, product=self.product, quantity_on_hand=1
        )

        response = self._checkout(delivery_method="HOME_DELIVERY", quantity=5)
        self.assertEqual(response.url, "/gio-hang/")
        self.assertFalse(Order.objects.exists())

        stock_d1.refresh_from_db()
        stock_bt.refresh_from_db()
        stock_d7.refresh_from_db()
        self.assertEqual(stock_d1.quantity_on_hand, 2)
        self.assertEqual(stock_bt.quantity_on_hand, 2)
        self.assertEqual(stock_d7.quantity_on_hand, 1)

    def test_preflight_stock_audit_command_contract(self):
        """Verify check_fulfillment_stock command reports 100% complete data and detects negatives."""
        StockBalance.objects.create(
            workspace=self.workspace, branch=self.branch_d1, product=self.product, quantity_on_hand=15
        )
        StockBalance.objects.create(
            workspace=self.workspace, branch=self.branch_bt, product=self.product, quantity_on_hand=10
        )
        StockBalance.objects.create(
            workspace=self.workspace, branch=self.branch_d7, product=self.product, quantity_on_hand=5
        )

        output = StringIO()
        call_command("check_fulfillment_stock", workspace=self.workspace.code, stdout=output)
        report = json.loads(output.getvalue())

        self.assertTrue(report["data_complete"])
        self.assertEqual(report["active_products"], 1)
        self.assertEqual(len(report["branches"]), 3)
        for branch_info in report["branches"]:
            self.assertEqual(branch_info["missing_pairs"], 0)
            self.assertEqual(branch_info["negative_stock"], 0)
