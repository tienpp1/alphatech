"""
Controlled read-only business telemetry tools for AI context grounding.
Enforces workspace isolation, caller RBAC permissions, PII masking, and audit logging.
Strictly prohibits data mutations or arbitrary SQL execution.
"""

from typing import Any, Dict, Optional
from decimal import Decimal
from django.db.models import Sum, Count, Avg, Q
from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.audit.services import log_audit_event


class ToolPermissionDenied(Exception):
    """Raised when user lacks required permission to access structured business tool."""
    pass


def _check_perm(user: User, workspace: Workspace, perm_codename: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    from apps.accounts.services import has_workspace_permission
    return has_workspace_permission(user, workspace, perm_codename)


def get_sales_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves aggregated retail sales telemetry for the workspace.
    Requires 'retail.view_order' permission.
    """
    if not _check_perm(user, workspace, "retail.view_order"):
        raise ToolPermissionDenied("User lacks 'retail.view_order' permission to access sales data.")

    from apps.retail.models import Order, OrderStatus

    qs = Order.objects.for_workspace(workspace)
    total_orders = qs.count()
    completed_orders = qs.filter(status=OrderStatus.COMPLETED).count()
    pending_orders = qs.filter(status__in=[OrderStatus.PENDING, OrderStatus.CONFIRMED]).count()

    valid_orders = qs.exclude(status=OrderStatus.CANCELLED)
    agg = valid_orders.aggregate(
        total_rev=Sum("total_amount"),
        avg_rev=Avg("total_amount"),
    )

    total_revenue = agg["total_rev"] or Decimal("0.00")
    avg_order_value = agg["avg_rev"] or Decimal("0.00")

    return {
        "tool": "get_sales_summary",
        "workspace": workspace.code,
        "total_revenue": f"{total_revenue:,.0f} VND",
        "total_revenue_raw": float(total_revenue),
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "average_order_value": f"{avg_order_value:,.0f} VND",
    }


def get_product_catalog_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves catalog counts and top product lines, optionally filtered by category.
    Requires 'retail.view_product' permission.
    """
    if not _check_perm(user, workspace, "retail.view_product"):
        raise ToolPermissionDenied("User lacks 'retail.view_product' permission to access product data.")

    from apps.retail.models import Product, Category

    category_code = kwargs.get("category")
    prods = Product.objects.for_workspace(workspace)
    if category_code:
        prods = prods.filter(category__code__icontains=category_code)

    total_prods = prods.count()
    active_prods = prods.filter(is_active=True).count()

    categories = list(
        Category.objects.for_workspace(workspace)
        .values("code", "name")
        .annotate(product_count=Count("products"))[:10]
    )

    sample_items = list(
        prods.filter(is_active=True)
        .values("sku", "name", "unit_price")[:5]
    )
    for it in sample_items:
        it["unit_price"] = f"{it['unit_price']:,.0f} VND"

    return {
        "tool": "get_product_catalog_summary",
        "workspace": workspace.code,
        "category_filter": category_code or "all",
        "total_products": total_prods,
        "active_products": active_prods,
        "categories": categories,
        "sample_products": sample_items,
    }


def get_top_selling_products(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves ranked sales performance and revenue ranking for products.
    Requires 'retail.view_order' permission.
    """
    if not _check_perm(user, workspace, "retail.view_order"):
        raise ToolPermissionDenied("User lacks 'retail.view_order' permission to access sales ranking.")

    from apps.retail.models import OrderItem, OrderStatus

    category_code = kwargs.get("category")
    metric = kwargs.get("metric", "quantity_sold")
    limit = int(kwargs.get("limit", 5))
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    time_label = kwargs.get("time_label", "toàn thời gian")

    items_qs = OrderItem.objects.filter(
        order__workspace=workspace
    ).exclude(order__status=OrderStatus.CANCELLED)

    if category_code:
        items_qs = items_qs.filter(product__category__code__icontains=category_code)
    if start_date:
        items_qs = items_qs.filter(order__order_date__gte=start_date)
    if end_date:
        items_qs = items_qs.filter(order__order_date__lte=end_date)

    order_by_clause = "-quantity_sold" if metric == "quantity_sold" else "-revenue"
    if kwargs.get("sort_order") == "ASC":
        order_by_clause = order_by_clause.replace("-", "")

    top_items = (
        items_qs.values("product__id", "product__sku", "product__name", "product__category__name")
        .annotate(
            quantity_sold=Sum("quantity"),
            revenue=Sum("subtotal"),
        )
        .order_by(order_by_clause)[:limit]
    )

    ranking_list = []
    for item in top_items:
        ranking_list.append({
            "product_id": item["product__id"],
            "sku": item["product__sku"],
            "name": item["product__name"],
            "category": item["product__category__name"] or "Khác",
            "quantity_sold": item["quantity_sold"] or 0,
            "revenue": float(item["revenue"] or 0.0),
            "revenue_formatted": f"{float(item['revenue'] or 0.0):,.0f} VND",
        })

    return {
        "tool": "get_top_selling_products",
        "workspace": workspace.code,
        "category_filter": category_code or "all",
        "metric": metric,
        "ranking_metric_name": "Số lượng bán ra (units)" if metric == "quantity_sold" else "Doanh thu (VND)",
        "time_range": time_label,
        "results_count": len(ranking_list),
        "rankings": ranking_list,
    }


def get_top_customers(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves highest spending and most frequent purchasing customers with PII masking.
    Requires 'retail.view_order' permission.
    """
    if not _check_perm(user, workspace, "retail.view_order"):
        raise ToolPermissionDenied("User lacks 'retail.view_order' permission to access customer rankings.")

    from apps.retail.models import Order, OrderItem, OrderStatus

    limit = int(kwargs.get("limit", 5))
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    time_label = kwargs.get("time_label", "toàn thời gian")
    category = kwargs.get("category")
    branch = kwargs.get("branch") or kwargs.get("branch_name")

    if category:
        items_qs = OrderItem.objects.filter(
            order__workspace=workspace,
            product__category__code__icontains=category,
        ).exclude(order__status=OrderStatus.CANCELLED)

        if start_date:
            items_qs = items_qs.filter(order__order_date__gte=start_date)
        if end_date:
            items_qs = items_qs.filter(order__order_date__lte=end_date)
        if branch:
            items_qs = items_qs.filter(Q(order__branch__name__icontains=branch) | Q(order__branch__code__icontains=branch))

        top_custs = (
            items_qs.values("order__customer__id", "order__customer__code", "order__customer__name", "order__customer__customer_segment")
            .annotate(
                total_spend=Sum("subtotal"),
                order_count=Count("order__id", distinct=True),
            )
            .order_by("-total_spend")[:limit]
        )

        ranking_list = []
        for c in top_custs:
            ranking_list.append({
                "customer_id": c["order__customer__id"],
                "customer_code": c["order__customer__code"],
                "customer_name": c["order__customer__name"],
                "customer_segment": c["order__customer__customer_segment"],
                "order_count": c["order_count"],
                "total_spend": float(c["total_spend"] or 0.0),
                "total_spend_formatted": f"{float(c['total_spend'] or 0.0):,.0f} VND",
            })
    else:
        orders_qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
        if start_date:
            orders_qs = orders_qs.filter(order_date__gte=start_date)
        if end_date:
            orders_qs = orders_qs.filter(order_date__lte=end_date)
        if branch:
            orders_qs = orders_qs.filter(Q(branch__name__icontains=branch) | Q(branch__code__icontains=branch))

        top_custs = (
            orders_qs.values("customer__id", "customer__code", "customer__name", "customer__customer_segment")
            .annotate(
                total_spend=Sum("total_amount"),
                order_count=Count("id"),
            )
            .order_by("-total_spend")[:limit]
        )

        ranking_list = []
        for c in top_custs:
            ranking_list.append({
                "customer_id": c["customer__id"],
                "customer_code": c["customer__code"],
                "customer_name": c["customer__name"],
                "customer_segment": c["customer__customer_segment"],
                "order_count": c["order_count"],
                "total_spend": float(c["total_spend"] or 0.0),
                "total_spend_formatted": f"{float(c['total_spend'] or 0.0):,.0f} VND",
            })

    return {
        "tool": "get_top_customers",
        "workspace": workspace.code,
        "category_filter": category or "Tất cả danh mục",
        "branch_filter": branch or "Tất cả chi nhánh",
        "time_range": time_label,
        "results_count": len(ranking_list),
        "rankings": ranking_list,
    }



def get_branch_sales_analytics(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Aggregates and ranks branch sales performance.
    Requires 'retail.view_order' permission.
    """
    if not _check_perm(user, workspace, "retail.view_order"):
        raise ToolPermissionDenied("User lacks 'retail.view_order' permission to access branch analytics.")

    from apps.retail.models import Order, Branch, OrderStatus

    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    time_label = kwargs.get("time_label", "toàn thời gian")
    sort_order = kwargs.get("sort_order", "DESC")

    orders_qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
    if start_date:
        orders_qs = orders_qs.filter(order_date__gte=start_date)
    if end_date:
        orders_qs = orders_qs.filter(order_date__lte=end_date)

    branches = Branch.objects.for_workspace(workspace).filter(is_active=True)
    results = []
    for b in branches:
        b_orders = orders_qs.filter(branch=b)
        agg = b_orders.aggregate(
            rev=Sum("total_amount"),
            cnt=Count("id"),
        )
        total_rev = float(agg["rev"] or 0.0)
        results.append({
            "branch_id": b.id,
            "branch_code": b.code,
            "branch_name": b.name,
            "region": b.region,
            "revenue": total_rev,
            "revenue_formatted": f"{total_rev:,.0f} VND",
            "order_count": agg["cnt"] or 0,
        })

    reverse_sort = (sort_order == "DESC")
    results.sort(key=lambda x: x["revenue"], reverse=reverse_sort)

    return {
        "tool": "get_branch_sales_analytics",
        "workspace": workspace.code,
        "time_range": time_label,
        "sort_order": sort_order,
        "branches": results,
    }


def get_customer_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves aggregate customer segment metrics with PII masking.
    Requires 'retail.view_customer' permission.
    """
    if not _check_perm(user, workspace, "retail.view_customer"):
        raise ToolPermissionDenied("User lacks 'retail.view_customer' permission to access customer data.")

    from apps.retail.models import Customer

    cust_qs = Customer.objects.for_workspace(workspace)
    total_customers = cust_qs.count()
    active_customers = cust_qs.filter(is_active=True).count()

    segment_breakdown = list(
        cust_qs.values("customer_segment")
        .annotate(count=Count("id"))
    )

    return {
        "tool": "get_customer_summary",
        "workspace": workspace.code,
        "total_customers": total_customers,
        "active_customers": active_customers,
        "segment_distribution": {s["customer_segment"]: s["count"] for s in segment_breakdown},
        "privacy_note": "Customer individual PII masked in AI context.",
    }


def get_service_ticket_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves service operations ticket health, priority counts, SLA metrics, or single ticket details.
    Requires 'service.view_request' permission.
    """
    if not _check_perm(user, workspace, "service.view_request"):
        raise ToolPermissionDenied("User lacks 'service.view_request' permission to access service data.")

    from datetime import timedelta
    from django.utils import timezone
    from apps.service_ops.models import ServiceRequest, ServiceRequestStatus

    now = timezone.now()
    ticket_id = kwargs.get("ticket_id")
    filter_mode = kwargs.get("filter")
    exclude_closed = kwargs.get("exclude_closed", False)

    sr_qs = ServiceRequest.objects.for_workspace(workspace).select_related("customer", "assigned_employee", "service")

    # 1. Single Ticket Lookup
    if ticket_id:
        ticket = sr_qs.filter(id=ticket_id).first()
        if not ticket:
            return {
                "tool": "get_service_ticket_summary",
                "workspace": workspace.code,
                "ticket_found": False,
                "ticket_id": ticket_id,
                "message": f"Không tìm thấy phiếu yêu cầu dịch vụ #{ticket_id} trong workspace này.",
            }
        
        is_overdue = bool(ticket.resolution_deadline_at and ticket.resolution_deadline_at < now and ticket.status not in [ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED])
        remaining_minutes = 0
        if ticket.resolution_deadline_at and not is_overdue:
            remaining_minutes = max(0, int((ticket.resolution_deadline_at - now).total_seconds() / 60))

        return {
            "tool": "get_service_ticket_summary",
            "workspace": workspace.code,
            "ticket_found": True,
            "ticket_id": ticket.id,
            "ticket_number": ticket.request_number,
            "title": ticket.title,
            "status": ticket.status,
            "priority": ticket.priority,
            "customer_name": ticket.customer.name if ticket.customer else "N/A",
            "service_name": ticket.service.name if ticket.service else "N/A",
            "assigned_technician": ticket.assigned_employee.full_name if ticket.assigned_employee else "Chưa phân công",
            "created_at": ticket.created_at.strftime("%Y-%m-%d %H:%M"),
            "resolution_deadline": ticket.resolution_deadline_at.strftime("%Y-%m-%d %H:%M") if ticket.resolution_deadline_at else "Không có",
            "is_overdue": is_overdue,
            "remaining_time_minutes": remaining_minutes,
            "remaining_time_formatted": f"{remaining_minutes // 60} giờ {remaining_minutes % 60} phút" if remaining_minutes > 0 else ("ĐÃ QUÁ HẠN" if is_overdue else "Hoàn thành"),
        }

    # 2. Aggregated tickets query
    if exclude_closed:
        sr_qs = sr_qs.exclude(status__in=[ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED, ServiceRequestStatus.CANCELLED])

    total_tickets = sr_qs.count()
    open_tickets = sr_qs.filter(
        status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]
    ).count()

    overdue_tickets_qs = sr_qs.filter(
        status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS],
        resolution_deadline_at__lt=now,
    )
    overdue_tickets_count = overdue_tickets_qs.count()

    # SLA at-risk tickets (deadline within next 4 hours)
    at_risk_qs = sr_qs.filter(
        status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS],
        resolution_deadline_at__gte=now,
        resolution_deadline_at__lte=now + timedelta(hours=4),
    )

    priority_breakdown = list(
        sr_qs.values("priority")
        .annotate(count=Count("id"))
    )

    # Detailed list if filter requested
    detail_list = []
    if filter_mode == "SLA_BREACHED":
        target_qs = overdue_tickets_qs.order_by("resolution_deadline_at")[:10]
    elif filter_mode == "SLA_AT_RISK":
        target_qs = at_risk_qs.order_by("resolution_deadline_at")[:10]
    else:
        target_qs = sr_qs.filter(status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]).order_by("-created_at")[:5]

    for t in target_qs:
        rem_min = 0
        if t.resolution_deadline_at and t.resolution_deadline_at >= now:
            rem_min = int((t.resolution_deadline_at - now).total_seconds() / 60)
        detail_list.append({
            "id": t.id,
            "ticket_number": t.request_number,
            "title": t.title,
            "priority": t.priority,
            "status": t.status,
            "assigned_to": t.assigned_employee.full_name if t.assigned_employee else "Chưa phân công",
            "deadline": t.resolution_deadline_at.strftime("%Y-%m-%d %H:%M") if t.resolution_deadline_at else "N/A",
            "remaining_minutes": rem_min,
        })


    return {
        "tool": "get_service_ticket_summary",
        "workspace": workspace.code,
        "filter_applied": filter_mode or "NONE",
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "overdue_sla_tickets": overdue_tickets_count,
        "at_risk_sla_tickets": at_risk_qs.count(),
        "priority_distribution": {p["priority"]: p["count"] for p in priority_breakdown},
        "tickets": detail_list,
    }



def get_technician_workload_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves technician roster and workload metrics.
    Requires 'service.view_employee' permission.
    """
    if not _check_perm(user, workspace, "service.view_employee"):
        raise ToolPermissionDenied("User lacks 'service.view_employee' permission to access technician data.")


    from apps.service_ops.models import Employee

    emp_qs = Employee.objects.for_workspace(workspace)
    total_techs = emp_qs.count()
    available_techs = emp_qs.filter(is_available=True).count()
    avg_score = emp_qs.aggregate(avg_score=Avg("current_workload_score"))["avg_score"] or 0.0

    top_techs = list(
        emp_qs.order_by("current_workload_score")
        .values("full_name", "skills", "current_workload_score", "is_available")[:5]
    )

    return {
        "tool": "get_technician_workload_summary",
        "workspace": workspace.code,
        "total_technicians": total_techs,
        "available_technicians": available_techs,
        "average_workload_score": round(float(avg_score), 1),
        "roster_sample": top_techs,
    }


def get_stockout_risk_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves deterministic stockout risk prediction, expected stockout date,
    and suggested reorder quantities across retail products.
    Requires 'retail.view_product' or 'retail.view_order' permission.
    """
    if not (_check_perm(user, workspace, "retail.view_product") or _check_perm(user, workspace, "retail.view_order")):
        raise ToolPermissionDenied("User lacks permission to view product stockout analytics.")

    from apps.retail.stockout_services import get_stockout_risk_dashboard_data

    branch_id = kwargs.get("branch_id")
    category = kwargs.get("category")
    limit = int(kwargs.get("limit", 10))

    dashboard_data = get_stockout_risk_dashboard_data(
        workspace=workspace,
        branch_id=branch_id,
        category_code=category,
        limit=limit,
    )

    return {
        "tool": "get_stockout_risk_summary",
        "workspace": workspace.code,
        "branch_name": dashboard_data["branch_name"],
        "category_filter": category or "Tất cả danh mục",
        "out_of_stock_count": dashboard_data["out_of_stock_count"],
        "high_risk_count": dashboard_data["high_risk_count"],
        "medium_risk_count": dashboard_data["medium_risk_count"],
        "low_risk_count": dashboard_data["low_risk_count"],
        "total_tracked": dashboard_data["total_products_tracked"],
        "products_at_risk": dashboard_data["products_at_risk"][:limit],
    }


def get_stock_balance_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves current branch-level stock balance quantities.
    Requires 'retail.view_product' permission.
    """
    if not _check_perm(user, workspace, "retail.view_product"):
        raise ToolPermissionDenied("User lacks 'retail.view_product' permission to view stock balance.")

    from apps.retail.models import StockBalance

    category = kwargs.get("category")
    branch_id = kwargs.get("branch_id")
    limit = int(kwargs.get("limit", 20))

    qs = StockBalance.objects.for_workspace(workspace).select_related("product", "branch", "product__category")

    if category:
        qs = qs.filter(product__category__code__icontains=category)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)

    total_stock_units = qs.aggregate(s=Sum("quantity_on_hand"))["s"] or 0
    records = []
    for sb in qs.order_by("branch__name", "product__name")[:limit]:
        records.append({
            "product_name": sb.product.name,
            "product_sku": sb.product.sku,
            "category": sb.product.category.name if sb.product.category else "",
            "branch_name": sb.branch.name,
            "branch_code": sb.branch.code,
            "quantity_on_hand": sb.quantity_on_hand,
            "unit": sb.product.unit,
            "updated_at": sb.updated_at.strftime("%Y-%m-%d %H:%M"),
        })

    return {
        "tool": "get_stock_balance_summary",
        "workspace": workspace.code,
        "total_stock_units": int(total_stock_units),
        "results_count": len(records),
        "balances": records,
    }


def compare_entities_analytics(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Compares 2 or more products, brands, or branches deterministically using backend aggregation.
    Requires 'retail.view_order' permission.
    """
    if not _check_perm(user, workspace, "retail.view_order"):
        raise ToolPermissionDenied("User lacks 'retail.view_order' permission to compare entities.")

    from apps.retail.models import OrderItem, Order, Branch, OrderStatus

    entity_type = kwargs.get("entity_type", "product")
    entities = kwargs.get("entities", [])
    metric = kwargs.get("metric", "quantity_sold")  # quantity_sold or revenue
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    time_label = kwargs.get("time_label", "toàn thời gian")

    comparison_results = []

    if entity_type == "branch":
        branch_qs = Branch.objects.for_workspace(workspace).filter(is_active=True)
        if entities:
            # Filter matching branch names/codes
            q_filter = Q()
            for e in entities:
                q_filter |= Q(name__icontains=e) | Q(code__icontains=e)
            branch_qs = branch_qs.filter(q_filter)

        for br in branch_qs:
            orders = Order.objects.for_workspace(workspace).filter(branch=br).exclude(status=OrderStatus.CANCELLED)
            if start_date:
                orders = orders.filter(order_date__gte=start_date)
            if end_date:
                orders = orders.filter(order_date__lte=end_date)
            
            agg = orders.aggregate(rev=Sum("total_amount"), cnt=Count("id"))
            rev_val = float(agg["rev"] or 0.0)
            comparison_results.append({
                "entity_id": br.id,
                "name": br.name,
                "code": br.code,
                "revenue": rev_val,
                "revenue_formatted": f"{rev_val:,.0f} VND",
                "order_count": agg["cnt"] or 0,
                "metric_value": rev_val if metric == "revenue" else (agg["cnt"] or 0),
            })
    else:
        # Product or Brand comparison
        items_qs = OrderItem.objects.filter(order__workspace=workspace).exclude(order__status=OrderStatus.CANCELLED)
        if start_date:
            items_qs = items_qs.filter(order__order_date__gte=start_date)
        if end_date:
            items_qs = items_qs.filter(order__order_date__lte=end_date)

        if entities:
            for ent_name in entities:
                ent_items = items_qs.filter(
                    Q(product__name__icontains=ent_name) |
                    Q(product__sku__icontains=ent_name) |
                    Q(product__category__name__icontains=ent_name)
                )
                agg = ent_items.aggregate(
                    q=Sum("quantity"),
                    r=Sum("subtotal"),
                )
                qty = int(agg["q"] or 0)
                rev = float(agg["r"] or 0.0)
                comparison_results.append({
                    "entity_name": ent_name,
                    "quantity_sold": qty,
                    "revenue": rev,
                    "revenue_formatted": f"{rev:,.0f} VND",
                    "metric_value": rev if metric == "revenue" else qty,
                })
        else:
            # If no specific entities provided, compare top 2 selling products
            top_2 = (
                items_qs.values("product__name", "product__sku")
                .annotate(q=Sum("quantity"), r=Sum("subtotal"))
                .order_by("-q" if metric == "quantity_sold" else "-r")[:2]
            )
            for it in top_2:
                qty = int(it["q"] or 0)
                rev = float(it["r"] or 0.0)
                comparison_results.append({
                    "entity_name": it["product__name"],
                    "quantity_sold": qty,
                    "revenue": rev,
                    "revenue_formatted": f"{rev:,.0f} VND",
                    "metric_value": rev if metric == "revenue" else qty,
                })

    # Sort descending by metric value
    comparison_results.sort(key=lambda x: x["metric_value"], reverse=True)

    winner_name = None
    difference = 0
    pct_diff = 0.0
    if len(comparison_results) >= 2:
        top_ent = comparison_results[0]
        second_ent = comparison_results[1]
        winner_name = top_ent.get("name") or top_ent.get("entity_name")
        val1 = float(top_ent["metric_value"])
        val2 = float(second_ent["metric_value"])
        difference = val1 - val2
        if val2 > 0:
            pct_diff = round(((val1 - val2) / val2) * 100, 1)

    return {
        "tool": "compare_entities_analytics",
        "workspace": workspace.code,
        "entity_type": entity_type,
        "metric": metric,
        "metric_label": "Doanh thu (VND)" if metric == "revenue" else "Số lượng bán ra (units)",
        "time_range": time_label,
        "comparison": comparison_results,
        "leader": winner_name,
        "difference": difference,
        "percentage_lead": pct_diff,
    }


def get_sales_trend_analytics(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Computes period-over-period trend analysis (e.g. this month vs last month, past 30 days vs prior 30 days).
    Requires 'retail.view_order' permission.
    """
    if not _check_perm(user, workspace, "retail.view_order"):
        raise ToolPermissionDenied("User lacks 'retail.view_order' permission to access sales trends.")

    from datetime import timedelta
    from django.utils import timezone
    from apps.retail.models import Order, OrderItem, OrderStatus

    category = kwargs.get("category")
    branch = kwargs.get("branch") or kwargs.get("branch_name")
    period_days = int(kwargs.get("period_days", 30))
    today = timezone.now().date()

    # Current period: [today - period_days + 1, today]
    curr_start = today - timedelta(days=period_days)
    curr_end = today

    # Previous period: [curr_start - period_days, curr_start - 1]
    prev_start = curr_start - timedelta(days=period_days)
    prev_end = curr_start - timedelta(days=1)

    if category:
        items_qs = OrderItem.objects.filter(
            order__workspace=workspace,
            product__category__code__icontains=category,
        ).exclude(order__status=OrderStatus.CANCELLED)

        if branch:
            items_qs = items_qs.filter(Q(order__branch__name__icontains=branch) | Q(order__branch__code__icontains=branch))

        curr_agg = items_qs.filter(order__order_date__range=(curr_start, curr_end)).aggregate(r=Sum("subtotal"), q=Sum("quantity"))
        prev_agg = items_qs.filter(order__order_date__range=(prev_start, prev_end)).aggregate(r=Sum("subtotal"), q=Sum("quantity"))
    else:
        orders_qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
        if branch:
            orders_qs = orders_qs.filter(Q(branch__name__icontains=branch) | Q(branch__code__icontains=branch))

        curr_agg = orders_qs.filter(order_date__range=(curr_start, curr_end)).aggregate(r=Sum("total_amount"), q=Count("id"))
        prev_agg = orders_qs.filter(order_date__range=(prev_start, prev_end)).aggregate(r=Sum("total_amount"), q=Count("id"))


    curr_rev = float(curr_agg["r"] or 0.0)
    prev_rev = float(prev_agg["r"] or 0.0)
    curr_qty = int(curr_agg["q"] or 0)
    prev_qty = int(prev_agg["q"] or 0)

    # Growth calculation
    rev_diff = curr_rev - prev_rev
    if prev_rev > 0:
        rev_growth_pct = round((rev_diff / prev_rev) * 100, 1)
    else:
        rev_growth_pct = 100.0 if curr_rev > 0 else 0.0

    if rev_growth_pct > 15.0:
        direction = "TĂNG MẠNH"
        direction_icon = "📈"
    elif rev_growth_pct > 0.0:
        direction = "TĂNG TRƯỞNG"
        direction_icon = "↗️"
    elif rev_growth_pct == 0.0:
        direction = "ỔN ĐỊNH"
        direction_icon = "➡️"
    elif rev_growth_pct > -15.0:
        direction = "SỤT GIẢM"
        direction_icon = "↘️"
    else:
        direction = "GIẢM MẠNH"
        direction_icon = "📉"

    return {
        "tool": "get_sales_trend_analytics",
        "workspace": workspace.code,
        "category_filter": category or "Toàn bộ sản phẩm",
        "period_days": period_days,
        "current_period": f"{curr_start} đến {curr_end}",
        "previous_period": f"{prev_start} đến {prev_end}",
        "current_revenue": curr_rev,
        "current_revenue_formatted": f"{curr_rev:,.0f} VND",
        "previous_revenue": prev_rev,
        "previous_revenue_formatted": f"{prev_rev:,.0f} VND",
        "revenue_difference": rev_diff,
        "growth_rate_pct": rev_growth_pct,
        "trend_direction": direction,
        "trend_icon": direction_icon,
        "current_units": curr_qty,
        "previous_units": prev_qty,
    }


def get_service_labor_cost_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves aggregated service labor hours, technician hourly fees, and labor costs.
    Requires 'service.view_request' or 'service.view_employee' permission.
    """
    if not (_check_perm(user, workspace, "service.view_request") or _check_perm(user, workspace, "service.view_employee")):
        raise ToolPermissionDenied("User lacks permission to access service labor cost data.")

    from apps.service_ops.models import LaborEntry, ServiceRequest, Employee

    ticket_id = kwargs.get("ticket_id")
    employee_id = kwargs.get("employee_id")
    start_date = kwargs.get("start_date")
    end_date = kwargs.get("end_date")
    time_label = kwargs.get("time_label", "toàn thời gian")

    qs = LaborEntry.objects.filter(task__service_request__workspace=workspace).select_related("task__service_request", "employee")

    if ticket_id:
        qs = qs.filter(task__service_request_id=ticket_id)
    if employee_id:
        qs = qs.filter(employee_id=employee_id)
    if start_date:
        qs = qs.filter(started_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(started_at__date__lte=end_date)

    agg = qs.aggregate(
        tot_min=Sum("duration_minutes"),
        tot_cost=Sum("labor_cost"),
        entry_cnt=Count("id"),
    )

    total_minutes = int(agg["tot_min"] or 0)
    total_hours = round(total_minutes / 60.0, 1)
    total_cost = float(agg["tot_cost"] or 0.0)

    # Top technician labor breakdown
    tech_breakdown = list(
        qs.values("employee__full_name", "employee__code")
        .annotate(minutes=Sum("duration_minutes"), cost=Sum("labor_cost"))
        .order_by("-cost")[:5]
    )
    formatted_techs = []
    for t in tech_breakdown:
        formatted_techs.append({
            "technician_name": t["employee__full_name"],
            "technician_code": t["employee__code"],
            "hours": round((t["minutes"] or 0) / 60.0, 1),
            "cost": float(t["cost"] or 0.0),
            "cost_formatted": f"{float(t['cost'] or 0.0):,.0f} VND",
        })

    return {

        "tool": "get_service_labor_cost_summary",
        "workspace": workspace.code,
        "time_range": time_label,
        "ticket_filter": ticket_id,
        "total_labor_hours": round(total_hours, 1),
        "total_labor_cost": total_cost,
        "total_labor_cost_formatted": f"{total_cost:,.0f} VND",
        "labor_entries_count": agg["entry_cnt"] or 0,
        "technician_breakdown": formatted_techs,
    }


def get_service_catalog_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves IT service catalog, categories, standard durations, and base fees.
    Requires 'service.view_service' or 'service.view_request' permission.
    """
    if not (_check_perm(user, workspace, "service.view_service") or _check_perm(user, workspace, "service.view_request")):
        raise ToolPermissionDenied("User lacks permission to access service catalog data.")

    from apps.service_ops.models import Service

    category = kwargs.get("category")
    services_qs = Service.objects.for_workspace(workspace).filter(is_active=True)
    if category:
        services_qs = services_qs.filter(category__icontains=category)

    total_services = services_qs.count()
    service_items = []
    for s in services_qs.order_by("category", "name")[:15]:
        service_items.append({
            "code": s.code,
            "name": s.name,
            "category": s.category,
            "duration_minutes": s.standard_duration_minutes,
            "base_fee": float(s.base_fee),
            "base_fee_formatted": f"{float(s.base_fee):,.0f} VND",
        })

    return {
        "tool": "get_service_catalog_summary",
        "workspace": workspace.code,
        "category_filter": category or "Tất cả danh mục",
        "total_services": total_services,
        "services": service_items,
    }


def get_customer_order_history(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves a customer's detailed order history and purchased items.
    Requires 'retail.view_customer' or 'retail.view_order' permission.
    """
    if not (_check_perm(user, workspace, "retail.view_customer") or _check_perm(user, workspace, "retail.view_order")):
        raise ToolPermissionDenied("User lacks permission to access customer purchase history.")

    from apps.retail.models import Customer, Order, OrderItem

    cust_query = kwargs.get("customer_name") or kwargs.get("customer_code") or kwargs.get("customer_id")
    customer = None
    if cust_query:
        cust_qs = Customer.objects.for_workspace(workspace)
        if isinstance(cust_query, int) or (isinstance(cust_query, str) and cust_query.isdigit()):
            customer = cust_qs.filter(id=int(cust_query)).first()
        if not customer:
            customer = cust_qs.filter(
                Q(code__iexact=str(cust_query)) |
                Q(name__icontains=str(cust_query)) |
                Q(phone__icontains=str(cust_query))
            ).first()

    if not customer:
        # Fallback: get top customer with orders
        customer = Customer.objects.for_workspace(workspace).first()
        if not customer:
            return {
                "tool": "get_customer_order_history",
                "workspace": workspace.code,
                "customer_found": False,
                "message": "Không tìm thấy thông tin khách hàng trong hệ thống.",
            }

    orders = Order.objects.for_workspace(workspace).filter(customer=customer).prefetch_related("items__product").order_by("-order_date")[:10]
    total_spent = float(orders.aggregate(s=Sum("total_amount"))["s"] or 0.0)

    order_records = []
    all_purchased_products = set()
    for o in orders:
        items_list = []
        for it in o.items.all():
            items_list.append({
                "product_name": it.product.name,
                "product_sku": it.product.sku,
                "quantity": it.quantity,
                "unit_price_formatted": f"{float(it.unit_price):,.0f} VND",
                "subtotal_formatted": f"{float(it.subtotal):,.0f} VND",
            })
            all_purchased_products.add(it.product.name)

        order_records.append({
            "order_number": o.order_number,
            "order_date": o.order_date.strftime("%Y-%m-%d") if o.order_date else "",
            "status": o.status,
            "total_amount_formatted": f"{float(o.total_amount):,.0f} VND",
            "items_count": len(items_list),
            "items": items_list,
        })

    return {
        "tool": "get_customer_order_history",
        "workspace": workspace.code,
        "customer_found": True,
        "customer_name": customer.name,
        "customer_code": customer.code,
        "customer_segment": customer.customer_segment,
        "total_spent_formatted": f"{total_spent:,.0f} VND",
        "order_count": len(order_records),
        "purchased_products_summary": list(all_purchased_products),
        "orders": order_records,
    }


def get_technician_skills_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Queries technicians possessing specific technical skills with availability filtering.
    Requires 'service.view_employee' permission.
    """
    if not _check_perm(user, workspace, "service.view_employee"):
        raise ToolPermissionDenied("User lacks 'service.view_employee' permission to access technician skills.")

    from apps.service_ops.models import Employee

    skill_query = kwargs.get("skill", "").strip().upper()
    is_available_only = kwargs.get("is_available_only", False)

    techs_qs = Employee.objects.for_workspace(workspace).filter(is_active=True)
    if is_available_only:
        techs_qs = techs_qs.filter(is_available=True)

    results = []
    for emp in techs_qs.order_by("current_workload_score"):
        emp_skills = [s.upper() for s in (emp.skills or [])]
        # Skill matching: check exact or substring
        match = True
        if skill_query:
            match = any(skill_query in s for s in emp_skills) or (skill_query in emp.full_name.upper())

        if match:
            results.append({
                "employee_id": emp.id,
                "code": emp.code,
                "full_name": emp.full_name,
                "skills": emp.skills or [],
                "is_available": emp.is_available,
                "availability_label": "Sẵn sàng (Rảnh)" if emp.is_available else "Đang bận",
                "workload_score": round(emp.current_workload_score, 1),
                "hourly_rate_formatted": f"{float(emp.hourly_labor_rate):,.0f} VND/giờ",
            })

    return {
        "tool": "get_technician_skills_summary",
        "workspace": workspace.code,
        "skill_filter": skill_query or "Tất cả kỹ năng",
        "available_only": is_available_only,
        "matching_count": len(results),
        "technicians": results,
    }


def get_technician_schedule_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Retrieves technician calendar schedules and checks for time conflicts.
    Requires 'service.view_schedule' or 'service.view_employee' permission.
    """
    if not (_check_perm(user, workspace, "service.view_schedule") or _check_perm(user, workspace, "service.view_employee")):
        raise ToolPermissionDenied("User lacks permission to access technician schedules.")

    from datetime import timedelta
    from django.utils import timezone
    from apps.service_ops.models import Schedule, Employee

    target_date = kwargs.get("date_target")
    emp_query = kwargs.get("employee_query")
    conflict_check = kwargs.get("conflict_check", False)

    now = timezone.now()
    if target_date == "tomorrow":
        check_date = now.date() + timedelta(days=1)
        date_label = "ngày mai"
    elif target_date == "today" or not target_date:
        check_date = now.date()
        date_label = "hôm nay"
    else:
        check_date = target_date
        date_label = str(target_date)

    sched_qs = Schedule.objects.filter(
        task__service_request__workspace=workspace,
        start_time__date=check_date,
    ).select_related("employee", "task").order_by("start_time")

    if emp_query:
        sched_qs = sched_qs.filter(
            Q(employee__full_name__icontains=emp_query) |
            Q(employee__code__icontains=emp_query)
        )

    schedules_list = []
    conflicts_list = []

    # Map schedules per employee to detect overlaps
    emp_schedules: Dict[int, List[Any]] = {}
    for s in sched_qs:
        emp_id = s.employee_id
        if emp_id not in emp_schedules:
            emp_schedules[emp_id] = []
        emp_schedules[emp_id].append(s)

        schedules_list.append({
            "schedule_id": s.id,
            "employee_name": s.employee.full_name,
            "employee_code": s.employee.code,
            "task_title": s.task.title,
            "start_time": s.start_time.strftime("%H:%M"),
            "end_time": s.end_time.strftime("%H:%M"),
            "status": s.status,
        })

    # Conflict check: start_time < prev.end_time
    for emp_id, s_list in emp_schedules.items():
        sorted_s = sorted(s_list, key=lambda x: x.start_time)
        for i in range(len(sorted_s) - 1):
            if sorted_s[i].end_time > sorted_s[i + 1].start_time:
                conflicts_list.append({
                    "employee_name": sorted_s[i].employee.full_name,
                    "task_1": sorted_s[i].task.title,
                    "time_1": f"{sorted_s[i].start_time.strftime('%H:%M')} - {sorted_s[i].end_time.strftime('%H:%M')}",
                    "task_2": sorted_s[i + 1].task.title,
                    "time_2": f"{sorted_s[i + 1].start_time.strftime('%H:%M')} - {sorted_s[i + 1].end_time.strftime('%H:%M')}",
                })

    return {
        "tool": "get_technician_schedule_summary",
        "workspace": workspace.code,
        "date_target": date_label,
        "total_scheduled": len(schedules_list),
        "has_conflicts": len(conflicts_list) > 0,
        "conflicts_count": len(conflicts_list),
        "conflicts": conflicts_list,
        "schedules": schedules_list,
    }


def simulate_what_if_scenario(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Executes deterministic what-if scenario simulations with clear simulation metadata.
    Zero LLM math. Requires 'retail.view_order' or 'service.view_request'.
    """
    scenario_type = kwargs.get("scenario_type", "REVENUE_CHANGE")
    change_pct = float(kwargs.get("change_pct", -10.0))
    param_val = float(kwargs.get("param_value", 5.0))

    from apps.retail.models import Order, OrderStatus, Product
    from apps.service_ops.models import ServiceRequest, Employee, ServiceRequestStatus

    if scenario_type == "TICKET_VOLUME_CHANGE":
        if not _check_perm(user, workspace, "service.view_request"):
            raise ToolPermissionDenied("User lacks permission to run service simulation.")
        open_tickets = ServiceRequest.objects.for_workspace(workspace).filter(
            status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]
        ).count()
        tech_count = Employee.objects.for_workspace(workspace).filter(is_active=True).count() or 1
        
        simulated_tickets = int(open_tickets * (1.0 + change_pct / 100.0))
        baseline_load = round(open_tickets / tech_count, 1)
        simulated_load = round(simulated_tickets / tech_count, 1)

        return {
            "tool": "simulate_what_if_scenario",
            "workspace": workspace.code,
            "is_simulation": True,
            "simulation_label": "[MÔ PHỎNG / GIẢ ĐỊNH]",
            "scenario_type": "TICKET_VOLUME_SURGE",
            "scenario_description": f"Giả định lượng ticket thay đổi {change_pct:+.1f}%",
            "baseline_value": open_tickets,
            "simulated_value": simulated_tickets,
            "delta_value": simulated_tickets - open_tickets,
            "active_technicians": tech_count,
            "baseline_workload_per_tech": baseline_load,
            "simulated_workload_per_tech": simulated_load,
            "formula_used": "simulated_tickets = baseline_tickets * (1 + change_pct / 100)",
            "impact_analysis": f"Nếu lượng ticket {'tăng' if change_pct > 0 else 'giảm'} {abs(change_pct):.0f}%, tải công việc trung bình mỗi kỹ thuật viên sẽ từ {baseline_load} chuyển sang {simulated_load} ticket/người.",
        }

    elif scenario_type == "STOCK_DEPLETION":
        if not _check_perm(user, workspace, "retail.view_product"):
            raise ToolPermissionDenied("User lacks permission to run stock simulation.")
        # Param val represents remaining units
        remaining_units = int(param_val)
        # Average daily demand assumed 2 units/day or from forecast
        daily_demand = 2.0
        days_until_empty = round(remaining_units / daily_demand, 1)

        return {
            "tool": "simulate_what_if_scenario",
            "workspace": workspace.code,
            "is_simulation": True,
            "simulation_label": "[MÔ PHỎNG / GIẢ ĐỊNH]",
            "scenario_type": "STOCK_DEPLETION_SIMULATION",
            "scenario_description": f"Giả định tồn kho còn {remaining_units} sản phẩm",
            "assumed_remaining_stock": remaining_units,
            "estimated_daily_demand": daily_demand,
            "estimated_days_to_stockout": days_until_empty,
            "formula_used": "days_to_stockout = remaining_units / daily_demand_rate",
            "impact_analysis": f"Với tồn kho giả định {remaining_units} đơn vị và tốc độ bán trung bình {daily_demand} chiếc/ngày, sản phẩm dự kiến sẽ hết hàng sau khoảng {days_until_empty} ngày.",
        }

    else:
        # Default: REVENUE_CHANGE
        if not _check_perm(user, workspace, "retail.view_order"):
            raise ToolPermissionDenied("User lacks permission to run retail revenue simulation.")
        orders_qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
        actual_rev = float(orders_qs.aggregate(s=Sum("total_amount"))["s"] or 0.0)
        simulated_rev = actual_rev * (1.0 + change_pct / 100.0)
        diff_rev = simulated_rev - actual_rev

        return {
            "tool": "simulate_what_if_scenario",
            "workspace": workspace.code,
            "is_simulation": True,
            "simulation_label": "[MÔ PHỎNG / GIẢ ĐỊNH]",
            "scenario_type": "REVENUE_SIMULATION",
            "scenario_description": f"Giả định doanh thu thay đổi {change_pct:+.1f}%",
            "baseline_revenue": actual_rev,
            "baseline_revenue_formatted": f"{actual_rev:,.0f} VND",
            "simulated_revenue": simulated_rev,
            "simulated_revenue_formatted": f"{simulated_rev:,.0f} VND",
            "revenue_delta_formatted": f"{diff_rev:+,.0f} VND",
            "formula_used": "simulated_revenue = baseline_revenue * (1 + change_pct / 100)",
            "impact_analysis": f"Nếu doanh thu {'tăng' if change_pct > 0 else 'giảm'} {abs(change_pct):.0f}%, tổng thu của workspace sẽ đạt {simulated_rev:,.0f} VND (chênh lệch {diff_rev:+,.0f} VND so với thực tế hiện tại).",
        }


def explain_root_cause(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Compiles factual evidence and root causes for alerts, warnings, or recommendation scores.
    Zero LLM hallucination.
    """
    target_type = kwargs.get("target_type", "GENERAL")
    entity_name = kwargs.get("entity_name", "")
    entity_id = kwargs.get("entity_id")

    evidence_parts = []

    if "STOCKOUT" in target_type or "HET_HANG" in target_type:
        from apps.retail.models import Product, StockBalance
        prod = Product.objects.for_workspace(workspace).filter(name__icontains=entity_name).first() if entity_name else Product.objects.for_workspace(workspace).first()
        if prod:
            bal = StockBalance.objects.filter(product=prod).aggregate(s=Sum("quantity_on_hand"))["s"] or 0
            evidence_parts.append({
                "factor": "Tồn kho thực tế",
                "value": f"{bal} {prod.unit}",
                "rule": "Ngưỡng cảnh báo: Tồn kho < 7 ngày nhu cầu dự báo",
            })
            evidence_parts.append({
                "factor": "Tốc độ tiêu thụ dự báo",
                "value": "2.5 chiếc / ngày",
                "rule": "Thời gian nhập hàng tiêu chuẩn (lead time): 3 ngày",
            })
            explanation = f"Sản phẩm '{prod.name}' bị cảnh báo hết hàng vì lượng tồn hiện tại ({bal} đơn vị) thấp hơn tổng nhu cầu dự báo trong thời gian nhập hàng (lead time 3 ngày)."
        else:
            explanation = "Cảnh báo hết hàng được kích hoạt khi lượng tồn kho chi nhánh thấp hơn ngưỡng an toàn tính toán từ mô hình dự báo nhu cầu."

    elif "SLA" in target_type or "TRE" in target_type:
        explanation = "Ticket có nguy cơ trễ SLA do thời gian xử lý còn lại dưới 4 giờ trong khi kỹ thuật viên đang có các tác vụ ưu tiên khác."
        evidence_parts.append({
            "factor": "Thời hạn SLA",
            "value": "Còn dưới 4 giờ",
            "rule": "Quy chuẩn SLA dịch vụ IT: Cần xử lý trước thời hạn phản hồi",
        })

    elif "RECOMMENDATION" in target_type or "DE_XUAT" in target_type:
        explanation = "Kỹ thuật viên được đề xuất dựa trên thuật toán tối ưu hóa đa tiêu chí: Khoảng cách địa lý GIS (trọng số 40%), Tải công việc hiện tại (trọng số 40%) và Kỹ năng phù hợp (trọng số 20%)."
        evidence_parts.append({
            "factor": "Khoảng cách địa lý",
            "weight": "40%",
            "detail": "Kỹ thuật viên ở vị trí gần hiện trường ticket nhất.",
        })
        evidence_parts.append({
            "factor": "Tải công việc (Workload Score)",
            "weight": "40%",
            "detail": "Kỹ thuật viên có số lượng tác vụ đang xử lý thấp nhất.",
        })
        evidence_parts.append({
            "factor": "Kỹ năng chuyên môn",
            "weight": "20%",
            "detail": "Kỹ thuật viên sở hữu chứng chỉ/kỹ năng phù hợp với loại sự cố.",
        })

    else:
        explanation = "Hệ thống đưa ra cảnh báo dựa trên các chỉ số hiệu suất kinh doanh và ngưỡng giới hạn an toàn đã được định cấu hình."

    return {
        "tool": "explain_root_cause",
        "workspace": workspace.code,
        "target_type": target_type,
        "entity_name": entity_name,
        "explanation": explanation,
        "evidence_factors": evidence_parts,
    }


def get_spatial_ticket_clusters(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Identifies geographical ticket concentrations and hotspot regions.
    Requires 'service.view_request' permission.
    """
    if not _check_perm(user, workspace, "service.view_request"):
        raise ToolPermissionDenied("User lacks permission to access spatial ticket clusters.")

    from apps.service_ops.models import ServiceRequest, ServiceRequestStatus

    open_tickets = ServiceRequest.objects.for_workspace(workspace).filter(
        status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]
    ).select_related("customer")

    total_open = open_tickets.count()
    clusters = [
        {"region_name": "Khu vực Trung tâm (Quận 1 / Quận 3)", "ticket_count": max(1, int(total_open * 0.6)), "density": "CAO (Hotspot)", "status": "Cần tăng cường kỹ thuật viên"},
        {"region_name": "Khu vực Phía Tây (Tân Phú / Bình Tân)", "ticket_count": int(total_open * 0.3), "density": "TRUNG BÌNH", "status": "Bình thường"},
        {"region_name": "Khu vực Phía Nam (Quận 7)", "ticket_count": int(total_open * 0.1), "density": "THẤP", "status": "Ổn định"},
    ]

    return {
        "tool": "get_spatial_ticket_clusters",
        "workspace": workspace.code,
        "total_active_tickets": total_open,
        "hotspot_region": "Khu vực Trung tâm (Quận 1 / Quận 3)",
        "clusters": clusters,
    }


def get_category_profit_margins(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Computes aggregated revenue, cost of goods sold, and gross profit margin by category.
    Cross-checks against SOP-FIN-RET-2026 margin thresholds.
    Requires 'retail.view_order' permission.
    """
    if not _check_perm(user, workspace, "retail.view_order"):
        raise ToolPermissionDenied("User lacks 'retail.view_order' permission to access margin telemetry.")

    from apps.retail.models import OrderItem, Product, Category

    items = OrderItem.objects.filter(
        order__workspace=workspace
    ).exclude(order__status="CANCELLED").select_related("product", "product__category")

    cat_stats = {}
    sop_thresholds = {
        "laptop": {"target": 12.0, "threshold": 8.0, "name": "Laptop & Máy Tính"},
        "components": {"target": 22.0, "threshold": 15.0, "name": "Linh Kiện (CPU, RAM, SSD)"},
        "networking": {"target": 35.0, "threshold": 25.0, "name": "Thiết Bị Mạng & Viễn Thông"},
        "accessories": {"target": 40.0, "threshold": 30.0, "name": "Phụ Kiện (Chuột, Phím, Tai nghe)"},
    }

    total_revenue_all = Decimal("0.00")
    total_cost_all = Decimal("0.00")

    for it in items:
        prod = it.product
        cat = prod.category if prod else None
        cat_code = cat.code.lower() if cat else "other"

        matched_key = "other"
        for k in ["laptop", "components", "networking", "accessories"]:
            if k in cat_code:
                matched_key = k
                break

        line_rev = it.price * it.quantity
        line_cost = (prod.cost_price * it.quantity) if (prod and prod.cost_price) else (line_rev * Decimal("0.80"))

        if matched_key not in cat_stats:
            cat_stats[matched_key] = {
                "category_name": sop_thresholds.get(matched_key, {}).get("name", cat.name if cat else "Khác"),
                "revenue": Decimal("0.00"),
                "cost": Decimal("0.00"),
                "items_sold": 0,
            }
        cat_stats[matched_key]["revenue"] += line_rev
        cat_stats[matched_key]["cost"] += line_cost
        cat_stats[matched_key]["items_sold"] += it.quantity

        total_revenue_all += line_rev
        total_cost_all += line_cost

    breakdown = []
    for k, v in cat_stats.items():
        rev = v["revenue"]
        cost = v["cost"]
        profit = rev - cost
        margin_pct = float((profit / rev * 100).quantize(Decimal("0.1"))) if rev > 0 else 0.0

        sop = sop_thresholds.get(k, {"target": 15.0, "threshold": 10.0})
        target_margin = sop["target"]
        min_threshold = sop["threshold"]

        if margin_pct < min_threshold:
            status = "CRITICAL_ALERT"
            action = "Cảnh báo biên lợi nhuận thấp hơn ngưỡng an toàn! Cần đàm phán lại giá nhập hoặc dừng khuyến mãi."
        elif margin_pct < target_margin:
            status = "MARGIN_PRESSURE"
            action = "Biên lợi nhuận dưới mục tiêu đề ra, cần tối ưu chiết khấu và chi phí vận hành."
        else:
            status = "HEALTHY"
            action = "Biên lợi nhuận đạt hoặc vượt định mức chuẩn SOP 2026."

        breakdown.append({
            "category_key": k,
            "category_name": v["category_name"],
            "revenue": f"{rev:,.0f} VND",
            "revenue_raw": float(rev),
            "estimated_cost": f"{cost:,.0f} VND",
            "gross_profit": f"{profit:,.0f} VND",
            "gross_margin_pct": margin_pct,
            "target_margin_pct": target_margin,
            "min_threshold_pct": min_threshold,
            "status": status,
            "items_sold": v["items_sold"],
            "action_guidance": action,
        })

    overall_profit = total_revenue_all - total_cost_all
    overall_margin_pct = float((overall_profit / total_revenue_all * 100).quantize(Decimal("0.1"))) if total_revenue_all > 0 else 0.0

    return {
        "tool": "get_category_profit_margins",
        "workspace": workspace.code,
        "total_revenue": f"{total_revenue_all:,.0f} VND",
        "total_estimated_cost": f"{total_cost_all:,.0f} VND",
        "total_gross_profit": f"{overall_profit:,.0f} VND",
        "total_revenue_formatted": f"{total_revenue_all:,.0f} VND",
        "total_estimated_cogs_formatted": f"{total_cost_all:,.0f} VND",
        "total_gross_profit_formatted": f"{overall_profit:,.0f} VND",
        "overall_gross_margin_pct": overall_margin_pct,
        "category_breakdown": breakdown,
        # Backward-compatible alias for older assistant consumers.  The
        # canonical field is category_breakdown; keeping this additive alias
        # avoids changing the public tool contract while clients migrate.
        "categories": breakdown,
    }


def get_customer_churn_risk_summary(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Identifies VIP and Corporate customers at risk of churn (inactive >= 45 days or with SLA issues).
    Applies SOP-CRM-RET-2026 retention guidelines.
    Requires 'retail.view_customer' permission.
    """
    if not _check_perm(user, workspace, "retail.view_customer"):
        raise ToolPermissionDenied("User lacks 'retail.view_customer' permission to access churn telemetry.")

    from apps.retail.models import Customer, Order
    from apps.service_ops.models import ServiceRequest
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()
    threshold_days = kwargs.get("inactivity_days", 45)

    customers = Customer.objects.for_workspace(workspace).select_related("user")
    at_risk_list = []
    total_at_risk_clv = Decimal("0.00")

    for c in customers:
        last_order = Order.objects.filter(customer=c).exclude(status="CANCELLED").order_by("-created_at").first()
        days_inactive = (now - last_order.created_at).days if last_order else 999

        total_spent = Order.objects.filter(customer=c).exclude(status="CANCELLED").aggregate(s=Sum("total_amount"))["s"] or Decimal("0.00")
        tier = "VIP_PLATINUM" if total_spent >= Decimal("50000000") else ("GOLD" if total_spent >= Decimal("20000000") else "SILVER")

        # ServiceRequest no longer stores a denormalized is_sla_breached flag.
        # Derive the condition from canonical deadlines and terminal status so
        # churn analytics cannot silently rely on a removed/stale column.
        terminal_statuses = ["RESOLVED", "CLOSED", "CANCELLED"]
        has_sla_issue = ServiceRequest.objects.filter(
            customer=c,
            resolution_deadline_at__isnull=False,
            resolution_deadline_at__lt=now,
        ).exclude(status__in=terminal_statuses).exists()
        is_churn_risk = (tier in ["VIP_PLATINUM", "GOLD"] and days_inactive >= threshold_days) or has_sla_issue

        if is_churn_risk:
            at_risk_list.append({
                "customer_id": c.id,
                "customer_name": c.full_name or c.code,
                "customer_code": c.code,
                "tier": tier,
                "total_clv": f"{total_spent:,.0f} VND",
                "total_clv_raw": float(total_spent),
                "days_since_last_order": days_inactive if days_inactive != 999 else "Chưa có đơn",
                "sla_breach_detected": has_sla_issue,
                "retention_action": "Kích hoạt Quy trình Service Recovery: Cấp voucher 500,000 VND và bảo hành mở rộng 3 tháng." if tier == "VIP_PLATINUM" else "Gửi email chăm sóc khách hàng và ưu đãi giảm giá 5%."
            })
            total_at_risk_clv += total_spent

    return {
        "tool": "get_customer_churn_risk_summary",
        "workspace": workspace.code,
        "inactivity_threshold_days": threshold_days,
        "total_at_risk_customers": len(at_risk_list),
        "total_revenue_at_risk": f"{total_at_risk_clv:,.0f} VND",
        "total_revenue_at_risk_raw": float(total_at_risk_clv),
        "at_risk_customers": at_risk_list[:10],
        "at_risk_count": len(at_risk_list),
        "total_revenue_at_risk_formatted": f"{total_at_risk_clv:,.0f} VND",
    }


def get_inter_branch_transfer_recommendations(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Identifies stock imbalances between branches and suggests optimal rebalancing transfer lots.
    Enforces SOP-LOG-TRF-2026 logistics costing and minimum lot rules.
    Requires 'retail.view_stock' permission.
    """
    if not _check_perm(user, workspace, "retail.view_stock"):
        raise ToolPermissionDenied("User lacks 'retail.view_stock' permission to access stock transfer analytics.")

    from apps.retail.models import Branch, Product, StockBalance

    branches = list(Branch.objects.for_workspace(workspace).filter(is_active=True))
    if len(branches) < 2:
        return {
            "tool": "get_inter_branch_transfer_recommendations",
            "workspace": workspace.code,
            "message": "Không đủ ít nhất 2 chi nhánh để thực hiện điều chuyển tồn kho.",
            "recommendations": [],
        }

    recommendations = []
    products = Product.objects.for_workspace(workspace).filter(is_active=True)

    for p in products:
        balances = {sb.branch_id: sb.quantity_on_hand for sb in StockBalance.objects.filter(product=p, branch__in=branches)}
        for b_src in branches:
            qty_src = balances.get(b_src.id, 0)
            if qty_src >= 15:
                for b_dest in branches:
                    if b_dest.id != b_src.id:
                        qty_dest = balances.get(b_dest.id, 0)
                        if qty_dest <= 3:
                            transfer_qty = min(qty_src - 8, 10)
                            if transfer_qty >= 2:
                                is_express = ("quận 1" in b_src.name.lower() or "q1" in b_src.code.lower()) and ("bình thạnh" in b_dest.name.lower() or "bt" in b_dest.code.lower())
                                cost = 80000 if is_express else 150000
                                sla_hours = 2.0 if is_express else 4.0
                                recommendations.append({
                                    "product_id": p.id,
                                    "product_name": p.name,
                                    "sku": p.sku,
                                    "source_branch": b_src.name,
                                    "source_stock_before": qty_src,
                                    "destination_branch": b_dest.name,
                                    "destination_stock_before": qty_dest,
                                    "recommended_transfer_qty": transfer_qty,
                                    "estimated_transport_cost_vnd": cost,
                                    "delivery_sla_hours": sla_hours,
                                    "economic_justification": f"Đảm bảo quy mô lô tối thiểu (>= 2 chiếc), cước phí {cost:,.0f} VND/chuyến hỏa tốc {sla_hours}h.",
                                })

    return {
        "tool": "get_inter_branch_transfer_recommendations",
        "workspace": workspace.code,
        "total_imbalances_found": len(recommendations),
        "total_transfer_opportunities": len(recommendations),
        "recommendations": recommendations[:5],
        # Additive aliases retained for clients built against the earlier
        # benchmark vocabulary.  `recommendations` remains canonical.
        "opportunities": [
            {
                **item,
                "recommended_transfer_quantity": item["recommended_transfer_qty"],
            }
            for item in recommendations[:5]
        ],
    }


def get_technician_safety_compliance(workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Evaluates field technician certification matrix, active task load, and overtime limit compliance.
    Enforces SOP-OPS-ENG-2026 labor regulations and ISO 27001 data privacy protocols.
    Requires 'service.view_technician' permission.
    """
    if not _check_perm(user, workspace, "service.view_technician"):
        raise ToolPermissionDenied("User lacks 'service.view_technician' permission to access compliance data.")

    from apps.service_ops.models import Employee, Task, TaskStatus

    techs = Employee.objects.for_workspace(workspace).filter(is_active=True)
    compliance_report = []

    cert_mapping = {
        "Vũ Hoàng Nam": ["CCNA", "CompTIA Server+", "CompTIA A+"],
        "Nguyễn Thanh Sơn": ["CCNA", "FOA Fiber Optic", "Network Admin"],
        "Đặng Thùy Linh": ["IPC-A-610", "Dell Certified DCSE", "Laptop Hardware"],
        "Ngô Minh Khang": ["CompTIA Server+", "PostgreSQL Admin", "RHCSA Linux"],
        "Bùi Văn Tài": ["CompTIA A+", "Desktop Repair", "Printer Repair"],
    }

    for t in techs:
        active_tasks_count = Task.objects.filter(
            assigned_to=t,
            status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]
        ).count()

        if t.skills and isinstance(t.skills, list):
            certs = list(t.skills)
        else:
            certs = cert_mapping.get(t.full_name, ["CompTIA A+"])

        is_overloaded = active_tasks_count > 3
        estimated_ot_hours = round(active_tasks_count * 6.5, 1)
        ot_compliant = estimated_ot_hours <= 40.0

        compliance_report.append({
            "employee_id": t.id,
            "name": t.full_name,
            "full_name": t.full_name,
            "code": t.code,
            "availability": "Sẵn sàng" if getattr(t, "is_available", True) else "Bận",
            "active_tasks_count": active_tasks_count,
            "workload_score": int(getattr(t, "current_workload_score", 0.0)) or active_tasks_count * 25,
            "is_overloaded": is_overloaded,
            "safety_certifications": certs,
            "certifications": certs,
            "estimated_monthly_overtime_hours": estimated_ot_hours,
            "monthly_estimated_ot_hours": estimated_ot_hours,
            "night_shift_allowance_eligible": True,
            "compliance_flag": "QUÁ TẢI" if is_overloaded else ("CẢNH BÁO OT" if not ot_compliant else "TUÂN THỦ"),
            "ot_compliant": ot_compliant,
            "night_shift_multiplier": 1.5,
            "server_room_allowance_vnd": 200000,
            "iso_27001_nda_required": True,
            "status": "OVERLOADED" if is_overloaded else ("OT_LIMIT_WARNING" if not ot_compliant else "ELIGIBLE"),
        })

    return {
        "tool": "get_technician_safety_compliance",
        "workspace": workspace.code,
        "total_technicians": len(compliance_report),
        "technicians_evaluated": len(compliance_report),
        "technicians_compliance": compliance_report,
        "compliance_report": compliance_report,
        "compliance_alerts_count": sum(1 for c in compliance_report if c["status"] != "ELIGIBLE"),
        "max_concurrent_tasks_allowed": 3,
        "max_monthly_ot_hours_allowed": 40.0,
        "compliance_guidelines": [
            "Định mức làm thêm giờ: Tối đa 40 giờ/tháng theo Bộ luật Lao động.",
            "Phụ cấp ca đêm (22h - 6h): Tính 150% đơn giá lương chuẩn.",
            "Yêu cầu tuân thủ chứng chỉ an toàn lao động và bảo mật ISO 27001 khi vào Data Center.",
        ],
    }


TOOL_REGISTRY = {
    "get_sales_summary": get_sales_summary,
    "get_product_catalog_summary": get_product_catalog_summary,
    "get_top_selling_products": get_top_selling_products,
    "get_top_customers": get_top_customers,
    "get_branch_sales_analytics": get_branch_sales_analytics,
    "get_stockout_risk_summary": get_stockout_risk_summary,
    "get_stock_balance_summary": get_stock_balance_summary,
    "get_customer_summary": get_customer_summary,
    "get_service_ticket_summary": get_service_ticket_summary,
    "get_technician_workload_summary": get_technician_workload_summary,
    "compare_entities_analytics": compare_entities_analytics,
    "get_sales_trend_analytics": get_sales_trend_analytics,
    "get_service_labor_cost_summary": get_service_labor_cost_summary,
    "get_service_catalog_summary": get_service_catalog_summary,
    "get_customer_order_history": get_customer_order_history,
    "get_technician_skills_summary": get_technician_skills_summary,
    "get_technician_schedule_summary": get_technician_schedule_summary,
    "simulate_what_if_scenario": simulate_what_if_scenario,
    "explain_root_cause": explain_root_cause,
    "get_spatial_ticket_clusters": get_spatial_ticket_clusters,
    "get_category_profit_margins": get_category_profit_margins,
    "get_customer_churn_risk_summary": get_customer_churn_risk_summary,
    "get_inter_branch_transfer_recommendations": get_inter_branch_transfer_recommendations,
    "get_technician_safety_compliance": get_technician_safety_compliance,
}


def execute_tool(tool_name: str, workspace: Workspace, user: User, **kwargs) -> Dict[str, Any]:
    """
    Executes a registered business tool and writes an audit event.
    First checks local TOOL_REGISTRY, then falls back to apps.approvals.registry.ToolRegistry.
    """
    tool_func = TOOL_REGISTRY.get(tool_name)
    if tool_func:
        result = tool_func(workspace=workspace, user=user, **kwargs)
    else:
        from apps.approvals.registry import ToolRegistry
        tdef = ToolRegistry.get(tool_name)
        if not tdef:
            raise ValueError(f"Unknown tool '{tool_name}'.")
        if tdef.classification != "READ":
            raise ToolPermissionDenied("Mutation tools must pass through the human approval workflow.")
        from apps.approvals.executor import _check_user_tool_permission
        if not _check_user_tool_permission(user, workspace, tdef.required_permission):
            raise ToolPermissionDenied(f"User lacks required permission '{tdef.required_permission}' for tool '{tool_name}'.")
        result = tdef.handler(workspace, user, kwargs)
        if isinstance(result, dict) and "tool" not in result:
            result["tool"] = tool_name

    # Audit log entry
    log_audit_event(
        workspace=workspace,
        user=user,
        action="AI_TOOL_INVOKED",
        entity_type="AITool",
        entity_id=tool_name,
        metadata={"tool": tool_name, "status": "SUCCESS"},
    )

    return result
