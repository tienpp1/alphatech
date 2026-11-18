"""Read-only experimental XGBoost versus MA7 on scoped order history."""
import pandas as pd
from datetime import timedelta
from django.utils import timezone

from apps.forecasting import adaptive, guarded
from apps.forecasting.models import Granularity, TargetType
from apps.forecasting.selectors import get_historical_timeseries


def evaluate_revenue_xgboost(workspace):
    history = get_historical_timeseries(workspace, TargetType.RETAIL_REVENUE,
        granularity=Granularity.DAILY, data_mode="operational", closed_periods=True,
        start_date=timezone.localdate() - timedelta(days=365))
    values = adaptive.validate_history(history, Granularity.DAILY, minimum=85)
    observed = {pd.Timestamp(day).date() for day in history.attrs.get("observed_period_dates", [])}
    cutoff = len(history) - 28
    if sum(day.date() in observed for day in history.index[:cutoff]) < 20:
        raise ValueError("Không đủ kỳ có quan sát trong dữ liệu huấn luyện.")
    params = adaptive.model_params({"n_estimators": 100, "max_depth": 2, "learning_rate": 0.05})
    fitted = adaptive.fit_direct(history.iloc[:cutoff], "none", params, Granularity.DAILY)
    rows = []
    for end in (cutoff, cutoff + 14):
        dates = history.index[end:end + 14]
        prediction = adaptive.predict_direct(fitted, values[:end], history.index[end - 1], dates,
                                              Granularity.DAILY, "none")
        rows.extend(guarded._rows(values, history.index, end - 1, 14, observed, prediction))
    scored = [row for row in rows if row["observed"]]
    if not scored:
        raise ValueError("Không có quan sát thực trong 28 kỳ kiểm thử.")
    actual = [row["actual"] for row in scored]
    metrics = {name: guarded._metrics(actual, [row[field] for row in scored])
               for name, field in (("xgboost", "prediction"), ("ma7", "ma7"), ("lag7", "naive"))}
    final = adaptive.fit_direct(history, "none", params, Granularity.DAILY)
    future_dates = pd.date_range(history.index[-1] + pd.Timedelta(days=1), periods=14, freq="D")
    predictions = adaptive.predict_direct(final, values, history.index[-1], future_dates, Granularity.DAILY, "none")
    return {
        "source": "COMPLETED_ORDERS", "data_mode": "EXPERIMENTAL_NOT_OPERATIONAL",
        "start": history.index[0].date().isoformat(), "end": history.index[-1].date().isoformat(),
        "periods": len(history), "observed": len(observed), "imputed": len(history) - len(observed),
        "holdout_periods": 28, "holdout_observed": len(scored), "metrics": metrics,
        "training_end": history.index[cutoff - 1].date().isoformat(),
        "training_periods": cutoff, "holdout_start": history.index[cutoff].date().isoformat(),
        "holdout_end": history.index[-1].date().isoformat(), "holdout_rows": scored,
        "forecast": [{"date": day.date().isoformat(), "value": float(value)} for day, value in zip(future_dates, predictions)],
        "warning": "Thử nghiệm tham khảo: nguồn thương mại chưa xác minh; ngày thiếu được điền 0 chưa được xác thực; không dùng làm quyết định vận hành.",
    }
