"""
Models for Human Approval Workflow and Controlled Actions (Phase 10).
Inherits WorkspaceScopedModel for multi-tenant isolation.
"""

from django.db import models
from django.conf import settings
from apps.workspaces.models import WorkspaceScopedModel


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Approval"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"
    EXECUTED = "EXECUTED", "Executed"


class RiskLevel(models.TextChoices):
    LOW = "LOW", "Low Risk"
    MEDIUM = "MEDIUM", "Medium Risk"
    HIGH = "HIGH", "High Risk"
    CRITICAL = "CRITICAL", "Critical Risk"


class ApprovalRequest(WorkspaceScopedModel):
    """
    Two-step human-in-the-loop approval record for proposed database mutations.
    Enforces idempotency, RBAC, and audit logging.
    """

    id = models.BigAutoField(primary_key=True)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="approval_requests_submitted",
        help_text="User who initiated or requested the mutation action.",
    )
    proposed_action = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Whitelisted tool name (e.g. dispatch_technician, update_order_status).",
    )
    parameters = models.JSONField(
        default=dict,
        help_text="Validated JSON payload parameters for tool execution.",
    )
    reason = models.TextField(
        help_text="Business justification or AI explanation for requesting the mutation.",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        default=RiskLevel.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_requests_reviewed",
        help_text="Authorized manager/admin who approved or rejected the request.",
    )
    review_timestamp = models.DateTimeField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    idempotency_key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Unique key preventing duplicate replay execution of the mutation.",
    )
    execution_result = models.JSONField(
        null=True,
        blank=True,
        help_text="Cached execution output payload stored after success.",
    )
    executed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "approvals_approvalrequest"
        ordering = ["-created_at"]
        verbose_name = "Approval Request"
        verbose_name_plural = "Approval Requests"
        constraints = [
            models.UniqueConstraint(fields=["workspace", "idempotency_key"], name="unique_workspace_approval_key"),
        ]
        permissions = [
            ("manage_approval", "Can approve or reject mutation requests"),
        ]

    def __str__(self):
        return f"[{self.workspace.code}] Request #{self.id} ({self.proposed_action}) - {self.status}"
