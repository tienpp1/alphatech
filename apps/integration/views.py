"""
Data Integration & Ingestion REST API Views.
Exposes endpoints for data source registration, file/API import preview,
ingestion execution, job monitoring, and error retrieval.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import PermissionDenied
from apps.workspaces.permissions import IsWorkspaceMember
from apps.accounts.services import has_workspace_permission
from apps.integration.models import DataSource, ImportJob, RawImportRecord, SourceType
from apps.integration.serializers import (
    DataSourceSerializer,
    DataSourceCreateSerializer,
    ImportJobSerializer,
    ImportJobDetailSerializer,
    RawImportRecordSerializer,
    ImportPreviewRequestSerializer,
    ImportExecutionRequestSerializer,
)
from apps.integration.services import (
    create_data_source,
    update_data_source,
    generate_import_preview,
    execute_import_job,
    get_import_job_errors,
)


def _resolve_request_workspace(request):
    return getattr(request, "active_workspace", None) or getattr(request._request, "active_workspace", None)


def _require_permission(request, workspace, codename):
    if not has_workspace_permission(request.user, workspace, codename):
        raise PermissionDenied(f"Missing workspace permission: {codename}")


class DataSourceListCreateAPIView(APIView):
    """
    GET  /api/v1/integration/data-sources/ (List all data sources in active workspace)
    POST /api/v1/integration/data-sources/ (Register a new data source)
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "integration.view_datasource")
        qs = DataSource.objects.for_workspace(workspace)
        source_type = request.query_params.get("source_type")
        if source_type:
            qs = qs.filter(source_type=source_type)

        serializer = DataSourceSerializer(qs, many=True)
        return Response({"status": "success", "count": qs.count(), "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "integration.manage_datasource")

        serializer = DataSourceCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"status": "error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ds = create_data_source(
                workspace=workspace,
                user=request.user,
                name=serializer.validated_data["name"],
                source_type=serializer.validated_data["source_type"],
                connection_config=serializer.validated_data.get("connection_config", {}),
                is_active=serializer.validated_data.get("is_active", True),
            )
            return Response({"status": "success", "data": DataSourceSerializer(ds).data}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DataSourceDetailAPIView(APIView):
    """
    GET    /api/v1/integration/data-sources/{id}/
    PATCH  /api/v1/integration/data-sources/{id}/
    DELETE /api/v1/integration/data-sources/{id}/
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        workspace = _resolve_request_workspace(request)
        _require_permission(request, workspace, "integration.view_datasource")
        ds = get_object_or_404(DataSource.objects.for_workspace(workspace), id=pk)
        return Response({"status": "success", "data": DataSourceSerializer(ds).data}, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        workspace = _resolve_request_workspace(request)
        _require_permission(request, workspace, "integration.manage_datasource")
        ds = get_object_or_404(DataSource.objects.for_workspace(workspace), id=pk)

        try:
            updated_ds = update_data_source(
                data_source=ds,
                user=request.user,
                name=request.data.get("name"),
                connection_config=request.data.get("connection_config"),
                is_active=request.data.get("is_active"),
            )
            return Response({"status": "success", "data": DataSourceSerializer(updated_ds).data}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        workspace = _resolve_request_workspace(request)
        _require_permission(request, workspace, "integration.manage_datasource")
        ds = get_object_or_404(DataSource.objects.for_workspace(workspace), id=pk)

        ds.delete()
        return Response({"status": "success", "message": "Data source deleted."}, status=status.HTTP_200_OK)


class ImportPreviewAPIView(APIView):
    """
    POST /api/v1/integration/imports/preview/
    Inspects uploaded file or registered data source and returns columns, detected datatypes,
    sample records, row counts, and structural warnings.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def post(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "integration.execute_import")
        file_obj = request.FILES.get("file")
        ds_id = request.data.get("data_source_id")
        source_type = request.data.get("source_type")
        sheet_name = request.data.get("sheet_name")
        endpoint_url = request.data.get("endpoint_url")
        sample_count = int(request.data.get("sample_count", 5))

        ds = None
        if ds_id:
            try:
                ds = DataSource.objects.for_workspace(workspace).get(id=ds_id)
            except DataSource.DoesNotExist:
                return Response({"status": "error", "message": f"DataSource '{ds_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

        # File size safety limit (e.g. 50MB)
        if file_obj and file_obj.size > 50 * 1024 * 1024:
            return Response({"status": "error", "message": "File exceeds 50MB maximum upload limit."}, status=status.HTTP_400_BAD_REQUEST)

        preview_result = generate_import_preview(
            file_obj=file_obj,
            data_source=ds,
            source_type=source_type,
            sheet_name=sheet_name,
            endpoint_url=endpoint_url,
            sample_count=sample_count,
        )

        return Response({"status": "success", "data": preview_result}, status=status.HTTP_200_OK)


class ImportJobListCreateAPIView(APIView):
    """
    GET  /api/v1/integration/import-jobs/ (List import jobs in workspace)
    POST /api/v1/integration/import-jobs/ (Execute a new ingestion job)
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "integration.view_datasource")
        qs = ImportJob.objects.for_workspace(workspace).select_related("data_source", "created_by")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = ImportJobSerializer(qs, many=True)
        return Response({"status": "success", "count": qs.count(), "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace context."}, status=status.HTTP_400_BAD_REQUEST)

        _require_permission(request, workspace, "integration.execute_import")

        ds_id = request.data.get("data_source_id")
        if not ds_id:
            return Response({"status": "error", "message": "Missing 'data_source_id'."}, status=status.HTTP_400_BAD_REQUEST)

        data_source = get_object_or_404(DataSource.objects.for_workspace(workspace), id=ds_id)
        file_obj = request.FILES.get("file")
        entity_type = request.data.get("entity_type", "GENERAL")
        sheet_name = request.data.get("sheet_name")

        if file_obj and file_obj.size > 50 * 1024 * 1024:
            return Response({"status": "error", "message": "File exceeds 50MB maximum upload limit."}, status=status.HTTP_400_BAD_REQUEST)

        job = execute_import_job(
            workspace=workspace,
            user=request.user,
            data_source=data_source,
            file_obj=file_obj,
            entity_type=entity_type,
            sheet_name=sheet_name,
        )

        return Response(
            {"status": "success", "data": ImportJobDetailSerializer(job).data},
            status=status.HTTP_201_CREATED if job.status in ("COMPLETED", "PARTIAL") else status.HTTP_200_OK,
        )


class ImportJobDetailAPIView(APIView):
    """
    GET /api/v1/integration/import-jobs/{id}/
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        workspace = _resolve_request_workspace(request)
        _require_permission(request, workspace, "integration.view_datasource")
        job = get_object_or_404(
            ImportJob.objects.for_workspace(workspace).select_related("data_source", "created_by"),
            id=pk,
        )
        return Response({"status": "success", "data": ImportJobDetailSerializer(job).data}, status=status.HTTP_200_OK)


class ImportJobErrorsAPIView(APIView):
    """
    GET /api/v1/integration/import-jobs/{id}/errors/
    Returns the list of validation and structural errors encountered during ingestion.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        workspace = _resolve_request_workspace(request)
        _require_permission(request, workspace, "integration.view_datasource")
        job = get_object_or_404(ImportJob.objects.for_workspace(workspace), id=pk)
        errors = get_import_job_errors(job)
        return Response({"status": "success", "count": len(errors), "data": errors}, status=status.HTTP_200_OK)


class ImportJobRawRecordsAPIView(APIView):
    """
    GET /api/v1/integration/import-jobs/{id}/raw-records/
    Paginated viewer for raw staged records before mapping.
    """
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get(self, request, pk):
        workspace = _resolve_request_workspace(request)
        _require_permission(request, workspace, "integration.view_datasource")
        job = get_object_or_404(ImportJob.objects.for_workspace(workspace), id=pk)

        records_qs = job.raw_records.all()
        is_valid_filter = request.query_params.get("is_valid")
        if is_valid_filter is not None:
            records_qs = records_qs.filter(is_valid=is_valid_filter.lower() in ("true", "1"))

        serializer = RawImportRecordSerializer(records_qs[:100], many=True)
        return Response({
            "status": "success",
            "job_id": job.id,
            "total_staged_records": job.raw_records.count(),
            "count": len(serializer.data),
            "data": serializer.data,
        }, status=status.HTTP_200_OK)
