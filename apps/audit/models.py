"""
AuditLog Model (Append-Only Immutable System Trail).
Adheres strictly to docs/erd.md Section 2.8 and security design invariants.
"""

from django.db import models
from django.conf import settings
from django.core.exceptions import PermissionDenied


class ActorType(models.TextChoices):
    USER = "USER", "User"
    AI_ASSISTANT = "AI_ASSISTANT", "AI Assistant"
    SYSTEM_JOB = "SYSTEM_JOB", "System Job"


class AuditLog(models.Model):
    """
    Immutable, append-only system audit log.
    Records critical domain mutations, logins, approvals, and system jobs.
    """

    id = models.BigAutoField(primary_key=True)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
        db_index=True,
    )
    actor_type = models.CharField(
        max_length=20,
        choices=ActorType.choices,
        default=ActorType.USER,
        db_index=True,
    )
    action = models.CharField(max_length=100, db_index=True)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=50, db_index=True)
    changes = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_auditlog"
        ordering = ["-timestamp"]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        indexes = [
            models.Index(fields=["workspace", "-timestamp"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def save(self, *args, **kwargs):
        # Enforce immutability: updates to existing rows are strictly rejected
        if self.pk is not None and not kwargs.get("force_insert", False):
            # Check if record already exists in database
            if AuditLog.objects.filter(pk=self.pk).exists():
                raise PermissionDenied("AuditLog records are append-only and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("AuditLog records are permanent and cannot be deleted.")

    def __str__(self):
        actor = self.actor_user.username if self.actor_user else self.actor_type
        ws_code = self.workspace.code if self.workspace else "GLOBAL"
        return f"[{self.timestamp:%Y-%m-%d %H:%M:%S}] [{ws_code}] {actor}: {self.action} on {self.entity_type}#{self.entity_id}"
