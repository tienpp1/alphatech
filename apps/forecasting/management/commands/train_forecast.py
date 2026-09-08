"""
Management command to train and evaluate an XGBoost forecasting model.
Usage:
  python manage.py train_forecast --workspace=abc-retail --target=RETAIL_REVENUE --horizon=14
"""

from django.core.management.base import BaseCommand, CommandError
from apps.workspaces.models import Workspace
from apps.forecasting.models import TargetType
from apps.forecasting.training import train_forecast_model
from apps.forecasting.services import get_or_create_default_config


class Command(BaseCommand):
    help = "Trains and evaluates an XGBoost time-series forecasting model for a workspace."

    def add_arguments(self, parser):
        parser.add_argument("--workspace", type=str, required=True, help="Workspace code or ID")
        parser.add_argument(
            "--target",
            type=str,
            required=True,
            choices=[t.value for t in TargetType],
            help="Forecasting target type",
        )
        parser.add_argument("--horizon", type=int, default=14, help="Forecast horizon in days")
        parser.add_argument("--estimators", type=int, default=100, help="Number of XGBoost estimators")
        parser.add_argument("--max-depth", type=int, default=4, help="Maximum tree depth")
        parser.add_argument("--learning-rate", type=float, default=0.05, help="Learning rate")

    def handle(self, *args, **options):
        ws_identifier = options["workspace"]
        target = options["target"]
        horizon = options["horizon"]

        ws = (
            Workspace.objects.filter(code=ws_identifier).first()
            or Workspace.objects.filter(id=int(ws_identifier) if ws_identifier.isdigit() else -1).first()
        )
        if not ws:
            raise CommandError(f"Workspace '{ws_identifier}' not found.")

        self.stdout.write(self.style.NOTICE(f"\n======================================================="))
        self.stdout.write(self.style.NOTICE(f"Training XGBoost Model: {target} for Workspace '{ws.name}' ({ws.code})"))
        self.stdout.write(self.style.NOTICE(f"Horizon: {horizon} days | Estimators: {options['estimators']} | Depth: {options['max_depth']} | LR: {options['learning_rate']}"))
        self.stdout.write(self.style.NOTICE(f"=======================================================\n"))

        config = get_or_create_default_config(ws, target)
        hyperparams = {
            "n_estimators": options["estimators"],
            "max_depth": options["max_depth"],
            "learning_rate": options["learning_rate"],
        }

        try:
            run = train_forecast_model(
                workspace=ws,
                target_type=target,
                model_config=config,
                hyperparams=hyperparams,
                horizon_days=horizon,
            )
            self.stdout.write(self.style.SUCCESS(f"[SUCCESS] ForecastRun #{run.id} completed!"))
            self.stdout.write(f"  - Dataset rows: {run.dataset_row_count} ({run.dataset_period_start} to {run.dataset_period_end})")
            self.stdout.write(f"  - Train rows: {run.train_row_count}, Test rows: {run.test_row_count}")
            self.stdout.write(f"  - Model Metrics: {run.model_metrics}")
            self.stdout.write(f"  - Baseline Metrics: {run.baseline_metrics}")
            self.stdout.write(f"  - Feature Importances: {run.feature_importances}")
            self.stdout.write(f"  - Artifact Saved: {run.artifact_path}")
            self.stdout.write(f"  - Future Results Created: {run.results.count()} predictions\n")
        except Exception as e:
            raise CommandError(f"Training failed: {e}")
