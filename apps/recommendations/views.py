"""
REST API Views for Business Recommendations & Decision Support (Phase 10).
Enforces workspace isolation, RBAC, and standard platform envelope.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.workspaces.models import WorkspaceType
from apps.workspaces.services import resolve_request_workspace as get_request_workspace
from apps.workspaces.permissions import IsWorkspaceMember, require_permission
from apps.accounts.services import has_workspace_permission
from apps.audit.services import log_audit_event
from apps.recommendations.models import Recommendation, RecommendationStatus
from apps.recommendations.serializers import RecommendationSerializer, RecommendationDecisionSerializer
from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations
from apps.recommendations.services import accept_recommendation
from apps.approvals.registry import ToolException


def api_response(data=None, error=None, status_code=status.HTTP_200_OK):
    success = error is None and status.is_success(status_code)
    return Response(
        {"success": success, "data": data, "error": error},
        status=status_code,
    )


class RecommendationListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("recommendations.view_recommendation")]

    def get(self, request):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        status_filter = request.query_params.get("status")
        type_filter = request.query_params.get("recommendation_type")

        qs = Recommendation.objects.for_workspace(workspace)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if type_filter:
            qs = qs.filter(recommendation_type=type_filter)

        serializer = RecommendationSerializer(qs, many=True)
        return api_response(data=serializer.data)


class RecommendationDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("recommendations.view_recommendation")]

    def get(self, request, pk):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        rec = Recommendation.objects.for_workspace(workspace).filter(pk=pk).first()
        if not rec:
            return api_response(error="Recommendation not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = RecommendationSerializer(rec)
        return api_response(data=serializer.data)


class RecommendationAcceptAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("recommendations.manage_recommendation")]

    def post(self, request, pk):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        if not has_workspace_permission(request.user, workspace, "recommendations.manage_recommendation") and not request.user.is_superuser:
            return api_response(error="Permission denied: 'recommendations.manage_recommendation' required.", status_code=status.HTTP_403_FORBIDDEN)

        rec = Recommendation.objects.for_workspace(workspace).filter(pk=pk).first()
        if not rec:
            return api_response(error="Recommendation not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = RecommendationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rec = accept_recommendation(
                rec,
                request.user,
                serializer.validated_data.get("decision_reason", ""),
            )
        except ToolException as exc:
            return api_response(error=str(exc), status_code=status.HTTP_400_BAD_REQUEST)

        log_audit_event(
            user=request.user,
            workspace=workspace,
            action="RECOMMENDATION_ACCEPTED",
            target=f"Recommendation #{rec.id}",
            metadata={
                "recommendation_id": rec.id,
                "recommendation_type": rec.recommendation_type,
                "decision_reason": serializer.validated_data.get("decision_reason"),
                "approval_request_id": rec.approval_request_id,
            }
        )

        return api_response(data=RecommendationSerializer(rec).data)


class RecommendationRejectAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("recommendations.manage_recommendation")]

    def post(self, request, pk):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        if not has_workspace_permission(request.user, workspace, "recommendations.manage_recommendation") and not request.user.is_superuser:
            return api_response(error="Permission denied: 'recommendations.manage_recommendation' required.", status_code=status.HTTP_403_FORBIDDEN)

        rec = Recommendation.objects.for_workspace(workspace).filter(pk=pk).first()
        if not rec:
            return api_response(error="Recommendation not found.", status_code=status.HTTP_404_NOT_FOUND)

        serializer = RecommendationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rec.status = RecommendationStatus.REJECTED
        rec.save()

        log_audit_event(
            user=request.user,
            workspace=workspace,
            action="RECOMMENDATION_REJECTED",
            target=f"Recommendation #{rec.id}",
            metadata={
                "recommendation_id": rec.id,
                "recommendation_type": rec.recommendation_type,
                "decision_reason": serializer.validated_data.get("decision_reason"),
            }
        )

        return api_response(data=RecommendationSerializer(rec).data)


class RecommendationEvaluateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("recommendations.manage_recommendation")]

    def post(self, request):
        workspace = get_request_workspace(request)
        if not workspace:
            return api_response(error="No active workspace bound to user.", status_code=status.HTTP_400_BAD_REQUEST)

        if not has_workspace_permission(request.user, workspace, "recommendations.manage_recommendation") and not request.user.is_superuser:
            return api_response(error="Permission denied: 'recommendations.manage_recommendation' required.", status_code=status.HTTP_403_FORBIDDEN)

        if workspace.workspace_type == WorkspaceType.RETAIL:
            created = evaluate_retail_recommendations(workspace)
        elif workspace.workspace_type == WorkspaceType.SERVICE:
            created = evaluate_service_recommendations(workspace)
        else:
            created = []

        log_audit_event(
            user=request.user,
            workspace=workspace,
            action="RECOMMENDATIONS_EVALUATED",
            target=f"Workspace {workspace.code}",
            metadata={"created_count": len(created)}
        )

        serializer = RecommendationSerializer(created, many=True)
        return api_response(data={"created_count": len(created), "recommendations": serializer.data})
