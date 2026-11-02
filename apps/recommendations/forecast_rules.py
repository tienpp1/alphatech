"""Bounded advisory rules from saved forecasts; no inference or mutation tools."""
import datetime
from decimal import Decimal, InvalidOperation
import math
import re

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.forecasting.diagnostics import get_guarded_holdout_evidence, get_run_model_label
from apps.forecasting.models import ForecastModelConfig, ForecastResult, ForecastRun
from apps.recommendations.models import Recommendation, RecommendationPriority, RecommendationType
from apps.retail.models import Order
from apps.workspaces.models import Workspace


RULE_KEY = 'forecast_revenue_decline_v1'


def _finite_amount(value):
    if isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return amount if amount.is_finite() and amount >= 0 else None


def _eligible_provenance(run, config, workspace):
    parameters = run.job_parameters
    if not isinstance(parameters, dict) or parameters.get('dimensions') != {}:
        return None
    provenance = parameters.get('provenance')
    if not isinstance(provenance, dict):
        return None
    if (provenance.get('workspace_code') != workspace.code
            or provenance.get('target_type') != 'RETAIL_REVENUE'
            or type(provenance.get('model_config_id')) is not int
            or provenance['model_config_id'] != config.pk
            or type(provenance.get('model_version')) is not int
            or provenance['model_version'] != config.model_version
            or provenance.get('granularity') != 'DAILY'
            or provenance.get('dimensions') != {}):
        return None
    dataset = provenance.get('dataset')
    if (not isinstance(dataset, dict) or run.dataset_period_end is None
            or dataset.get('period_end') != run.dataset_period_end.isoformat()
            or not isinstance(dataset.get('fingerprint_sha256'), str)
            or not re.fullmatch(r'[0-9a-f]{64}', dataset['fingerprint_sha256'])):
        return None
    evidence = get_guarded_holdout_evidence(provenance)
    observed = evidence['observed_holdout_count']
    if (observed is None or observed < 14
            or evidence['holdout_periods'] != run.test_row_count):
        return None
    strategy = provenance.get('strategy')
    if strategy == 'guarded_direct_v1':
        if (provenance.get('deployment_qualification') is not True
                or provenance.get('effective_model') not in ('MA7', 'XGBOOST_DIRECT')):
            return None
    elif (strategy is not None or not isinstance(config.training_config, dict)
          or config.training_config.get('strategy')):
        return None
    metrics = run.model_metrics
    if (not isinstance(metrics, dict)
            or any(type(metrics.get(key)) not in (int, float)
                   or not math.isfinite(metrics[key]) or metrics[key] < 0
                   for key in ('mae', 'rmse'))):
        return None
    return provenance


@transaction.atomic
def evaluate_forecast_recommendations(workspace, *, include_historical=False):
    """Compare a complete saved forecast week with seven measured source days.

    Canonical orders are read at evaluation time, not claimed to be the training
    snapshot. The first recommendation freezes those facts; repeated evaluation
    of a run never overwrites them. Workspace locking serializes this rule's
    deduplication without introducing a new schema or modifying old records.
    """
    if type(include_historical) is not bool:
        raise ValueError('include_historical must be a boolean')
    if not workspace or workspace.workspace_type != 'RETAIL' or not workspace.is_active:
        return []
    workspace = Workspace.objects.select_for_update().get(pk=workspace.pk)
    if not workspace.is_active:
        return []
    config = (ForecastModelConfig.objects.for_workspace(workspace)
              .filter(target_type='RETAIL_REVENUE', is_active=True)
              .order_by('-updated_at', '-pk').first())
    if config is None or config.model_type != 'XGBOOST_REGRESSOR':
        return []
    run = (ForecastRun.objects.for_workspace(workspace)
           .filter(model_config=config, target_type='RETAIL_REVENUE')
           .order_by('-created_at', '-pk').first())
    if run is None or run.status != 'COMPLETED':
        return []
    provenance = _eligible_provenance(run, config, workspace)
    if provenance is None:
        return []
    if Recommendation.objects.for_workspace(workspace).filter(
        supporting_data__rule_key=RULE_KEY, supporting_data__forecast_run_id=run.pk,
    ).exists():
        return []
    today = timezone.localdate()
    end = run.dataset_period_end
    if end > today:
        return []
    points = list(ForecastResult.objects.for_workspace(workspace)
                  .filter(forecast_run=run).order_by('forecast_date', 'pk')[:7])
    expected_dates = [end + datetime.timedelta(days=index) for index in range(1, 8)]
    if (len(points) != 7 or [point.forecast_date for point in points] != expected_dates
            or any(point.target_type != 'RETAIL_REVENUE' for point in points)):
        return []
    amounts = [_finite_amount(point.predicted_value) for point in points]
    if any(amount is None for amount in amounts):
        return []
    historical = (today-end).days > 7 or any(day <= today for day in expected_dates)
    if historical and not include_historical:
        return []
    start = end-datetime.timedelta(days=6)
    observed = list(Order.objects.for_workspace(workspace)
                    .filter(status='COMPLETED', order_date__gte=start, order_date__lte=end)
                    .values('order_date').annotate(total=Sum('total_amount'), count=Count('id')))
    if {row['order_date'] for row in observed} != {end-datetime.timedelta(days=i) for i in range(7)}:
        return []
    observed_amounts = [_finite_amount(row['total']) for row in observed]
    if any(amount is None for amount in observed_amounts):
        return []
    observed_total = sum(observed_amounts, Decimal(0))
    forecast_total = sum(amounts, Decimal(0))
    if observed_total <= 0 or forecast_total >= observed_total * Decimal('0.9'):
        return []
    evaluated_at = timezone.now()
    model = get_run_model_label(run)
    ratio = float((forecast_total/observed_total-1)*100)
    r2 = run.model_metrics.get('r2')
    negative_r2 = isinstance(r2, (int, float)) and not isinstance(r2, bool) and math.isfinite(r2) and r2 < 0
    warning = ' R² âm; chưa chứng minh chất lượng tổng quát.' if negative_r2 else ''
    mode = 'HISTORICAL' if historical else 'CURRENT_SNAPSHOT'
    evidence = {
        'rule_key': RULE_KEY, 'analysis_mode': mode, 'forecast_run_id': run.pk,
        'model_config_id': config.pk, 'model': model, 'target_type': run.target_type,
        'granularity': 'DAILY', 'dimensions': {}, 'period_start': start.isoformat(),
        'period_end': end.isoformat(), 'forecast_start': expected_dates[0].isoformat(),
        'forecast_end': expected_dates[-1].isoformat(),
        'forecast_result_ids': [point.pk for point in points],
        'forecast_total': float(forecast_total), 'observed_total': float(observed_total),
        'observed_days': 7, 'observed_order_count': sum(row['count'] for row in observed),
        'predicted_change_pct': ratio, 'decline_threshold_pct': 10,
        'baseline_source': 'canonical_completed_orders_at_evaluation',
        'evaluated_at': evaluated_at.isoformat(), 'negative_r2': negative_r2,
        'observed_holdout_count': get_guarded_holdout_evidence(provenance)['observed_holdout_count'],
        'dataset_fingerprint_sha256': provenance['dataset']['fingerprint_sha256'],
        'operationally_validated': False,
    }
    recommendation = Recommendation.objects.create(
        workspace=workspace, recommendation_type=RecommendationType.RETAIL_DECLINING_REVENUE,
        title=('Phân tích lịch sử — ' if historical else '') + 'Rà soát doanh thu dự báo giảm trên ngưỡng tham khảo',
        priority=RecommendationPriority.MEDIUM,
        supporting_data=evidence,
        source_references=[f'workspace:{workspace.code}', f'forecast_run:{run.pk}', f'forecast_config:{config.pk}']
                          + [f'forecast_result:{point.pk}' for point in points],
        explanation={
            'what': 'Rà soát dữ liệu và kế hoạch bán hàng; đề xuất tham khảo, không tự đổi giá hoặc đặt hàng.',
            'why': (f'{model} dự báo tổng doanh thu 7 ngày {forecast_total:,.2f} VND, '
                    f'so với {observed_total:,.2f} VND của 7 ngày có đơn COMPLETED trước đó '
                    f'({ratio:.2f}%; ngưỡng minh họa giảm trên 10%). '
                    'Số liệu đối chiếu được đọc từ giao dịch tại thời điểm đánh giá, không phải bản sao dữ liệu huấn luyện.'
                    + (' Đây là phân tích snapshot lịch sử, không phải cảnh báo vận hành hiện tại.' if historical else '')
                    + warning),
            'evidence': evidence,
            'expected_effect': 'Bổ sung căn cứ xem xét; không cam kết tăng trưởng hoặc chất lượng dự báo tương lai.',
        },
        proposed_action='', proposed_parameters={},
        expires_at=evaluated_at if historical else evaluated_at+datetime.timedelta(days=7),
    )
    return [recommendation]
