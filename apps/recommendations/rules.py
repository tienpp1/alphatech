"""
Deterministic Business Rule Engine for Recommendations (Phase 10).
Evaluates operational thresholds, forecasts, and GIS data to produce explainable recommendations.
Does NOT use LLM or non-deterministic inference to evaluate rules.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
import datetime
from django.utils import timezone
from django.db.models import Sum, Count, Q, Max

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

    from apps.retail.models import Order, OrderStatus

    created_recs = []

    today = timezone.localdate()
    recent_start = today - datetime.timedelta(days=6)
    previous_start = recent_start - datetime.timedelta(days=7)
    all_orders = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
    latest_order_date = all_orders.aggregate(last=Max("order_date"))["last"]
    # An old imported snapshot is not evidence of a current business decline.
    if latest_order_date and (latest_order_date < today - datetime.timedelta(days=7) or latest_order_date > today):
        return evaluate_retail_stockout_recommendations(workspace)
    recent_orders = all_orders.filter(order_date__gte=recent_start, order_date__lte=today)

    agg = recent_orders.aggregate(s=Sum("total_amount"), c=Count("id"))
    recent_rev = float(recent_orders.filter(status=OrderStatus.COMPLETED).aggregate(s=Sum("total_amount"))["s"] or 0)
    previous_rev = float(all_orders.filter(status=OrderStatus.COMPLETED, order_date__gte=previous_start,
                                          order_date__lt=recent_start).aggregate(s=Sum("total_amount"))["s"] or 0)
    order_count = int(agg["c"] or 0)

    period = {"period_start": recent_start.isoformat(), "period_end": today.isoformat(),
              "latest_order_date": latest_order_date.isoformat() if latest_order_date else None,
              "revenue_definition": "completed_order_total_amount", "scope": "workspace",
              "data_status": "CURRENT_SNAPSHOT" if latest_order_date else "NO_DATA"}
    expiry = timezone.now() + datetime.timedelta(days=7)
    # Forecast error improvement says nothing about the direction of revenue.
    # A decline requires a measured comparison with the previous equal period.
    if previous_rev > 0 and recent_rev < previous_rev * 0.9:
        # Check if active recommendation already exists to avoid duplicates
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_DECLINING_REVENUE,
            status=RecommendationStatus.PENDING,
            supporting_data__period_end=today.isoformat(),
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.RETAIL_DECLINING_REVENUE,
                title="Rà soát doanh thu đã hoàn tất của workspace giảm so với kỳ trước",
                priority=RecommendationPriority.HIGH,
                status=RecommendationStatus.PENDING,
                explanation={
                    "what": "Rà soát nguyên nhân trước khi quyết định chương trình bán hàng; đây là đề xuất tham khảo.",
                    "why": f"Doanh thu đơn COMPLETED của 7 ngày đạt {recent_rev:,.0f} VND so với {previous_rev:,.0f} VND của 7 ngày trước, giảm trên 10%.",
                    "evidence": {
                        "recent_7d_revenue_vnd": recent_rev,
                        "recent_7d_order_count": order_count,
                        "previous_7d_completed_revenue_vnd": previous_rev,
                        **period,
                    },
                    "expected_effect": "Hỗ trợ đánh giá tình hình; chưa cam kết cải thiện doanh thu."
                },
                supporting_data={
                    "recent_7d_revenue_vnd": recent_rev,
                    "previous_7d_completed_revenue_vnd": previous_rev,
                    **period,
                },
                expires_at=expiry,
                source_references=[f"workspace:{workspace.code}"]
            )
            created_recs.append(rec)

    # Rule 2: Low Order Volume Alert
    if order_count < 10:
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME,
            status=RecommendationStatus.PENDING,
            supporting_data__period_end=today.isoformat(),
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.RETAIL_LOW_ORDER_VOLUME,
                title="Cảnh báo số lượng đơn hàng bán lẻ thấp" if latest_order_date else "Chưa có dữ liệu đơn hàng để đánh giá vận hành",
                priority=RecommendationPriority.MEDIUM,
                status=RecommendationStatus.PENDING,
                explanation={
                    "what": "Rà soát hoạt động tiếp thị và tiếp cận khách hàng thân thiết." if latest_order_date else "Đối chiếu nguồn và bổ sung dữ liệu nghiệp vụ trước khi đánh giá.",
                    "why": f"Số đơn không hủy trong kỳ nghiệp vụ 7 ngày là {order_count}; ngưỡng tham khảo 10 đơn." if latest_order_date else "Chưa có đơn không hủy trong workspace; không thể kết luận hoạt động thực tế sụt giảm.",
                    "evidence": {
                        "order_count_7d": order_count,
                        "threshold": 10,
                        **period,
                    },
                    "expected_effect": "Hỗ trợ xem xét số lượng giao dịch; chưa cam kết tăng trưởng." if latest_order_date else "Có đủ dữ liệu kiểm chứng thay vì suy diễn tình hình kinh doanh."
                },
                supporting_data={"order_count_7d": order_count, **period},
                expires_at=expiry,
                source_references=[f"workspace:{workspace.code}"]
            )
            created_recs.append(rec)

    # Rule 3: High Performing Branch Best Practice Sharing
    if recent_rev >= 150000000.0:
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_HIGH_PERFORMING,
            status=RecommendationStatus.PENDING,
            supporting_data__period_end=today.isoformat(),
        ).first()

        if not existing:
            rec = Recommendation.objects.create(
                workspace=workspace,
                recommendation_type=RecommendationType.RETAIL_HIGH_PERFORMING,
                title="Rà soát thực hành bán hàng của workspace có doanh thu hoàn tất cao",
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
                supporting_data={"recent_7d_revenue_vnd": recent_rev, **period},
                expires_at=expiry,
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
    now = timezone.now()
    evaluated_on = timezone.localdate().isoformat()

    for prod_info in products_at_risk:
        if prod_info["risk_level"] not in ("OUT_OF_STOCK", "HIGH"):
            continue
        inventory = prod_info.get("inventory_assessment") or {}
        demand = prod_info.get("demand_assessment") or {}
        if not isinstance(inventory, dict):
            inventory = {}
        if not isinstance(demand, dict):
            demand = {}
        if inventory.get("status") in ("MISSING_BALANCE", "NEGATIVE_BALANCE") or prod_info["current_stock"] < 0:
            # Missing/invalid balances cannot justify an urgent stockout claim.
            continue
        from apps.recommendations.services import _stockout_evidence_is_current
        current_evidence = _stockout_evidence_is_current(prod_info)

        prod_id = prod_info["product_id"]
        source_ref = f"product:{prod_id}"

        # Prevent duplicate active recommendations
        existing = Recommendation.objects.for_workspace(workspace).filter(
            recommendation_type=RecommendationType.RETAIL_STOCKOUT_RISK,
            status=RecommendationStatus.PENDING,
            source_references__contains=[source_ref],
            supporting_data__evaluated_on=evaluated_on,
            expires_at__gt=now,
        ).first()

        if existing:
            continue

        p_name = prod_info["product_name"]
        curr_stock = prod_info["current_stock"]
        pred_demand = prod_info["predicted_daily_demand"]
        days_left = prod_info["days_to_stockout"]
        lead_time = prod_info["lead_time_days"]
        suggested_qty = prod_info["suggested_reorder_quantity"]
        recorded_zero = inventory.get("verified_record") is True and inventory.get("status") == "RECORDED_BALANCE" and curr_stock == 0
        prio = (RecommendationPriority.CRITICAL if recorded_zero else RecommendationPriority.HIGH) if current_evidence else RecommendationPriority.MEDIUM
        assumptions = f"Tham số kịch bản: thời gian nhập {lead_time} ngày, đệm an toàn {prod_info['safety_buffer_days']} ngày; chưa có cam kết nhà cung cấp đã được xác minh."

        if not current_evidence:
            what_text = f"Rà soát tồn kho và xác minh nhu cầu sản phẩm {p_name} trước khi quyết định nhập; đề xuất tham khảo chưa đủ căn cứ chấp thuận."
            stock_text = f"Số dư tồn kho đã ghi nhận bằng 0 {prod_info['unit']}. " if recorded_zero else "Chưa đủ bằng chứng tồn kho/nhu cầu hiện hành. "
            why_text = stock_text + f"Nhu cầu heuristic {pred_demand} {prod_info['unit']}/ngày chỉ là ước tính lịch sử/kịch bản, không phải dự báo XGBoost đã kiểm chứng. " + str(demand.get("message") or "Nguồn/độ mới chưa được xác minh.") + " " + assumptions
        elif prod_info["risk_level"] == "OUT_OF_STOCK":
            what_text = f"Rà soát phương án nhập sản phẩm {p_name} (lượng tham khảo: {suggested_qty} {prod_info['unit']}); chưa tự thực hiện nghiệp vụ."
            why_text = f"Số dư tồn kho đã ghi nhận bằng 0 {prod_info['unit']}; nhu cầu heuristic từ giao dịch hoàn tất đạt {pred_demand} {prod_info['unit']}/ngày, không phải dự báo XGBoost đã kiểm chứng. " + assumptions
        else:
            what_text = f"Rà soát phương án nhập {p_name} (lượng tham khảo: {suggested_qty} {prod_info['unit']}); chỉ lập nghiệp vụ sau khi xác nhận điều kiện."
            why_text = f"Nhu cầu heuristic {pred_demand} {prod_info['unit']}/ngày và số dư tồn đã lưu {curr_stock} {prod_info['unit']} cho kịch bản cạn tồn sau {days_left} ngày; không bảo đảm ngày hết hàng hoặc chất lượng XGBoost. " + assumptions

        rec = Recommendation.objects.create(
            workspace=workspace,
            recommendation_type=RecommendationType.RETAIL_STOCKOUT_RISK,
            title=f"Cảnh báo nguy cơ hết hàng: {p_name}" if current_evidence else f"Rà soát dữ liệu tồn kho/nhu cầu: {p_name}",
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
                    "inventory_assessment": inventory,
                    "demand_assessment": demand,
                    "evaluated_on": evaluated_on,
                    "current_evidence": current_evidence,
                    "assumptions": assumptions,
                },
                "expected_effect": "Hỗ trợ quyết định sau khi đối chiếu nguồn; không cam kết ngày hết hàng, cung ứng hoặc doanh thu.",
            },
            supporting_data={**prod_info, "evaluated_on": evaluated_on},
            expires_at=now + datetime.timedelta(days=1),
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
    cutoff_12h = now - datetime.timedelta(hours=12)
    target_ticket = (
        ServiceRequest.objects.for_workspace(workspace)
        .filter(
            status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]
        )
        .filter(Q(created_at__lte=cutoff_12h) | Q(priority="HIGH"))
        .select_related("customer")
        .first()
    )

    if target_ticket:
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
    overloaded = Employee.objects.for_workspace(workspace).annotate(
        task_cnt=Count("assigned_tasks", filter=Q(assigned_tasks__status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
    ).filter(task_cnt__gte=3).first()

    if overloaded:
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
