import os
import subprocess
import sys
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from django.core.management.base import CommandError
from apps.forecasting.management.commands.forecast_worker import Command
from apps.forecasting.management.commands.forecast_worker import _stop_child


class WorkerProcessTests(SimpleTestCase):
    def test_spawn_can_import_command_without_initialized_apps(self):
        env = dict(os.environ)
        env.pop('DJANGO_SETTINGS_MODULE', None)
        result = subprocess.run(
            [sys.executable, '-c',
             'from apps.forecasting.management.commands.forecast_worker import _execute_claimed_run; print("IMPORT_OK")'],
            env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('IMPORT_OK', result.stdout)

    def test_unresponsive_child_is_killed_and_reaped(self):
        child = Mock()
        child.is_alive.side_effect = [True, True]
        _stop_child(child)
        child.terminate.assert_called_once()
        child.kill.assert_called_once()
        self.assertEqual(child.join.call_count, 2)

    def test_finished_child_is_not_terminated(self):
        child = Mock()
        child.is_alive.return_value = False
        _stop_child(child)
        child.terminate.assert_not_called()
        child.kill.assert_not_called()

    def test_start_failure_is_sanitized_and_requeues_owned_job(self):
        run = Mock(pk=12, lease_token='lease')
        child = Mock(pid=None)
        child.start.side_effect = OSError('private process details')
        with patch('apps.forecasting.queue.claim_job', return_value=run), \
             patch('apps.forecasting.queue.finish_failed') as failed, \
             patch('multiprocessing.Process', return_value=child), \
             patch('apps.forecasting.management.commands.forecast_worker.connections.close_all'):
            with self.assertRaisesMessage(CommandError, 'WORKER_PROCESS_FAILED'):
                Command().handle(once=True, timeout=10, execute_run=None, lease_token=None)
        failed.assert_called_once_with(12, 'lease', 'WORKER_PROCESS_FAILED')
        child.join.assert_not_called()
        child.terminate.assert_not_called()

    def test_unreaped_child_never_causes_unbounded_join(self):
        run = Mock(pk=12, lease_token='lease')
        child = Mock(pid=123)
        child.is_alive.return_value = True
        with patch('apps.forecasting.queue.claim_job', return_value=run), \
             patch('apps.forecasting.queue.heartbeat', return_value=False), \
             patch('apps.forecasting.queue.finish_failed'), \
             patch('multiprocessing.Process', return_value=child), \
             patch('apps.forecasting.management.commands.forecast_worker.connections.close_all'):
            with self.assertRaisesMessage(CommandError, 'WORKER_CHILD_NOT_REAPED'):
                Command().handle(once=True, timeout=10, execute_run=None, lease_token=None)
        self.assertTrue(child.join.call_count)
        for call in child.join.call_args_list:
            self.assertEqual(call.kwargs, {'timeout': 10})
