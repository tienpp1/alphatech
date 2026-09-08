"""
REST API Views for Approvals and Controlled Tool Execution (Phase 10).
Enforces workspace isolation, RBAC, schema validation, and standard response envelopes.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.workspaces.services import resolve_request_workspace as get_request_workspace
from apps.workspaces.permissions import IsWorkspaceMember, require_permission
from apps.accounts.services import has_workspace_permission
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.approvals.serializers import (
    ApprovalRequestSerializer,
    ApprovalDecisionSerializer,
    ToolExecuteRequestSerializer,
)
from apps.approvals.registry import ToolRegistry, ToolException
from apps.approvals.executor import execute_tool, process_approval_decision


def api_response(data=None, error=None, status_code=status.HTTP_200_OK):
    success = error is None and status.is_success(status_code)
    return Response(
        {"success": success, "data": data, "error": error},
        status=status_code,
    )


class ApprovalRequestListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("approvals.view_approval")]

    def get(self, request):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        status_filter = request.query_params.get("status")
        qs = ApprovalRequest.objects.for_workspace(workspace)
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = ApprovalRequestSerializer(qs, many=True)
        return api_response(data=serializer.data)


class ApprovalRequestDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("approvals.view_approval")]

    def get(self, request, pk):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        app_req = ApprovalRequest.objects.for_workspace(workspace).filter(pk=pk).first()
        if not app_req:
            return api_response(error="Approval request not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = ApprovalRequestSerializer(app_req)
        return api_response(data=serializer.data)


class ApprovalRequestDecisionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("approvals.manage_approval")]

    def post(self, request, pk):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        app_req = ApprovalRequest.objects.for_workspace(workspace).filter(pk=pk).first()
        if not app_req:
            return api_response(error="Approval request not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = ApprovalDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            res = process_approval_decision(
                approval_request=app_req,
                reviewer=request.user,
                decision=serializer.validated_data["decision"],
                decision_reason=serializer.validated_data.get("decision_reason", ""),
            )
            return api_response(data=res)
        except ToolException as e:
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class ToolRegistryListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("approvals.view_approval")]

    def get(self, request):
        tools = ToolRegistry.list_tools()
        return api_response(data={"tools": tools})


class ToolExecuteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request, name=None):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        tool_name = name or request.data.get("tool_name")
        if not tool_name:
            return api_response(error="Parameter 'tool_name' is required.", status_code=status.HTTP_400_BAD_REQUEST)

        parameters = request.data.get("parameters", {})
        idempotency_key = request.data.get("idempotency_key", "")
        reason = request.data.get("reason", "Thực thi qua REST API Tool")

        try:
            res = execute_tool(
                name=tool_name,
                workspace=workspace,
                user=request.user,
                parameters=parameters,
                idempotency_key=idempotency_key,
                reason=reason,
            )
            return api_response(data=res)
        except ToolException as e:
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)
