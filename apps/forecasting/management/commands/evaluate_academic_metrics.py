"""Export stored evidence without generating claims or invoking external AI."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone

from apps.approvals.models import ApprovalRequest
from apps.forecasting.academic_reporting import render_report
from apps.forecasting.models import ForecastRun
from apps.recommendations.models import Recommendation
from apps.workspaces.models import Workspace


class Command(BaseCommand):
    help = 'Export stored forecast runs and workflow counts; no AI calls or certification.'

    def add_arguments(self, parser):
        parser.add_argument('--output', default=str(Path(settings.BASE_DIR) / 'output' / 'academic_evidence.md'))
        parser.add_argument('--workspace', required=True, help='Exact workspace code; no implicit first workspace.')
        parser.add_argument('--run-id', type=int, action='append', help='Optional run IDs, repeatable; all must belong to workspace.')

    def handle(self, *args, **options):
        workspace = Workspace.objects.filter(code=options['workspace']).first()
        if workspace is None:
            raise CommandError('Unknown workspace code.')
        runs = ForecastRun.objects.filter(workspace=workspace).select_related('model_config').order_by('id')
        selected = set(options.get('run_id') or [])
        if selected:
            runs = runs.filter(pk__in=selected)
            if set(runs.values_list('pk', flat=True)) != selected:
                raise CommandError('Run selection is unavailable in this workspace.')
        rows = [{
            'id': run.pk, 'workspace': workspace.code, 'config': run.model_config_id,
            'target': run.target_type, 'status': run.status, 'train': run.train_row_count,
            'test': run.test_row_count, 'metrics': run.model_metrics or {},
            'baseline': run.baseline_metrics or {}, 'start': run.dataset_period_start,
            'end': run.dataset_period_end, 'parameters': run.job_parameters,
        } for run in runs]
        approvals = ApprovalRequest.objects.filter(workspace=workspace)
        counts = {
            'recommendations': Recommendation.objects.filter(workspace=workspace).count(),
            'approvals': approvals.count(),
            'statuses': dict(approvals.values('status').annotate(n=Count('pk')).values_list('status', 'n')),
        }
        output = Path(options['output'])
        # Preserve prior evidence and historical reports by default.
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with output.open('x', encoding='utf-8') as stream:
                stream.write(render_report(rows, counts, timezone.now().isoformat()))
        except FileExistsError as exc:
            raise CommandError('Output already exists; choose a new --output to preserve evidence.') from exc
        self.stdout.write(self.style.SUCCESS(f'Exported stored evidence: {output}; unmeasured sections remain unmeasured.'))
