"""Read-only source eligibility. Readiness is neither provenance nor accuracy."""
from .models import ForecastModelConfig, Granularity
from .selectors import get_historical_timeseries


def assess_readiness(series, *, guarded=False, granularity=Granularity.DAILY):
    attrs = series.attrs
    observed = int(attrs.get('observed_period_count', 0))
    periods = len(series)
    coverage = observed / periods if periods else 0.
    minimum = 49 if guarded else 34  # 14 lag rows plus at least 20 usable rows.
    reasons = []
    latest = series.index[-1].date().isoformat() if periods else None
    if latest != attrs.get('closed_period_end'):
        reasons.append('STALE_OR_MISSING_CLOSED_PERIOD')
    if observed < minimum:
        reasons.append('INSUFFICIENT_OBSERVED_PERIODS')
    if coverage < .8 or attrs.get('observed_daily_coverage', 0.) < .8:
        reasons.append('LOW_OBSERVED_COVERAGE')
    observed_dates = set(attrs.get('observed_period_dates', []))
    recent = series.index[-14:]
    recent_observed = sum(day.date().isoformat() in observed_dates for day in recent)
    if len(recent) < 14 or recent_observed < 14:
        reasons.append('INSUFFICIENT_RECENT_OBSERVATIONS')
    return {
        **{key: attrs.get(key) for key in (
            'as_of', 'closed_period_end', 'source_period_start', 'source_period_end',
            'observed_daily_coverage', 'open_day_observation_count',
            'future_day_observation_count', 'excluded_open_or_future_day_count')},
        'data_mode': 'operational', 'granularity': granularity,
        'ready': not reasons, 'reasons': reasons,
        'period_count': periods, 'observed_period_count': observed,
        'imputed_period_count': periods - observed, 'observed_period_coverage': coverage,
        'recent_observed_period_count': recent_observed,
        'commercial_provenance': 'UNKNOWN', 'completeness_attested': False,
        'operationally_validated': False,
        'policy': {'version': 'closed_observed_v1', 'minimum_observed_periods': minimum,
                   'minimum_observed_coverage': .8, 'recent_required_observed_periods': 14,
                   'latest_period_must_equal_closed_end': True},
        'message': ('Dữ liệu đủ điều kiện kỹ thuật; chưa xác minh nguồn thương mại hoặc chất lượng tương lai.'
                    if not reasons else 'Chưa đủ dữ liệu kỳ đã đóng, mới và có quan sát để dự báo vận hành. Có thể chọn đánh giá lịch sử.'),
    }


def get_forecast_readiness(workspace, target_type, dimensions=None, model_config=None):
    from .training import validate_target_for_workspace
    validate_target_for_workspace(workspace, target_type)
    configs = ForecastModelConfig.objects.for_workspace(workspace).filter(target_type=target_type)
    config = model_config or configs.filter(is_active=True).order_by('-model_version', '-updated_at', '-pk').first()
    granularity = config.granularity if config else Granularity.DAILY
    series = get_historical_timeseries(workspace, target_type, granularity=granularity,
                                      dimensions=dimensions, data_mode='operational', closed_periods=True)
    result = assess_readiness(series, guarded=bool(config and (config.training_config or {}).get('strategy') == 'guarded_direct_v1'),
                              granularity=granularity)
    result['model_config_id'] = config.pk if config else None
    if config is None and configs.exists():
        result['reasons'].append('NO_ACTIVE_CONFIGURATION')
        result['ready'] = False
    return result
