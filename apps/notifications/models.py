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
    CUSTOMER_ORDER_APPROVED = "CUSTOMER_ORDER_APPROVED", "Đơn hàng của bạn đã được duyệt"
    CUSTOMER_SERVICE_APPROVED = "CUSTOMER_SERVICE_APPROVED", "Yêu cầu dịch vụ đã được tiếp nhận"


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
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "recipient", "event_type", "entity_type", "entity_id"],
                condition=models.Q(event_type__in=["CUSTOMER_ORDER_APPROVED", "CUSTOMER_SERVICE_APPROVED"]),
                name="unique_customer_approval_notice",
            ),
        ]
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


class BulletinPriority(models.TextChoices):
    NORMAL = "NORMAL", "Thông thường"
    URGENT = "URGENT", "Khẩn cấp"
    PINNED = "PINNED", "Ghim đầu trang"


class InternalBulletin(models.Model):
    """
    Internal administrative and operational bulletin scoped strictly to a Workspace.
    Allows managers and admins to publish announcements, guidelines, and directives
    to all staff members within that workspace.
    """
    id = models.BigAutoField(primary_key=True)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="bulletins",
        db_index=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="authored_bulletins",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    priority = models.CharField(
        max_length=20,
        choices=BulletinPriority.choices,
        default=BulletinPriority.NORMAL,
        db_index=True,
    )
    pinned_until = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications_internal_bulletin"
        ordering = ["-created_at"]
        verbose_name = "Internal Bulletin"
        verbose_name_plural = "Internal Bulletins"
        indexes = [
            models.Index(fields=["workspace", "is_published", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.priority}] {self.title} ({self.workspace.code})"

    @property
    def is_pinned(self) -> bool:
        if self.priority == BulletinPriority.PINNED:
            if self.pinned_until:
                return timezone.now() <= self.pinned_until
            return True
        return False


class TeamChatMessage(models.Model):
    """
    Internal real-time messaging entity between team members strictly scoped to a Workspace.
    Enforces tenant isolation, chronological delivery, and staff-only communication.
    """
    id = models.BigAutoField(primary_key=True)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="team_chat_messages",
        db_index=True,
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_team_messages",
    )
    message = models.TextField()
    attachment_name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications_team_chat_message"
        ordering = ["created_at"]
        verbose_name = "Team Chat Message"
        verbose_name_plural = "Team Chat Messages"
        indexes = [
            models.Index(fields=["workspace", "created_at"]),
            models.Index(fields=["workspace", "-id"]),
        ]

    def __str__(self):
        return f"{self.sender.username} in {self.workspace.code}: {self.message[:30]}"

