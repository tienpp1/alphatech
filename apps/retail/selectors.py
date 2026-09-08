"""
Retail Query Selectors & Sales Analytics Aggregations.
High-performance database aggregations for business metrics, dashboards, and reporting.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
from datetime import date, timedelta
from django.db.models import Sum, Count, Avg, F, Q, Value, DecimalField
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from apps.retail.models import Order, OrderItem, Product, Branch, Customer, OrderStatus


def get_revenue_summary(
    workspace,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    branch_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Computes headline sales metrics for the active workspace.
    Excludes CANCELLED orders from realized revenue.
    """
    qs = Order.objects.for_workspace(workspace)

    if start_date:
        qs = qs.filter(order_date__gte=start_date)
    if end_date:
        qs = qs.filter(order_date__lte=end_date)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    # Active / Valid revenue orders (excluding CANCELLED)
    valid_qs = qs.exclude(status=OrderStatus.CANCELLED)

    agg = valid_qs.aggregate(
        total_revenue=Coalesce(
            Sum("total_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        order_count=Count("id"),
        avg_order_value=Coalesce(
            Avg("total_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        total_items_sold=Coalesce(Sum("items__quantity"), Value(0)),
    )

    cancelled_count = qs.filter(status=OrderStatus.CANCELLED).count()

    return {
        "total_revenue": agg["total_revenue"],
        "order_count": agg["order_count"],
        "average_order_value": agg["avg_order_value"],
        "total_items_sold": agg["total_items_sold"],
        "cancelled_order_count": cancelled_count,
    }


def get_revenue_timeseries(
    workspace,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    interval: str = "day",
    branch_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Returns time-series revenue and volume data aggregated by day or month.
    """
    if not end_date:
        end_date = timezone.now().date()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
    qs = qs.filter(order_date__gte=start_date, order_date__lte=end_date)

    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    trunc_fn = TruncMonth("order_date") if interval == "month" else TruncDate("order_date")

    grouped = (
        qs.annotate(period=trunc_fn)
        .values("period")
        .annotate(
            revenue=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            orders=Count("id"),
            items_sold=Coalesce(Sum("items__quantity"), Value(0)),
        )
        .order_by("period")
    )

    results = []
    for entry in grouped:
        period_val = entry["period"]
        date_str = period_val.strftime("%Y-%m-%d") if isinstance(period_val, (date, timezone.datetime)) else str(period_val)
        results.append(
            {
                "date": date_str,
                "revenue": float(entry["revenue"]),
                "order_count": entry["orders"],
                "items_sold": entry["items_sold"],
            }
        )

    return results


def get_branch_revenue_breakdown(
    workspace,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Aggregates revenue and order volume by retail branch.
    """
    qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
    if start_date:
        qs = qs.filter(order_date__gte=start_date)
    if end_date:
        qs = qs.filter(order_date__lte=end_date)

    branches = Branch.objects.for_workspace(workspace).filter(is_active=True)
    results = []

    for branch in branches:
        branch_orders = qs.filter(branch=branch)
        agg = branch_orders.aggregate(
            revenue=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            orders=Count("id"),
        )
        results.append(
            {
                "branch_id": branch.id,
                "branch_code": branch.code,
                "branch_name": branch.name,
                "region": branch.region,
                "revenue": float(agg["revenue"]),
                "order_count": agg["orders"],
            }
        )

    # Sort descending by revenue
    results.sort(key=lambda x: x["revenue"], reverse=True)
    return results


def get_top_products(
    workspace,
    limit: int = 10,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Returns the top selling products ranked by revenue and units sold.
    """
    items_qs = OrderItem.objects.filter(
        order__workspace=workspace,
    ).exclude(order__status=OrderStatus.CANCELLED)

    if start_date:
        items_qs = items_qs.filter(order__order_date__gte=start_date)
    if end_date:
        items_qs = items_qs.filter(order__order_date__lte=end_date)

    top_items = (
        items_qs.values("product__id", "product__sku", "product__name", "product__category__name")
        .annotate(
            quantity_sold=Coalesce(Sum("quantity"), Value(0)),
            revenue=Coalesce(
                Sum("subtotal"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )
        .order_by("-revenue")[:limit]
    )

    results = []
    for item in top_items:
        results.append(
            {
                "product_id": item["product__id"],
                "sku": item["product__sku"],
                "name": item["product__name"],
                "category": item["product__category__name"] or "Uncategorized",
                "quantity_sold": item["quantity_sold"],
                "revenue": float(item["revenue"]),
            }
        )
    return results


def get_customer_sales_summary(workspace, customer_id: int) -> Dict[str, Any]:
    """
    Summarizes lifetime purchase history for a specific customer.
    """
    customer = Customer.objects.for_workspace(workspace).filter(id=customer_id).first()
    if not customer:
        return {}

    orders = Order.objects.for_workspace(workspace).filter(customer=customer).exclude(status=OrderStatus.CANCELLED)
    agg = orders.aggregate(
        total_spend=Coalesce(
            Sum("total_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
        total_orders=Count("id"),
        avg_order=Coalesce(
            Avg("total_amount"),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    last_order = orders.order_by("-order_timestamp").first()

    return {
        "customer_id": customer.id,
        "customer_code": customer.code,
        "customer_name": customer.name,
        "customer_segment": customer.customer_segment,
        "total_spend": float(agg["total_spend"]),
        "total_orders": agg["total_orders"],
        "average_order_value": float(agg["avg_order"]),
        "last_order_date": last_order.order_date.strftime("%Y-%m-%d") if last_order else None,
    }
