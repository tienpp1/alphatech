"""
Security & RBAC Tests for Forecasting Subsystem.
Verifies multi-tenant isolation, RBAC role restrictions, and artifact path safety.
"""

from decimal import Decimal
import datetime
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.accounts.models import Role, Permission
from apps.retail.models import Customer
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    TargetType,
    ModelType,
)
from apps.forecasting.training import train_forecast_model, validate_target_for_workspace
from apps.forecasting.prediction import load_model_artifact

User = get_user_model()


class ForecastingSecurityRBACTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Workspaces
        self.ws_retail = Workspace.objects.create(
            name="Alpha Retail",
            code="alpha-retail",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.ws_service = Workspace.objects.create(
            name="Beta Service",
            code="beta-service",
            workspace_type=WorkspaceType.SERVICE,
        )

        # Permissions
        self.perm_view, _ = Permission.objects.get_or_create(
            codename="forecasting.view_forecast",
            defaults={"name": "View Forecast", "module": "forecasting"},
        )
        self.perm_manage, _ = Permission.objects.get_or_create(
            codename="forecasting.manage_forecast",
            defaults={"name": "Manage Forecast", "module": "forecasting"},
        )

        # Roles
        self.role_admin = Role.objects.create(name="ADMIN")
        self.role_admin.permissions.add(self.perm_view, self.perm_manage)

        self.role_viewer = Role.objects.create(name="VIEWER")
        self.role_viewer.permissions.add(self.perm_view)

        # Users
        self.admin_user = User.objects.create_user(
            username="admin_user",
            email="admin@alpha.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.admin_user,
            role=self.role_admin,
            is_default=True,
        )

        self.viewer_user = User.objects.create_user(
            username="viewer_user",
            email="viewer@alpha.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.viewer_user,
            role=self.role_viewer,
            is_default=True,
        )

        self.unauth_user = User.objects.create_user(
            username="other_user",
            email="other@beta.com",
            password="Password123!",
        )
        # Unauth user only belongs to Beta Service
        WorkspaceMembership.objects.create(
            workspace=self.ws_service,
            user=self.unauth_user,
            role=self.role_admin,
            is_default=True,
        )

        # Configs
        self.config_alpha = ForecastModelConfig.objects.create(
            workspace=self.ws_retail,
            name="Alpha Revenue Forecaster",
            target_type=TargetType.RETAIL_REVENUE,
            model_type=ModelType.XGBOOST_REGRESSOR,
        )
        self.config_beta = ForecastModelConfig.objects.create(
            workspace=self.ws_service,
            name="Beta Ticket Forecaster",
            target_type=TargetType.SERVICE_TICKET_VOLUME,
            model_type=ModelType.XGBOOST_REGRESSOR,
        )

    def test_unauthenticated_api_rejection(self):
        """Unauthenticated requests are rejected with 401."""
        response = self.client.get("/api/v1/forecasting/models/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_training_requires_manage_permission(self):
        """Users with only view permissions cannot trigger model training (403 Forbidden)."""
        self.client.force_authenticate(user=self.viewer_user)
        response = self.client.post(
            "/api/v1/forecasting/train/",
            data={"target_type": TargetType.RETAIL_REVENUE},
            headers={"X-Workspace": "alpha-retail"},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("forecasting.manage_forecast", response.data["error"])

    def test_cross_workspace_isolation_on_configs(self):
        """Alpha Retail user cannot see Beta Service forecast configurations."""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            "/api/v1/forecasting/models/",
            headers={"X-Workspace": "alpha-retail"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = [c["id"] for c in response.data["data"]]
        self.assertIn(self.config_alpha.id, returned_ids)
        self.assertNotIn(self.config_beta.id, returned_ids)

    def test_incompatible_target_type_rejected(self):
        """Ensures Retail workspace cannot train Service targets and vice-versa."""
        with self.assertRaises(ValueError):
            validate_target_for_workspace(self.ws_retail, TargetType.SERVICE_TICKET_VOLUME)

        with self.assertRaises(ValueError):
            validate_target_for_workspace(self.ws_service, TargetType.RETAIL_REVENUE)

    def test_artifact_path_traversal_rejection(self):
        """Attempts to load model artifact outside trusted directory are rejected."""
        with self.assertRaises(PermissionError):
            load_model_artifact("../../windows/system32/cmd.exe")

        with self.assertRaises(PermissionError):
            load_model_artifact("../../../secrets.json")
