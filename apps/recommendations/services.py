from django.db import transaction

from apps.approvals.executor import execute_tool
from apps.approvals.models import ApprovalRequest
from apps.approvals.registry import ToolValidationError, validate_action_contract
from apps.approvals.registry import ToolRegistry
from apps.recommendations.models import Recommendation, RecommendationStatus, RecommendationType
from django.utils import timezone
import datetime


def dispatch_evidence_snapshot(workspace, ticket_id, employee_id):
    from apps.service_ops.models import ServiceRequest, Employee, Task
    ticket = ServiceRequest.objects.for_workspace(workspace).filter(pk=ticket_id).first()
    employee = Employee.objects.for_workspace(workspace).filter(pk=employee_id).first()
    if not ticket or not employee:
        return None
    return {
        'ticket_status': ticket.status, 'assigned_employee_id': ticket.assigned_employee_id,
        'ticket_location': ticket.location.ewkt if ticket.location else None,
        'ticket_latitude': str(ticket.latitude), 'ticket_longitude': str(ticket.longitude),
        'response_deadline_at': ticket.response_deadline_at.isoformat() if ticket.response_deadline_at else None,
        'resolution_deadline_at': ticket.resolution_deadline_at.isoformat() if ticket.resolution_deadline_at else None,
        'employee_location': employee.current_location.ewkt if employee.current_location else None,
        'employee_available': employee.is_available, 'employee_active': employee.is_active,
        'employee_skills': employee.skills,
        'active_tasks': Task.objects.filter(service_request__workspace=workspace, assigned_to=employee,
                                            status__in=['PENDING', 'IN_PROGRESS']).count(),
    }


def _stockout_evidence_is_current(supporting_data):
    """Current recorded inventory/history, not a model accuracy certificate."""
    if not isinstance(supporting_data, dict):
        return False
    inventory = supporting_data.get("inventory_assessment")
    demand = supporting_data.get("demand_assessment")
    if not isinstance(inventory, dict) or not isinstance(demand, dict):
        return False
    if inventory.get("status") != "RECORDED_BALANCE" or inventory.get("verified_record") is not True:
        return False
    if demand.get("status") != "CURRENT_HISTORY":
        return False
    today = timezone.localdate()
    for value in (inventory.get("as_of"), demand.get("as_of"), demand.get("latest_observation_date")):
        try:
            day = datetime.date.fromisoformat(value)
        except (TypeError, ValueError):
            return False
        if not 0 <= (today - day).days <= 7:
            return False
    return True


def _forecast_advisory_date_state(data, workspace):
    from apps.recommendations.forecast_rules import RULE_KEY
    if data.get('rule_key') != RULE_KEY:
        return None
    try:
        source = datetime.date.fromisoformat(data.get('period_end'))
        start = datetime.date.fromisoformat(data.get('forecast_start'))
        end = datetime.date.fromisoformat(data.get('forecast_end'))
    except (TypeError, ValueError):
        return 'INVALID'
    today = timezone.localdate()
    if source > today or start != source+datetime.timedelta(days=1) or end != start+datetime.timedelta(days=6):
        return 'INVALID'
    if start < today or source < today-datetime.timedelta(days=7):
        return 'HISTORICAL'
    from apps.forecasting.models import ForecastRun
    from apps.forecasting.diagnostics import assess_run_compatibility
    run = ForecastRun.objects.for_workspace(workspace).filter(pk=data.get('forecast_run_id')).first()
    if run is None or not assess_run_compatibility(run)['operational_eligible']:
        return 'INVALID'
    return 'CURRENT_SNAPSHOT'


def recommendation_review_state(recommendation):
    """Assess snapshot age without rewriting historical records on a GET."""
    now = timezone.now()
    expired = recommendation.expires_at is not None and recommendation.expires_at <= now
    outdated = recommendation.created_at < now - datetime.timedelta(days=7)
    supporting_data = recommendation.supporting_data if isinstance(recommendation.supporting_data, dict) else {}
    period_end = supporting_data.get("period_end")
    if period_end:
        try:
            day = datetime.date.fromisoformat(period_end)
            outdated = outdated or day < timezone.localdate() - datetime.timedelta(days=7) or day > timezone.localdate()
        except (TypeError, ValueError):
            outdated = True
    unverified_stockout = recommendation.recommendation_type == RecommendationType.RETAIL_STOCKOUT_RISK and not _stockout_evidence_is_current(recommendation.supporting_data)
    forecast_state = _forecast_advisory_date_state(supporting_data, recommendation.workspace)
    historical = supporting_data.get('analysis_mode') == 'HISTORICAL' or forecast_state == 'HISTORICAL'
    invalid_forecast = forecast_state == 'INVALID'
    invalid_action = None
    if recommendation.proposed_action:
        try:
            tool = ToolRegistry.get(recommendation.proposed_action)
            if tool is None or tool.classification != 'MUTATION':
                raise ToolValidationError('Hành động không còn là contract thay đổi hợp lệ.')
            validate_action_contract(tool, recommendation.workspace, recommendation.proposed_parameters)
            snapshot = supporting_data.get('dispatch_snapshot')
            if recommendation.proposed_action == 'dispatch_technician' and snapshot is not None:
                current = dispatch_evidence_snapshot(recommendation.workspace,
                    recommendation.proposed_parameters.get('ticket_id'), recommendation.proposed_parameters.get('employee_id'))
                if snapshot != current:
                    raise ToolValidationError('Điều kiện phiếu/kỹ thuật viên đã đổi từ snapshot; cần đánh giá lại.')
        except ToolValidationError as exc:
            invalid_action = str(exc)
    stale = expired or outdated or unverified_stockout or historical or invalid_forecast or bool(invalid_action)
    return {"stale": stale,
            "current": recommendation.status == RecommendationStatus.PENDING and not stale,
            "label": invalid_action or ("Snapshot dự báo thiếu ngày hoặc ngày không hợp lệ — cần đánh giá lại" if invalid_forecast else
            "Phân tích lịch sử — chỉ tham khảo, không chấp thuận như hành động hiện tại" if historical else
            "Tồn kho/nhu cầu cũ hoặc chưa xác minh — cần đánh giá lại; không đủ căn cứ chấp thuận" if unverified_stockout else
            "Hết hạn / snapshot cũ — cần đánh giá lại" if expired or outdated else "Snapshot tại thời điểm tạo; cần đối chiếu trước khi quyết định"),
            "period_end": period_end,
            "stockout_evidence_current": not unverified_stockout if recommendation.recommendation_type == RecommendationType.RETAIL_STOCKOUT_RISK else None,
            "actionable": bool(recommendation.proposed_action)}


@transaction.atomic
def reject_recommendation(recommendation: Recommendation):
    """Serialize rejection with acceptance; terminal decisions are immutable."""
    from apps.workspaces.models import Workspace
    Workspace.objects.select_for_update(no_key=True).get(pk=recommendation.workspace_id)
    recommendation = Recommendation.objects.select_for_update().get(pk=recommendation.pk, workspace_id=recommendation.workspace_id)
    if recommendation.status == RecommendationStatus.REJECTED:
        return recommendation
    if recommendation.status != RecommendationStatus.PENDING:
        raise ToolValidationError(
            "Chỉ có thể từ chối khuyến nghị đang chờ xem xét; quyết định đã chốt không được ghi đè."
        )
    recommendation.status = RecommendationStatus.REJECTED
    recommendation.save(update_fields=["status"])
    return recommendation


@transaction.atomic
def accept_recommendation(recommendation: Recommendation, user, decision_reason: str = ""):
    from apps.workspaces.models import Workspace
    from apps.approvals.executor import _check_user_tool_permission
    Workspace.objects.select_for_update(no_key=True).get(pk=recommendation.workspace_id)
    recommendation = Recommendation.objects.select_for_update().get(pk=recommendation.pk, workspace_id=recommendation.workspace_id)
    if not _check_user_tool_permission(user, recommendation.workspace, 'recommendations.manage_recommendation'):
        from apps.approvals.registry import ToolPermissionDenied
        raise ToolPermissionDenied('Bạn không có quyền chấp thuận khuyến nghị trong workspace.')
    if recommendation.status == RecommendationStatus.ACCEPTED:
        return recommendation
    if recommendation.status != RecommendationStatus.PENDING:
        raise ToolValidationError(
            f"Recommendation #{recommendation.pk} is in status '{recommendation.status}' and cannot be accepted."
        )

    if recommendation_review_state(recommendation)["stale"]:
        raise ToolValidationError(f"Recommendation #{recommendation.pk} has expired or its snapshot is stale; evaluate again.")

    if recommendation.proposed_action:
        tool_def = ToolRegistry.get(recommendation.proposed_action)
        if not tool_def:
            raise ToolValidationError("Recommendation action is not registered.")
        if tool_def.classification != "MUTATION":
            raise ToolValidationError("Recommendation action must be a registered mutation contract.")
        result = execute_tool(
            name=recommendation.proposed_action,
            workspace=recommendation.workspace,
            user=user,
            parameters=recommendation.proposed_parameters or {},
            idempotency_key=f"RECOMMENDATION-{recommendation.pk}",
            reason=decision_reason or f"Chấp thuận khuyến nghị #{recommendation.pk}: {recommendation.title}",
        )
        if result.get("status") not in {"APPROVAL_REQUIRED", "EXECUTED"}:
            raise ToolValidationError("Recommendation action did not produce a controlled approval result.")
        approval_id = result.get("approval_request_id")
        if approval_id:
            recommendation.approval_request = ApprovalRequest.objects.get(
                pk=approval_id,
                workspace=recommendation.workspace,
            )

    recommendation.status = RecommendationStatus.ACCEPTED
    recommendation.save(update_fields=["status", "approval_request"])
    return recommendation
