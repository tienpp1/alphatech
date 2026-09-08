"""
Models for Business Recommendations & Decision Support (Phase 10).
Inherits WorkspaceScopedModel for strict multi-tenant isolation.
"""

from django.db import models
from django.conf import settings
from apps.workspaces.models import WorkspaceScopedModel


class RecommendationType(models.TextChoices):
    # Retail domain cases
    RETAIL_DECLINING_REVENUE = "RETAIL_DECLINING_REVENUE", "Declining Branch Revenue"
    RETAIL_LOW_ORDER_VOLUME = "RETAIL_LOW_ORDER_VOLUME", "Low Order Volume Alert"
    RETAIL_HIGH_PERFORMING = "RETAIL_HIGH_PERFORMING", "High Performing Branch Practice Sharing"
    RETAIL_STOCKOUT_RISK = "RETAIL_STOCKOUT_RISK", "Retail Stockout Risk Alert"
    # Service domain cases
    SERVICE_SLA_AT_RISK = "SERVICE_SLA_AT_RISK", "SLA Breach Risk Alert"
    SERVICE_TECHNICIAN_OVERLOAD = "SERVICE_TECHNICIAN_OVERLOAD", "Technician Workload Imbalance"
    SERVICE_TICKET_SPIKE = "SERVICE_TICKET_SPIKE", "Service Ticket Volume Spike"
    SERVICE_NEARBY_TECHNICIAN = "SERVICE_NEARBY_TECHNICIAN", "Nearby Technician Dispatch Candidate"


class RecommendationPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class RecommendationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    EXPIRED = "EXPIRED", "Expired"


class Recommendation(WorkspaceScopedModel):
    """
    Explainable operational recommendation generated deterministically by business rules.
    """

    id = models.BigAutoField(primary_key=True)
    recommendation_type = models.CharField(
        max_length=60,
        choices=RecommendationType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    explanation = models.JSONField(
        default=dict,
        help_text="Structured explanation schema containing 'what', 'why', 'evidence', and 'expected_effect'.",
    )
    supporting_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw metrics, forecast outputs, or GIS proximity payload supporting the recommendation.",
    )
    source_references = models.JSONField(
        default=list,
        blank=True,
        help_text="List of source entity URIs/IDs (e.g. branch_id, ticket_id, forecast_run_id).",
    )
    proposed_action = models.CharField(max_length=100, blank=True, db_index=True)
    proposed_parameters = models.JSONField(default=dict, blank=True)
    approval_request = models.OneToOneField(
        "approvals.ApprovalRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_recommendation",
    )
    priority = models.CharField(
        max_length=20,
        choices=RecommendationPriority.choices,
        default=RecommendationPriority.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=RecommendationStatus.choices,
        default=RecommendationStatus.PENDING,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_recommendations",
        help_text="User actor or None for system-generated rules.",
    )
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "recommendations_recommendation"
        ordering = ["-created_at"]
        verbose_name = "Recommendation"
        verbose_name_plural = "Recommendations"
        permissions = [
            ("manage_recommendation", "Can accept, reject or trigger recommendations"),
        ]

    def __str__(self):
        return f"[{self.workspace.code}] {self.get_recommendation_type_display()} ({self.priority}) - {self.status}"
