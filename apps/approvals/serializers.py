"""
DRF Serializers for Approvals and Tool Execution (Phase 10).
"""

from rest_framework import serializers
from apps.approvals.models import ApprovalRequest, ApprovalStatus, RiskLevel


class ApprovalRequestSerializer(serializers.ModelSerializer):
    requester_name = serializers.ReadOnlyField(source="requester.get_full_name")
    reviewer_name = serializers.ReadOnlyField(source="reviewer.get_full_name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    risk_level_display = serializers.CharField(source="get_risk_level_display", read_only=True)

    class Meta:
        model = ApprovalRequest
        fields = [
            "id",
            "workspace",
            "requester",
            "requester_name",
            "proposed_action",
            "parameters",
            "reason",
            "risk_level",
            "risk_level_display",
            "status",
            "status_display",
            "reviewer",
            "reviewer_name",
            "review_timestamp",
            "decision_reason",
            "idempotency_key",
            "execution_result",
            "executed_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "requester",
            "reviewer",
            "review_timestamp",
            "execution_result",
            "executed_at",
            "created_at",
        ]


class ApprovalDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    decision_reason = serializers.CharField(required=False, allow_blank=True, default="")


class ToolExecuteRequestSerializer(serializers.Serializer):
    tool_name = serializers.CharField(max_length=100)
    parameters = serializers.DictField(required=False, default=dict)
    idempotency_key = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="Thực thi qua API Tool Call")
