"""Plan or append a guarded forecast release using canonical workspace data."""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from apps.audit.models import ActorType
from apps.audit.services import log_action
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    Granularity,
    ModelType,
    RunStatus,
    TargetType,
)
from apps.forecasting.selectors import get_historical_timeseries
from apps.workspaces.models import Workspace, WorkspaceType


TARGET_BY_WORKSPACE_TYPE = {
    WorkspaceType.RETAIL: TargetType.RETAIL_REVENUE,
    WorkspaceType.SERVICE: TargetType.SERVICE_TICKET_VOLUME,
}
RETAIL_TARGETS = (
    TargetType.RETAIL_REVENUE,
    TargetType.RETAIL_ORDER_VOLUME,
    TargetType.RETAIL_PRODUCT_DEMAND,
)
DEFAULT_FEATURE_CONFIG = {
    "lags": [1, 7, 14],
    "rolling_windows": [7, 14],
    "calendar_features": True,
}
DEFAULT_TRAINING_CONFIG = {
    "n_estimators": 100,
    "max_depth": 4,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "test_size": 0.20,
}


class Command(BaseCommand):
    help = "Plan or append a guarded forecast release from canonical workspace data."

    def add_arguments(self, parser):
        parser.add_argument("--release-id", required=True, type=str)
        parser.add_argument("--workspace", required=True, action="append", help="Workspace code; repeatable.")
        parser.add_argument("--apply", action="store_true", help="Append release rows; default is read-only plan.")
        parser.add_argument("--all-targets", action="store_true", help="Include all existing targets for each workspace type.")

    def handle(self, *args, **options):
        release_id = (options.get("release_id") or "").strip()
        requested_codes = options.get("workspace") or []
        if not release_id or len(release_id) > 200:
            raise CommandError("Release ID must contain 1–200 characters.")
        if not requested_codes:
            raise CommandError("At least one --workspace code is required.")
        if len(set(requested_codes)) != len(requested_codes):
            raise CommandError("Workspace codes must be unique in one release command.")

        workspaces = list(Workspace.objects.filter(code__in=requested_codes).order_by("pk"))
        found_codes = {workspace.code for workspace in workspaces}
        missing = [code for code in requested_codes if code not in found_codes]
        if missing:
            raise CommandError("Unknown workspace code(s): " + ", ".join(missing))
        inactive = [workspace.code for workspace in workspaces if not workspace.is_active]
        if inactive:
            raise CommandError("Inactive workspace scope is not publishable: " + ", ".join(inactive))
        unsupported = [workspace.code for workspace in workspaces
                       if workspace.workspace_type not in TARGET_BY_WORKSPACE_TYPE]
        if unsupported:
            raise CommandError("Workspace type has no guarded publication target: " + ", ".join(unsupported))

        if not options.get("apply"):
            rows = [
                self._plan_row(workspace, target_type, release_id)
                for workspace in workspaces
                for target_type in self._targets_for(workspace, options.get("all_targets", False))
            ]
            self.stdout.write("Guarded forecast publication plan (read-only; no fitting or writes):")
            for row in rows:
                self.stdout.write(
                    f"- {row['workspace']} / {row['target']}: {row['history_rows']} canonical rows; "
                    f"active config v{row['active_version'] or 'none'}; {row['release_status']}"
                )
            self.stdout.write("Pass --apply to append a new config, run, results, and SYSTEM_JOB audit.")
            return

        created_runs = []
        result_rows = []
        try:
            with transaction.atomic():
                locked_workspaces = list(
                    Workspace.objects.select_for_update().filter(pk__in=[ws.pk for ws in workspaces]).order_by("pk")
                )
                if len(locked_workspaces) != len(workspaces) or any(not ws.is_active for ws in locked_workspaces):
                    raise CommandError("Workspace scope changed or became inactive before publication.")

                from apps.forecasting import training

                for workspace in locked_workspaces:
                    for target_type in self._targets_for(workspace, options.get("all_targets", False)):
                        existing = self._existing_release_run(workspace, target_type, release_id)
                        if existing is not None:
                            result_rows.append((workspace.code, target_type, existing.pk, "already-published"))
                            continue

                        base_config = self._latest_active_config(workspace, target_type)
                        config = self._new_release_config(workspace, target_type, release_id, base_config)
                        run = ForecastRun.objects.create(
                            workspace=workspace,
                            model_config=config,
                            target_type=target_type,
                            status=RunStatus.PENDING,
                            created_by=None,
                            job_parameters={
                                "dimensions": {},
                                "release_id": release_id,
                                "publication": {
                                    "release_id": release_id,
                                    "target_type": target_type,
                                    "actor_type": ActorType.SYSTEM_JOB,
                                },
                            },
                        )
                        created_runs.append(run)
                        trained = training.train_forecast_model(
                            workspace=workspace,
                            target_type=target_type,
                            model_config=config,
                            user=None,
                            run=run,
                            lease_token=None,
                            dimensions={},
                            horizon_days=14,
                        )
                        if trained.status != RunStatus.COMPLETED:
                            raise RuntimeError("forecast run did not complete")

                        config.is_active = True
                        config.save(update_fields=["is_active", "updated_at"])
                        provenance = (trained.job_parameters or {}).get("provenance", {})
                        log_action(
                            workspace=workspace,
                            actor_user=None,
                            actor_type=ActorType.SYSTEM_JOB,
                            action="PUBLISH_GUARDED_FORECAST",
                            entity_type="ForecastRun",
                            entity_id=str(trained.pk),
                            changes={
                                "release_id": release_id,
                                "target_type": target_type,
                                "config_id": config.pk,
                                "config_version": config.model_version,
                                "run_id": trained.pk,
                                "status": trained.status,
                                "effective_model": provenance.get("effective_model"),
                            },
                        )
                        result_rows.append((workspace.code, target_type, trained.pk, "published"))
        except Exception as exc:
            self._remove_new_artifacts(created_runs)
            if isinstance(exc, CommandError):
                raise
            raise CommandError(
                f"Guarded forecast publication failed ({type(exc).__name__}); transaction rolled back."
            ) from None

        for workspace_code, target_type, run_id, status in result_rows:
            self.stdout.write(f"{workspace_code} / {target_type}: run #{run_id} ({status})")
        self.stdout.write(self.style.SUCCESS("Guarded forecast release applied; existing rows were retained."))

    def _existing_release_run(self, workspace, target_type, release_id):
        return ForecastRun.objects.for_workspace(workspace).filter(
            target_type=target_type,
            job_parameters__release_id=release_id,
        ).order_by("pk").first()

    def _targets_for(self, workspace, all_targets):
        if workspace.workspace_type == WorkspaceType.RETAIL and all_targets:
            return RETAIL_TARGETS
        return (TARGET_BY_WORKSPACE_TYPE[workspace.workspace_type],)

    def _latest_active_config(self, workspace, target_type):
        configs = ForecastModelConfig.objects.for_workspace(workspace).filter(target_type=target_type)
        config = configs.filter(is_active=True).order_by("-model_version", "-updated_at", "-pk").first()
        if config is None and configs.exists():
            raise CommandError(
                f"Workspace {workspace.code} has forecast configs for {target_type}, but none is active."
            )
        return config

    def _new_release_config(self, workspace, target_type, release_id, base_config):
        configs = ForecastModelConfig.objects.for_workspace(workspace).filter(target_type=target_type)
        version = (configs.aggregate(value=Max("model_version"))["value"] or 0) + 1
        feature_config = dict(base_config.feature_config or {}) if base_config else dict(DEFAULT_FEATURE_CONFIG)
        training_config = dict(base_config.training_config or {}) if base_config else dict(DEFAULT_TRAINING_CONFIG)
        training_config["strategy"] = "guarded_direct_v1"
        name_prefix = base_config.name if base_config else f"Default {target_type.replace('_', ' ').title()}"
        return ForecastModelConfig.objects.create(
            workspace=workspace,
            name=f"{name_prefix[:65]} guarded {release_id[:20]}",
            target_type=target_type,
            model_type=ModelType.XGBOOST_REGRESSOR,
            granularity=base_config.granularity if base_config else Granularity.DAILY,
            feature_config=feature_config,
            training_config=training_config,
            is_active=False,
            model_version=version,
        )

    def _plan_row(self, workspace, target_type, release_id):
        existing = self._existing_release_run(workspace, target_type, release_id)
        config = self._latest_active_config(workspace, target_type)
        granularity = config.granularity if config else Granularity.DAILY
        history = get_historical_timeseries(workspace, target_type, granularity=granularity)
        return {
            "workspace": workspace.code,
            "target": target_type,
            "history_rows": len(history),
            "active_version": config.model_version if config else None,
            "release_status": f"already-published run #{existing.pk}" if existing else "would append one run",
        }

    def _remove_new_artifacts(self, runs):
        from django.conf import settings

        base = Path(settings.BASE_DIR).resolve()
        artifact_root = Path(getattr(
            settings,
            "FORECASTING_ARTIFACTS_DIR",
            settings.BASE_DIR / "ml_models" / "forecasting",
        )).resolve()
        try:
            artifact_root.relative_to(base)
        except ValueError:
            return
        for run in runs:
            relative = getattr(run, "artifact_path", "")
            if not relative:
                continue
            path = (base / relative).resolve()
            try:
                path.relative_to(artifact_root)
            except ValueError:
                continue
            if path.name.startswith(f"run_{run.pk}_"):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
