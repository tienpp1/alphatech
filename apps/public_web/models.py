"""Persistent identities and transactional customer-email delivery state."""

import uuid

from django.conf import settings
from django.db import models


class OrderDeliveryAddress(models.Model):
    """Structured checkout snapshot, never inferred from mutable customer details."""
    order = models.OneToOneField("retail.Order", on_delete=models.CASCADE, related_name="delivery_address")
    recipient_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address_line = models.CharField(max_length=255, blank=True)
    district = models.CharField(max_length=150, blank=True)
    city = models.CharField(max_length=150, blank=True)
    delivery_method = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)


class ContactSubmission(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # A public contact can arrive before an operational workspace is configured.
    workspace = models.ForeignKey("workspaces.Workspace", null=True, blank=True, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    message = models.TextField()
    deduplication_key = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SocialIdentity(models.Model):
    class Provider(models.TextChoices):
        GOOGLE = "GOOGLE", "Google"

    provider = models.CharField(max_length=20, choices=Provider.choices)
    subject = models.CharField(max_length=255)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_identities")
    provider_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_web_social_identity"
        constraints = [
            models.UniqueConstraint(fields=("provider", "subject"), name="uniq_social_provider_subject"),
            models.UniqueConstraint(fields=("provider", "user"), name="uniq_social_provider_user"),
        ]


class RegistrationCode(models.Model):
    """One bounded mailbox challenge per pending account; secrets are hashed."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField()
    window_started_at = models.DateTimeField()
    sends = models.PositiveSmallIntegerField(default=1)
    failures = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)


class CustomerEmailDelivery(models.Model):
    class EventType(models.TextChoices):
        EMAIL_VERIFICATION = "EMAIL_VERIFICATION", "Email verification"
        WELCOME = "WELCOME", "Welcome"
        LOGIN_ALERT = "LOGIN_ALERT", "Login alert"
        ORDER = "ORDER", "Order"
        SERVICE_REQUEST = "SERVICE_REQUEST", "Service request"
        CONTACT = "CONTACT", "Contact"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customer_email_deliveries",
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    entity_type = models.CharField(max_length=50, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    plain_body = models.TextField()
    html_body = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempt_count = models.PositiveIntegerField(default=0)
    last_error_code = models.CharField(max_length=80, blank=True)
    attempted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    deduplication_key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "public_web_customer_email_delivery"
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("status", "created_at"), name="public_email_status_idx")]
