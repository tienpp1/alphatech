"""Real PostgreSQL connections and HTTP checkout; no mocked stock mutation."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection, connections, close_old_connections
from django.test import Client, TransactionTestCase, override_settings

from apps.audit.models import AuditLog
from apps.retail.models import Branch, Category, Product, StockBalance, Order, OrderStatus
from apps.retail.services import transition_order_status
from apps.workspaces.models import Workspace


@override_settings(HOME_DELIVERY_FULFILLMENT_POLICY='strict',
    HOME_DELIVERY_DEFAULT_BRANCH_CODE='BR-D1', HOME_DELIVERY_FALLBACK_BRANCH_CODES=())
class CheckoutConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, 'postgresql')
        self.ws = Workspace.objects.create(code='checkout-race', name='Fixture', workspace_type='RETAIL')
        category = Category.objects.create(workspace=self.ws, code='RACE', name='Fixture')
        self.product = Product.objects.create(workspace=self.ws, category=category,
            sku='RACE', name='Fixture', unit_price=100)
        self.branch = Branch.objects.create(workspace=self.ws, code='BR-D1', name='Fixture')
        self.stock = StockBalance.objects.create(workspace=self.ws, branch=self.branch,
            product=self.product, quantity_on_hand=1)

    def client_with_cart(self):
        client = Client()
        response = client.post(f'/gio-hang/them/{self.product.pk}/',
            {'quantity': '1', 'action': 'add_to_cart'})
        self.assertEqual(response.status_code, 302)
        return client

    def checkout(self, client, method, suffix):
        response = client.post('/thanh-toan/dat-hang/', dict(
            name='Fixture', phone='0900000000', email=f'race-{suffix}@example.test',
            address='Fixture', city='Fixture', district='Fixture',
            delivery_method=method, branch_id=str(self.branch.pk)))
        return response.status_code, response.url

    def parallel(self, operations):
        barrier = Barrier(2, timeout=15)
        def run(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '15s'")
                    cursor.execute('SELECT pg_backend_pid()')
                    pid = cursor.fetchone()[0]
                barrier.wait()
                return pid, operation()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, operation) for operation in operations]
            results = [future.result(timeout=40) for future in futures]
        self.assertNotEqual(results[0][0], results[1][0])
        return [result for _, result in results]

    def race_checkouts(self, first, second):
        clients = [self.client_with_cart(), self.client_with_cart()]
        results = self.parallel([
            lambda: self.checkout(clients[0], first, 'a'),
            lambda: self.checkout(clients[1], second, 'b'),
        ])
        self.assertEqual([status for status, _ in results], [302, 302])
        self.assertEqual(sum(url.startswith('/dat-hang-thanh-cong/') for _, url in results), 1)
        self.assertEqual(sum(url == '/gio-hang/' for _, url in results), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertTrue(Order.objects.get().fulfillment_stock_reserved)
        self.assertEqual(AuditLog.objects.filter(action='ORDER_CREATED').count(), 1)
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, 0)

    def test_two_home_deliveries_cannot_sell_last_unit_twice(self):
        self.race_checkouts('HOME_DELIVERY', 'HOME_DELIVERY')

    def test_two_pickups_cannot_sell_last_unit_twice(self):
        self.race_checkouts('STORE_PICKUP', 'STORE_PICKUP')

    def test_pickup_and_delivery_share_same_stock_lock(self):
        self.race_checkouts('STORE_PICKUP', 'HOME_DELIVERY')

    def test_reverse_cart_order_reserves_two_products_without_deadlock(self):
        other = Product.objects.create(workspace=self.ws, category=self.product.category,
            sku='SECOND', name='Second fixture', unit_price=200)
        second_stock = StockBalance.objects.create(workspace=self.ws, branch=self.branch,
            product=other, quantity_on_hand=1)
        clients = [Client(), Client()]
        for client, products in zip(clients, [(self.product, other), (other, self.product)]):
            for product in products:
                self.assertEqual(client.post(f'/gio-hang/them/{product.pk}/',
                    {'quantity': '1', 'action': 'add_to_cart'}).status_code, 302)
        results = self.parallel([
            lambda: self.checkout(clients[0], 'HOME_DELIVERY', 'multi-a'),
            lambda: self.checkout(clients[1], 'STORE_PICKUP', 'multi-b'),
        ])
        self.assertEqual(sum(url.startswith('/dat-hang-thanh-cong/') for _, url in results), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().items.count(), 2)
        for stock in (self.stock, second_stock):
            stock.refresh_from_db()
            self.assertEqual(stock.quantity_on_hand, 0)

    def test_exception_after_reservation_rolls_back_order_and_stock(self):
        client = self.client_with_cart()
        with patch('apps.public_web.views.OrderItem.objects.create', side_effect=RuntimeError('fixture failure')):
            with self.assertRaisesMessage(RuntimeError, 'fixture failure'):
                self.checkout(client, 'HOME_DELIVERY', 'rollback')
        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, 1)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action='ORDER_CREATED').exists())

    def test_two_cancellations_release_reservation_once(self):
        self.assertTrue(self.checkout(self.client_with_cart(), 'HOME_DELIVERY', 'cancel')[1]
                        .startswith('/dat-hang-thanh-cong/'))
        order = Order.objects.get()
        def cancel():
            try:
                transition_order_status(order, OrderStatus.CANCELLED, None)
                return 'CANCELLED'
            except ValidationError:
                return 'DENIED'
        self.assertCountEqual(self.parallel([cancel, cancel]), ['CANCELLED', 'DENIED'])
        self.stock.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.stock.quantity_on_hand, 1)
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertIsNotNone(order.fulfillment_stock_released_at)
        self.assertEqual(AuditLog.objects.filter(action='ORDER_CANCELLED').count(), 1)
