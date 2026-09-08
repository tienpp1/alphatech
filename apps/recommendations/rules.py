"""
Deterministic Business Rule Engine for Recommendations (Phase 10).
Evaluates operational thresholds, forecasts, and GIS data to produce explainable recommendations.
Does NOT use LLM or non-deterministic inference to evaluate rules.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
import datetime
from django.utils import timezone
from django.db.models import Sum, Count, Q

from apps.workspaces.models import Workspace, WorkspaceType
from apps.recommendations.models import (
    Recommendation,
    RecommendationType,
    RecommendationPriority,
    RecommendationStatus,
)
from apps.recommendations.scoring import calculate_technician_score


def evaluate_retail_recommendations(workspace: Workspace) -> List[Recommendation]:
    """
    Evaluates deterministic Retail rules for a workspace.
    """
    if workspace.workspace_type != WorkspaceType.RETAIL:
        return []

    from apps.retail.models import Order, OrderStatus, Branch
    from apps.forecasting.models import ForecastRun, ForecastResult, TargetType

    created_recs = []

    # Rule 1: Declining Branch Revenue Check (Forecast or Recent Performance)
    # Check latest forecast run for RETAIL_REVENUE
    forecast_run = (
        ForecastRun.objects.for_workspace(workspace)
        .filter(target_type=TargetType.RETAIL_REVENUE, status="COMPLETED")
        .order_by("-created_at")
        .first()
    )

    recent_7d = timezone.now() - datetime.timedelta(days=7)
    recent_orders = Order.objects.for_workspace(workspace).filter(
        created_at__gte=recent_7d
    ).exclude(status=OrderStatus.CANCELLED)

    recent_rev = float(recent_orders.aggregate(s=Sum("total_amount"))["s"] or 0.0)
    order_count = recent_orders.count()

    # If forecast indicates MAE improvement over baseline or low revenue
    if recent_rev < 100000000.0 or (forecast_run and forecast_run.model_metrics.get("mae_improvement_pct", 0) > 10.0):
        # Check if active recommendation already exists to avoid duplicates
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_DECLINING_REVENUE,
            status=RecommendationStatus.PENDING,
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.RETAIL_DECLINING_REVENUE,
                title="Đề xuất xem xét khuyến mãi cho chi nhánh doanh thu sụt giảm",
                priority=RecommendationPriority.HIGH,
                status=RecommendationStatus.PENDING,
                explanation={
                    "what": "Xem xét triển khai chương trình khuyến mãi kích cầu hoặc tối ưu kênh bán lẻ lẻ tại chi nhánh.",
                    "why": f"Tổng doanh thu 7 ngày gần nhất đạt {recent_rev:,.0f} VND, thấp hơn ngưỡng kỳ vọng 100,000,000 VND.",
                    "evidence": {
                        "recent_7d_revenue_vnd": recent_rev,
                        "recent_7d_order_count": order_count,
                        "forecast_run_id": forecast_run.id if forecast_run else None,
                        "forecast_mae_improvement_pct": forecast_run.model_metrics.get("mae_improvement_pct") if forecast_run else None,
                    },
                    "expected_effect": "Kích cầu mua sắm, khôi phục doanh thu chi nhánh và nâng cao tỷ lệ chuyển đổi đơn hàng."
                },
                supporting_data={
                    "recent_7d_revenue_vnd": recent_rev,
                    "threshold_vnd": 100000000.0,
                },
                source_references=[f"workspace:{workspace.code}"]
            )
            created_recs.append(rec)

    # Rule 2: Low Order Volume Alert
    if order_count < 10:
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME,
            status=RecommendationStatus.PENDING,
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME,
                title="Cảnh báo số lượng đơn hàng bán lẻ thấp",
                priority=RecommendationPriority.MEDIUM,
                status=RecommendationStatus.PENDING,
                explanation={
                    "what": "Rà soát hoạt động tiếp thị và tiếp cận khách hàng thân thiết.",
                    "why": f"Số lượng đơn hàng 7 ngày qua đạt {order_count} đơn, thấp hơn ngưỡng cảnh báo 10 đơn.",
                    "evidence": {
                        "order_count_7d": order_count,
                        "threshold": 10,
                    },
                    "expected_effect": "Tăng tần suất đặt hàng và số lượng giao dịch phát sinh."
                },
                supporting_data={"order_count_7d": order_count},
                source_references=[f"workspace:{workspace.code}"]
            )
            created_recs.append(rec)

    # Rule 3: High Performing Branch Best Practice Sharing
    if recent_rev >= 150000000.0:
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_HIGH_PERFORMING,
            status=RecommendationStatus.PENDING,
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.RETAIL_HIGH_PERFORMING,
                title="Đề xuất nhân rộng quy chuẩn vận hành từ chi nhánh đạt doanh số cao",
                priority=RecommendationPriority.LOW,
                status=RecommendationStatus.PENDING,
                explanation={
                    "what": "Tổng hợp quy trình bán hàng hiệu quả để chia sẻ toàn hệ thống.",
                    "why": f"Doanh thu 7 ngày gần nhất đạt mức ấn tượng {recent_rev:,.0f} VND vượt ngưỡng 150,000,000 VND.",
                    "evidence": {
                        "recent_7d_revenue_vnd": recent_rev,
                        "order_count_7d": order_count,
                    },
                    "expected_effect": "Tối ưu hóa quy trình bán hàng cho các chi nhánh khác."
                },
                supporting_data={"recent_7d_revenue_vnd": recent_rev},
                source_references=[f"workspace:{workspace.code}"]
            )
            created_recs.append(rec)

    # Rule 4: Stockout Risk Check & Reorder Recommendation
    stockout_recs = evaluate_retail_stockout_recommendations(workspace)
    created_recs.extend(stockout_recs)

    return created_recs


def evaluate_retail_stockout_recommendations(workspace: Workspace) -> List[Recommendation]:
    """
    Evaluates deterministic Stockout Risk rules for retail products.
    Generates explainable recommendations for products with HIGH or OUT_OF_STOCK risk.
    """
    if workspace.workspace_type != WorkspaceType.RETAIL:
        return []

    from apps.retail.stockout_services import get_stockout_risk_dashboard_data

    created_recs = []
    dashboard_data = get_stockout_risk_dashboard_data(workspace, limit=15)
    products_at_risk = dashboard_data.get("products_at_risk", [])

    for prod_info in products_at_risk:
        if prod_info["risk_level"] not in ("OUT_OF_STOCK", "HIGH"):
            continue

        prod_id = prod_info["product_id"]
        source_ref = f"product:{prod_id}"

        # Prevent duplicate active recommendations
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_STOCKOUT_RISK,
            status=RecommendationStatus.PENDING,
            source_references__contains=[source_ref],
        ).first()

        if existing:
            continue

        p_name = prod_info["product_name"]
        curr_stock = prod_info["current_stock"]
        pred_demand = prod_info["predicted_daily_demand"]
        days_left = prod_info["days_to_stockout"]
        lead_time = prod_info["lead_time_days"]
        suggested_qty = prod_info["suggested_reorder_quantity"]
        prio = RecommendationPriority.CRITICAL if prod_info["risk_level"] == "OUT_OF_STOCK" else RecommendationPriority.HIGH

        if prod_info["risk_level"] == "OUT_OF_STOCK":
            what_text = f"Đề xuất nhập thêm khẩn cấp sản phẩm {p_name} (đề xuất: {suggested_qty} {prod_info['unit']})."
            why_text = f"Sản phẩm hiện tại đã hết hàng (tồn kho: 0 {prod_info['unit']}) trong khi nhu cầu dự báo đạt {pred_demand} {prod_info['unit']}/ngày và thời gian giao hàng là {lead_time} ngày."
        else:
            what_text = f"Đề xuất tạo đơn nhập hàng {p_name} (số lượng đề xuất: {suggested_qty} {prod_info['unit']})."
            why_text = f"Dự báo nhu cầu {pred_demand} {prod_info['unit']}/ngày nhưng tồn hiện tại chỉ còn {curr_stock} {prod_info['unit']} (dự kiến hết hàng trong {days_left} ngày), trong khi thời gian nhập hàng trung bình là {lead_time} ngày."

        rec = Recommendation.objects.create(
            workspace=workspace,
            recommendation_type=RecommendationType.RETAIL_STOCKOUT_RISK,
            title=f"Cảnh báo nguy cơ hết hàng: {p_name}",
            priority=prio,
            status=RecommendationStatus.PENDING,
            explanation={
                "what": what_text,
                "why": why_text,
                "evidence": {
                    "product_id": prod_id,
                    "product_sku": prod_info["product_sku"],
                    "product_name": p_name,
                    "current_stock": curr_stock,
                    "predicted_daily_demand": pred_demand,
                    "days_to_stockout": days_left,
                    "expected_stockout_date": prod_info["expected_stockout_date"],
                    "lead_time_days": lead_time,
                    "safety_buffer_days": prod_info["safety_buffer_days"],
                    "suggested_reorder_quantity": suggested_qty,
                    "risk_level": prod_info["risk_level"],
                },
                "expected_effect": "Giảm nguy cơ gián đoạn bán hàng, đảm bảo cung ứng sản phẩm liên tục và duy trì doanh thu bán lẻ.",
            },
            supporting_data=prod_info,
            source_references=[source_ref],
        )
        created_recs.append(rec)

    return created_recs


def evaluate_service_recommendations(workspace: Workspace) -> List[Recommendation]:
    """
    Evaluates deterministic Service Ops rules for a workspace.
    """
    if workspace.workspace_type != WorkspaceType.SERVICE:
        return []

    from apps.service_ops.models import ServiceRequest, ServiceRequestStatus, Employee, Task, TaskStatus
    from apps.gis.services import find_nearby_technicians

    created_recs = []

    # Rule 1: SLA At-Risk Ticket Check
    now = timezone.now()
    at_risk_requests = ServiceRequest.objects.for_workspace(workspace).filter(
        status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]
    )

    high_risk_tickets = []
    for req in at_risk_requests:
        hours_open = (now - req.created_at).total_seconds() / 3600.0
        if hours_open > 12.0 or req.priority == "HIGH":
            high_risk_tickets.append(req)

    if high_risk_tickets:
        target_ticket = high_risk_tickets[0]
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.SERVICE_SLA_AT_RISK,
            status=RecommendationStatus.PENDING,
            source_references__contains=[f"ticket:{target_ticket.id}"]
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.SERVICE_SLA_AT_RISK,
                title=f"Cảnh báo rủi ro vi phạm SLA cho yêu cầu dịch vụ #{getattr(target_ticket, 'request_number', target_ticket.id)}",
                priority=RecommendationPriority.CRITICAL if target_ticket.priority == "HIGH" else RecommendationPriority.HIGH,
                status=RecommendationStatus.PENDING,
                explanation={
                    "what": f"Ưu tiên phân công hoặc điều phối nhân sự xử lý khẩn cấp yêu cầu #{getattr(target_ticket, 'request_number', target_ticket.id)}.",
                    "why": f"Yêu cầu dịch vụ đang ở trạng thái '{target_ticket.get_status_display()}' với mức độ ưu tiên '{target_ticket.get_priority_display()}'.",
                    "evidence": {
                        "ticket_id": target_ticket.id,
                        "ticket_code": getattr(target_ticket, "request_number", str(target_ticket.id)),
                        "priority": target_ticket.priority,
                        "hours_open": round((now - target_ticket.created_at).total_seconds() / 3600.0, 1),
                    },
                    "expected_effect": "Đảm bảo tuân thủ cam kết SLA, tránh vi phạm hợp đồng và nâng cao độ hài lòng của khách hàng."
                },
                supporting_data={
                    "ticket_id": target_ticket.id,
                    "customer_name": target_ticket.customer.name if target_ticket.customer else "N/A",
                },
                source_references=[f"ticket:{target_ticket.id}"]
            )
            created_recs.append(rec)

            # Rule 4: GIS Nearby Technician Candidate Scoring Recommendation for this ticket
            gis_results = find_nearby_technicians(workspace, service_request_id=target_ticket.id, radius_km=25.0)
            candidates = gis_results.get("candidates", [])
            if candidates:
                scored_candidates = []
                for c in candidates:
                    sc = calculate_technician_score(
                        distance_km=c["distance_km"],
                        active_tasks=c["active_tasks"],
                        has_matching_skill=True,
                    )
                    scored_candidates.append({
                        "technician_id": c["id"],
                        "name": c["name"],
                        "code": c["code"],
                        "distance_km": c["distance_km"],
                        "active_tasks": c["active_tasks"],
                        "total_score": sc["score"],
                        "score_breakdown": sc["subscores"],
                    })
                
                scored_candidates.sort(key=lambda x: x["total_score"], reverse=True)
                top_candidate = scored_candidates[0]

                rec_gis = Recommendation.objects.create(
                    workspace=workspace,
                    recommendation_type=RecommendationType.SERVICE_NEARBY_TECHNICIAN,
                    title=f"Đề xuất phân công Kỹ thuật viên {top_candidate['name']} cho ticket #{getattr(target_ticket, 'request_number', target_ticket.id)}",
                    priority=RecommendationPriority.HIGH,
                    status=RecommendationStatus.PENDING,
                    explanation={
                        "what": f"Điều động Kỹ thuật viên {top_candidate['name']} ({top_candidate['code']}) tiếp nhận xử lý yêu cầu #{getattr(target_ticket, 'request_number', target_ticket.id)}.",
                        "why": f"Kỹ thuật viên có điểm đánh giá tối ưu {top_candidate['total_score']}/100 dựa trên khoảng cách địa lý ({top_candidate['distance_km']} km) và số công việc hiện tại ({top_candidate['active_tasks']} công việc).",
                        "evidence": {
                            "ticket_id": target_ticket.id,
                            "top_candidate": top_candidate,
                            "ranked_candidates_count": len(scored_candidates),
                            "scoring_formula": "0.4 * max(0, 100 - dist*10) + 0.4 * max(0, 100 - tasks*20) + 0.2 * skill_score"
                        },
                        "expected_effect": "Tối ưu hóa thời gian di chuyển, cân bằng tải lao động và đảm bảo tiến độ xử lý yêu cầu."
                    },
                    supporting_data={
                        "ticket_id": target_ticket.id,
                        "recommended_employee_id": top_candidate["technician_id"],
                        "top_candidates": scored_candidates[:3],
                    },
                    source_references=[f"ticket:{target_ticket.id}", f"employee:{top_candidate['technician_id']}"],
                    proposed_action="dispatch_technician",
                    proposed_parameters={
                        "ticket_id": target_ticket.id,
                        "employee_id": top_candidate["technician_id"],
                    },
                )
                created_recs.append(rec_gis)

    # Rule 2: Technician Overload Check
    overloaded_techs = Employee.objects.for_workspace(workspace).annotate(
        task_cnt=Count("assigned_tasks", filter=Q(assigned_tasks__status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
    ).filter(task_cnt__gte=3)

    if overloaded_techs.exists():
        overloaded = overloaded_techs.first()
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.SERVICE_TECHNICIAN_OVERLOAD,
            status=RecommendationStatus.PENDING,
            source_references__contains=[f"employee:{overloaded.id}"]
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.SERVICE_TECHNICIAN_OVERLOAD,
                title=f"Cảnh báo quá tải công việc kỹ thuật viên {overloaded.full_name}",
                priority=RecommendationPriority.MEDIUM,
                status=RecommendationStatus.PENDING,
                explanation={
                    "what": f"Tái điều phối bớt công việc tồn đọng của Kỹ thuật viên {overloaded.full_name} cho các nhân sự khả dụng khác.",
                    "why": f"Kỹ thuật viên hiện đang đảm nhận {overloaded.task_cnt} công việc đang xử lý, vượt ngưỡng khuyến nghị 3 công việc.",
                    "evidence": {
                        "employee_id": overloaded.id,
                        "employee_name": overloaded.full_name,
                        "active_task_count": overloaded.task_cnt,
                        "threshold": 3,
                    },
                    "expected_effect": "Giảm áp lực công việc, hạn chế sai sót kỹ thuật và cân bằng khối lượng lao động trong ca."
                },
                supporting_data={"employee_id": overloaded.id, "active_tasks": overloaded.task_cnt},
                source_references=[f"employee:{overloaded.id}"]
            )
            created_recs.append(rec)

    return created_recs
