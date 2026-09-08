"""Run a durable worker; isolate training in a bounded child process."""
import subprocess
import sys
import time
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.forecasting.models import ForecastRun
from apps.forecasting.queue import claim_job, heartbeat, finish_failed
from apps.forecasting.training import train_forecast_model


class Command(BaseCommand):
    help = "Consume persisted forecast jobs with heartbeat, timeout and restart recovery."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--timeout", type=int, default=900)
        parser.add_argument("--execute-run", type=int)
        parser.add_argument("--lease-token")

    def handle(self, *args, **options):
        if options["timeout"] < 10:
            raise CommandError("Timeout must be at least 10 seconds.")
        if options["execute_run"]:
            token = uuid.UUID(options["lease_token"])
            run = ForecastRun.objects.select_related("workspace", "model_config", "created_by").get(
                pk=options["execute_run"], lease_token=token,
            )
            try:
                train_forecast_model(workspace=run.workspace, target_type=run.target_type,
                    model_config=run.model_config, user=run.created_by, run=run,
                    hyperparams=run.job_parameters.get("hyperparams", {}),
                    horizon_days=run.job_parameters.get("horizon_days", 14), lease_token=token)
            except Exception:
                raise CommandError("FORECAST_TRAINING_FAILED") from None
            return
        while True:
            run = claim_job()
            if run:
                child = None
                try:
                    child = subprocess.Popen(
                        [sys.executable, str(settings.BASE_DIR / "manage.py"), "forecast_worker",
                         "--execute-run", str(run.pk), "--lease-token", str(run.lease_token)],
                        cwd=settings.BASE_DIR,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                    )
                    deadline = time.monotonic() + options["timeout"]
                    while child.poll() is None:
                        if time.monotonic() >= deadline or not heartbeat(run.pk, run.lease_token):
                            child.terminate()
                            try:
                                child.wait(timeout=10)
                            except subprocess.TimeoutExpired:
                                child.kill()
                                child.wait()
                            finish_failed(run.pk, run.lease_token, "WORKER_TIMEOUT_OR_CANCELLED")
                            break
                        time.sleep(5)
                    if child.returncode:
                        finish_failed(run.pk, run.lease_token, "WORKER_EXITED")
                finally:
                    if child and child.poll() is None:
                        child.terminate()
                        child.wait(timeout=10)
            if options["once"]:
                return
            if run is None:
                time.sleep(5)
