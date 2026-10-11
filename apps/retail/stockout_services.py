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
from django.db.models import Sum, Min, Max, Count, Q
from django.http import Http404
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
DEMAND_HISTORY_MAX_AGE_DAYS = 7


def _inventory_assessment(quantity, record_count=None, has_negative_balance=False):
    """A missing row is unknown inventory, never proof of zero on hand."""
    status = "NEGATIVE_BALANCE" if quantity < 0 or has_negative_balance else (
        "SUPPLIED_ESTIMATE" if record_count is None else
        "MISSING_BALANCE" if record_count == 0 else "RECORDED_BALANCE")
    return {
        "status": status,
        "verified_record": status == "RECORDED_BALANCE",
        "source_record_count": record_count,
        "observed_quantity": int(quantity),
        "as_of": timezone.localdate().isoformat(),
        "message": "Chưa ghi nhận tồn kho; giá trị 0 dùng trong phép tính không chứng minh đã hết hàng." if status == "MISSING_BALANCE" else
        "Có số dư tồn kho âm; cần đối soát, không dùng làm kết luận vận hành." if status == "NEGATIVE_BALANCE" else
        "Tồn kho đầu vào là giá trị giả định/chưa đối chiếu bản ghi; chỉ dùng cho kịch bản tham khảo." if status == "SUPPLIED_ESTIMATE" else
        "Theo số dư tồn kho đã lưu; không phải kết quả kiểm kê thực địa hoặc xác nhận đầy đủ mọi chi nhánh.",
    }


def _demand_assessment(method, today, first_date=None, last_date=None):
    """Provenance for a heuristic estimate, not a trained XGBoost forecast."""
    age = (today - last_date).days if last_date else None
    status = "NO_DATA" if last_date is None else "STALE_HISTORY" if age > DEMAND_HISTORY_MAX_AGE_DAYS else "CURRENT_HISTORY"
    return {
        "method": method,
        "status": status,
        "as_of": today.isoformat(),
        "first_observation_date": first_date.isoformat() if first_date else None,
        "latest_observation_date": last_date.isoformat() if last_date else None,
        "age_days": age,
        "max_age_days": DEMAND_HISTORY_MAX_AGE_DAYS,
        "operationally_validated": False,
        "message": "Chưa có giao dịch hoàn tất để ước tính nhu cầu; không thể kết luận tồn kho an toàn." if status == "NO_DATA" else
        "Ước tính từ lịch sử đã cũ; không phải dự báo XGBoost cho vận hành hiện tại." if status == "STALE_HISTORY" else
        "Ước tính heuristic từ lượng bán đã ghi nhận, không phải kết quả mô hình XGBoost đã được đánh giá.",
    }


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
    today = timezone.localdate()
    start_date = today - datetime.timedelta(days=days)

    qs = OrderItem.objects.filter(
        order__workspace=workspace,
        order__status=OrderStatus.COMPLETED,
        product_id=product_id,
        product__workspace=workspace,
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
    df.attrs["observation_dates"] = sorted(day for day, quantity in data.items() if quantity > 0)
    return df


def predict_product_daily_demand(
    workspace: Workspace,
    product: Product,
    branch: Optional[Branch] = None,
    historical_daily_data: Optional[Dict[datetime.date, float]] = None,
    assessment_out: Optional[Dict[str, Any]] = None,
) -> float:
    """
    Computes forecasted product-level daily demand using historical sales time-series.
    Employs shifted rolling means and lag features to prevent future data leakage.
    Returns expected daily units sold (float).
    """
    today = timezone.localdate()
    if historical_daily_data is not None:
        start_date = today - datetime.timedelta(days=60)
        idx = pd.date_range(start=start_date, end=today, freq="D")
        series_data = [historical_daily_data.get(d.date(), 0.0) for d in idx]
        df = pd.DataFrame({"target": series_data}, index=idx)
        observation_dates = sorted(day for day, quantity in historical_daily_data.items()
                                   if start_date <= day <= today and quantity > 0)
    else:
        branch_id = branch.id if branch else None
        df = get_product_historical_timeseries(workspace, product.id, branch_id=branch_id, days=60)
        observation_dates = df.attrs.get("observation_dates", [])

    if df.empty or df["target"].sum() == 0:
        # Fallback to general product order items if recent window is empty
        all_time_items = OrderItem.objects.filter(
            order__workspace=workspace,
            order__status=OrderStatus.COMPLETED,
            product=product,
            product__workspace=workspace,
            order__order_date__lte=today,
        )
        if branch:
            all_time_items = all_time_items.filter(order__branch=branch)

        history = all_time_items.aggregate(t=Sum("quantity"), first=Min("order__order_date"), last=Max("order__order_date"))
        total_qty = history["t"] or 0
        if assessment_out is not None:
            assessment_out.update(_demand_assessment(
                "ALL_TIME_AVERAGE_HEURISTIC" if total_qty > 0 else "NO_OBSERVATIONS",
                today, history["first"], history["last"],
            ))
        if total_qty > 0:
            if history["first"]:
                span_days = max(1, (today - history["first"]).days)
                return round(float(total_qty) / span_days, 2)
        return 0.0

    if assessment_out is not None:
        assessment_out.update(_demand_assessment("WEIGHTED_LAG_HEURISTIC", today,
                                               observation_dates[0] if observation_dates else None,
                                               observation_dates[-1] if observation_dates else None))

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
    current_stock: Optional[int] = None,
    historical_daily_data: Optional[Dict[datetime.date, float]] = None,
    inventory_assessment: Optional[Dict[str, Any]] = None,
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
    today = timezone.localdate()

    # 1. Fetch current stock balance
    if branch:
        branch_name = branch.name
        branch_code = branch.code
        if current_stock is None:
            stock_obj = StockBalance.objects.filter(
                workspace=workspace,
                branch=branch,
                product=product,
            ).first()
            current_stock = stock_obj.quantity_on_hand if stock_obj else 0
            inventory_assessment = _inventory_assessment(current_stock, 1 if stock_obj else 0)
    else:
        branch_name = "Tất cả chi nhánh"
        branch_code = "ALL"
        if current_stock is None:
            agg = StockBalance.objects.filter(
                workspace=workspace,
                product=product,
            ).aggregate(total=Sum("quantity_on_hand"), records=Count("id"),
                        negative=Count("id", filter=Q(quantity_on_hand__lt=0)))
            current_stock = agg["total"] or 0
            inventory_assessment = _inventory_assessment(current_stock, agg["records"], bool(agg["negative"]))
    if inventory_assessment is None:
        inventory_assessment = _inventory_assessment(current_stock)

    # 2. Predicted Demand
    demand_assessment = {}
    predicted_daily_demand = predict_product_daily_demand(
        workspace, product, branch, historical_daily_data=historical_daily_data,
        assessment_out=demand_assessment,
    )

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

    # Retain numerical scenario results, but never label absent/old demand as safety.
    if current_stock > 0 and demand_assessment.get("status") != "CURRENT_HISTORY":
        risk_label_vi = "Chưa đủ dữ liệu nhu cầu" if demand_assessment.get("status") == "NO_DATA" else "Ước tính từ lịch sử cũ"
        risk_badge = "badge-warning"
        risk_color = "#facc15"
    if inventory_assessment["status"] in ("MISSING_BALANCE", "NEGATIVE_BALANCE"):
        risk_label_vi = "Chưa ghi nhận tồn kho" if inventory_assessment["status"] == "MISSING_BALANCE" else "Tồn kho âm — cần đối soát"
        risk_badge = "badge-warning"
        risk_color = "#facc15"

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
        "inventory_assessment": inventory_assessment,
        "risk_level_is_operational": inventory_assessment["verified_record"] and (
            current_stock == 0 or demand_assessment.get("status") == "CURRENT_HISTORY"),
        "predicted_daily_demand": float(predicted_daily_demand),
        "demand_assessment": demand_assessment,
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
    if branch_id is not None and branch_id != "":
        branch_text = str(branch_id)
        if isinstance(branch_id, bool) or not branch_text.isascii() or not branch_text.isdigit() or len(branch_text) > 19 or not 0 < int(branch_text) <= 9223372036854775807:
            raise ValueError("Mã chi nhánh phải là số nguyên dương.")
        branch = Branch.objects.for_workspace(workspace).filter(id=int(branch_id)).first()
        if branch is None:
            raise Http404("Không tìm thấy chi nhánh trong workspace.")

    products_qs = (
        Product.objects.for_workspace(workspace)
        .filter(is_active=True)
        .select_related("category")
    )

    if category_code:
        products_qs = products_qs.filter(category__code=category_code)

    # Bulk fetch current stock balances for all active products
    if branch:
        stock_qs = StockBalance.objects.filter(workspace=workspace, branch=branch)
        stock_map = {sb.product_id: sb.quantity_on_hand for sb in stock_qs}
        inventory_map = {product_id: _inventory_assessment(quantity, 1)
                         for product_id, quantity in stock_map.items()}
    else:
        stock_agg = (
            StockBalance.objects.filter(workspace=workspace)
            .values("product_id")
            .annotate(total=Sum("quantity_on_hand"), records=Count("id"),
                      negative=Count("id", filter=Q(quantity_on_hand__lt=0)))
        )
        stock_rows = list(stock_agg)
        stock_map = {item["product_id"]: (item["total"] or 0) for item in stock_rows}
        inventory_map = {item["product_id"]: _inventory_assessment(item["total"] or 0,
                         item["records"], bool(item["negative"])) for item in stock_rows}

    # Bulk pre-aggregate daily sales for all products over the last 60 days
    today = timezone.localdate()
    start_date = today - datetime.timedelta(days=60)
    items_qs = OrderItem.objects.filter(
        order__workspace=workspace,
        order__status=OrderStatus.COMPLETED,
        product__workspace=workspace,
        order__order_date__gte=start_date,
        order__order_date__lte=today,
    )
    if branch:
        items_qs = items_qs.filter(order__branch=branch)

    daily_sales = (
        items_qs.values("product_id", "order__order_date")
        .annotate(daily_qty=Sum("quantity"))
    )
    from collections import defaultdict
    history_map = defaultdict(dict)
    for row in daily_sales:
        history_map[row["product_id"]][row["order__order_date"]] = float(row["daily_qty"] or 0)

    all_analyses: List[Dict[str, Any]] = []
    out_of_stock_count = 0
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0

    for prod in products_qs:
        c_stock = stock_map.get(prod.id, 0)
        h_data = history_map.get(prod.id, {})
        analysis = evaluate_product_stockout_risk(
            workspace,
            prod,
            branch=branch,
            current_stock=c_stock,
            historical_daily_data=h_data,
            inventory_assessment=inventory_map.get(prod.id, _inventory_assessment(c_stock, 0)),
        )
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
        "unassessed_demand_count": sum(p["demand_assessment"]["status"] != "CURRENT_HISTORY" for p in all_analyses),
        "inventory_unverified_count": sum(not p["inventory_assessment"]["verified_record"] for p in all_analyses),
        "verified_out_of_stock_count": sum(p["risk_level"] == "OUT_OF_STOCK" and p["inventory_assessment"]["verified_record"] for p in all_analyses),
        "at_risk_count": out_of_stock_count + high_risk_count + medium_risk_count,
        "products_at_risk": products_at_risk[:limit],
        "all_products": all_analyses[:limit],
    }
