"""
Data selectors and aggregators for historical time-series datasets.
Enforces strict workspace scoping and produces continuous, gapless pandas series.
"""

from decimal import Decimal
from typing import Optional
import datetime
import pandas as pd
from django.db.models import Sum, Count, Min, Max
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.workspaces.models import Workspace
from apps.retail.models import Order, OrderItem, OrderStatus, Product, Category, Branch
from apps.service_ops.models import ServiceRequest
from apps.forecasting.models import TargetType, Granularity


def get_historical_timeseries(
    workspace: Workspace,
    target_type: str,
    granularity: str = Granularity.DAILY,
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    dimensions: Optional[dict] = None,
    data_mode: str = "historical",
    as_of: Optional[datetime.date] = None,
    closed_periods: bool = False,
) -> pd.DataFrame:
    """
    Extracts canonical business records for the given workspace and target type,
    aggregates them chronologically, and reindexes across a gapless date range.

    Returns DataFrame with DatetimeIndex and a single float column 'target'.
    """
    if data_mode not in ("historical", "operational"):
        raise ValueError("Unsupported forecast data_mode.")
    as_of = as_of or timezone.localdate()
    closed_periods = closed_periods or data_mode == "operational"
    closed_end = as_of - datetime.timedelta(days=1)
    if granularity == Granularity.WEEKLY:
        closed_end -= datetime.timedelta(days=closed_end.weekday())
    dimensions = dimensions or {}
    if dimensions and target_type != TargetType.RETAIL_PRODUCT_DEMAND:
        raise ValueError("Product dimensions require RETAIL_PRODUCT_DEMAND.")
    for key, model in (("product_id", Product), ("category_id", Category), ("branch_id", Branch)):
        if key in dimensions and not model.objects.filter(pk=dimensions[key], workspace=workspace).exists():
            raise ValueError("Invalid forecast dimension for this workspace.")
    if set(dimensions) - {"product_id", "category_id", "branch_id"}:
        raise ValueError("Unsupported forecast dimension.")
    if target_type == TargetType.RETAIL_REVENUE:
        # Completed retail orders, sum total_amount
        qs = (
            Order.objects.for_workspace(workspace)
            .filter(status=OrderStatus.COMPLETED)
        )
        if start_date:
            qs = qs.filter(order_date__gte=start_date)
        if end_date:
            qs = qs.filter(order_date__lte=end_date)

        records = (
            qs.values("order_date")
            .annotate(total=Sum("total_amount"))
            .order_by("order_date")
        )
        data = {
            r["order_date"]: float(r["total"] or 0.0)
            for r in records
        }

    elif target_type == TargetType.RETAIL_ORDER_VOLUME:
        # All valid retail orders (excluding cancelled), count orders
        qs = (
            Order.objects.for_workspace(workspace)
            .exclude(status=OrderStatus.CANCELLED)
        )
        if start_date:
            qs = qs.filter(order_date__gte=start_date)
        if end_date:
            qs = qs.filter(order_date__lte=end_date)

        records = (
            qs.values("order_date")
            .annotate(total=Count("id"))
            .order_by("order_date")
        )
        data = {
            r["order_date"]: float(r["total"] or 0.0)
            for r in records
        }

    elif target_type == TargetType.RETAIL_PRODUCT_DEMAND:
        qs = OrderItem.objects.filter(
            order__workspace=workspace,
            product__workspace=workspace,
            order__status=OrderStatus.COMPLETED,
        )
        if "product_id" in dimensions:
            qs = qs.filter(product_id=dimensions["product_id"])
        if "category_id" in dimensions:
            qs = qs.filter(product__category_id=dimensions["category_id"], product__category__workspace=workspace)
        if "branch_id" in dimensions:
            qs = qs.filter(order__branch_id=dimensions["branch_id"], order__branch__workspace=workspace)
        if start_date:
            qs = qs.filter(order__order_date__gte=start_date)
        if end_date:
            qs = qs.filter(order__order_date__lte=end_date)

        records = (
            qs.values("order__order_date")
            .annotate(total=Sum("quantity"))
            .order_by("order__order_date")
        )
        data = {
            record["order__order_date"]: float(record["total"] or 0.0)
            for record in records
        }

    elif target_type == TargetType.SERVICE_TICKET_VOLUME:
        # Service requests grouped by date of creation
        qs = ServiceRequest.objects.for_workspace(workspace)
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        records = (
            qs.annotate(ticket_date=TruncDate("created_at"))
            .values("ticket_date")
            .annotate(total=Count("id"))
            .order_by("ticket_date")
        )
        data = {
            r["ticket_date"]: float(r["total"] or 0.0)
            for r in records
        }
    else:
        raise ValueError(f"Unsupported target_type '{target_type}'. Must be one of {[t.value for t in TargetType]}.")

    open_count = sum(day == as_of for day in data)
    future_count = sum(day > as_of for day in data)
    excluded_count = sum(day > closed_end for day in data) if closed_periods else 0
    if closed_periods:
        data = {day: value for day, value in data.items() if day <= closed_end}
    source_start, source_end = (min(data), max(data)) if data else (None, None)
    daily_span = (source_end - source_start).days + 1 if data else 0
    source_metadata = {
        "data_mode": data_mode,
        "as_of": as_of.isoformat(),
        "closed_periods": closed_periods,
        "closed_period_end": closed_end.isoformat(),
        "source_period_start": source_start.isoformat() if source_start else None,
        "source_period_end": source_end.isoformat() if source_end else None,
        "open_day_observation_count": open_count,
        "future_day_observation_count": future_count,
        "excluded_open_or_future_day_count": excluded_count,
        "observed_daily_coverage": len(data) / daily_span if daily_span else 0.,
        "commercial_provenance": "UNKNOWN",
        "completeness_attested": False,
        # Keep daily source presence even when weekly totals have the same value
        # and the same observed-bin labels after a zero-valued source deletion.
        "source_observed_dates": [day.isoformat() for day in sorted(data)],
    }
    if not data:
        # Return empty DataFrame with appropriate structure
        empty = pd.DataFrame(columns=["target"], index=pd.DatetimeIndex([], name="date"))
        empty.attrs.update(
            {
                "source_observation_count": 0,
                "missing_period_count": 0,
                "missing_period_policy": "zero_fill_daily_gap",
                "source_frequency": granularity,
                "observed_period_dates": [],
                "observed_period_count": 0,
                "imputed_period_count": 0,
                **source_metadata,
            }
        )
        return empty

    # Determine span
    min_d = min(data.keys())
    max_d = max(data.keys())

    # Build continuous daily DatetimeIndex
    full_idx = pd.date_range(start=min_d, end=max_d, freq="D", name="date")
    series_data = [data.get(d.date(), 0.0) for d in full_idx]
    missing_period_count = len(full_idx) - len(data)

    df = pd.DataFrame({"target": series_data}, index=full_idx)

    observed = pd.Series(1, index=pd.DatetimeIndex(sorted(data)), dtype=int)
    if granularity == Granularity.WEEKLY:
        # Resample to Monday-based weekly totals
        df = df.resample("W-MON").sum()
        observed = observed.resample("W-MON").sum()
        observed = observed[observed > 0]
        if closed_periods:
            # W-MON bins cover Tuesday through Monday. Calendar closure alone
            # cannot make an unknown leading/trailing partial source week full.
            eligible = ((df.index - pd.Timedelta(days=6) >= pd.Timestamp(min_d))
                        & (df.index <= pd.Timestamp(max_d)))
            df = df.loc[eligible]
            observed = observed.loc[observed.index.intersection(df.index)]

    df.attrs.update(
        {
            "source_observation_count": len(data),
            "missing_period_count": missing_period_count,
            "missing_period_policy": "zero_fill_daily_gap",
            "source_frequency": granularity,
            # Source presence is separate from the unchanged zero-filled values.
            # Weekly source presence does not certify completeness of every day.
            "observed_period_dates": [day.date().isoformat() for day in observed.index],
            "observed_period_count": len(observed),
            "imputed_period_count": len(df) - len(observed),
            **source_metadata,
        }
    )

    return df
