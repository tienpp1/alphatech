"""
REST API ViewSets & Views for Predictive Analytics & XGBoost Forecasting.
Enforces workspace isolation, RBAC, and standard platform envelope {'success', 'data', 'error'}.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.workspaces.services import resolve_request_workspace as get_request_workspace
from apps.workspaces.permissions import IsWorkspaceMember
from apps.forecasting.models import (
    ForecastModelConfig,
    ForecastRun,
    ForecastResult,
    TargetType,
    RunStatus,
)
from apps.forecasting.serializers import (
    ForecastModelConfigSerializer,
    ForecastRunSerializer,
    ForecastResultSerializer,
    TrainForecastRequestSerializer,
)
from apps.forecasting.services import (
    execute_training_job,
    get_forecast_chart_data,
    get_or_create_default_config,
)


def api_response(data=None, error=None, status_code=status.HTTP_200_OK):
    """Standard platform API envelope: {'success': bool, 'data': Any, 'error': Any}"""
    success = error is None and status.is_success(status_code)
    return Response(
        {"success": success, "data": data, "error": error},
        status=status_code,
    )


def check_view_permission(request, workspace, perm_codename: str) -> bool:
    """Verifies caller has superuser status or workspace-scoped / global RBAC permission."""
    if not request.user or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    from apps.accounts.services import has_workspace_permission
    if workspace and has_workspace_permission(request.user, workspace, perm_codename):
        return True
    return False


class ForecastModelConfigListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.view_forecast"):
            return api_response(error="Permission denied: forecasting.view_forecast required", status_code=status.HTTP_403_FORBIDDEN)

        configs = ForecastModelConfig.objects.for_workspace(ws)
        target_type = request.query_params.get("target_type")
        if target_type:
            configs = configs.filter(target_type=target_type)

        serializer = ForecastModelConfigSerializer(configs, many=True)
        return api_response(data=serializer.data)

    def post(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.manage_forecast"):
            return api_response(error="Permission denied: forecasting.manage_forecast required", status_code=status.HTTP_403_FORBIDDEN)

        serializer = ForecastModelConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(error=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        config = serializer.save(workspace=ws)
        return api_response(data=ForecastModelConfigSerializer(config).data, status_code=status.HTTP_201_CREATED)


class ForecastModelConfigDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.view_forecast"):
            return api_response(error="Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        config = ForecastModelConfig.objects.for_workspace(ws).filter(pk=pk).first()
        if not config:
            return api_response(error="ForecastModelConfig not found", status_code=status.HTTP_404_NOT_FOUND)

        return api_response(data=ForecastModelConfigSerializer(config).data)

    def patch(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.manage_forecast"):
            return api_response(error="Permission denied: forecasting.manage_forecast required", status_code=status.HTTP_403_FORBIDDEN)

        config = ForecastModelConfig.objects.for_workspace(ws).filter(pk=pk).first()
        if not config:
            return api_response(error="ForecastModelConfig not found", status_code=status.HTTP_404_NOT_FOUND)

        serializer = ForecastModelConfigSerializer(config, data=request.data, partial=True)
        if not serializer.is_valid():
            return api_response(error=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        updated = serializer.save()
        return api_response(data=ForecastModelConfigSerializer(updated).data)

    def delete(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.manage_forecast"):
            return api_response(error="Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        config = ForecastModelConfig.objects.for_workspace(ws).filter(pk=pk).first()
        if not config:
            return api_response(error="ForecastModelConfig not found", status_code=status.HTTP_404_NOT_FOUND)

        config.delete()
        return api_response(data={"deleted": True}, status_code=status.HTTP_200_OK)


class ForecastRunListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.view_forecast"):
            return api_response(error="Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        runs = ForecastRun.objects.for_workspace(ws)
        target_type = request.query_params.get("target_type")
        if target_type:
            runs = runs.filter(target_type=target_type)

        serializer = ForecastRunSerializer(runs, many=True)
        return api_response(data=serializer.data)


class ForecastRunDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.view_forecast"):
            return api_response(error="Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        run = ForecastRun.objects.for_workspace(ws).filter(pk=pk).first()
        if not run:
            return api_response(error="ForecastRun not found", status_code=status.HTTP_404_NOT_FOUND)

        return api_response(data=ForecastRunSerializer(run).data)


class TrainForecastAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.manage_forecast"):
            return api_response(error="Permission denied: forecasting.manage_forecast required to train models", status_code=status.HTTP_403_FORBIDDEN)

        serializer = TrainForecastRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response(error=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        vdata = serializer.validated_data
        target_type = vdata["target_type"]
        is_async = vdata.get("is_async", False)
        horizon_days = vdata.get("horizon_days", 14)

        hyperparams = {}
        for param in ["n_estimators", "max_depth", "learning_rate", "test_size"]:
            if param in vdata:
                hyperparams[param] = vdata[param]

        try:
            run = execute_training_job(
                workspace=ws,
                target_type=target_type,
                user=request.user,
                hyperparams=hyperparams if hyperparams else None,
                horizon_days=horizon_days,
                is_async=is_async,
                dimensions=vdata.get("dimensions", {}),
            )
            return api_response(
                data=ForecastRunSerializer(run).data,
                status_code=status.HTTP_202_ACCEPTED if is_async else status.HTTP_200_OK,
            )
        except Exception as e:
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)


class ForecastRunCancelAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request, pk):
        ws = get_request_workspace(request)
        if not check_view_permission(request, ws, "forecasting.manage_forecast"):
            return api_response(error="Permission denied", status_code=status.HTTP_403_FORBIDDEN)
        from .queue import cancel_run
        try:
            run = cancel_run(workspace=ws, user=request.user, run_id=pk)
        except ForecastRun.DoesNotExist:
            return api_response(error="ForecastRun not found", status_code=status.HTTP_404_NOT_FOUND)
        return api_response(data=ForecastRunSerializer(run).data)


class ForecastResultListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.view_forecast"):
            return api_response(error="Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        results = ForecastResult.objects.for_workspace(ws)
        run_id = request.query_params.get("run_id")
        target_type = request.query_params.get("target_type")

        if run_id:
            results = results.filter(forecast_run_id=run_id)
        if target_type:
            results = results.filter(target_type=target_type)

        serializer = ForecastResultSerializer(results[:100], many=True)
        return api_response(data=serializer.data)


class ForecastChartDataAPIView(APIView):
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        ws = get_request_workspace(request)
        if not ws:
            return api_response(error="Workspace context required", status_code=status.HTTP_400_BAD_REQUEST)
        if not check_view_permission(request, ws, "forecasting.view_forecast"):
            return api_response(error="Permission denied", status_code=status.HTTP_403_FORBIDDEN)

        target_type = request.query_params.get("target_type")
        history_days = int(request.query_params.get("history_days", 60))
        horizon_days = int(request.query_params.get("horizon_days", 14))

        try:
            data = get_forecast_chart_data(
                workspace=ws,
                target_type=target_type,
                history_days=history_days,
                horizon_days=horizon_days,
            )
            return api_response(data=data)
        except Exception as e:
            return api_response(error=str(e), status_code=status.HTTP_400_BAD_REQUEST)
