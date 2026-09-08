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
) -> pd.DataFrame:
    """
    Extracts canonical business records for the given workspace and target type,
    aggregates them chronologically, and reindexes across a gapless date range.

    Returns DataFrame with DatetimeIndex and a single float column 'target'.
    """
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

    if not data:
        # Return empty DataFrame with appropriate structure
        return pd.DataFrame(columns=["target"], index=pd.DatetimeIndex([], name="date"))

    # Determine span
    min_d = min(data.keys())
    max_d = max(data.keys())

    # Build continuous daily DatetimeIndex
    full_idx = pd.date_range(start=min_d, end=max_d, freq="D", name="date")
    series_data = [data.get(d.date(), 0.0) for d in full_idx]

    df = pd.DataFrame({"target": series_data}, index=full_idx)

    if granularity == Granularity.WEEKLY:
        # Resample to Monday-based weekly totals
        df = df.resample("W-MON").sum()

    return df
