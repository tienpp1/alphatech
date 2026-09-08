"""
apps.service_ops.filters - Queryset Filter Helpers for Service Operations.
"""

from django.db.models import Q
from django.utils import timezone


def filter_services(queryset, params):
    search = params.get("search")
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search))
    category = params.get("category")
    if category:
        queryset = queryset.filter(category=category.upper())
    is_active = params.get("is_active")
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() in ["true", "1"])
    return queryset


def filter_employees(queryset, params):
    search = params.get("search")
    if search:
        queryset = queryset.filter(Q(full_name__icontains=search) | Q(code__icontains=search) | Q(phone__icontains=search))
    is_available = params.get("is_available")
    if is_available is not None:
        queryset = queryset.filter(is_available=is_available.lower() in ["true", "1"])
    is_active = params.get("is_active")
    if is_active is not None:
        queryset = queryset.filter(is_active=is_active.lower() in ["true", "1"])
    skill = params.get("skill")
    if skill:
        queryset = queryset.filter(skills__contains=[skill])
    return queryset


def filter_service_requests(queryset, params):
    search = params.get("search")
    if search:
        queryset = queryset.filter(
            Q(request_number__icontains=search) | Q(title__icontains=search) | Q(customer__name__icontains=search)
        )
    category = params.get("category")
    if category:
        queryset = queryset.filter(service__category=category.upper())
    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status.upper())
    priority = params.get("priority")
    if priority:
        queryset = queryset.filter(priority=priority.upper())
    service_id = params.get("service_id")
    if service_id:
        queryset = queryset.filter(service_id=service_id)
    employee_id = params.get("employee_id")
    if employee_id:
        queryset = queryset.filter(assigned_employee_id=employee_id)
    customer_id = params.get("customer_id")
    if customer_id:
        queryset = queryset.filter(customer_id=customer_id)
    return queryset


def filter_tasks(queryset, params):
    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status.upper())
    priority = params.get("priority")
    if priority:
        queryset = queryset.filter(priority=priority.upper())
    assigned_to_id = params.get("assigned_to_id")
    if assigned_to_id:
        queryset = queryset.filter(assigned_to_id=assigned_to_id)
    request_id = params.get("request_id")
    if request_id:
        queryset = queryset.filter(service_request_id=request_id)
    return queryset


def filter_schedules(queryset, params):
    employee_id = params.get("employee_id")
    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)
    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status.upper())
    return queryset


def filter_labor_entries(queryset, params):
    employee_id = params.get("employee_id")
    if employee_id:
        queryset = queryset.filter(employee_id=employee_id)
    task_id = params.get("task_id")
    if task_id:
        queryset = queryset.filter(task_id=task_id)
    request_id = params.get("request_id")
    if request_id:
        queryset = queryset.filter(task__service_request_id=request_id)
    return queryset
