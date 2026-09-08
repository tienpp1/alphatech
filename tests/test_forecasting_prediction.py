"""
Tests for Prediction Engine & Horizon Forecasting.
"""

from decimal import Decimal
import datetime
from django.test import TestCase
from django.utils import timezone

from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import Order, OrderStatus, Customer
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    ForecastResult,
    TargetType,
    RunStatus,
)
from apps.forecasting.training import train_forecast_model
from apps.forecasting.prediction import generate_future_forecast


class ForecastingPredictionTestCase(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Retail Pred WS",
            code="retail-pred-ws",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-PRED-01",
            name="Pred Customer",
        )

        start_date = datetime.date(2026, 2, 1)
        for d in range(40):
            cur_date = start_date + datetime.timedelta(days=d)
            Order.objects.create(
                workspace=self.workspace,
                order_number=f"ORD-PRED-{d:03d}",
                customer=self.customer,
                order_date=cur_date,
                order_timestamp=timezone.make_aware(datetime.datetime(cur_date.year, cur_date.month, cur_date.day, 10, 0)),
                status=OrderStatus.COMPLETED,
                total_amount=Decimal("150000.00"),
            )

        self.run = train_forecast_model(
            workspace=self.workspace,
            target_type=TargetType.RETAIL_REVENUE,
            horizon_days=7,
        )

    def test_future_forecast_generation_bounds_and_clamping(self):
        """Tests that forecast points are consecutive future dates, non-negative, with proper bounds."""
        results = generate_future_forecast(self.run, horizon_days=14)

        self.assertEqual(len(results), 14)
        self.assertEqual(self.run.results.count(), 14)

        last_observed = datetime.date(2026, 2, 1) + datetime.timedelta(days=39)

        for i, res in enumerate(results):
            expected_date = last_observed + datetime.timedelta(days=i + 1)
            self.assertEqual(res.forecast_date, expected_date)

            # Invariant: predicted_value >= 0.0
            self.assertGreaterEqual(res.predicted_value, Decimal("0.00"))

            # Invariant: lower_bound >= 0.0
            self.assertGreaterEqual(res.lower_bound, Decimal("0.00"))

            # Invariant: upper_bound >= lower_bound
            self.assertGreaterEqual(res.upper_bound, res.lower_bound)

    def test_forecast_idempotency(self):
        """Tests that re-generating predictions for the same run does not duplicate records or fail."""
        res_first = generate_future_forecast(self.run, horizon_days=7)
        self.assertEqual(len(res_first), 7)
        self.assertEqual(self.run.results.count(), 7)

        # Second invocation
        res_second = generate_future_forecast(self.run, horizon_days=10)
        self.assertEqual(len(res_second), 10)
        self.assertEqual(self.run.results.count(), 10)
