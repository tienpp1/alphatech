"""
apps.service_ops.sla_engine - Deterministic Service Level Agreement (SLA) Engine.

Calculates:
- Response deadlines & compliance (ON_TIME, AT_RISK, BREACHED)
- Resolution deadlines & compliance (ON_TIME, AT_RISK, BREACHED)
- Overall SLA health status and remaining time counters
"""

from datetime import datetime, timezone
from django.utils import timezone as django_timezone


class SLAComplianceStatus:
    ON_TIME = "ON_TIME"
    AT_RISK = "AT_RISK"
    BREACHED = "BREACHED"


def calculate_sla_status(service_request, reference_time=None) -> dict:
    """
    Evaluates SLA deadlines for a given ServiceRequest deterministically.
    """
    now = reference_time or django_timezone.now()
    created_at = service_request.created_at or now

    response_deadline = service_request.response_deadline_at
    resolution_deadline = service_request.resolution_deadline_at
    responded_at = service_request.responded_at
    resolved_at = service_request.resolved_at

    # 1. Response SLA calculation
    if not response_deadline:
        response_status = SLAComplianceStatus.ON_TIME
        response_remaining_minutes = 0
        is_response_breached = False
    elif responded_at:
        if responded_at <= response_deadline:
            response_status = SLAComplianceStatus.ON_TIME
            is_response_breached = False
        else:
            response_status = SLAComplianceStatus.BREACHED
            is_response_breached = True
        response_remaining_minutes = int((response_deadline - responded_at).total_seconds() / 60)
    else:
        # Not yet responded
        diff_seconds = (response_deadline - now).total_seconds()
        response_remaining_minutes = int(diff_seconds / 60)
        total_window_seconds = max((response_deadline - created_at).total_seconds(), 1)

        if now > response_deadline:
            response_status = SLAComplianceStatus.BREACHED
            is_response_breached = True
        elif diff_seconds <= (0.2 * total_window_seconds):  # <= 20% of total SLA window
            response_status = SLAComplianceStatus.AT_RISK
            is_response_breached = False
        else:
            response_status = SLAComplianceStatus.ON_TIME
            is_response_breached = False

    # 2. Resolution SLA calculation
    if not resolution_deadline:
        resolution_status = SLAComplianceStatus.ON_TIME
        resolution_remaining_minutes = 0
        is_resolution_breached = False
    elif resolved_at:
        if resolved_at <= resolution_deadline:
            resolution_status = SLAComplianceStatus.ON_TIME
            is_resolution_breached = False
        else:
            resolution_status = SLAComplianceStatus.BREACHED
            is_resolution_breached = True
        resolution_remaining_minutes = int((resolution_deadline - resolved_at).total_seconds() / 60)
    elif service_request.status in ["CANCELLED", "CLOSED"]:
        closed_at = service_request.closed_at or now
        if closed_at <= resolution_deadline:
            resolution_status = SLAComplianceStatus.ON_TIME
            is_resolution_breached = False
        else:
            resolution_status = SLAComplianceStatus.BREACHED
            is_resolution_breached = True
        resolution_remaining_minutes = int((resolution_deadline - closed_at).total_seconds() / 60)
    else:
        # Ongoing ticket
        diff_seconds = (resolution_deadline - now).total_seconds()
        resolution_remaining_minutes = int(diff_seconds / 60)
        total_window_seconds = max((resolution_deadline - created_at).total_seconds(), 1)

        if now > resolution_deadline:
            resolution_status = SLAComplianceStatus.BREACHED
            is_resolution_breached = True
        elif diff_seconds <= (0.2 * total_window_seconds):  # <= 20% of total SLA window
            resolution_status = SLAComplianceStatus.AT_RISK
            is_resolution_breached = False
        else:
            resolution_status = SLAComplianceStatus.ON_TIME
            is_resolution_breached = False

    # 3. Overall composite SLA status
    if response_status == SLAComplianceStatus.BREACHED or resolution_status == SLAComplianceStatus.BREACHED:
        overall_status = SLAComplianceStatus.BREACHED
    elif response_status == SLAComplianceStatus.AT_RISK or resolution_status == SLAComplianceStatus.AT_RISK:
        overall_status = SLAComplianceStatus.AT_RISK
    else:
        overall_status = SLAComplianceStatus.ON_TIME

    return {
        "response_status": response_status,
        "resolution_status": resolution_status,
        "overall_status": overall_status,
        "response_remaining_minutes": response_remaining_minutes,
        "resolution_remaining_minutes": resolution_remaining_minutes,
        "is_response_breached": is_response_breached,
        "is_resolution_breached": is_resolution_breached,
    }
