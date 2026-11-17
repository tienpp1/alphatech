"""Read-only assessments: successful execution is not a quality certificate."""
import datetime
import math
import hashlib
from pathlib import Path
from numbers import Real

from django.utils import timezone
from django.conf import settings


def get_run_model_label(run):
    """Use stored evidence for guarded runs; preserve the historical default otherwise."""
    parameters = run.job_parameters if isinstance(run.job_parameters, dict) else {}
    provenance = parameters.get("provenance")
    provenance = provenance if isinstance(provenance, dict) else {}
    config = getattr(run, "model_config", None)
    training_config = getattr(config, "training_config", None)
    config_strategy = training_config.get("strategy") if isinstance(training_config, dict) else None
    strategy = provenance.get("strategy") or config_strategy
    if strategy != "guarded_direct_v1":
        return "XGBoost"
    effective_model = {
        "MA7": "MA7",
        "XGBOOST_DIRECT": "XGBoost Direct",
    }.get(provenance.get("effective_model"))
    if effective_model:
        return effective_model
    if getattr(run, "status", None) in ("PENDING", "RUNNING"):
        return "Đang chờ lựa chọn"
    return "Chưa xác định"


def get_guarded_holdout_evidence(provenance):
    """Return validated guarded holdout coverage for UI/API display."""
    evaluation = provenance.get("evaluation", {}) if isinstance(provenance, dict) else {}
    counts = evaluation.get("counts", {}) if isinstance(evaluation, dict) else {}
    observed = counts.get("observed_holdout") if isinstance(counts, dict) else None
    periods = counts.get("holdout") if isinstance(counts, dict) else None
    if (
        isinstance(observed, bool)
        or not isinstance(observed, int)
        or observed < 0
        or isinstance(periods, bool)
        or not isinstance(periods, int)
        or periods < 1
        or observed > periods
    ):
        return {
            "observed_holdout_count": None,
            "holdout_periods": None,
            "holdout_evidence_message": None,
        }

    message = f"Bằng chứng holdout: {observed}/{periods} kỳ có quan sát thực."
    if observed < 14:
        message += " Dưới 14 kỳ quan sát; chưa đủ căn cứ và không chứng minh chất lượng tổng quát."
    return {
        "observed_holdout_count": observed,
        "holdout_periods": periods,
        "holdout_evidence_message": message,
    }


def get_run_granularity(run):
    """Prefer the training snapshot over a subsequently edited configuration."""
    parameters = run.job_parameters if isinstance(run.job_parameters, dict) else {}
    provenance = parameters.get("provenance")
    provenance = provenance if isinstance(provenance, dict) else {}
    return provenance.get("granularity", run.model_config.granularity)


def _number(value):
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def assess_model_quality(metrics, baselines, model_label="XGBoost"):
    metrics, baselines = metrics or {}, baselines or {}
    comparisons = {}
    for metric in ("mae", "rmse"):
        candidates = {name: value for name, value in (
            ("naive", _number(baselines.get(f"naive_{metric}"))),
            ("moving_average_7", _number(baselines.get(f"moving_average_7_{metric}"))),
        ) if value is not None and value >= 0}
        best = min(candidates, key=candidates.get) if candidates else None
        model_value = _number(metrics.get(metric))
        comparisons[metric] = {
            "best_baseline": best, "baseline_value": candidates.get(best),
            "model_value": model_value,
            "beats_best_baseline": (model_value < candidates[best])
            if best and model_value is not None and model_value >= 0 else None,
        }
    r2 = _number(metrics.get("r2"))
    assessed = all(comparisons[key]["beats_best_baseline"] is not None for key in comparisons)
    negative_r2 = r2 is not None and r2 < 0
    beats_all = assessed and all(item["beats_best_baseline"] for item in comparisons.values())
    status = "UNASSESSED" if not assessed else "BASELINE_PREFERRED" if not beats_all else "LOW_R2" if negative_r2 else "BEATS_BASELINES_ON_HOLDOUT"
    return {"status": status, "comparisons": comparisons, "negative_r2": negative_r2,
            "operationally_validated": False,
            "message": "Chưa đủ số liệu đối sánh." if not assessed else
            f"Đường cơ sở tốt hơn hoặc bằng {model_label} ở ít nhất một chỉ số; cần ưu tiên đối sánh trước khi vận hành." if not beats_all else
            f"{model_label} tốt hơn các baseline có số liệu đối sánh trên MAE/RMSE của tập kiểm thử này; không bảo đảm chất lượng tương lai.",
            "r2_warning": "R² âm: mô hình chưa giải thích tốt biến thiên của tập kiểm thử." if negative_r2 else ""}


def assess_snapshot(period_end, forecast_dates=(), granularity="DAILY"):
    today = timezone.localdate()
    if not period_end:
        return {"status": "UNKNOWN", "operational": False, "message": "Chưa xác định được ngày cuối dữ liệu."}
    if isinstance(period_end, str):
        period_end = datetime.date.fromisoformat(period_end)
    lag = (today - period_end).days
    max_lag = 14 if granularity == "WEEKLY" else 7
    dates = [datetime.date.fromisoformat(day) if isinstance(day, str) else day for day in forecast_dates]
    elapsed = sum(day < today for day in dates)
    upcoming = len(dates) - elapsed
    historical = bool(dates) and not upcoming
    horizon_status = "MIXED" if elapsed and upcoming else "ELAPSED" if historical else "UPCOMING" if dates else "UNKNOWN"
    source_status = "FUTURE_DATA" if lag < 0 else "OPEN_PERIOD" if lag == 0 else "STALE" if lag > max_lag else "CURRENT_SNAPSHOT"
    status = source_status if lag <= 0 else "HISTORICAL" if historical else source_status
    operational = status == "CURRENT_SNAPSHOT"
    return {"status": status, "operational": operational, "period_end": period_end.isoformat(),
            "horizon_status": horizon_status, "elapsed_point_count": elapsed,
            "upcoming_point_count": upcoming, "operationally_validated": False,
            "source_freshness_status": source_status,
            "as_of": today.isoformat(), "age_days": lag, "max_age_days": max_lag,
            "message": "Dữ liệu có ngày trong tương lai; cần rà soát nguồn." if lag < 0 else
            "Ngày hiện tại chưa đóng; không coi quan sát đang mở là dữ liệu vận hành đầy đủ." if lag == 0 else
            "Dự báo từ snapshot lịch sử, không phải dự báo các ngày sắp tới hiện tại." if historical else
            "Dữ liệu đã cũ; chưa đủ căn cứ dùng cho vận hành hiện tại." if lag > max_lag else
            "Dữ liệu có ngày trong tương lai; cần rà soát nguồn." if lag < 0 else
            "Dữ liệu trong cửa sổ độ mới; vẫn cần đánh giá chất lượng mô hình."}


def assess_run_snapshot(run):
    """Use actual source bounds, not a future weekly bin label, for freshness."""
    if run is None:
        return assess_snapshot(None)
    parameters = run.job_parameters if isinstance(run.job_parameters, dict) else {}
    provenance = parameters.get('provenance') or {}
    dataset = provenance.get('dataset') or {}
    source_end = dataset.get('source_period_end') or run.dataset_period_end
    result = assess_snapshot(source_end,
        run.results.filter(workspace_id=run.workspace_id).values_list('forecast_date', flat=True),
        get_run_granularity(run))
    result['period_label_end'] = run.dataset_period_end.isoformat() if run.dataset_period_end else None
    return result


def assess_run_compatibility(run, current_readiness=None):
    """Keep saved results readable while detecting edited config/code/source history."""
    import pandas as pd
    from .models import ForecastModelConfig
    from .training import configuration_fingerprint, observation_evidence_fingerprint
    from .selectors import get_historical_timeseries
    parameters = run.job_parameters if isinstance(run.job_parameters, dict) else {}
    provenance = parameters.get("provenance") or {}
    dataset = provenance.get("dataset") or {}
    active = ForecastModelConfig.objects.for_workspace(run.workspace).filter(
        target_type=run.target_type, is_active=True).order_by('-model_version', '-updated_at', '-pk').first()
    reasons, unknown = [], []
    if active is None:
        reasons.append('NO_ACTIVE_CONFIGURATION')
    elif active.pk != run.model_config_id:
        reasons.append('ACTIVE_CONFIGURATION_CHANGED')
    saved_config = provenance.get('configuration_fingerprint_sha256')
    if saved_config:
        if saved_config != configuration_fingerprint(run.model_config):
            reasons.append('CONFIGURATION_CHANGED')
    else:
        unknown.append('CONFIGURATION_FINGERPRINT_UNAVAILABLE')
    for name, digest in (provenance.get('source_sha256') or {}).items():
        # Saved metadata is not an arbitrary filesystem read capability.
        if name not in {'training.py', 'selectors.py', 'features.py', 'evaluation.py',
                         'adaptive.py', 'guarded.py', 'artifacts.py', 'prediction.py', 'readiness.py'}:
            continue
        source = Path(settings.BASE_DIR) / 'apps' / 'forecasting' / name
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            reasons.append('SOURCE_CODE_CHANGED')
            break
    new_observations = None
    fingerprint = dataset.get('fingerprint_sha256')
    evidence_fingerprint = dataset.get('observation_evidence_fingerprint_sha256')
    evidence_available = bool(evidence_fingerprint and dataset.get('observation_evidence_fingerprint_version') == 1)
    if not evidence_available:
        # Old results stay readable and immutable; never infer an observation
        # mask from zero-filled values or silently backfill a saved attestation.
        unknown.append('OBSERVATION_EVIDENCE_FINGERPRINT_UNAVAILABLE')
    if fingerprint and run.dataset_period_start and run.dataset_period_end:
        try:
            current = get_historical_timeseries(run.workspace, run.target_type,
                granularity=get_run_granularity(run), dimensions=provenance.get('dimensions', parameters.get('dimensions', {})),
                data_mode=parameters.get('data_mode', 'historical'))
            new_observations = bool(not current.empty and current.index[-1].date() > run.dataset_period_end)
            # Append-only new observations do not revise the old scored history.
            bounded = get_historical_timeseries(run.workspace, run.target_type,
                granularity=get_run_granularity(run), dimensions=provenance.get('dimensions', parameters.get('dimensions', {})),
                start_date=dataset.get('source_period_start') or run.dataset_period_start,
                end_date=dataset.get('source_period_end') or run.dataset_period_end,
                data_mode=parameters.get('data_mode', 'historical'),
                as_of=datetime.date.fromisoformat(dataset['as_of']) if dataset.get('as_of') else None)
            actual = hashlib.sha256(pd.util.hash_pandas_object(bounded, index=True).values.tobytes()).hexdigest()
            if fingerprint != actual:
                reasons.append('HISTORY_CHANGED')
            if evidence_available:
                actual_evidence = observation_evidence_fingerprint(bounded,
                    workspace_id=run.workspace_id, target_type=run.target_type,
                    granularity=get_run_granularity(run),
                    dimensions=provenance.get('dimensions', parameters.get('dimensions', {})))
                if actual_evidence is None:
                    unknown.append('CURRENT_OBSERVATION_EVIDENCE_UNAVAILABLE')
                elif evidence_fingerprint != actual_evidence:
                    reasons.append('OBSERVATION_EVIDENCE_CHANGED')
        except (TypeError, ValueError):
            reasons.append('DATA_SCOPE_CHANGED')
    else:
        unknown.append('DATASET_FINGERPRINT_UNAVAILABLE')
    compatible = False if reasons else None if unknown else True
    mode = parameters.get('data_mode')
    operational_reasons = []
    if mode != 'operational':
        operational_reasons.append('HISTORICAL_MODE' if mode == 'historical' else 'LEGACY_MODE_UNKNOWN')
    if (parameters.get('readiness') or {}).get('ready') is not True:
        operational_reasons.append('SAVED_READINESS_UNAVAILABLE_OR_INELIGIBLE')
    if mode == 'operational':
        if current_readiness is None:
            from .readiness import get_forecast_readiness
            current_readiness = get_forecast_readiness(run.workspace, run.target_type,
                dimensions=provenance.get('dimensions', parameters.get('dimensions', {})))
        if not current_readiness['ready']:
            operational_reasons.append('CURRENT_DATA_NOT_READY')
    return {'compatible': compatible, 'reasons': reasons, 'unassessed': unknown,
            'active_model_config_id': active.pk if active else None,
            'new_observations_available': new_observations,
            'data_mode': mode or 'unknown', 'commercial_provenance': 'UNKNOWN',
            'operational_eligible': compatible is True and not operational_reasons,
            'operational_reasons': operational_reasons,
            'message': ('Lượt chạy lưu được giữ nguyên; cấu hình, mã nguồn hoặc dữ liệu đã thay đổi.' if reasons
                        else 'Chưa đủ metadata để xác minh tương thích lượt chạy cũ.' if unknown
                        else 'Lịch sử đã lưu tương thích; không phải chứng nhận chất lượng hay nguồn thương mại.')}
