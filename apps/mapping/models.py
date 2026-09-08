import uuid
from django.conf import settings
from django.db import models
from apps.workspaces.models import WorkspaceScopedModel
from apps.integration.models import DataSource


class RuleType(models.TextChoices):
    FIELD_MAPPING = "FIELD_MAPPING", "Field Mapping (Direct Rename)"
    TYPE_CONVERSION = "TYPE_CONVERSION", "Type Conversion (Cast & Sanitize)"
    VALUE_MAPPING = "VALUE_MAPPING", "Value Mapping (Categorical / Code Lookup)"
    BUSINESS_FORMULA = "BUSINESS_FORMULA", "Business Formula (Safe Expression)"
    AI_ASSISTED_MAPPING = "AI_ASSISTED_MAPPING", "AI-Assisted Mapping (Recommendation)"


class ValidationStatus(models.TextChoices):
    VALID = "VALID", "Valid"
    INVALID = "INVALID", "Invalid"
    PENDING = "PENDING", "Pending Validation"


class AIConfirmationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Human Review"
    ACCEPTED = "ACCEPTED", "Accepted by Human"
    REJECTED = "REJECTED", "Rejected by Human"


class MappingProfile(WorkspaceScopedModel):
    """
    Workspace-scoped declarative mapping profile.
    Encapsulates a collection of mapping rules connecting an external data source
    or raw feed to a canonical Standard Data Model entity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mapping_profiles",
        help_text="Optional associated external data source.",
    )
    name = models.CharField(max_length=150, help_text="Human-readable mapping profile name.")
    target_entity = models.CharField(
        max_length=50,
        help_text="Target Canonical Standard Data Model entity (e.g. Order, Customer, ServiceRequest).",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_mapping_profiles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mapping_mappingprofile"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_workspace_mapping_profile_name",
            )
        ]

    def __str__(self):
        return f"{self.name} -> {self.target_entity} [{self.workspace.code}]"

    @property
    def active_rules_count(self) -> int:
        return self.rules.filter(is_active=True).count()


class MappingRule(WorkspaceScopedModel):
    """
    Individual field transformation rule inside a MappingProfile.
    Maps a raw external column or expression to a target canonical attribute.
    """

    id = models.BigAutoField(primary_key=True)
    profile = models.ForeignKey(
        MappingProfile,
        on_delete=models.CASCADE,
        related_name="rules",
    )
    source_field = models.CharField(
        max_length=100,
        help_text="Raw external column header name, formula expression, or source identifier.",
    )
    target_field = models.CharField(
        max_length=100,
        help_text="Canonical field name in Standard Data Model.",
    )
    rule_type = models.CharField(
        max_length=30,
        choices=RuleType.choices,
        default=RuleType.FIELD_MAPPING,
        db_index=True,
    )
    transformation_config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Transformation details: "
            "For TYPE_CONVERSION: {'target_type': 'DECIMAL', 'format': '%d/%m/%Y'}. "
            "For VALUE_MAPPING: {'value_map': {'raw': 'CANONICAL'}, 'default': 'DEFAULT'}. "
            "For BUSINESS_FORMULA: {'expression': 'unit_price * quantity - discount'}. "
            "For AI_ASSISTED_MAPPING: {'confidence': 0.94, 'reason': '...'}"
        ),
    )
    confidence_score = models.FloatField(
        default=1.0,
        help_text="Confidence rating (0.0 to 1.0) for AI-suggested mappings. Heuristic mappings default to 1.0.",
    )
    ai_status = models.CharField(
        max_length=20,
        choices=AIConfirmationStatus.choices,
        default=AIConfirmationStatus.ACCEPTED,
        help_text="Human-in-the-loop review state. AI rules require explicit human acceptance.",
    )
    validation_status = models.CharField(
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.VALID,
    )
    validation_error = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    order = models.PositiveIntegerField(default=0, help_text="Execution precedence order.")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_mapping_rules",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "mapping_mappingrule"
        ordering = ["order", "id"]
        indexes = [
            models.Index(fields=["profile", "is_active"]),
            models.Index(fields=["workspace", "rule_type"]),
        ]

    def __str__(self):
        return f"Rule {self.id}: {self.source_field} -> {self.target_field} ({self.rule_type})"
