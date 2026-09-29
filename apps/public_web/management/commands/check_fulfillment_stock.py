"""Read-only, workspace-explicit preflight; never enables the fulfillment policy."""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.retail.models import Branch, Product, StockBalance
from apps.workspaces.models import Workspace, WorkspaceType


class Command(BaseCommand):
    help = 'Kiểm tra dữ liệu kho giao hàng; không sửa dữ liệu hay bật strict.'

    def add_arguments(self, parser):
        parser.add_argument('--workspace', required=True, help='Workspace code, not a default database fallback.')

    def handle(self, *args, **options):
        workspace = Workspace.objects.filter(code=options['workspace'], is_active=True,
                                             workspace_type=WorkspaceType.RETAIL).first()
        if workspace is None:
            raise CommandError('Active retail workspace not found.')
        codes = list(dict.fromkeys([settings.HOME_DELIVERY_DEFAULT_BRANCH_CODE,
                                  *settings.HOME_DELIVERY_FALLBACK_BRANCH_CODES]))
        products = list(Product.objects.filter(workspace=workspace, is_active=True,
                                               deleted_at__isnull=True).values_list('pk', flat=True))
        branches = {b.code: b for b in Branch.objects.filter(workspace=workspace, code__in=codes, is_active=True)}
        report = {'workspace': workspace.code, 'policy': settings.HOME_DELIVERY_FULFILLMENT_POLICY,
                  'active_products': len(products), 'branches': [],
                  'scope': 'Current database snapshot only; not physical inventory, cart availability or production certification.'}
        for code in codes:
            branch = branches.get(code)
            quantities = list(StockBalance.objects.filter(workspace=workspace, branch=branch,
                              product_id__in=products).values_list('quantity_on_hand', flat=True)) if branch else []
            report['branches'].append({'code': code, 'active_branch_found': branch is not None,
                'rows': len(quantities), 'missing_pairs': len(products)-len(quantities),
                'zero_stock': sum(q == 0 for q in quantities), 'negative_stock': sum(q < 0 for q in quantities)})
        report['data_complete'] = bool(products) and all(
            b['active_branch_found'] and not b['missing_pairs'] and not b['negative_stock'] for b in report['branches'])
        self.stdout.write(json.dumps(report, ensure_ascii=False))
