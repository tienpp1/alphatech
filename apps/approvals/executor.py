"""
Execution and Idempotency Engine for Controlled Tools & Human Approvals (Phase 10).
Handles RBAC enforcement, parameter validation, approval creation, approval processing, and replay protection.
"""

import uuid
from typing import Dict, Any, Tuple
from django.utils import timezone
from django.db import transaction

from apps.workspaces.models import Workspace
from apps.accounts.models import User
from apps.accounts.services import has_workspace_permission
from apps.audit.services import log_audit_event
from apps.approvals.models import ApprovalRequest, ApprovalStatus, RiskLevel
from apps.approvals.registry import (
    ToolRegistry,
    ToolException,
    ToolPermissionDenied,
    ToolValidationError,
    validate_action_contract,
)


def _check_user_tool_permission(user: User, workspace: Workspace, perm_codename: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    
    # Direct check
    if has_workspace_permission(user, workspace, perm_codename):
        return True

    # Check semantic aliases between standard Django model perms and custom workspace perms
    aliases = {
        "service_ops.change_servicerequest": ["service.manage_request", "service.assign_request"],
        "service_ops.view_servicerequest": ["service.view_request"],
        "service_ops.view_employee": ["service.view_employee"],
        "service_ops.add_servicetask": ["service.manage_request", "service.assign_request"],
        "retail.change_order": ["retail.manage_order"],
        "retail.view_order": ["retail.view_order"],
        "retail.change_product": ["retail.manage_product"],
        "retail.view_product": ["retail.view_product"],
        "retail.add_goodsreceipt": ["retail.manage_product", "retail.manage_order"],
        "retail.change_goodsreceipt": ["retail.manage_product", "retail.manage_order"],
    }
    for alias in aliases.get(perm_codename, []):
        if has_workspace_permission(user, workspace, alias):
            return True

    return False



@transaction.atomic
def execute_tool(
    name: str,
    workspace: Workspace,
    user: User,
    parameters: Dict[str, Any],
    idempotency_key: str = "",
    reason: str = "Tự động kích hoạt từ hệ thống Hỗ trợ Ra quyết định",
) -> Dict[str, Any]:
    """
    Main entry point for executing a registered tool.
    - READ tools execute immediately if authorized.
    - MUTATION tools submit a PENDING ApprovalRequest for human review.
    """
    tool_def = ToolRegistry.get(name)
    if not tool_def:
        raise ToolValidationError(f"Tool '{name}' is not registered in the system registry.")

    # 1. Permission check
    if not _check_user_tool_permission(user, workspace, tool_def.required_permission):
        log_audit_event(
            user=user,
            workspace=workspace,
            action="TOOL_PERMISSION_DENIED",
            target=f"Tool:{name}",
            metadata={"tool_name": name, "required_permission": tool_def.required_permission}
        )
        raise ToolPermissionDenied(f"User lacks required permission '{tool_def.required_permission}' for tool '{name}'.")

    # 2. Input Parameter Validation against Schema
    required_fields = tool_def.input_schema.get("required", [])
    for field_name in required_fields:
        if field_name not in parameters or parameters[field_name] is None:
            raise ToolValidationError(f"Missing required parameter '{field_name}' for tool '{name}'.")
    validate_action_contract(tool_def, workspace, parameters)

    # Generate idempotency key if not provided
    if not idempotency_key:
        idempotency_key = f"IK-{uuid.uuid4().hex[:16]}"

    # 3. Handle READ tools -> Execute immediately
    if tool_def.classification == "READ":
        result_data = tool_def.handler(workspace, user, parameters)
        log_audit_event(
            user=user,
            workspace=workspace,
            action="TOOL_SELECTED",
            target=f"Tool:{name}",
            metadata={"tool_name": name, "classification": "READ", "status": "SUCCESS"}
        )
        return {
            "status": "EXECUTED",
            "classification": "READ",
            "tool_name": name,
            "result": result_data,
        }

    # 4. Handle MUTATION tools -> Requires Human Approval Workflow
    # Serialize proposal creation within a workspace; the database constraint is
    # the final guard for callers that do not use this service.
    Workspace.objects.select_for_update().get(pk=workspace.pk)
    # Check if an active ApprovalRequest already exists with this idempotency key
    existing = ApprovalRequest.objects.for_workspace(workspace).filter(
        idempotency_key=idempotency_key
    ).first()

    if existing:
        if existing.requester_id != user.pk or existing.proposed_action != name or existing.parameters != parameters:
            raise ToolValidationError("Idempotency key already belongs to a different request.")
        if existing.status == ApprovalStatus.EXECUTED:
            return {
                "status": "EXECUTED",
                "classification": "MUTATION",
                "tool_name": name,
                "approval_request_id": existing.id,
                "result": existing.execution_result,
                "idempotent_replay": True,
            }

        elif existing.status == ApprovalStatus.PENDING:
            return {
                "status": "APPROVAL_REQUIRED",
                "classification": "MUTATION",
                "tool_name": name,
                "approval_request_id": existing.id,
                "message": f"Phê duyệt #{existing.id} đang chờ Quản lý duyệt.",
                "idempotent_replay": True,
            }
        raise ToolValidationError("This request is terminal; create a new explicit request to proceed.")

    approval_req = ApprovalRequest.objects.create(
        workspace=workspace,
        requester=user,
        proposed_action=name,
        parameters=parameters,
        reason=reason,
        risk_level=tool_def.risk_level,
        status=ApprovalStatus.PENDING,
        idempotency_key=idempotency_key,
    )

    log_audit_event(
        user=user,
        workspace=workspace,
        action="APPROVAL_CREATED",
        target=f"ApprovalRequest #{approval_req.id}",
        metadata={
            "approval_id": approval_req.id,
            "proposed_action": name,
            "risk_level": tool_def.risk_level,
            "idempotency_key": idempotency_key,
        }
    )

    return {
        "status": "APPROVAL_REQUIRED",
        "classification": "MUTATION",
        "tool_name": name,
        "approval_request_id": approval_req.id,
        "message": f"Hành động thay đổi '{name}' đã tạo Yêu cầu Phê duyệt #{approval_req.id} và cần Quản lý duyệt.",
    }


@transaction.atomic
def process_approval_decision(
    approval_request: ApprovalRequest,
    reviewer: User,
    decision: str,  # "APPROVED" or "REJECTED"
    decision_reason: str = "",
) -> Dict[str, Any]:
    """
    Processes a human decision on a PENDING ApprovalRequest.
    If APPROVED: atomically executes the tool handler with replay protection.
    If REJECTED: marks status as REJECTED.
    """
    approval_request = ApprovalRequest.objects.select_for_update().select_related("workspace").get(
        pk=approval_request.pk, workspace_id=approval_request.workspace_id,
    )
    workspace = approval_request.workspace
    # Authorize before returning even a cached result, and re-read state under
    # the same lock for rejection and execution.
    if not _check_user_tool_permission(reviewer, workspace, "approvals.manage_approval"):
        raise ToolPermissionDenied("Reviewer lacks 'approvals.manage_approval' permission.")
    if approval_request.requester_id == reviewer.pk and not reviewer.is_superuser:
        raise ToolPermissionDenied("Quản lý không thể tự phê duyệt yêu cầu thay đổi do chính mình tạo ra.")
    if decision not in ("APPROVED", "REJECTED"):
        raise ToolValidationError("Invalid approval decision.")

    # Idempotency / Replay Check
    if approval_request.status == ApprovalStatus.EXECUTED:
        return {
            "status": "EXECUTED",
            "approval_id": approval_request.id,
            "result": approval_request.execution_result,
            "idempotent_replay": True,
            "message": "Approval request has already been executed.",
        }

    if approval_request.status != ApprovalStatus.PENDING:
        raise ToolValidationError(f"Approval request #{approval_request.id} is in status '{approval_request.status}' and cannot be reviewed.")

    # Permission check for reviewer
    if not _check_user_tool_permission(reviewer, workspace, "approvals.manage_approval"):
        log_audit_event(
            user=reviewer,
            workspace=workspace,
            action="APPROVAL_PERMISSION_DENIED",
            target=f"ApprovalRequest #{approval_request.id}",
            metadata={"approval_id": approval_request.id}
        )
        raise ToolPermissionDenied("Reviewer lacks 'approvals.manage_approval' permission.")

    # Separation of duties check (requester cannot approve own request unless superuser)
    if approval_request.requester == reviewer and not reviewer.is_superuser:
        raise ToolPermissionDenied("Quản lý không thể tự phê duyệt yêu cầu thay đổi do chính mình tạo ra.")

    now = timezone.now()

    if decision == "REJECTED":
        approval_request.status = ApprovalStatus.REJECTED
        approval_request.reviewer = reviewer
        approval_request.review_timestamp = now
        approval_request.decision_reason = decision_reason or "Từ chối phê duyệt bởi quản lý."
        approval_request.save()

        log_audit_event(
            user=reviewer,
            workspace=workspace,
            action="APPROVAL_REJECTED",
            target=f"ApprovalRequest #{approval_request.id}",
            metadata={"approval_id": approval_request.id, "reason": approval_request.decision_reason}
        )

        return {
            "status": "REJECTED",
            "approval_id": approval_request.id,
            "message": f"Yêu cầu phê duyệt #{approval_request.id} đã bị từ chối.",
        }

    elif decision == "APPROVED":
        tool_def = ToolRegistry.get(approval_request.proposed_action)
        if not tool_def:
            raise ToolValidationError(f"Tool '{approval_request.proposed_action}' is not registered.")

        with transaction.atomic():
            # Re-fetch with row lock to prevent race condition double executions
            req = ApprovalRequest.objects.select_for_update().get(id=approval_request.id)
            if req.status == ApprovalStatus.EXECUTED:
                return {
                    "status": "EXECUTED",
                    "approval_id": req.id,
                    "result": req.execution_result,
                    "idempotent_replay": True,
                }

            # Execute tool mutation handler
            try:
                handler_parameters = dict(req.parameters or {})
                handler_parameters.setdefault("idempotency_key", f"APPROVAL-{req.id}")
                exec_result = tool_def.handler(workspace, reviewer, handler_parameters)
            except Exception as e:
                log_audit_event(
                    user=reviewer,
                    workspace=workspace,
                    action="MUTATION_FAILED",
                    target=f"ApprovalRequest #{req.id}",
                    metadata={"approval_id": req.id, "error": str(e)}
                )
                raise ToolValidationError(f"Tool execution failed: {str(e)}")

            # Update approval state
            req.status = ApprovalStatus.EXECUTED
            req.reviewer = reviewer
            req.review_timestamp = now
            req.decision_reason = decision_reason or "Được phê duyệt bởi quản lý."
            req.execution_result = exec_result
            req.executed_at = now
            req.save()

            log_audit_event(
                user=reviewer,
                workspace=workspace,
                action="MUTATION_EXECUTED",
                entity_type="ApprovalRequest",
                entity_id=str(req.id),
                metadata={
                    "approval_id": req.id,
                    "proposed_action": req.proposed_action,
                    "result": exec_result,
                }
            )

        return {
            "status": "EXECUTED",
            "approval_id": req.id,
            "result": exec_result,
            "message": f"Yêu cầu phê duyệt #{req.id} đã được chấp thuận và thực thi thành công.",
        }
    else:
        raise ToolValidationError(f"Invalid decision '{decision}'. Must be 'APPROVED' or 'REJECTED'.")
