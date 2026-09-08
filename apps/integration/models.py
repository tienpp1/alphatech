import uuid
from django.conf import settings
from django.db import models
from apps.workspaces.models import WorkspaceScopedModel


class SourceType(models.TextChoices):
    CSV = "CSV", "CSV File"
    EXCEL = "EXCEL", "Excel Spreadsheet (.xlsx)"
    MOCK_API = "MOCK_API", "Mock External REST API"


class ImportStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"
    PARTIAL = "PARTIAL", "Partially Completed"
    FAILED = "FAILED", "Failed"


class EntityType(models.TextChoices):
    RETAIL_ORDERS = "RETAIL_ORDERS", "Retail Orders"
    RETAIL_CUSTOMERS = "RETAIL_CUSTOMERS", "Retail Customers"
    RETAIL_PRODUCTS = "RETAIL_PRODUCTS", "Retail Products"
    SERVICE_REQUESTS = "SERVICE_REQUESTS", "Service Incident Tickets"
    SERVICE_TECHNICIANS = "SERVICE_TECHNICIANS", "Field Technicians"
    GENERAL = "GENERAL", "General Dataset"


class DataSource(WorkspaceScopedModel):
    """
    Workspace-scoped external data source registry.
    Defines the origin and connection settings for external business datasets.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, help_text="Human-readable name for this data source.")
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    connection_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Safe configuration parameters (e.g. endpoint URL, sheet name, delimiter). Never store raw secrets.",
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_data_sources",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_datasource"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="unique_workspace_datasource_name",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.source_type}) [{self.workspace.code}]"


class ImportJob(WorkspaceScopedModel):
    """
    Tracks an execution instance of data ingestion from a DataSource.
    Records file metadata, processing statistics, error summaries, and lifecycle state.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name="import_jobs",
    )
    entity_type = models.CharField(
        max_length=50,
        choices=EntityType.choices,
        default=EntityType.GENERAL,
        help_text="Expected business entity category for this import batch.",
    )
    status = models.CharField(
        max_length=20,
        choices=ImportStatus.choices,
        default=ImportStatus.PENDING,
        db_index=True,
    )
    total_rows = models.IntegerField(default=0, help_text="Total rows identified in source file/payload.")
    successful_rows = models.IntegerField(default=0, help_text="Rows parsed and staged successfully.")
    failed_rows = models.IntegerField(default=0, help_text="Rows rejected due to structural or formatting errors.")
    error_summary = models.JSONField(
        default=list,
        blank=True,
        help_text="List of error objects: [{'row': int, 'error_type': str, 'message': str, 'raw': dict}]",
    )
    source_file = models.FileField(
        upload_to="imports/%Y/%m/",
        null=True,
        blank=True,
        help_text="Archived raw input file.",
    )
    source_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Technical metadata: filename, file_size_bytes, columns, detected_encoding, sheet_name.",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="import_jobs",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "integration_importjob"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["data_source", "status"]),
        ]

    def __str__(self):
        return f"ImportJob {self.id} - {self.data_source.name} ({self.status})"

    @property
    def success_rate(self) -> float:
        if self.total_rows <= 0:
            return 0.0
        return round((self.successful_rows / self.total_rows) * 100.0, 1)


class RawImportRecord(WorkspaceScopedModel):
    """
    Staging table for raw, untransformed external records.
    Stores the exact foreign key-value pairs before Phase 7 Data Mapping.
    """
    id = models.BigAutoField(primary_key=True)
    import_job = models.ForeignKey(
        ImportJob,
        on_delete=models.CASCADE,
        related_name="raw_records",
    )
    row_number = models.PositiveIntegerField(help_text="1-indexed row number in the source file.")
    raw_data = models.JSONField(
        default=dict,
        help_text="Unaltered raw dictionary extracted from the source row.",
    )
    is_valid = models.BooleanField(
        default=True,
        help_text="Whether this record passed structural and datatype checks at ingestion time.",
    )
    validation_errors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of validation error messages encountered during ingestion.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "integration_rawimportrecord"
        ordering = ["row_number"]
        indexes = [
            models.Index(fields=["import_job", "row_number"]),
            models.Index(fields=["import_job", "is_valid"]),
        ]

    def __str__(self):
        return f"RawRecord #{self.row_number} (Job: {self.import_job_id})"
