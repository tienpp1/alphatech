"""
Tests for Forecasting Dataset Construction & Aggregation.
Verifies aggregation rules, gapless chronological reindexing, and workspace isolation.
"""

from decimal import Decimal
import datetime
from django.test import TestCase
from django.utils import timezone

from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import Category, Customer, CustomerSegment, Order, OrderItem, OrderStatus, Product
from apps.service_ops.models import Service, ServiceRequest, ServiceRequestStatus, SLAPriority, SLA
from apps.forecasting.models import TargetType, Granularity
from apps.forecasting.selectors import get_historical_timeseries


class ForecastingDatasetTestCase(TestCase):
    def setUp(self):
        self.retail_ws_a = Workspace.objects.create(
            name="Retail WS A",
            code="retail-ws-a",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.retail_ws_b = Workspace.objects.create(
            name="Retail WS B",
            code="retail-ws-b",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.service_ws = Workspace.objects.create(
            name="Service WS",
            code="service-ws",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.customer_a = Customer.objects.create(
            workspace=self.retail_ws_a,
            code="CUST-A-01",
            name="Customer A",
            customer_segment=CustomerSegment.STANDARD,
        )
        self.customer_b = Customer.objects.create(
            workspace=self.retail_ws_b,
            code="CUST-B-01",
            name="Customer B",
            customer_segment=CustomerSegment.STANDARD,
        )

        self.base_date = datetime.date(2026, 1, 1)

        # Create retail orders for Workspace A
        # Day 1: Completed order 100,000
        Order.objects.create(
            workspace=self.retail_ws_a,
            order_number="ORD-A-01",
            customer=self.customer_a,
            order_date=self.base_date,
            order_timestamp=timezone.make_aware(datetime.datetime(2026, 1, 1, 10, 0)),
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("100000.00"),
        )
        # Day 1: Another Completed order 50,000 (total Day 1 = 150,000, count = 2)
        Order.objects.create(
            workspace=self.retail_ws_a,
            order_number="ORD-A-02",
            customer=self.customer_a,
            order_date=self.base_date,
            order_timestamp=timezone.make_aware(datetime.datetime(2026, 1, 1, 14, 0)),
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("50000.00"),
        )
        # Day 1: Cancelled order (should be excluded from completed revenue and order volume)
        Order.objects.create(
            workspace=self.retail_ws_a,
            order_number="ORD-A-03",
            customer=self.customer_a,
            order_date=self.base_date,
            order_timestamp=timezone.make_aware(datetime.datetime(2026, 1, 1, 16, 0)),
            status=OrderStatus.CANCELLED,
            total_amount=Decimal("30000.00"),
        )
        # Day 3: Completed order 200,000 (Day 2 has zero orders)
        Order.objects.create(
            workspace=self.retail_ws_a,
            order_number="ORD-A-04",
            customer=self.customer_a,
            order_date=self.base_date + datetime.timedelta(days=2),
            order_timestamp=timezone.make_aware(datetime.datetime(2026, 1, 3, 11, 0)),
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("200000.00"),
        )

        # Workspace B: Order on Day 1 (should never leak to Workspace A)
        Order.objects.create(
            workspace=self.retail_ws_b,
            order_number="ORD-B-01",
            customer=self.customer_b,
            order_date=self.base_date,
            order_timestamp=timezone.make_aware(datetime.datetime(2026, 1, 1, 10, 0)),
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("999999.00"),
        )

        category_a = Category.objects.create(workspace=self.retail_ws_a, code="CAT-A", name="Category A")
        category_b = Category.objects.create(workspace=self.retail_ws_b, code="CAT-B", name="Category B")
        product_a = Product.objects.create(
            workspace=self.retail_ws_a, category=category_a, sku="SKU-A", name="Product A", unit_price=Decimal("1000.00")
        )
        product_b = Product.objects.create(
            workspace=self.retail_ws_b, category=category_b, sku="SKU-B", name="Product B", unit_price=Decimal("1000.00")
        )
        OrderItem.objects.create(
            order=Order.objects.get(order_number="ORD-A-01"), product=product_a, quantity=2,
            unit_price=Decimal("1000.00"), subtotal=Decimal("2000.00"),
        )
        OrderItem.objects.create(
            order=Order.objects.get(order_number="ORD-A-02"), product=product_a, quantity=3,
            unit_price=Decimal("1000.00"), subtotal=Decimal("3000.00"),
        )
        OrderItem.objects.create(
            order=Order.objects.get(order_number="ORD-A-03"), product=product_a, quantity=99,
            unit_price=Decimal("1000.00"), subtotal=Decimal("99000.00"),
        )
        OrderItem.objects.create(
            order=Order.objects.get(order_number="ORD-A-04"), product=product_a, quantity=4,
            unit_price=Decimal("1000.00"), subtotal=Decimal("4000.00"),
        )
        OrderItem.objects.create(
            order=Order.objects.get(order_number="ORD-B-01"), product=product_b, quantity=50,
            unit_price=Decimal("1000.00"), subtotal=Decimal("50000.00"),
        )

        # Service Workspace: Setup service request
        self.sla = SLA.objects.create(
            workspace=self.service_ws,
            name="Standard SLA",
            priority=SLAPriority.MEDIUM,
        )
        self.service = Service.objects.create(
            workspace=self.service_ws,
            code="SVC-01",
            name="Network Setup",
            base_fee=Decimal("500000.00"),
        )
        self.svc_cust = Customer.objects.create(
            workspace=self.service_ws,
            code="CUST-SVC-01",
            name="Service Corp",
        )

        # Service tickets
        # Day 1: 2 tickets
        for idx in range(2):
            sr = ServiceRequest.objects.create(
                workspace=self.service_ws,
                request_number=f"SR-01-{idx}",
                customer=self.svc_cust,
                service=self.service,
                sla=self.sla,
                title="Incident Ticket",
                description="Issue",
            )
            ServiceRequest.objects.filter(id=sr.id).update(
                created_at=timezone.make_aware(datetime.datetime(2026, 1, 1, 10 + idx, 0))
            )
        # Day 4: 1 ticket (Days 2 and 3 should have 0 tickets)
        sr4 = ServiceRequest.objects.create(
            workspace=self.service_ws,
            request_number="SR-04-01",
            customer=self.svc_cust,
            service=self.service,
            sla=self.sla,
            title="Incident Ticket Day 4",
            description="Issue",
        )
        ServiceRequest.objects.filter(id=sr4.id).update(
            created_at=timezone.make_aware(datetime.datetime(2026, 1, 4, 15, 0))
        )

    def test_retail_revenue_aggregation_and_gap_filling(self):
        """Tests that retail revenue aggregates completed orders and fills missing days with 0.0."""
        df = get_historical_timeseries(self.retail_ws_a, TargetType.RETAIL_REVENUE)

        self.assertFalse(df.empty)
        self.assertEqual(len(df), 3)  # Day 1 (Jan 1), Day 2 (Jan 2), Day 3 (Jan 3)

        # Day 1 total: 100,000 + 50,000 = 150,000
        self.assertEqual(df.loc["2026-01-01", "target"], 150000.0)
        # Day 2 (gap day filled with 0.0)
        self.assertEqual(df.loc["2026-01-02", "target"], 0.0)
        # Day 3 total: 200,000
        self.assertEqual(df.loc["2026-01-03", "target"], 200000.0)

    def test_retail_order_volume_aggregation(self):
        """Tests order volume counting non-cancelled orders and filling gaps."""
        df = get_historical_timeseries(self.retail_ws_a, TargetType.RETAIL_ORDER_VOLUME)

        self.assertEqual(len(df), 3)
        # Day 1: 2 non-cancelled orders (cancelled order excluded)
        self.assertEqual(df.loc["2026-01-01", "target"], 2.0)
        # Day 2: 0 orders
        self.assertEqual(df.loc["2026-01-02", "target"], 0.0)
        # Day 3: 1 order
        self.assertEqual(df.loc["2026-01-03", "target"], 1.0)

    def test_product_dimension_validates_workspace(self):
        product = Product.objects.get(sku="SKU-A")
        series = get_historical_timeseries(self.retail_ws_a, TargetType.RETAIL_PRODUCT_DEMAND,
                                          dimensions={"product_id": product.pk})
        self.assertEqual(float(series["target"].sum()), 9.0)
        with self.assertRaises(ValueError):
            get_historical_timeseries(self.retail_ws_b, TargetType.RETAIL_PRODUCT_DEMAND,
                                      dimensions={"product_id": product.pk})

    def test_retail_product_demand_aggregates_completed_item_quantities(self):
        df = get_historical_timeseries(self.retail_ws_a, TargetType.RETAIL_PRODUCT_DEMAND)

        self.assertEqual(len(df), 3)
        self.assertEqual(df.loc["2026-01-01", "target"], 5.0)
        self.assertEqual(df.loc["2026-01-02", "target"], 0.0)
        self.assertEqual(df.loc["2026-01-03", "target"], 4.0)

    def test_service_ticket_volume_aggregation(self):
        """Tests service request volume aggregation across continuous calendar dates."""
        df = get_historical_timeseries(self.service_ws, TargetType.SERVICE_TICKET_VOLUME)

        self.assertEqual(len(df), 4)  # Jan 1 through Jan 4
        self.assertEqual(df.loc["2026-01-01", "target"], 2.0)
        self.assertEqual(df.loc["2026-01-02", "target"], 0.0)
        self.assertEqual(df.loc["2026-01-03", "target"], 0.0)
        self.assertEqual(df.loc["2026-01-04", "target"], 1.0)

    def test_workspace_isolation_in_datasets(self):
        """Ensures data from Workspace B is strictly excluded from Workspace A."""
        df_a = get_historical_timeseries(self.retail_ws_a, TargetType.RETAIL_REVENUE)
        df_b = get_historical_timeseries(self.retail_ws_b, TargetType.RETAIL_REVENUE)

        self.assertEqual(df_a.loc["2026-01-01", "target"], 150000.0)
        self.assertEqual(df_b.loc["2026-01-01", "target"], 999999.0)
