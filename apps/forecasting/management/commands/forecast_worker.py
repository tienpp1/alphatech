"""Run a durable worker; isolate training in a bounded child process."""
import multiprocessing
import time
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from apps.forecasting.models import ForecastRun
from apps.forecasting.queue import claim_job, heartbeat, finish_failed
from apps.forecasting.training import train_forecast_model


def _execute_claimed_run(run_id, lease_token):
    """Execute one fenced run in a child process with fresh DB connections."""
    close_old_connections()
    token = uuid.UUID(str(lease_token))
    run = ForecastRun.objects.select_related("workspace", "model_config", "created_by").get(
        pk=run_id,
        lease_token=token,
    )
    try:
        train_forecast_model(
            workspace=run.workspace,
            target_type=run.target_type,
            model_config=run.model_config,
            user=run.created_by,
            run=run,
            hyperparams=run.job_parameters.get("hyperparams", {}),
            horizon_days=run.job_parameters.get("horizon_days", 14),
            lease_token=token,
        )
    except Exception as exc:
        raise RuntimeError("FORECAST_TRAINING_FAILED") from exc
    finally:
        close_old_connections()


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
            try:
                _execute_claimed_run(options["execute_run"], options["lease_token"])
            except Exception:
                raise CommandError("FORECAST_TRAINING_FAILED") from None
            return
        while True:
            run = claim_job()
            if run:
                child = None
                try:
                    close_old_connections()
                    child = multiprocessing.Process(
                        target=_execute_claimed_run,
                        args=(run.pk, str(run.lease_token)),
                        name=f"forecast-run-{run.pk}",
                    )
                    child.start()
                    deadline = time.monotonic() + options["timeout"]
                    while child.is_alive():
                        if time.monotonic() >= deadline or not heartbeat(run.pk, run.lease_token):
                            child.terminate()
                            child.join(timeout=10)
                            if child.is_alive():
                                child.kill()
                                child.join()
                            finish_failed(run.pk, run.lease_token, "WORKER_TIMEOUT_OR_CANCELLED")
                            break
                        time.sleep(5)
                    child.join()
                    if child.exitcode:
                        finish_failed(run.pk, run.lease_token, "WORKER_EXITED")
                finally:
                    if child and child.is_alive():
                        child.terminate()
                        child.join(timeout=10)
            if options["once"]:
                return
            if run is None:
                time.sleep(5)
