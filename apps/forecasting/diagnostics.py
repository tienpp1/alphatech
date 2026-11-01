"""Read-only assessments: successful execution is not a quality certificate."""
import datetime
import math
from numbers import Real

from django.utils import timezone


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
    historical = any(date <= today for date in forecast_dates)
    status = "HISTORICAL" if historical else "STALE" if lag > max_lag else "FUTURE_DATA" if lag < 0 else "CURRENT_SNAPSHOT"
    operational = status == "CURRENT_SNAPSHOT"
    return {"status": status, "operational": operational, "period_end": period_end.isoformat(),
            "as_of": today.isoformat(), "age_days": lag, "max_age_days": max_lag,
            "message": "Dự báo từ snapshot lịch sử, không phải dự báo các ngày sắp tới hiện tại." if historical else
            "Dữ liệu đã cũ; chưa đủ căn cứ dùng cho vận hành hiện tại." if lag > max_lag else
            "Dữ liệu có ngày trong tương lai; cần rà soát nguồn." if lag < 0 else
            "Dữ liệu trong cửa sổ độ mới; vẫn cần đánh giá chất lượng mô hình."}
