import json
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.forecasting.models import ForecastRun, RunStatus
from apps.forecasting.selectors import get_historical_timeseries


class Command(BaseCommand):
    help = "Report forecast freshness and realized MAE versus holdout MAE (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **options):
        today = timezone.now().date()
        reports = []
        for run in ForecastRun.objects.filter(status=RunStatus.COMPLETED).select_related("workspace", "model_config")[:max(1, min(options["limit"], 100))]:
            series = get_historical_timeseries(run.workspace, run.target_type,
                granularity=run.model_config.granularity, dimensions=run.job_parameters.get("dimensions", {}))
            actuals = {d.date(): float(v) for d, v in zip(series.index, series["target"])}
            errors = [abs(float(result.predicted_value)-actuals[result.forecast_date])
                      for result in run.results.filter(forecast_date__lt=today)
                      if result.forecast_date in actuals]
            mae = sum(errors)/len(errors) if errors else None
            baseline = (run.model_metrics or {}).get("mae")
            reports.append(dict(run_id=run.pk, workspace_id=str(run.workspace_id),
                age_days=(today-run.created_at.date()).days, matched_actuals=len(errors),
                realized_mae=mae, holdout_mae=baseline,
                drift_warning=(mae > max(float(baseline), 1e-6)*2) if len(errors)>=7 and baseline is not None else None,
                note="Heuristic error drift; missing observations are not assumed zero."))
        self.stdout.write(json.dumps(reports))
