"""
AI Stockout Risk Prediction & Product Demand Forecasting Service.
Follows deterministic mathematical formulas and time-series feature engineering.
"""

import math
import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from django.db.models import Sum, Count, Q
from django.utils import timezone

from apps.workspaces.models import Workspace
from apps.retail.models import (
    Product,
    Branch,
    Order,
    OrderItem,
    OrderStatus,
    StockBalance,
)


DEFAULT_LEAD_TIME_DAYS = 7
DEFAULT_SAFETY_BUFFER_DAYS = 3


def get_product_historical_timeseries(
    workspace: Workspace,
    product_id: int,
    branch_id: Optional[int] = None,
    days: int = 90,
) -> pd.DataFrame:
    """
    Extracts daily sales quantity for a specific product and optional branch
    over the last N days. Reindexes into a continuous date series.
    """
    today = timezone.now().date()
    start_date = today - datetime.timedelta(days=days)

    qs = OrderItem.objects.filter(
        order__workspace=workspace,
        order__status=OrderStatus.COMPLETED,
        product_id=product_id,
        order__order_date__gte=start_date,
        order__order_date__lte=today,
    )

    if branch_id:
        qs = qs.filter(order__branch_id=branch_id)

    records = (
        qs.values("order__order_date")
        .annotate(daily_qty=Sum("quantity"))
        .order_by("order__order_date")
    )

    data = {r["order__order_date"]: float(r["daily_qty"] or 0) for r in records}

    # Generate full date index
    idx = pd.date_range(start=start_date, end=today, freq="D")
    series_data = [data.get(d.date(), 0.0) for d in idx]

    df = pd.DataFrame({"target": series_data}, index=idx)
    return df


def predict_product_daily_demand(
    workspace: Workspace,
    product: Product,
    branch: Optional[Branch] = None,
) -> float:
    """
    Computes forecasted product-level daily demand using historical sales time-series.
    Employs shifted rolling means and lag features to prevent future data leakage.
    Returns expected daily units sold (float).
    """
    branch_id = branch.id if branch else None
    df = get_product_historical_timeseries(workspace, product.id, branch_id=branch_id, days=60)

    if df.empty or df["target"].sum() == 0:
        # Fallback to general product order items if recent window is empty
        all_time_items = OrderItem.objects.filter(
            order__workspace=workspace,
            order__status=OrderStatus.COMPLETED,
            product=product,
        )
        if branch:
            all_time_items = all_time_items.filter(order__branch=branch)

        total_qty = all_time_items.aggregate(t=Sum("quantity"))["t"] or 0
        if total_qty > 0:
            first_order = Order.objects.filter(
                workspace=workspace,
                status=OrderStatus.COMPLETED,
                items__product=product,
            ).order_by("order_date").first()
            if first_order:
                span_days = max(1, (timezone.now().date() - first_order.order_date).days)
                return round(float(total_qty) / span_days, 2)
        return 0.0

    target = df["target"]
    # Rolling 7-day and 14-day mean shifted by 1 to prevent leakage
    rolling_7 = target.shift(1).rolling(window=7, min_periods=1).mean().iloc[-1]
    rolling_14 = target.shift(1).rolling(window=14, min_periods=1).mean().iloc[-1]
    lag_1 = target.iloc[-2] if len(target) >= 2 else target.iloc[-1]
    lag_7 = target.iloc[-8] if len(target) >= 8 else rolling_7

    # Weighted forecast combining recent velocity and weekly seasonality
    predicted_demand = (
        0.50 * (rolling_7 if not np.isnan(rolling_7) else 0.0)
        + 0.25 * (rolling_14 if not np.isnan(rolling_14) else 0.0)
        + 0.15 * (lag_7 if not np.isnan(lag_7) else 0.0)
        + 0.10 * (lag_1 if not np.isnan(lag_1) else 0.0)
    )

    return max(0.0, round(float(predicted_demand), 2))


def evaluate_product_stockout_risk(
    workspace: Workspace,
    product: Product,
    branch: Optional[Branch] = None,
    lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
    safety_buffer_days: int = DEFAULT_SAFETY_BUFFER_DAYS,
) -> Dict[str, Any]:
    """
    Evaluates deterministic stockout risk for a given product and branch.
    
    FORMULAS:
    - current_stock = on-hand inventory quantity
    - predicted_daily_demand = predicted units per day
    - days_to_stockout = current_stock / predicted_daily_demand (safe division)
    - expected_stockout_date = today + days_to_stockout
    - Risk levels:
        * OUT_OF_STOCK: current_stock <= 0
        * HIGH: days_to_stockout < lead_time_days
        * MEDIUM: days_to_stockout <= lead_time_days + safety_buffer_days
        * LOW: days_to_stockout > lead_time_days + safety_buffer_days
    - suggested_reorder_quantity = max(0, ceil(predicted_daily_demand * (lead_time_days + safety_buffer_days) - current_stock))
    """
    today = timezone.now().date()

    # 1. Fetch current stock balance
    if branch:
        stock_obj = StockBalance.objects.filter(
            workspace=workspace,
            branch=branch,
            product=product,
        ).first()
        current_stock = stock_obj.quantity_on_hand if stock_obj else 0
        branch_name = branch.name
        branch_code = branch.code
    else:
        agg = StockBalance.objects.filter(
            workspace=workspace,
            product=product,
        ).aggregate(total=Sum("quantity_on_hand"))
        current_stock = agg["total"] or 0
        branch_name = "Tất cả chi nhánh"
        branch_code = "ALL"

    # 2. Predicted Demand
    predicted_daily_demand = predict_product_daily_demand(workspace, product, branch)

    # 3. Determine Days to Stockout & Risk Level
    if current_stock <= 0:
        risk_level = "OUT_OF_STOCK"
        risk_label_vi = "Hết hàng"
        risk_badge = "badge-danger"
        risk_color = "#ef4444"
        days_to_stockout = 0.0
        expected_stockout_date = today
    elif predicted_daily_demand <= 0.0:
        risk_level = "LOW"
        risk_label_vi = "Tồn kho an toàn"
        risk_badge = "badge-success"
        risk_color = "#22c55e"
        days_to_stockout = 999.0
        expected_stockout_date = None
    else:
        days_to_stockout = round(float(current_stock) / float(predicted_daily_demand), 1)
        expected_stockout_date = today + datetime.timedelta(days=int(days_to_stockout))

        if days_to_stockout < lead_time_days:
            risk_level = "HIGH"
            risk_label_vi = "Nguy cơ hết hàng cao"
            risk_badge = "badge-danger"
            risk_color = "#f87171"
        elif days_to_stockout <= (lead_time_days + safety_buffer_days):
            risk_level = "MEDIUM"
            risk_label_vi = "Nguy cơ hết hàng trung bình"
            risk_badge = "badge-warning"
            risk_color = "#facc15"
        else:
            risk_level = "LOW"
            risk_label_vi = "Tồn kho an toàn"
            risk_badge = "badge-success"
            risk_color = "#4ade80"

    # 4. Calculate Suggested Reorder Quantity
    target_coverage_days = lead_time_days + safety_buffer_days
    raw_reorder = (predicted_daily_demand * target_coverage_days) - float(current_stock)
    suggested_reorder_qty = max(0, math.ceil(raw_reorder))

    return {
        "product_id": product.id,
        "product_sku": product.sku,
        "product_name": product.name,
        "category_name": product.category.name if product.category else "",
        "category_code": product.category.code if product.category else "",
        "unit": product.unit,
        "unit_price": float(product.unit_price),
        "branch_id": branch.id if branch else None,
        "branch_name": branch_name,
        "branch_code": branch_code,
        "current_stock": int(current_stock),
        "predicted_daily_demand": float(predicted_daily_demand),
        "days_to_stockout": float(days_to_stockout),
        "expected_stockout_date": expected_stockout_date.strftime("%Y-%m-%d") if expected_stockout_date else "Không xác định",
        "lead_time_days": lead_time_days,
        "safety_buffer_days": safety_buffer_days,
        "suggested_reorder_quantity": int(suggested_reorder_qty),
        "risk_level": risk_level,
        "risk_label_vi": risk_label_vi,
        "risk_badge": risk_badge,
        "risk_color": risk_color,
    }


def get_stockout_risk_dashboard_data(
    workspace: Workspace,
    branch_id: Optional[int] = None,
    category_code: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Computes workspace-wide or branch-scoped stockout risk report across all active products.
    Returns KPI totals, risk counts, and sorted products at risk.
    """
    branch = None
    if branch_id:
        branch = Branch.objects.for_workspace(workspace).filter(id=branch_id).first()

    products_qs = (
        Product.objects.for_workspace(workspace)
        .filter(is_active=True)
        .select_related("category")
    )

    if category_code:
        products_qs = products_qs.filter(category__code=category_code)

    all_analyses: List[Dict[str, Any]] = []
    out_of_stock_count = 0
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0

    for prod in products_qs:
        analysis = evaluate_product_stockout_risk(workspace, prod, branch=branch)
        all_analyses.append(analysis)

        r_lvl = analysis["risk_level"]
        if r_lvl == "OUT_OF_STOCK":
            out_of_stock_count += 1
        elif r_lvl == "HIGH":
            high_risk_count += 1
        elif r_lvl == "MEDIUM":
            medium_risk_count += 1
        elif r_lvl == "LOW":
            low_risk_count += 1

    # Sort priority: OUT_OF_STOCK -> HIGH -> MEDIUM -> LOW, then ascending days_to_stockout
    risk_rank = {"OUT_OF_STOCK": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    all_analyses.sort(key=lambda x: (risk_rank.get(x["risk_level"], 9), x["days_to_stockout"]))

    # Products requiring attention (OUT_OF_STOCK, HIGH, MEDIUM)
    products_at_risk = [p for p in all_analyses if p["risk_level"] in ("OUT_OF_STOCK", "HIGH", "MEDIUM")]

    return {
        "workspace_code": workspace.code,
        "branch_name": branch.name if branch else "Tất cả chi nhánh",
        "branch_id": branch.id if branch else None,
        "total_products_tracked": len(all_analyses),
        "out_of_stock_count": out_of_stock_count,
        "high_risk_count": high_risk_count,
        "medium_risk_count": medium_risk_count,
        "low_risk_count": low_risk_count,
        "at_risk_count": out_of_stock_count + high_risk_count + medium_risk_count,
        "products_at_risk": products_at_risk[:limit],
        "all_products": all_analyses[:limit],
    }
