"""
Core System Views for Health Check and Platform Status.
"""

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db import connection

from django.utils import timezone
import sys
import django
import os


def _report_workspaces(user, surface):
    """Select only workspaces granting every capability used by this surface."""
    from django.core.exceptions import PermissionDenied
    from apps.accounts.services import has_workspace_permission
    from apps.notifications.services import get_user_authorized_workspaces

    workspaces = get_user_authorized_workspaces(user)
    if user.is_superuser:
        return workspaces
    allowed = []
    for workspace in workspaces:
        if surface == "csv":
            permissions = ("retail.view_order", "retail.view_customer")
        elif surface == "telemetry":
            permissions = ("gis.view_spatial_layers", "forecasting.view_forecast", "knowledge.view_knowledge", "approvals.view_approval")
        else:
            permissions = ("forecasting.view_forecast", "approvals.view_approval")
            permissions += (("retail.view_analytics", "retail.view_order", "retail.view_product", "retail.view_customer", "retail.view_branch")
                            if workspace.workspace_type == "RETAIL" else
                            ("service.view_analytics", "service.view_employee", "service.view_request"))
        if all(has_workspace_permission(user, workspace, permission) for permission in permissions):
            allowed.append(workspace.pk)
    if not allowed:
        raise PermissionDenied("Bạn không có quyền xem báo cáo này.")
    return workspaces.filter(pk__in=allowed)


def get_health_status():
    """Evaluate system dependencies and connectivity status."""
    db_status = "unknown"
    db_error = None
    postgis_status = "not_checked"

    # Test Database Connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            db_status = "connected"

            # Check PostGIS extension
            try:
                cursor.execute("SELECT PostGIS_Version();")
                postgis_version = cursor.fetchone()
                if postgis_version:
                    postgis_status = f"available ({postgis_version[0]})"
            except Exception:
                postgis_status = "extension_not_installed_or_disabled"
    except Exception:
        db_status = "disconnected"
        db_error = "database_unavailable"

    status_data = {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": timezone.now().isoformat(),
        "platform": "Intelligent Business Operations Platform",
        "version": "1.0.0-final",
        "environment": {
            "python_version": sys.version.split()[0],
            "django_version": django.get_version(),
            "debug_mode": os.getenv("DEBUG", "True").lower() in ("true", "1"),
        },
        "database": {
            "engine": connection.settings_dict.get("ENGINE", ""),
            "name": "redacted",
            "host": "redacted",
            "port": "redacted",
            "status": db_status,
            "error": db_error,
            "postgis": postgis_status,
        },
        "phase": {
            "current": "Production readiness baseline (local verified)",
            "status": "LOCAL VERIFIED / EXTERNAL GATES PENDING",
            "total_phases": 13,
            "completed_phases": 12,
            "next": "Staging, credential rotation, HTTPS OAuth/email, observability and restore evidence",
        },
    }
    return status_data


from django.contrib.auth.decorators import login_required


def health_check_api_view(request):
    """API endpoint returning health status JSON (GET /health/ and /api/health/)."""
    status_data = get_health_status()
    http_status = 200 if status_data["status"] == "healthy" else 503
    return JsonResponse(status_data, status=http_status)


def health_check_ui_view(request):
    """HTML status dashboard page (GET /status/). Preserves dedicated status/health route."""
    status_data = get_health_status()
    return render(request, "health.html", {"health": status_data, "active_tab": "health"})


@login_required(login_url="/accounts/login/")
def root_dashboard_ui_view(request):
    """
    Internal Business Management Portal Unified Dashboard (GET /noibo/).
    Requires authentication and internal workspace membership.
    Aggregates metrics and activities across ALL authorized workspaces (Retail + IT Services)
    so internal administrators do not need to switch workspaces.
    """
    from apps.workspaces.models import WorkspaceMembership
    from apps.notifications.services import get_user_authorized_workspaces

    if not request.user.is_superuser:
        has_internal_role = WorkspaceMembership.objects.filter(user=request.user, is_active=True).exists()
        if not has_internal_role:
            return redirect("/tai-khoan/?notice=customer_only")

    status_data = get_health_status()
    authorized_workspaces = get_user_authorized_workspaces(request.user)

    from apps.accounts.services import has_workspace_permission

    def permitted(*permissions):
        return authorized_workspaces.filter(pk__in=[
            ws.pk for ws in authorized_workspaces
            if all(has_workspace_permission(request.user, ws, p) for p in permissions)
        ])

    retail_scope = permitted("retail.view_analytics", "retail.view_order", "retail.view_product", "retail.view_branch")
    service_scope = permitted("service.view_analytics", "service.view_request", "service.view_service", "service.view_employee")
    order_activity_scope = permitted("retail.view_order", "retail.view_customer")
    customer_scope = permitted("retail.view_customer")
    request_scope = permitted("service.view_request")
    forecast_scope = permitted("forecasting.view_forecast")
    recommendation_scope = permitted("recommendations.view_recommendation")
    approval_scope = permitted("approvals.view_approval")

    from decimal import Decimal
    from django.db.models import Sum, Q
    from django.utils import timezone

    now = timezone.now()

    # 1. Retail Domain Metrics across authorized workspaces
    try:
        from apps.retail.models import Product, Order, OrderStatus, Branch, Customer
        retail_orders = Order.objects.filter(workspace__in=retail_scope)
        revenue_agg = retail_orders.filter(
            status__in=[OrderStatus.CONFIRMED, OrderStatus.COMPLETED]
        ).aggregate(total=Sum("total_amount"))

        retail_metrics = {
            "products_count": Product.objects.filter(workspace__in=retail_scope).count(),
            "new_orders_count": retail_orders.filter(status__in=[OrderStatus.PENDING, OrderStatus.CONFIRMED]).count(),
            "total_orders_count": retail_orders.count(),
            "total_revenue": revenue_agg["total"] or Decimal("0.00"),
            "branches_count": Branch.objects.filter(workspace__in=retail_scope).count(),
        }
    except Exception:
        retail_metrics = {
            "products_count": 0,
            "new_orders_count": 0,
            "total_orders_count": 0,
            "total_revenue": Decimal("0.00"),
            "branches_count": 0,
        }

    # 2. Service Domain Metrics across authorized workspaces
    try:
        from apps.service_ops.models import Service, ServiceRequest, ServiceRequestStatus, Employee
        service_requests = ServiceRequest.objects.filter(workspace__in=service_scope)
        active_requests = service_requests.filter(
            status__in=[ServiceRequestStatus.OPEN, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]
        )

        sla_risk_count = 0
        for req in active_requests:
            if req.resolution_deadline_at and req.resolution_deadline_at <= now:
                sla_risk_count += 1
            elif req.response_deadline_at and not req.responded_at and req.response_deadline_at <= now:
                sla_risk_count += 1
            elif req.resolution_deadline_at and (req.resolution_deadline_at - now).total_seconds() <= 7200:
                sla_risk_count += 1

        service_metrics = {
            "services_count": Service.objects.filter(workspace__in=service_scope).count(),
            "new_requests_count": service_requests.filter(status=ServiceRequestStatus.OPEN).count(),
            "in_progress_count": service_requests.filter(
                status__in=[ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.IN_PROGRESS]
            ).count(),
            "sla_risk_count": sla_risk_count,
            "technicians_count": Employee.objects.filter(workspace__in=service_scope, is_active=True).count(),
            "total_tickets_count": service_requests.count(),
        }
    except Exception:
        service_metrics = {
            "services_count": 0,
            "new_requests_count": 0,
            "in_progress_count": 0,
            "sla_risk_count": 0,
            "technicians_count": 0,
            "total_tickets_count": 0,
        }

    # 3. AI Insights & Governance across authorized workspaces
    try:
        from apps.forecasting.models import ForecastModelConfig, ForecastRun
        from apps.recommendations.models import Recommendation, RecommendationStatus
        from apps.approvals.models import ApprovalRequest, ApprovalStatus

        ai_insights = {
            "active_forecasts_count": ForecastModelConfig.objects.filter(workspace__in=forecast_scope, is_active=True).count(),
            "pending_recommendations_count": Recommendation.objects.filter(workspace__in=recommendation_scope, status=RecommendationStatus.PENDING).count(),
            "pending_approvals_count": ApprovalRequest.objects.filter(workspace__in=approval_scope, status=ApprovalStatus.PENDING).count(),
            "latest_recommendations": list(Recommendation.objects.filter(workspace__in=recommendation_scope, status=RecommendationStatus.PENDING).select_related("workspace").order_by("-created_at")[:3]),
        }
    except Exception:
        ai_insights = {
            "active_forecasts_count": 0,
            "pending_recommendations_count": 0,
            "pending_approvals_count": 0,
            "latest_recommendations": [],
        }

    # 4. Unified Recent Activity Feed across both domains
    recent_activities = []
    try:
        from apps.notifications.models import Notification, NotificationEventType

        # Recent Orders
        for o in Order.objects.filter(workspace__in=order_activity_scope).select_related("customer", "workspace").order_by("-created_at")[:6]:
            recent_activities.append({
                "type": "order",
                "badge_icon": "🛒",
                "domain_code": o.workspace.code,
                "domain_name": o.workspace.name,
                "title": f"Đơn hàng #{o.order_number}",
                "description": f"Khách hàng: {o.customer.name} · {o.total_amount:,.0f} VND",
                "status_label": o.get_status_display(),
                "status_badge": "badge-success" if o.status == OrderStatus.COMPLETED else ("badge-warning" if o.status == OrderStatus.PENDING else "badge-primary"),
                "timestamp": o.created_at,
                "url": f"/noibo/retail/orders/{o.id}/",
            })

        # Recent Service Requests
        for sr in ServiceRequest.objects.filter(workspace__in=request_scope).select_related("customer", "workspace").order_by("-created_at")[:6]:
            recent_activities.append({
                "type": "service_request",
                "badge_icon": "⚙️",
                "domain_code": sr.workspace.code,
                "domain_name": sr.workspace.name,
                "title": f"Sự cố #{sr.request_number}: {sr.title[:40]}",
                "description": f"Khách hàng: {sr.customer.name} · Ưu tiên: {sr.get_priority_display()}",
                "status_label": sr.get_status_display(),
                "status_badge": "badge-danger" if sr.priority in ["CRITICAL", "HIGH"] else "badge-info",
                "timestamp": sr.created_at,
                "url": f"/noibo/services/requests/{sr.id}/",
            })

        # Recent Customers
        for c in Customer.objects.filter(workspace__in=customer_scope).select_related("workspace").order_by("-created_at")[:4]:
            recent_activities.append({
                "type": "customer",
                "badge_icon": "👤",
                "domain_code": c.workspace.code,
                "domain_name": c.workspace.name,
                "title": f"Khách hàng mới: {c.name}",
                "description": f"Mã: {c.code} · SĐT: {c.phone or 'N/A'}",
                "status_label": "Đã tạo",
                "status_badge": "badge-primary",
                "timestamp": c.created_at,
                "url": "/noibo/retail/customers/",
            })

        # Recent Web Contacts
        for n in Notification.objects.filter(recipient=request.user, workspace__in=authorized_workspaces, event_type=NotificationEventType.NEW_CONTACT).select_related("workspace").order_by("-created_at")[:4]:
            recent_activities.append({
                "type": "contact",
                "badge_icon": "📩",
                "domain_code": n.workspace.code,
                "domain_name": n.workspace.name,
                "title": n.title,
                "description": n.message[:80],
                "status_label": "Liên hệ web",
                "status_badge": "badge-info",
                "timestamp": n.created_at,
                "url": "/noibo/thong-bao/?type=NEW_CONTACT",
            })

        recent_activities.sort(key=lambda item: item["timestamp"], reverse=True)
        recent_activities = recent_activities[:10]
    except Exception:
        recent_activities = []

    if not retail_scope.exists():
        retail_metrics = {key: "—" for key in retail_metrics}
    if not service_scope.exists():
        service_metrics = {key: "—" for key in service_metrics}
    for scope, key in ((forecast_scope, "active_forecasts_count"), (recommendation_scope, "pending_recommendations_count"), (approval_scope, "pending_approvals_count")):
        if not scope.exists():
            ai_insights[key] = "—"

    context = {
        "active_tab": "dashboard",
        "health": status_data,
        "retail": retail_metrics,
        "service": service_metrics,
        "ai_insights": ai_insights,
        "recent_activities": recent_activities,
        "authorized_workspaces": authorized_workspaces,
    }
    return render(request, "dashboard/main.html", context)


import csv
import hashlib
import time
from django.http import HttpResponse


def _csv_text(value):
    """Prevent spreadsheet software interpreting untrusted text as formulas."""
    value = str(value or "")
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


def _forecast_improvement(mae, baseline_mae):
    import math
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
           for value in (mae, baseline_mae)):
        return None
    if mae < 0 or baseline_mae <= 0:
        return None
    return round((baseline_mae - mae) / baseline_mae * 100, 1)


@login_required(login_url="/accounts/login/")
def executive_operational_report_ui_view(request):
    """
    Executive Operational Report View (GET /noibo/bao-cao-dieu-hanh/).
    Provides an enterprise printable A4 digest synthesizing cross-domain KPIs,
    XGBoost 14-day forecast, service SLA compliance, GIS branch radii, and HITL approvals.
    """
    from apps.workspaces.models import WorkspaceMembership
    from apps.notifications.services import get_user_authorized_workspaces

    if not request.user.is_superuser:
        has_internal_role = WorkspaceMembership.objects.filter(user=request.user, is_active=True).exists()
        if not has_internal_role:
            return redirect("/tai-khoan/?notice=customer_only")

    authorized_workspaces = _report_workspaces(request.user, "report")
    now = timezone.now()

    from decimal import Decimal
    from django.db.models import Sum
    from apps.retail.models import Product, Order, OrderStatus, Branch, Customer
    from apps.service_ops.models import ServiceRequest, ServiceRequestStatus, Employee
    from apps.forecasting.models import ForecastRun
    from apps.approvals.models import ApprovalRequest

    # 1. Retail Aggregations
    retail_orders = Order.objects.filter(workspace__in=authorized_workspaces)
    total_rev = retail_orders.filter(status=OrderStatus.COMPLETED).aggregate(s=Sum("total_amount"))["s"] or Decimal("0.00")
    completed_orders_cnt = retail_orders.filter(status=OrderStatus.COMPLETED).count()
    aov = (total_rev / completed_orders_cnt) if completed_orders_cnt > 0 else Decimal("0.00")
    total_products = Product.objects.filter(workspace__in=authorized_workspaces).count()
    total_customers = Customer.objects.filter(workspace__in=authorized_workspaces).count()

    # 2. Service Aggregations
    service_requests = ServiceRequest.objects.filter(workspace__in=authorized_workspaces)
    total_tickets = service_requests.count()
    resolved_tickets = service_requests.filter(status=ServiceRequestStatus.RESOLVED).count()
    resolution_rate = round((resolved_tickets / total_tickets * 100), 1) if total_tickets else None
    active_technicians = Employee.objects.filter(workspace__in=authorized_workspaces, is_active=True).count()

    # 3. XGBoost Latest Runs
    forecast_runs = []
    latest_completed_runs = ForecastRun.objects.filter(
        workspace__in=authorized_workspaces, status="COMPLETED"
    ).order_by("-created_at")[:4]
    for r in latest_completed_runs:
        m = r.model_metrics or {}
        b = r.baseline_metrics or {}
        forecast_runs.append({
            "target_name": r.model_config.get_target_type_display(),
            "workspace": r.workspace.name,
            "mae": m.get("mae"),
            "rmse": m.get("rmse"),
            "mape": m.get("mape"),
            "r2": m.get("r2"),
            "baseline_mae": b.get("naive_mae", b.get("mae")),
            "improvement_pct": _forecast_improvement(m.get("mae"), b.get("naive_mae", b.get("mae"))),
        })

    # 4. GIS Summary
    branches = list(Branch.objects.filter(workspace__in=authorized_workspaces)[:5])
    branch_count = Branch.objects.filter(workspace__in=authorized_workspaces).count()

    # 5. Controlled Approvals Summary
    recent_approvals = list(
        ApprovalRequest.objects.filter(workspace__in=authorized_workspaces)
        .select_related("workspace", "requester", "reviewer")
        .order_by("-created_at")[:5]
    )

    # Display reference only: this is not a signature or content verification.
    raw_signature_data = f"EXEC_REPORT_{now.strftime('%Y%m%d%H%M')}_{total_rev}_{total_tickets}_{request.user.id}"
    report_hash = hashlib.sha256(raw_signature_data.encode("utf-8")).hexdigest()[:16].upper()

    context = {
        "active_tab": "executive_report",
        "now": now,
        "report_id": f"REP-HCMUNRE-{now.strftime('%Y%m%d')}-{report_hash[:6]}",
        "verification_hash": report_hash,
        "operator": request.user,
        "authorized_workspaces": authorized_workspaces,
        "retail": {
            "total_revenue": total_rev,
            "completed_orders": completed_orders_cnt,
            "total_orders": retail_orders.count(),
            "aov": aov,
            "total_products": total_products,
            "total_customers": total_customers,
            "branches": branches,
            "branch_count": branch_count,
        },
        "service": {
            "total_tickets": total_tickets,
            "resolved_tickets": resolved_tickets,
            "resolution_rate": resolution_rate,
            "active_technicians": active_technicians,
        },
        "forecast_runs": forecast_runs,
        "recent_approvals": recent_approvals,
    }
    return render(request, "dashboard/executive_report.html", context)


@login_required(login_url="/accounts/login/")
def export_report_csv_view(request):
    """
    Exports summary operational orders and KPIs as CSV formatted with UTF-8 BOM for Excel compatibility.
    (GET /noibo/bao-cao-dieu-hanh/export-csv/)
    """
    from apps.workspaces.models import WorkspaceMembership
    from apps.notifications.services import get_user_authorized_workspaces

    if not request.user.is_superuser:
        has_internal_role = WorkspaceMembership.objects.filter(user=request.user, is_active=True).exists()
        if not has_internal_role:
            return redirect("/tai-khoan/?notice=customer_only")

    authorized_workspaces = _report_workspaces(request.user, "csv")
    from apps.retail.models import Order

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"bao_cao_van_hanh_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    # UTF-8 BOM for Excel Vietnamese display
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow(["BAO CAO TONG HOP DON HANG VA VAN HANH DOANH NGHIEP"])
    writer.writerow(["Thoi diem xuat", timezone.now().strftime("%d/%m/%Y %H:%M:%S")])
    writer.writerow(["Nguoi xuat", _csv_text(request.user.username)])
    writer.writerow([])

    writer.writerow([
        "Ma don hang",
        "Don vi kinh doanh",
        "Khach hang",
        "So dien thoai",
        "Tong gia tri (VND)",
        "Trang thai",
        "Thoi gian tao",
    ])

    orders = Order.objects.filter(workspace__in=authorized_workspaces).select_related("workspace", "customer").order_by("-created_at")[:100]
    for o in orders:
        writer.writerow([
            _csv_text(o.order_number),
            _csv_text(o.workspace.name),
            _csv_text(o.customer.name if o.customer else "N/A"),
            _csv_text(o.customer.phone if o.customer else "N/A"),
            f"{o.total_amount:,.0f}",
            o.get_status_display(),
            o.created_at.strftime("%d/%m/%Y %H:%M"),
        ])

    return response


@login_required(login_url="/accounts/login/")
def system_telemetry_ui_view(request):
    """
    Enterprise AI & GIS Telemetry Studio (GET /noibo/telemetry/).
    Provides real-time observability over PostGIS spatial connections,
    XGBoost model inference latency, pgvector Knowledge Base metrics, and RBAC posture.
    """
    from apps.workspaces.models import WorkspaceMembership
    from apps.notifications.services import get_user_authorized_workspaces

    if not request.user.is_superuser:
        has_internal_role = WorkspaceMembership.objects.filter(user=request.user, is_active=True).exists()
        if not has_internal_role:
            return redirect("/tai-khoan/?notice=customer_only")

    authorized_workspaces = _report_workspaces(request.user, "telemetry")

    # 1. PostGIS Connection & Spatial Table Metrics
    postgis_version = "Chưa xác minh phiên bản PostGIS"
    db_engine = connection.settings_dict.get("ENGINE", "")
    db_name = connection.settings_dict.get("NAME", "")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Full_Version();")
            row = cursor.fetchone()
            if row:
                postgis_version = row[0][:80]
    except Exception:
        pass

    from apps.retail.models import Branch, Customer
    from apps.service_ops.models import Employee
    spatial_stats = {
        "engine": db_engine,
        "database": db_name,
        "postgis_version": postgis_version,
        "srid": 4326,
        "branches_geocoded": Branch.objects.filter(workspace__in=authorized_workspaces, location__isnull=False).count(),
        "customers_geocoded": Customer.objects.filter(workspace__in=authorized_workspaces, location__isnull=False).count(),
        "technicians_geocoded": Employee.objects.filter(workspace__in=authorized_workspaces, current_location__isnull=False).count(),
    }

    # 2. XGBoost Machine Learning Model Latency & Status
    from apps.forecasting.models import ForecastModelConfig, ForecastRun
    t0 = time.perf_counter()
    trained_runs_count = ForecastRun.objects.filter(workspace__in=authorized_workspaces, status="COMPLETED").count()
    xgb_bench_latency = round((time.perf_counter() - t0) * 1000, 2)

    ml_stats = {
        "framework": "XGBoost Regressor v2.0 (Scikit-Learn API)",
        "models_configured": ForecastModelConfig.objects.filter(workspace__in=authorized_workspaces).count(),
        "runs_completed": trained_runs_count,
        "count_query_latency_ms": xgb_bench_latency,
        "drift_status": "Chưa đánh giá trong phiên đo này",
        "last_evaluation_gain": "Chưa tổng hợp từ kết quả đánh giá",
    }

    # 3. Grounded RAG Knowledge Base & pgvector Stats
    from apps.knowledge.models import KnowledgeBase, Document, DocumentChunk
    t_rag = time.perf_counter()
    total_chunks = DocumentChunk.objects.filter(document__knowledge_base__workspace__in=authorized_workspaces).count()
    rag_bench_latency = round((time.perf_counter() - t_rag) * 1000, 2)

    rag_stats = {
        "vector_engine": "PostgreSQL pgvector (Cosine Distance <->)",
        "embedding_dimensions": 768,
        "knowledge_bases": KnowledgeBase.objects.filter(workspace__in=authorized_workspaces).count(),
        "documents_ingested": Document.objects.filter(knowledge_base__workspace__in=authorized_workspaces).count(),
        "chunks_indexed": total_chunks,
        "count_query_latency_ms": rag_bench_latency,
        "grounded_accuracy": "Chưa đo trong phiên này",
        "retrieval_hit_rate": "Chưa đo trong phiên này",
    }

    # 4. Human-in-the-loop & RBAC Governance
    from apps.approvals.models import ApprovalRequest
    from apps.audit.models import AuditLog
    governance_stats = {
        "hitl_enforced": True,
        "approval_requests_count": ApprovalRequest.objects.filter(workspace__in=authorized_workspaces).count(),
        "audit_logs_count": AuditLog.objects.filter(workspace__in=authorized_workspaces).count(),
        "workspaces_active": authorized_workspaces.count(),
    }

    context = {
        "active_tab": "telemetry",
        "spatial": spatial_stats,
        "ml": ml_stats,
        "rag": rag_stats,
        "governance": governance_stats,
        "authorized_workspaces": authorized_workspaces,
    }
    return render(request, "dashboard/telemetry.html", context)
