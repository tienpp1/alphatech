"""Database-backed queue with expiring, fenced execution leases."""
import datetime
import uuid

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.accounts.services import has_workspace_permission
from .models import ForecastRun, RunStatus

MAX_ATTEMPTS = 3
LEASE_SECONDS = 60


def owned_job(run_id, token):
    return ForecastRun.objects.filter(pk=run_id, lease_token=token, status=RunStatus.RUNNING)


@transaction.atomic
def claim_job():
    now = timezone.now()
    # skip_locked allows several workers without executing the same run.
    expired = ForecastRun.objects.select_for_update(skip_locked=True).filter(
        status=RunStatus.RUNNING, lease_token__isnull=False, lease_expires_at__lt=now,
    )
    for run in expired:
        run.status = (RunStatus.CANCELLED if run.cancel_requested else
                      RunStatus.FAILED if run.attempt_count >= MAX_ATTEMPTS else RunStatus.PENDING)
        run.lease_token = None
        run.lease_expires_at = None
        run.error_message = "WORKER_LEASE_EXPIRED"
        run.save(update_fields=["status", "lease_token", "lease_expires_at", "error_message"])
    run = ForecastRun.objects.select_for_update(skip_locked=True).filter(
        status=RunStatus.PENDING, cancel_requested=False, attempt_count__lt=MAX_ATTEMPTS,
    ).order_by("created_at").first()
    if run is None:
        return None
    run.status = RunStatus.RUNNING
    run.attempt_count += 1
    run.lease_token = uuid.uuid4()
    run.heartbeat_at = now
    run.lease_expires_at = now + datetime.timedelta(seconds=LEASE_SECONDS)
    run.save(update_fields=["status", "attempt_count", "lease_token", "heartbeat_at", "lease_expires_at"])
    return run


def heartbeat(run_id, token):
    now = timezone.now()
    return owned_job(run_id, token).filter(cancel_requested=False, lease_expires_at__gt=now).update(
        heartbeat_at=now, lease_expires_at=now + datetime.timedelta(seconds=LEASE_SECONDS),
    ) == 1


def finish_failed(run_id, token, error_code):
    with transaction.atomic():
        run = owned_job(run_id, token).select_for_update().first()
        if not run:
            return
        run.status = (RunStatus.CANCELLED if run.cancel_requested else
                      RunStatus.PENDING if run.attempt_count < MAX_ATTEMPTS else RunStatus.FAILED)
        run.error_message = error_code
        run.lease_token = None
        run.lease_expires_at = None
        run.training_end_at = timezone.now()
        run.save(update_fields=["status", "error_message", "lease_token", "lease_expires_at", "training_end_at"])


def cancel_run(*, workspace, user, run_id):
    if not has_workspace_permission(user, workspace, "forecasting.manage_forecast"):
        raise PermissionDenied
    with transaction.atomic():
        run = ForecastRun.objects.select_for_update().get(pk=run_id, workspace=workspace)
        if run.status in (RunStatus.PENDING, RunStatus.RUNNING):
            run.cancel_requested = True
            run.status = RunStatus.CANCELLED
            run.lease_token = None
            run.lease_expires_at = None
            run.training_end_at = timezone.now()
            run.save(update_fields=["cancel_requested", "status", "lease_token", "lease_expires_at", "training_end_at"])
        return run
