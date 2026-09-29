"""Command boundary tests; forbid real database queries and external evaluation."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class AcademicReportCommandTests(SimpleTestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        module = 'apps.forecasting.management.commands.evaluate_academic_metrics.'
        self.models = {name: self.stack.enter_context(patch(module + name)) for name in
                       ('Workspace', 'ForecastRun', 'Recommendation', 'ApprovalRequest')}
        self.workspace = SimpleNamespace(code='selected')
        self.models['Workspace'].objects.filter.return_value.first.return_value = self.workspace
        self.runs = MagicMock()
        self.models['ForecastRun'].objects.filter.return_value.select_related.return_value.order_by.return_value = self.runs
        self.runs.__iter__.return_value = iter([])
        self.models['Recommendation'].objects.filter.return_value.count.return_value = 0
        approvals = self.models['ApprovalRequest'].objects.filter.return_value
        approvals.count.return_value = 0
        approvals.values.return_value.annotate.return_value.values_list.return_value = []
        self.directory = self.stack.enter_context(TemporaryDirectory())
        self.output = Path(self.directory) / 'evidence.md'

    def run_command(self, **kwargs):
        call_command('evaluate_academic_metrics', workspace='selected', output=str(self.output), **kwargs)

    def test_requires_explicit_workspace(self):
        with self.assertRaises(CommandError):
            call_command('evaluate_academic_metrics', output=str(self.output))
        self.models['Workspace'].objects.filter.assert_not_called()

    def test_unknown_workspace_denied_without_forecast_query(self):
        self.models['Workspace'].objects.filter.return_value.first.return_value = None
        with self.assertRaises(CommandError):
            self.run_command()
        self.models['ForecastRun'].objects.filter.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_all_collections_workspace_scoped(self):
        self.run_command()
        self.models['Workspace'].objects.filter.assert_called_once_with(code='selected')
        for name in ('ForecastRun', 'Recommendation', 'ApprovalRequest'):
            self.models[name].objects.filter.assert_called_once_with(workspace=self.workspace)
        self.assertIn('CHƯA ĐO', self.output.read_text(encoding='utf-8'))

    def test_unavailable_run_id_does_not_export(self):
        self.runs.filter.return_value.values_list.return_value = [1]
        with self.assertRaisesMessage(CommandError, 'unavailable in this workspace'):
            self.run_command(run_id=[1, 2])
        self.assertFalse(self.output.exists())

    def test_existing_output_preserved(self):
        self.run_command()
        original = self.output.read_bytes()
        with self.assertRaisesMessage(CommandError, 'Output already exists'):
            self.run_command()
        self.assertEqual(self.output.read_bytes(), original)
