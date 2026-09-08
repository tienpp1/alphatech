"""
Script to train XGBoost forecasting models for internal workspaces.
- abc-retail: RETAIL_REVENUE, RETAIL_ORDER_VOLUME
- xyz-service: SERVICE_TICKET_VOLUME
"""

import os
import sys
import django

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.forecasting.models import TargetType, ForecastRun
from apps.forecasting.services import execute_training_job


def main():
    print("=== TRAINING XGBOOST ENTERPRISE FORECASTING MODELS ===")
    admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
    
    # 1. Train RETAIL_REVENUE for abc-retail
    retail_ws = Workspace.objects.filter(code="abc-retail").first()
    if retail_ws:
        print(f"\n--- Training RETAIL_REVENUE for {retail_ws.name} ---")
        run1 = execute_training_job(retail_ws, TargetType.RETAIL_REVENUE, user=admin_user, is_async=False)
        print(f"Run ID: #{run1.id} | Status: {run1.status} | Rows: Train={run1.train_row_count}, Test={run1.test_row_count}")
        print(f"XGBoost Metrics: {run1.model_metrics}")
        print(f"Baseline Metrics: {run1.baseline_metrics}")
        print(f"Artifact: {run1.artifact_path}")
        print(f"14-Day Prediction horizon generated: {run1.results.count()} daily data points")

        print(f"\n--- Training RETAIL_ORDER_VOLUME for {retail_ws.name} ---")
        run2 = execute_training_job(retail_ws, TargetType.RETAIL_ORDER_VOLUME, user=admin_user, is_async=False)
        print(f"Run ID: #{run2.id} | Status: {run2.status} | Rows: Train={run2.train_row_count}, Test={run2.test_row_count}")
        print(f"XGBoost Metrics: {run2.model_metrics}")
        print(f"Artifact: {run2.artifact_path}")
        print(f"14-Day Prediction horizon generated: {run2.results.count()} daily data points")

    # 2. Train SERVICE_TICKET_VOLUME for xyz-service
    service_ws = Workspace.objects.filter(code="xyz-service").first()
    if service_ws:
        print(f"\n--- Training SERVICE_TICKET_VOLUME for {service_ws.name} ---")
        run3 = execute_training_job(service_ws, TargetType.SERVICE_TICKET_VOLUME, user=admin_user, is_async=False)
        print(f"Run ID: #{run3.id} | Status: {run3.status} | Rows: Train={run3.train_row_count}, Test={run3.test_row_count}")
        print(f"XGBoost Metrics: {run3.model_metrics}")
        print(f"Artifact: {run3.artifact_path}")
        print(f"14-Day Prediction horizon generated: {run3.results.count()} daily data points")

    print("\n=== RECENT COMPLETED FORECAST RUNS IN SYSTEM ===")
    for r in ForecastRun.objects.select_related("workspace").order_by("-id")[:6]:
        print(f"- Run #{r.id} | {r.workspace.code} | {r.target_type} | Status: {r.status} | Metrics: {r.model_metrics.get('mae')} MAE | Predictions: {r.results.count()}")


if __name__ == "__main__":
    main()
