"""
Audit services for structured action logging.
"""

from typing import Optional, Dict, Any
from django.db import models
from apps.audit.models import AuditLog, ActorType


def log_action(
    workspace: Optional[Any] = None,
    actor_user: Optional[Any] = None,
    actor_type: str = ActorType.USER,
    action: str = "",
    entity_type: str = "",
    entity_id: str = "",
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """
    Creates an immutable audit log entry.
    """
    return AuditLog.objects.create(
        workspace=workspace,
        actor_user=actor_user,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        changes=changes or {},
        ip_address=ip_address,
    )


def log_audit_event(
    workspace: Optional[Any] = None,
    user: Optional[Any] = None,
    action: str = "",
    entity_type: str = "",
    entity_id: str = "",
    target: str = "",
    metadata: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """Convenience alias for log_action with user and metadata kwargs."""
    if target and not entity_type:
        entity_type = target
    return log_action(
        workspace=workspace,
        actor_user=user,
        actor_type=ActorType.USER if user else ActorType.SYSTEM,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=metadata or {},
    )

