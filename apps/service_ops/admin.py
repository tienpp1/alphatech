"""
apps.service_ops.admin - Django Admin Registration for Service Operations.
"""

from django.contrib import admin
from apps.service_ops.models import (
    Service,
    Employee,
    SLA,
    ServiceRequest,
    Task,
    Schedule,
    LaborEntry,
)


class LaborEntryInline(admin.TabularInline):
    model = LaborEntry
    extra = 0
    fields = ("employee", "started_at", "ended_at", "duration_minutes", "hourly_rate_snapshot", "labor_cost", "notes")
    readonly_fields = ("hourly_rate_snapshot", "labor_cost")


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ("title", "assigned_to", "status", "priority", "estimated_duration_minutes", "actual_duration_minutes")


class ScheduleInline(admin.TabularInline):
    model = Schedule
    extra = 0
    fields = ("employee", "start_time", "end_time", "status")


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "workspace", "standard_duration_minutes", "base_fee", "is_active", "created_at")
    list_filter = ("workspace", "category", "is_active")
    search_fields = ("code", "name", "description")


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "workspace", "phone", "hourly_labor_rate", "is_available", "is_active", "current_workload_score")
    list_filter = ("workspace", "is_available", "is_active")
    search_fields = ("code", "full_name", "phone", "email")


@admin.register(SLA)
class SLAAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "priority", "response_time_hours", "resolution_time_hours", "is_active")
    list_filter = ("workspace", "priority", "is_active")
    search_fields = ("name",)


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("request_number", "title", "workspace", "customer", "service", "assigned_employee", "priority", "status", "created_at")
    list_filter = ("workspace", "status", "priority", "service__category")
    search_fields = ("request_number", "title", "customer__name", "description")
    inlines = [TaskInline]


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "service_request", "assigned_to", "status", "priority", "estimated_duration_minutes", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("title", "description", "service_request__request_number")
    inlines = [ScheduleInline, LaborEntryInline]


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "employee", "start_time", "end_time", "status")
    list_filter = ("status", "employee")
    search_fields = ("task__title", "employee__full_name", "notes")


@admin.register(LaborEntry)
class LaborEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "employee", "started_at", "ended_at", "duration_minutes", "hourly_rate_snapshot", "labor_cost", "created_at")
    list_filter = ("employee",)
    search_fields = ("task__title", "employee__full_name", "notes")
    readonly_fields = ("hourly_rate_snapshot", "labor_cost")
