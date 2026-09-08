"""
Tests for Forecasting REST API Endpoints.
Verifies model configs CRUD, runs retrieval, training invocation, results, and chart payloads.
"""

from decimal import Decimal
import datetime
from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.accounts.models import Role, Permission
from apps.retail.models import Order, OrderStatus, Customer
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    ForecastResult,
    TargetType,
    ModelType,
    RunStatus,
)
from apps.forecasting.training import train_forecast_model
from apps.forecasting.services import execute_training_job
from apps.forecasting.queue import claim_job

User = get_user_model()


class ForecastingAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.workspace = Workspace.objects.create(
            name="API Test Retail",
            code="api-retail",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.perm_view, _ = Permission.objects.get_or_create(
            codename="forecasting.view_forecast",
            defaults={"name": "View Forecast", "module": "forecasting"},
        )
        self.perm_manage, _ = Permission.objects.get_or_create(
            codename="forecasting.manage_forecast",
            defaults={"name": "Manage Forecast", "module": "forecasting"},
        )

        self.role_admin = Role.objects.create(name="ADMIN")
        self.role_admin.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(
            username="api_admin",
            email="admin@api.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.workspace,
            user=self.user,
            role=self.role_admin,
            is_default=True,
        )

        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-API-01",
            name="API Customer",
        )

        # Seed 30 orders
        start_date = datetime.date(2026, 1, 1)
        for d in range(30):
            cur_date = start_date + datetime.timedelta(days=d)
            Order.objects.create(
                workspace=self.workspace,
                order_number=f"ORD-API-{d:03d}",
                customer=self.customer,
                order_date=cur_date,
                order_timestamp=timezone.make_aware(datetime.datetime(cur_date.year, cur_date.month, cur_date.day, 12, 0)),
                status=OrderStatus.COMPLETED,
                total_amount=Decimal("120000.00"),
            )

        self.client.force_authenticate(user=self.user)
        self.auth_headers = {"HTTP_X_WORKSPACE": "api-retail"}

    def test_model_configs_crud(self):
        """Tests creating, listing, retrieving, updating, and deleting model configs."""
        # Create
        payload = {
            "name": "New Revenue Forecaster",
            "target_type": TargetType.RETAIL_REVENUE,
            "model_type": ModelType.XGBOOST_REGRESSOR,
            "training_config": {"n_estimators": 80, "max_depth": 3},
        }
        res = self.client.post("/api/v1/forecasting/models/", data=payload, format="json", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["success"])
        config_id = res.data["data"]["id"]

        # List
        res = self.client.get("/api/v1/forecasting/models/", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data["data"]), 1)

        # Retrieve
        res = self.client.get(f"/api/v1/forecasting/models/{config_id}/", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["name"], "New Revenue Forecaster")

        # Update
        res = self.client.patch(f"/api/v1/forecasting/models/{config_id}/", data={"name": "Updated Forecaster"}, format="json", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["name"], "Updated Forecaster")

        # Delete
        res = self.client.delete(f"/api/v1/forecasting/models/{config_id}/", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(ForecastModelConfig.objects.filter(id=config_id).exists())

    def test_train_api_synchronous(self):
        """Tests triggering model training via POST /api/v1/forecasting/train/."""
        payload = {
            "target_type": TargetType.RETAIL_REVENUE,
            "n_estimators": 50,
            "max_depth": 3,
            "is_async": False,
            "horizon_days": 7,
        }
        res = self.client.post("/api/v1/forecasting/train/", data=payload, format="json", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])
        run_data = res.data["data"]
        self.assertEqual(run_data["status"], RunStatus.COMPLETED)
        self.assertIn("mae", run_data["model_metrics"])

    def test_async_training_reuses_the_pending_run(self):
        pending_run = execute_training_job(
            workspace=self.workspace, target_type=TargetType.RETAIL_REVENUE,
            user=self.user, is_async=True,
        )

        self.assertEqual(pending_run.status, RunStatus.PENDING)
        self.assertEqual(ForecastRun.objects.filter(pk=pending_run.pk).count(), 1)
        claimed = claim_job()
        self.assertEqual(claimed.pk, pending_run.pk)
        train_forecast_model(workspace=self.workspace, target_type=TargetType.RETAIL_REVENUE,
                             run=claimed, lease_token=claimed.lease_token, horizon_days=14)

        pending_run.refresh_from_db()
        self.assertEqual(pending_run.status, RunStatus.COMPLETED)
        self.assertEqual(ForecastRun.objects.filter(workspace=self.workspace).count(), 1)
        self.assertEqual(pending_run.results.count(), 14)

    def test_runs_and_results_apis(self):
        """Tests querying training runs and forecast results via API."""
        run = train_forecast_model(
            workspace=self.workspace,
            target_type=TargetType.RETAIL_REVENUE,
            horizon_days=7,
        )

        # Runs list
        res = self.client.get("/api/v1/forecasting/runs/", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data["data"]), 1)

        # Run detail
        res = self.client.get(f"/api/v1/forecasting/runs/{run.id}/", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["data"]["id"], run.id)

        # Results list
        res = self.client.get(f"/api/v1/forecasting/results/?run_id={run.id}", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["data"]), 7)

    def test_chart_data_api(self):
        """Tests GET /api/v1/forecasting/chart-data/ payload."""
        train_forecast_model(
            workspace=self.workspace,
            target_type=TargetType.RETAIL_REVENUE,
            horizon_days=7,
        )

        res = self.client.get("/api/v1/forecasting/chart-data/?target_type=RETAIL_REVENUE", **self.auth_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["success"])

        data = res.data["data"]
        self.assertEqual(data["workspace_code"], "api-retail")
        self.assertEqual(data["target_type"], TargetType.RETAIL_REVENUE)
        self.assertGreater(len(data["historical"]), 0)
        self.assertEqual(len(data["forecast"]), 7)
        self.assertIn("mae", data["metrics"])
        self.assertIn("naive_mae", data["baseline_metrics"])
        self.assertGreater(len(data["feature_importances"]), 0)
