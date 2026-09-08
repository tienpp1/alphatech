"""
apps.service_ops.serializers - DRF Serializers conforming to docs/api-conventions.md.
"""

from rest_framework import serializers
from apps.retail.serializers import CustomerSerializer
from apps.service_ops.models import (
    Service,
    Employee,
    SLA,
    ServiceRequest,
    Task,
    Schedule,
    LaborEntry,
)
from apps.service_ops.sla_engine import calculate_sla_status
from apps.service_ops.services import get_service_request_cost_breakdown


class ServiceSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_display",
            "description",
            "standard_duration_minutes",
            "base_fee",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "category_display", "created_at", "updated_at"]


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            "id",
            "code",
            "full_name",
            "phone",
            "email",
            "skills",
            "hourly_labor_rate",
            "latitude",
            "longitude",
            "is_available",
            "is_active",
            "current_workload_score",
            "location_updated_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "current_workload_score", "location_updated_at", "created_at", "updated_at"]


class SLASerializer(serializers.ModelSerializer):
    class Meta:
        model = SLA
        fields = [
            "id",
            "name",
            "priority",
            "response_time_hours",
            "resolution_time_hours",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LaborEntrySerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    employee_id = serializers.IntegerField(write_only=True)
    task_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = LaborEntry
        fields = [
            "id",
            "task_id",
            "employee",
            "employee_id",
            "started_at",
            "ended_at",
            "duration_minutes",
            "hourly_rate_snapshot",
            "labor_cost",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "hourly_rate_snapshot", "labor_cost", "created_at", "updated_at"]


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = EmployeeSerializer(read_only=True)
    assigned_to_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    labor_entries = LaborEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "service_request_id",
            "assigned_to",
            "assigned_to_id",
            "title",
            "description",
            "status",
            "priority",
            "estimated_duration_minutes",
            "actual_duration_minutes",
            "started_at",
            "completed_at",
            "due_at",
            "labor_entries",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "started_at", "completed_at", "labor_entries", "created_at", "updated_at"]


class ScheduleSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)
    employee_id = serializers.IntegerField(write_only=True)
    task_id = serializers.IntegerField()

    class Meta:
        model = Schedule
        fields = [
            "id",
            "task_id",
            "employee",
            "employee_id",
            "start_time",
            "end_time",
            "status",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ServiceRequestSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    customer_id = serializers.IntegerField(write_only=True)
    service = ServiceSerializer(read_only=True)
    service_id = serializers.IntegerField(write_only=True)
    sla = SLASerializer(read_only=True)
    assigned_employee = EmployeeSerializer(read_only=True)
    assigned_employee_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    tasks = TaskSerializer(many=True, read_only=True)
    sla_metrics = serializers.SerializerMethodField()
    cost_summary = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "request_number",
            "customer",
            "customer_id",
            "service",
            "service_id",
            "sla",
            "assigned_employee",
            "assigned_employee_id",
            "title",
            "description",
            "latitude",
            "longitude",
            "priority",
            "status",
            "scheduled_at",
            "response_deadline_at",
            "resolution_deadline_at",
            "responded_at",
            "resolved_at",
            "closed_at",
            "tasks",
            "sla_metrics",
            "cost_summary",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "request_number",
            "response_deadline_at",
            "resolution_deadline_at",
            "responded_at",
            "resolved_at",
            "closed_at",
            "created_at",
            "updated_at",
        ]

    def get_sla_metrics(self, obj) -> dict:
        return calculate_sla_status(obj)

    def get_cost_summary(self, obj) -> dict:
        return get_service_request_cost_breakdown(obj)
