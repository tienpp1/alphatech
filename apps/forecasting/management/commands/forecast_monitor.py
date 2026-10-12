import json
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.forecasting.models import ForecastRun, RunStatus
from apps.forecasting.selectors import get_historical_timeseries
from apps.forecasting.diagnostics import assess_snapshot, get_run_granularity
from apps.forecasting.academic_reporting import measured


def monitor_run(run, today):
    """Score available source periods, never silently score imputed daily zeros."""
    parameters = run.job_parameters if isinstance(run.job_parameters, dict) else {}
    provenance = parameters.get("provenance")
    provenance = provenance if isinstance(provenance, dict) else {}
    granularity = get_run_granularity(run)
    dimensions = provenance.get("dimensions", parameters.get("dimensions", {}))
    if not isinstance(dimensions, dict) or granularity not in ("DAILY", "WEEKLY"):
        raise ValueError("Invalid saved series context")
    series = get_historical_timeseries(
        run.workspace, run.target_type, granularity=granularity, dimensions=dimensions,
        end_date=today - datetime.timedelta(days=1),
    )
    observed = set(series.attrs.get("observed_period_dates", []))
    actuals = {day.date(): measured(value) for day, value in zip(series.index, series["target"])
               if day.date().isoformat() in observed}
    results = list(run.results.filter(workspace=run.workspace, target_type=run.target_type))
    past_results = [result for result in results if result.forecast_date < today]
    errors, invalid_points = [], 0
    for result in past_results:
        actual = actuals.get(result.forecast_date)
        if actual is None:
            continue
        predicted = measured(result.predicted_value)
        # Decimal is not a Real, unlike canonical selector float values.
        if predicted is None:
            try:
                predicted = measured(float(result.predicted_value))
            except (TypeError, ValueError, OverflowError):
                predicted = None
        if predicted is None:
            invalid_points += 1
            continue
        errors.append(abs(predicted - actual))
    mae = sum(errors) / len(errors) if errors else None
    metrics = run.model_metrics if isinstance(run.model_metrics, dict) else {}
    holdout_mae = measured(metrics.get("mae"))
    series_dates = {day.date() for day in series.index}
    imputed_points = sum(result.forecast_date in series_dates
                         and result.forecast_date.isoformat() not in observed for result in past_results)
    return dict(
        run_id=run.pk, workspace_id=str(run.workspace_id), as_of=today.isoformat(),
        age_days=(today - timezone.localtime(run.created_at).date()).days,
        series_granularity=granularity,
        granularity_source="saved_provenance" if "granularity" in provenance else "legacy_current_configuration",
        matched_actuals=len(errors), realized_mae=mae, holdout_mae=holdout_mae,
        imputed_forecast_points_excluded=imputed_points, invalid_prediction_points=invalid_points,
        source_observation_count=series.attrs.get("source_observation_count", 0),
        missing_period_policy=series.attrs.get("missing_period_policy", "unknown"),
        snapshot=assess_snapshot(run.dataset_period_end, [result.forecast_date for result in results], granularity),
        drift_warning=(mae > holdout_mae * 2)
        if len(errors) >= 7 and holdout_mae is not None and holdout_mae > 0 else None,
        note="Heuristic drift, not a quality certificate. Only source-record periods are scored; "
             "imputed daily dates and the current incomplete day are excluded. Weekly totals retain "
             "the explicit daily zero-fill policy, not verified daily completeness.",
    )


class Command(BaseCommand):
    help = "Report forecast freshness and realized MAE versus holdout MAE (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        today = timezone.localdate()
        reports = []
        for run in ForecastRun.objects.filter(status=RunStatus.COMPLETED).select_related("workspace", "model_config")[:max(1, min(options["limit"], 100))]:
            try:
                reports.append(monitor_run(run, today))
            except (ValueError, TypeError):
                # One invalid legacy snapshot must not hide other runs or leak raw errors.
                reports.append(dict(run_id=run.pk, workspace_id=str(run.workspace_id),
                                    as_of=today.isoformat(), assessment_status="UNASSESSED",
                                    error_code="INVALID_SERIES_CONTEXT", drift_warning=None))
        self.stdout.write(json.dumps(reports, allow_nan=False))
