"""HTTP boundary for the fixed, synthetic algorithm lab."""
import re
from threading import Lock
from time import perf_counter
from urllib.parse import parse_qsl
from uuid import UUID

from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.internal_access import can_access_internal
from apps.accounts.services import get_user_permissions
from apps.forecasting.demo_lab import DEMO_CASES, run_demo_case
from apps.workspaces.models import Workspace, WorkspaceMembership


DEMO_PAGE_NAME = "noibo_ai_demo"
DEMO_RUN_NAME = "noibo_ai_demo_run"
REVENUE_RESEARCH_NAME = "noibo_revenue_research"
MAX_BODY_BYTES = 512
FORECAST_PERMISSION = "forecasting.manage_forecast"
WORKSPACE_QUERY_FIELDS = {"workspace_id", "workspace"}
_execution_lock = Lock()


def _problem(status, code, detail):
    return JsonResponse({"error": code, "detail": detail}, status=status)


def _invalid_form():
    return _problem(400, "invalid_form", "Chỉ gửi một kịch bản mô phỏng hợp lệ, tối đa 512 byte.")


class AiDemoBoundaryMiddleware(MiddlewareMixin):
    """Bound the lab body before CSRF form parsing; mark even early errors no-store."""

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.resolver_match.url_name not in (DEMO_RUN_NAME, REVENUE_RESEARCH_NAME) or request.method != "POST":
            return None
        length = request.META.get("CONTENT_LENGTH", "")
        if not re.fullmatch(r"[0-9]{1,3}", length) or not 1 <= int(length) <= MAX_BODY_BYTES:
            return _invalid_form()
        # Buffer only after checking the advertised size; do not parse or
        # exempt the body from Django's normal CSRF middleware.
        if len(request.body) != int(length):
            return _invalid_form()
        return None

    def process_response(self, request, response):
        match = request.resolver_match
        if match and match.url_name in (DEMO_PAGE_NAME, DEMO_RUN_NAME, REVENUE_RESEARCH_NAME):
            add_never_cache_headers(response)
        return response


def _matches_uuid(value, workspace_id):
    try:
        return UUID(value) == workspace_id
    except (ValueError, TypeError):
        return False


def _selectors_match(request, workspace):
    # Only middleware selects the workspace. Additional explicit selectors may
    # confirm that selection, but cannot replace it (even if authorized there).
    workspace_id = request.headers.get("X-Workspace-ID")
    if workspace_id is not None and not _matches_uuid(workspace_id, workspace.pk):
        return False
    code = request.headers.get("X-Workspace")
    if code is not None and (not code or code != workspace.code):
        return False
    for field in WORKSPACE_QUERY_FIELDS:
        query_ids = request.GET.getlist(field)
        if query_ids and (len(query_ids) != 1 or not _matches_uuid(query_ids[0], workspace.pk)):
            return False
    return True


def can_use_ai_demo(request):
    """Require an eligible identity and current rights in the verified workspace."""
    workspace = getattr(request, "active_workspace", None)
    if (not workspace or not workspace.is_active or getattr(request, "workspace_access_denied", False)
            or not _selectors_match(request, workspace) or not can_access_internal(request)):
        return False
    if request.user.is_superuser:
        return Workspace.objects.filter(pk=workspace.pk, is_active=True).exists()
    return WorkspaceMembership.objects.filter(
        Q(role__name__iexact="MANAGER") | Q(role__name__iexact="ADMIN"),
        workspace_id=workspace.pk,
        workspace__is_active=True,
        user=request.user,
        is_active=True,
        role__permissions__codename=FORECAST_PERMISSION,
    ).exists()


def _denied():
    return _problem(403, "access_denied", "Bạn không có quyền dùng phòng mô phỏng ở không gian làm việc hiện tại.")


@require_POST
def revenue_research(request):
    if not can_use_ai_demo(request) or request.active_workspace.workspace_type != "RETAIL":
        return _denied()
    if set(request.GET) - WORKSPACE_QUERY_FIELDS or request.content_type != "application/x-www-form-urlencoded":
        return _invalid_form()
    if request.body != b"run=1":
        return _invalid_form()
    if not _execution_lock.acquire(blocking=False):
        return _problem(409, "busy", "Hệ thống đang bận; vui lòng thử lại sau.")
    try:
        from apps.forecasting.revenue_research import evaluate_revenue_xgboost
        result = evaluate_revenue_xgboost(request.active_workspace)
        return JsonResponse(result, json_dumps_params={"allow_nan": False})
    except ValueError:
        return _problem(400, "insufficient_data", "Không đủ dữ liệu hợp lệ để chạy thử nghiệm XGBoost.")
    except Exception:
        return _problem(503, "unavailable", "Không thể chạy thử nghiệm XGBoost lúc này.")
    finally:
        _execution_lock.release()


@require_GET
def ai_demo_page(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not can_use_ai_demo(request):
        return _denied()
    permissions = get_user_permissions(request.user, request.active_workspace) if not request.user.is_superuser else set()
    return render(request, "forecasting/demo_lab.html", {
        "active_nav": "ai_demo",
        "demo_cases": DEMO_CASES.items(),
        "demo_can_view_recommendations": request.user.is_superuser or "recommendations.view_recommendation" in permissions,
        "demo_can_view_approvals": request.user.is_superuser or "approvals.view_approval" in permissions,
    })


def _parse_case(body):
    if not 0 < len(body) <= MAX_BODY_BYTES:
        raise ValueError("Invalid form size")
    text = body.decode("utf-8")
    if re.search(r"%(?![0-9a-fA-F]{2})", text):
        raise ValueError("Invalid form encoding")
    pairs = parse_qsl(text, keep_blank_values=True, strict_parsing=True, max_num_fields=2, errors="strict")
    fields = dict(pairs)
    if (len(fields) != len(pairs) or fields.keys() - {"case", "csrfmiddlewaretoken"}
            or fields.get("case") not in DEMO_CASES):
        raise ValueError("Invalid form fields")
    return fields["case"]


@require_POST
def ai_demo_run(request):
    if not can_use_ai_demo(request):
        return _denied()
    if set(request.GET) - WORKSPACE_QUERY_FIELDS:
        return _invalid_form()
    if request.content_type != "application/x-www-form-urlencoded":
        return _problem(415, "invalid_media_type", "Chỉ chấp nhận biểu mẫu của phòng mô phỏng.")
    try:
        case = _parse_case(request.body)
    except ValueError:
        return _invalid_form()
    if not _execution_lock.acquire(blocking=False):
        return _problem(409, "busy", "Phòng mô phỏng đang bận. Vui lòng thử lại bằng nút chạy.")
    try:
        started = perf_counter()
        result = run_demo_case(case)
        return JsonResponse({
            **result,
            "executed_at": timezone.now().isoformat(),
            "elapsed_seconds": round(perf_counter() - started, 6),
        }, json_dumps_params={"allow_nan": False})
    except Exception:
        # Fixed assets and native inference can raise multiple exception types.
        # Never include paths, provider credentials or partial results.
        return _problem(503, "unavailable", "Chưa thể chạy kịch bản mô phỏng. Vui lòng thử lại sau.")
    finally:
        _execution_lock.release()
