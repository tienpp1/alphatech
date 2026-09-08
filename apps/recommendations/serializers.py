"""
DRF Serializers for Recommendations & Decision Support (Phase 10).
"""

from rest_framework import serializers
from apps.recommendations.models import Recommendation, RecommendationStatus, RecommendationPriority, RecommendationType


class RecommendationSerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source="created_by.get_full_name")
    recommendation_type_display = serializers.CharField(source="get_recommendation_type_display", read_only=True)
    priority_display = serializers.CharField(source="get_priority_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Recommendation
        fields = [
            "id",
            "workspace",
            "recommendation_type",
            "recommendation_type_display",
            "title",
            "explanation",
            "supporting_data",
            "source_references",
            "proposed_action",
            "proposed_parameters",
            "approval_request",
            "priority",
            "priority_display",
            "status",
            "status_display",
            "created_by",
            "created_by_name",
            "expires_at",
            "created_at",
        ]
        read_only_fields = [
            "id", "workspace", "created_by", "created_at",
            "proposed_action", "proposed_parameters", "approval_request",
        ]


class RecommendationDecisionSerializer(serializers.Serializer):
    decision_reason = serializers.CharField(required=False, allow_blank=True, default="")
