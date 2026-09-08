"""
Data models for the Internal Notification Center.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.workspaces.models import Workspace


class NotificationEventType(models.TextChoices):
    NEW_CUSTOMER = "NEW_CUSTOMER", "Khách hàng mới"
    NEW_ORDER = "NEW_ORDER", "Đơn hàng mới"
    NEW_SERVICE_REQUEST = "NEW_SERVICE_REQUEST", "Yêu cầu dịch vụ mới"
    NEW_CONTACT = "NEW_CONTACT", "Liên hệ mới"


class Notification(models.Model):
    """
    Internal notification entity scoped strictly to a Workspace and an individual Recipient.
    Enforces multi-tenant isolation, granular unread counting, and direct target linking.
    """

    id = models.BigAutoField(primary_key=True)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    event_type = models.CharField(
        max_length=50,
        choices=NotificationEventType.choices,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()

    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    target_url = models.CharField(max_length=255, blank=True)

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications_notification"
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["recipient", "workspace", "is_read", "-created_at"]),
            models.Index(fields=["workspace", "event_type", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.title} -> {self.recipient.username} ({self.workspace.code})"

    def mark_as_read(self, commit: bool = True):
        """Marks this notification as read and timestamps it."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            if commit:
                self.save(update_fields=["is_read", "read_at"])

    @property
    def event_icon(self) -> str:
        """Returns visual indicator icon for this event type."""
        icons = {
            NotificationEventType.NEW_CUSTOMER: "👤",
            NotificationEventType.NEW_ORDER: "🛒",
            NotificationEventType.NEW_SERVICE_REQUEST: "🛠️",
            NotificationEventType.NEW_CONTACT: "📩",
        }
        return icons.get(self.event_type, "🔔")
