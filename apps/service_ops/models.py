"""
apps.service_ops.models - Service Operations Domain Models.

Includes:
- ServiceCategory: Standardized IT & Technical Service categories (Installation, Maintenance, Consulting, Repair).
- Service: Catalog of field and remote IT services.
- Employee: Technical staff / field technicians with skills and hourly labor rates.
- SLA: Service Level Agreement policies per priority tier.
- ServiceRequest: Primary incident ticket tracking resolution & SLA deadlines.
- Task: Actionable operational work items derived from service requests.
- Schedule: Planned time slots for technicians assigned to tasks.
- LaborEntry: Lightweight labor time tracking with immutable hourly rate snapshotting.
"""

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.conf import settings
from apps.workspaces.models import Workspace, WorkspaceScopedModel


class ServiceCategory(models.TextChoices):
    INSTALLATION = "INSTALLATION", "System Installation"
    MAINTENANCE = "MAINTENANCE", "System Maintenance"
    DATABASE_CONSULTING = "DATABASE_CONSULTING", "Database Consulting"
    DEVICE_REPAIR = "DEVICE_REPAIR", "Device Repair"


class Service(WorkspaceScopedModel):
    """
    Catalog of available IT and technical services offered in the workspace.
    """

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=50,
        choices=ServiceCategory.choices,
        default=ServiceCategory.INSTALLATION,
        db_index=True,
    )
    description = models.TextField(blank=True)
    standard_duration_minutes = models.PositiveIntegerField(default=60)
    base_fee = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_ops_service"
        ordering = ["name"]
        verbose_name = "Service"
        verbose_name_plural = "Services"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="unique_workspace_service_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) [{self.get_category_display()}]"


class Employee(WorkspaceScopedModel):
    """
    Field technician or operational employee with skill assignments and hourly labor rates.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employee_profile",
    )
    code = models.CharField(max_length=50, db_index=True)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    hourly_labor_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("150000.00"),
        help_text="Standard hourly labor rate in VND for technician",
    )
    current_location = gis_models.PointField(srid=4326, spatial_index=True, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)
    is_available = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    current_workload_score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_ops_employee"
        ordering = ["full_name"]
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="unique_workspace_employee_code",
            )
        ]

    def __str__(self):
        return f"{self.full_name} ({self.code}) - {self.hourly_labor_rate:,.0f} VND/h"


class SLAPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class SLA(WorkspaceScopedModel):
    """
    Service Level Agreement policy mapping priority levels to response and resolution deadlines.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    priority = models.CharField(
        max_length=20,
        choices=SLAPriority.choices,
        db_index=True,
    )
    response_time_hours = models.PositiveIntegerField(default=24)
    resolution_time_hours = models.PositiveIntegerField(default=48)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_ops_sla"
        ordering = ["priority"]
        verbose_name = "SLA Policy"
        verbose_name_plural = "SLA Policies"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "priority"],
                name="unique_workspace_sla_priority",
            )
        ]

    def __str__(self):
        return f"{self.name} [{self.priority}] (Resp: {self.response_time_hours}h, Resolv: {self.resolution_time_hours}h)"


class ServiceRequestStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    ASSIGNED = "ASSIGNED", "Assigned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    RESOLVED = "RESOLVED", "Resolved"
    CLOSED = "CLOSED", "Closed"
    CANCELLED = "CANCELLED", "Cancelled"


class ServiceRequestPriority(models.TextChoices):
    LOW = "LOW", "Low"
    MEDIUM = "MEDIUM", "Medium"
    HIGH = "HIGH", "High"
    CRITICAL = "CRITICAL", "Critical"


class ServiceRequest(WorkspaceScopedModel):
    """
    Core incident ticket recording client issue, SLA targets, status, and technician assignment.
    """

    id = models.BigAutoField(primary_key=True)
    request_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        "retail.Customer",
        on_delete=models.RESTRICT,
        related_name="service_requests",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.RESTRICT,
        related_name="requests",
    )
    sla = models.ForeignKey(
        SLA,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requests",
    )
    assigned_employee = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_requests",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = gis_models.PointField(srid=4326, spatial_index=True, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=ServiceRequestPriority.choices,
        default=ServiceRequestPriority.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=ServiceRequestStatus.choices,
        default=ServiceRequestStatus.OPEN,
        db_index=True,
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    response_deadline_at = models.DateTimeField(null=True, blank=True, db_index=True)
    resolution_deadline_at = models.DateTimeField(null=True, blank=True, db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_ops_request"
        ordering = ["-created_at"]
        verbose_name = "Service Request"
        verbose_name_plural = "Service Requests"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "request_number"],
                name="unique_workspace_request_number",
            )
        ]

    def __str__(self):
        return f"{self.request_number} - {self.title} [{self.status}]"

    def clean(self):
        super().clean()
        related_workspaces = {
            "customer": getattr(self.customer, "workspace_id", None) if self.customer_id else None,
            "service": getattr(self.service, "workspace_id", None) if self.service_id else None,
            "sla": getattr(self.sla, "workspace_id", None) if self.sla_id else None,
            "assigned_employee": getattr(self.assigned_employee, "workspace_id", None) if self.assigned_employee_id else None,
        }
        errors = {
            field: "Đối tượng liên quan phải thuộc cùng workspace với yêu cầu dịch vụ."
            for field, workspace_id in related_workspaces.items()
            if workspace_id is not None and workspace_id != self.workspace_id
        }
        if errors:
            raise ValidationError(errors)


class TaskStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class Task(models.Model):
    """
    Actionable task unit derived from a service request.
    Inherits workspace scope through self.service_request.workspace.
    """

    id = models.BigAutoField(primary_key=True)
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    assigned_to = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tasks",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20,
        choices=ServiceRequestPriority.choices,
        default=ServiceRequestPriority.MEDIUM,
    )
    estimated_duration_minutes = models.PositiveIntegerField(default=60)
    actual_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_ops_task"
        ordering = ["created_at"]
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    @property
    def workspace(self):
        return self.service_request.workspace

    def __str__(self):
        return f"Task #{self.id}: {self.title} [{self.status}]"


class ScheduleStatus(models.TextChoices):
    SCHEDULED = "SCHEDULED", "Scheduled"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    DONE = "DONE", "Done"
    CANCELLED = "CANCELLED", "Cancelled"


class Schedule(models.Model):
    """
    Calendar time slot assigned to an employee for a specific task.
    """

    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    start_time = models.DateTimeField(db_index=True)
    end_time = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ScheduleStatus.choices,
        default=ScheduleStatus.SCHEDULED,
        db_index=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_ops_schedule"
        ordering = ["start_time"]
        verbose_name = "Schedule"
        verbose_name_plural = "Schedules"

    @property
    def workspace(self):
        return self.task.workspace

    def __str__(self):
        return f"Schedule {self.employee.full_name}: {self.start_time.strftime('%Y-%m-%d %H:%M')} -> {self.end_time.strftime('%H:%M')} [{self.status}]"


class LaborEntry(models.Model):
    """
    Lightweight labor time tracking unit associated with a Task / Ticket.
    Inherits workspace through self.task.service_request.workspace.
    Snapshots employee's hourly labor rate at entry creation time so historical costs remain immutable.
    """

    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="labor_entries",
    )
    employee = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="labor_entries",
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(help_text="Duration of work in minutes")
    hourly_rate_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Snapshot of technician hourly rate in VND at log time",
    )
    labor_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Server-calculated total labor cost: (duration_minutes / 60) * hourly_rate_snapshot",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_ops_labor_entry"
        ordering = ["-started_at"]
        verbose_name = "Labor Entry"
        verbose_name_plural = "Labor Entries"

    @property
    def workspace(self):
        return self.task.workspace

    def __str__(self):
        return f"Labor #{self.id}: {self.employee.full_name} ({self.duration_minutes}m - {self.labor_cost:,.0f} VND)"
