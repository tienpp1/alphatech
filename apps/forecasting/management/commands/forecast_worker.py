"""Run a durable worker; isolate training in a bounded child process."""
import multiprocessing
import time
import uuid

from django.core.management.base import BaseCommand, CommandError
from django.db import connections


def _execute_claimed_run(run_id, lease_token):
    """Execute one fenced run in a child process with fresh DB connections."""
    # Windows spawn / Python forkserver import this module before Django setup.
    # Model imports must happen after app initialization in the child.
    import django
    django.setup()
    from apps.forecasting.models import ForecastRun
    from apps.forecasting.training import train_forecast_model
    connections.close_all()
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
    except Exception:
        raise RuntimeError("FORECAST_TRAINING_FAILED") from None
    finally:
        connections.close_all()


def _stop_child(child):
    """Bound graceful shutdown, then reap a child that ignores terminate."""
    if child.is_alive():
        child.terminate()
        child.join(timeout=10)
        if child.is_alive():
            child.kill()
            child.join(timeout=10)


class Command(BaseCommand):
    help = "Consume persisted forecast jobs with heartbeat, timeout and restart recovery."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--timeout", type=int, default=900)
        parser.add_argument("--execute-run", type=int)
        parser.add_argument("--lease-token")

    def handle(self, *args, **options):
        from apps.forecasting.queue import claim_job, heartbeat, finish_failed
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
                    # Never inherit a live database socket when the OS uses fork.
                    connections.close_all()
                    child = multiprocessing.Process(
                        target=_execute_claimed_run,
                        args=(run.pk, str(run.lease_token)),
                        name=f"forecast-run-{run.pk}",
                    )
                    child.start()
                    deadline = time.monotonic() + options["timeout"]
                    while child.is_alive():
                        if time.monotonic() >= deadline or not heartbeat(run.pk, run.lease_token):
                            _stop_child(child)
                            finish_failed(run.pk, run.lease_token, "WORKER_TIMEOUT_OR_CANCELLED")
                            break
                        time.sleep(5)
                    # A failed OS kill must not turn a bounded job into an
                    # unbounded parent join. Stop the supervisor if unreaped;
                    # its lease can be recovered by a subsequent worker.
                    child.join(timeout=10)
                    if child.is_alive():
                        raise CommandError("WORKER_CHILD_NOT_REAPED")
                    if child.exitcode:
                        finish_failed(run.pk, run.lease_token, "WORKER_EXITED")
                except CommandError:
                    raise
                except Exception:
                    finish_failed(run.pk, run.lease_token, "WORKER_PROCESS_FAILED")
                    raise CommandError("WORKER_PROCESS_FAILED") from None
                finally:
                    if child and child.pid is not None:
                        _stop_child(child)
            if options["once"]:
                return
            if run is None:
                time.sleep(5)
