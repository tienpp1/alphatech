import datetime
from django.test import TestCase
from django.utils import timezone
from apps.accounts.models import User
from apps.workspaces.models import Workspace
from apps.forecasting.services import execute_training_job
from apps.forecasting.models import ForecastRun, TargetType, RunStatus
from apps.forecasting.queue import claim_job, heartbeat, finish_failed, cancel_run
from apps.forecasting.training import train_forecast_model


class ForecastQueueTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code="queue-retail", name="Queue", workspace_type="RETAIL")
        self.user = User.objects.create_superuser(username="queue-admin", email="queue@example.com", password="test")

    def enqueue(self):
        return execute_training_job(self.ws, TargetType.RETAIL_REVENUE, user=self.user, is_async=True)

    def test_job_persists_until_worker_claims_it(self):
        pending = self.enqueue()
        self.assertEqual(pending.status, RunStatus.PENDING)
        claimed = claim_job()
        self.assertEqual(claimed.pk, pending.pk)
        self.assertEqual(claimed.attempt_count, 1)
        self.assertIsNone(claim_job())
        self.assertTrue(heartbeat(claimed.pk, claimed.lease_token))

    def test_expired_worker_is_fenced_from_recovered_job(self):
        self.enqueue()
        old = claim_job()
        ForecastRun.objects.filter(pk=old.pk).update(lease_expires_at=timezone.now()-datetime.timedelta(seconds=1))
        new = claim_job()
        self.assertEqual(old.pk, new.pk)
        self.assertNotEqual(old.lease_token, new.lease_token)
        self.assertFalse(heartbeat(old.pk, old.lease_token))
        finish_failed(old.pk, old.lease_token, "STALE_WORKER")
        with self.assertRaisesMessage(ValueError, "FORECAST_LEASE_LOST"):
            train_forecast_model(self.ws, TargetType.RETAIL_REVENUE, run=old, lease_token=old.lease_token)
        new.refresh_from_db()
        self.assertEqual(new.status, RunStatus.RUNNING)

    def test_retry_is_bounded(self):
        self.enqueue()
        for attempt in range(3):
            run = claim_job()
            self.assertEqual(run.attempt_count, attempt+1)
            finish_failed(run.pk, run.lease_token, "TEST_FAILURE")
        self.assertIsNone(claim_job())
        self.assertEqual(ForecastRun.objects.get().status, RunStatus.FAILED)

    def test_cancel_revokes_running_worker(self):
        self.enqueue()
        run = claim_job()
        cancel_run(workspace=self.ws, user=self.user, run_id=run.pk)
        self.assertFalse(heartbeat(run.pk, run.lease_token))
        self.assertIsNone(claim_job())
        self.assertEqual(ForecastRun.objects.get().status, RunStatus.CANCELLED)
