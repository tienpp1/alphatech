from django.db import transaction

from apps.approvals.executor import execute_tool
from apps.approvals.models import ApprovalRequest
from apps.approvals.registry import ToolValidationError
from apps.approvals.registry import ToolRegistry
from apps.recommendations.models import Recommendation, RecommendationStatus, RecommendationType
from django.utils import timezone
import datetime


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
    return {"stale": expired or outdated or unverified_stockout,
            "label": "Tồn kho/nhu cầu cũ hoặc chưa xác minh — cần đánh giá lại; không đủ căn cứ chấp thuận" if unverified_stockout else
            "Hết hạn / snapshot cũ — cần đánh giá lại" if expired or outdated else "Snapshot tại thời điểm tạo; cần đối chiếu trước khi quyết định",
            "period_end": period_end,
            "stockout_evidence_current": not unverified_stockout if recommendation.recommendation_type == RecommendationType.RETAIL_STOCKOUT_RISK else None,
            "actionable": bool(recommendation.proposed_action)}


@transaction.atomic
def reject_recommendation(recommendation: Recommendation):
    """Serialize rejection with acceptance; terminal decisions are immutable."""
    recommendation = Recommendation.objects.select_for_update().get(pk=recommendation.pk)
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
    recommendation = Recommendation.objects.select_for_update().get(pk=recommendation.pk)
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
