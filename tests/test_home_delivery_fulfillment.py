from decimal import Decimal
from io import StringIO
import json

from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.test import Client, TestCase, override_settings
from apps.public_web.fulfillment import allocate_home_delivery_stock, FulfillmentError

from apps.retail.models import Branch, Category, Order, OrderStatus, Product, StockBalance
from apps.retail.services import transition_order_status
from apps.workspaces.models import Workspace, WorkspaceType


@override_settings(
    HOME_DELIVERY_FULFILLMENT_POLICY="strict",
    HOME_DELIVERY_DEFAULT_BRANCH_CODE="BR-D1",
    HOME_DELIVERY_FALLBACK_BRANCH_CODES=("BR-BT", "BR-D7"),
)
class StrictHomeDeliveryFulfillmentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.workspace = Workspace.objects.create(
            name="Strict fulfillment workspace",
            code="strict-fulfillment",
            workspace_type=WorkspaceType.RETAIL,
        )
        category = Category.objects.create(
            workspace=self.workspace, name="Thiết bị", code="DEV"
        )
        self.product = Product.objects.create(
            workspace=self.workspace,
            category=category,
            sku="FULFILL-001",
            name="Thiết bị kiểm thử",
            unit_price=Decimal("1000000"),
            cost_price=Decimal("700000"),
        )
        self.central = self._branch("BR-D1", "Kho trung tâm", 10.774500, 106.703200)
        self.binh_thanh = self._branch("BR-BT", "Bình Thạnh", 10.799700, 106.718500)
        self.district_7 = self._branch("BR-D7", "Quận 7", 10.728800, 106.719600)

    def _branch(self, code, name, latitude, longitude):
        return Branch.objects.create(
            workspace=self.workspace,
            code=code,
            name=name,
            address=name,
            region="TP.HCM",
            latitude=Decimal(str(latitude)),
            longitude=Decimal(str(longitude)),
            is_active=True,
        )

    def _add_to_cart(self, quantity):
        self.client.post(
            f"/gio-hang/them/{self.product.pk}/",
            {"quantity": str(quantity), "action": "add_to_cart"},
        )

    def _checkout(self, quantity=1, **extra):
        self._add_to_cart(quantity)
        payload = {
            "name": "Khách strict",
            "phone": "0900000000",
            "email": "strict@example.com",
            "address": "123 Nguyễn Huệ",
            "district": "Quận 1",
            "city": "TP. Hồ Chí Minh",
            "delivery_method": "HOME_DELIVERY",
            **extra,
        }
        return self.client.post("/thanh-toan/dat-hang/", payload)

    def test_prefers_default_branch_and_reserves_every_line(self):
        central_stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.central, product=self.product, quantity_on_hand=5
        )
        response = self._checkout(quantity=2)

        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.branch, self.central)
        self.assertTrue(order.fulfillment_stock_reserved)
        self.assertIsNone(order.fulfillment_stock_released_at)
        central_stock.refresh_from_db()
        self.assertEqual(central_stock.quantity_on_hand, 3)

    def test_cancellation_releases_strict_reservation_once(self):
        stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.central, product=self.product, quantity_on_hand=5
        )
        self.assertEqual(self._checkout(quantity=2).status_code, 302)
        order = Order.objects.get()
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 3)

        cancelled = transition_order_status(order, OrderStatus.CANCELLED, None)
        self.assertEqual(cancelled.status, OrderStatus.CANCELLED)
        stock.refresh_from_db()
        cancelled.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 5)
        self.assertIsNotNone(cancelled.fulfillment_stock_released_at)

        # Terminal state prevents a second transition; the explicit timestamp
        # also makes the release idempotent if a caller retries the helper.
        with self.assertRaises(ValidationError):
            transition_order_status(cancelled, OrderStatus.CANCELLED, None)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 5)

    def test_pickup_cancellation_releases_the_deducted_stock(self):
        stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.central, product=self.product, quantity_on_hand=4
        )
        self.assertEqual(
            self._checkout(quantity=1, delivery_method="STORE_PICKUP", branch_id=str(self.central.pk)).status_code,
            302,
        )
        order = Order.objects.get()
        self.assertTrue(order.fulfillment_stock_reserved)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 3)

        transition_order_status(order, OrderStatus.CANCELLED, None)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 4)

    def test_cancellation_aborts_without_partial_release_when_balance_missing(self):
        stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.central, product=self.product, quantity_on_hand=4
        )
        self.assertEqual(self._checkout(quantity=1).status_code, 302)
        order = Order.objects.get()
        stock.delete()

        with self.assertRaises(ValidationError):
            transition_order_status(order, OrderStatus.CANCELLED, None)
        order.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertIsNone(order.fulfillment_stock_released_at)

    def test_reroutes_to_nearest_configured_satellite_when_central_is_short(self):
        central_stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.central, product=self.product, quantity_on_hand=1
        )
        satellite_stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.binh_thanh, product=self.product, quantity_on_hand=5
        )
        StockBalance.objects.create(
            workspace=self.workspace, branch=self.district_7, product=self.product, quantity_on_hand=5
        )
        response = self._checkout(
            quantity=2,
            delivery_latitude="10.800000",
            delivery_longitude="106.720000",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.get().branch, self.binh_thanh)
        central_stock.refresh_from_db()
        satellite_stock.refresh_from_db()
        self.assertEqual(central_stock.quantity_on_hand, 1)
        self.assertEqual(satellite_stock.quantity_on_hand, 3)

    def test_network_stockout_rejects_without_deducting_or_creating_order(self):
        central_stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.central, product=self.product, quantity_on_hand=1
        )
        satellite_stock = StockBalance.objects.create(
            workspace=self.workspace, branch=self.binh_thanh, product=self.product, quantity_on_hand=1
        )
        response = self._checkout(quantity=3)

        self.assertEqual(response.url, "/gio-hang/")
        self.assertFalse(Order.objects.exists())
        central_stock.refresh_from_db()
        satellite_stock.refresh_from_db()
        self.assertEqual(central_stock.quantity_on_hand, 1)
        self.assertEqual(satellite_stock.quantity_on_hand, 1)
        self.assertIn("chỉ còn 2 sản phẩm khả dụng", self.client.session["checkout_error"])

    def test_invalid_browser_coordinates_are_rejected_without_order(self):
        StockBalance.objects.create(
            workspace=self.workspace, branch=self.central, product=self.product, quantity_on_hand=5
        )
        response = self._checkout(delivery_latitude="not-a-number", delivery_longitude="106.7")

        self.assertEqual(response.url, "/gio-hang/")
        self.assertFalse(Order.objects.exists())
        self.assertIn("Vị trí giao hàng không hợp lệ", self.client.session["checkout_error"])

    def test_duplicate_lines_are_aggregated_before_stock_check(self):
        stock = StockBalance.objects.create(workspace=self.workspace, branch=self.central,
                                           product=self.product, quantity_on_hand=3)
        with self.assertRaises(FulfillmentError):
            allocate_home_delivery_stock(workspace=self.workspace,
                lines=[(self.product.pk, 2, 'A'), (self.product.pk, 2, 'A')])
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 3)

    def test_unconfigured_branch_is_not_used(self):
        other = self._branch('OTHER', 'Not approved', 10.8, 106.7)
        stock = StockBalance.objects.create(workspace=self.workspace, branch=other,
                                           product=self.product, quantity_on_hand=10)
        with self.assertRaises(FulfillmentError):
            allocate_home_delivery_stock(workspace=self.workspace, lines=[(self.product.pk, 1, 'A')])
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 10)

    def test_distributed_stock_has_distinct_truthful_failure(self):
        for branch in (self.central, self.binh_thanh):
            StockBalance.objects.create(workspace=self.workspace, branch=branch,
                                        product=self.product, quantity_on_hand=2)
        with self.assertRaises(FulfillmentError) as raised:
            allocate_home_delivery_stock(workspace=self.workspace, lines=[(self.product.pk, 3, 'A')])
        self.assertEqual(raised.exception.code, 'NO_SINGLE_BRANCH_STOCK')
        self.assertEqual(list(StockBalance.objects.values_list('quantity_on_hand', flat=True)), [2, 2])

    def test_foreign_product_in_malformed_balance_is_rejected(self):
        foreign = Workspace.objects.create(code='foreign-fulfillment', name='Foreign', workspace_type=WorkspaceType.RETAIL)
        category = Category.objects.create(workspace=foreign, name='Foreign', code='F')
        product = Product.objects.create(workspace=foreign, category=category, sku='F', name='Private', unit_price=10)
        stock = StockBalance.objects.create(workspace=self.workspace, branch=self.central,
                                           product=product, quantity_on_hand=9)
        with self.assertRaises(FulfillmentError) as raised:
            allocate_home_delivery_stock(workspace=self.workspace, lines=[(product.pk, 1, 'Private')])
        self.assertEqual(raised.exception.code, 'INVALID_LINES')
        self.assertNotIn('Private', raised.exception.message)
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 9)

    def test_fractional_quantity_is_not_truncated(self):
        with self.assertRaises(FulfillmentError) as raised:
            allocate_home_delivery_stock(workspace=self.workspace, lines=[(self.product.pk, 1.5, 'A')])
        self.assertEqual(raised.exception.code, 'INVALID_LINES')

    def test_readonly_preflight_distinguishes_zero_missing_negative(self):
        stock = StockBalance.objects.create(workspace=self.workspace, branch=self.central,
                                           product=self.product, quantity_on_hand=0)
        output = StringIO()
        call_command('check_fulfillment_stock', workspace=self.workspace.code, stdout=output)
        report = json.loads(output.getvalue())
        self.assertFalse(report['data_complete'])
        self.assertEqual(report['branches'][0]['zero_stock'], 1)
        self.assertEqual(report['branches'][1]['missing_pairs'], 1)
        for branch in (self.binh_thanh, self.district_7):
            StockBalance.objects.create(workspace=self.workspace, branch=branch, product=self.product, quantity_on_hand=5)
        output = StringIO()
        call_command('check_fulfillment_stock', workspace=self.workspace.code, stdout=output)
        self.assertTrue(json.loads(output.getvalue())['data_complete'])
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 0)
        stock.quantity_on_hand = -1
        stock.save()
        output = StringIO()
        call_command('check_fulfillment_stock', workspace=self.workspace.code, stdout=output)
        self.assertFalse(json.loads(output.getvalue())['data_complete'])
