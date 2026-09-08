from django.db import transaction

from apps.approvals.executor import execute_tool
from apps.approvals.models import ApprovalRequest
from apps.approvals.registry import ToolValidationError
from apps.approvals.registry import ToolRegistry
from apps.recommendations.models import Recommendation, RecommendationStatus
from django.utils import timezone


@transaction.atomic
def accept_recommendation(recommendation: Recommendation, user, decision_reason: str = ""):
    recommendation = Recommendation.objects.select_for_update().get(pk=recommendation.pk)
    if recommendation.status == RecommendationStatus.ACCEPTED:
        return recommendation
    if recommendation.status != RecommendationStatus.PENDING:
        raise ToolValidationError(
            f"Recommendation #{recommendation.pk} is in status '{recommendation.status}' and cannot be accepted."
        )

    if recommendation.expires_at and recommendation.expires_at <= timezone.now():
        recommendation.status = RecommendationStatus.EXPIRED
        recommendation.save(update_fields=["status"])
        raise ToolValidationError(f"Recommendation #{recommendation.pk} has expired.")

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
