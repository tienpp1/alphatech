"""
Data Integration & Ingestion Web UI Controllers.
Server-rendered dashboards for data source configuration, import wizard with live preview,
job history tracking, and raw staging inspection.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.core.exceptions import PermissionDenied
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.accounts.services import has_workspace_permission
from apps.integration.models import DataSource, ImportJob, RawImportRecord, SourceType, EntityType, ImportStatus
from apps.integration.services import create_data_source, execute_import_job, get_import_job_errors


def _get_active_workspace(request):
    return resolve_authorized_ui_workspace(request, None, "integration.view_datasource")


@login_required
def integration_dashboard_view(request):
    """
    GET /integration/
    High-level integration metrics, recent data sources, and import job activity.
    """
    workspace = _get_active_workspace(request)
    if not workspace:
        messages.error(request, "Please select an active workspace to manage data integration.")
        return redirect("workspace_list")

    data_sources_qs = DataSource.objects.for_workspace(workspace)
    import_jobs_qs = ImportJob.objects.for_workspace(workspace).select_related("data_source", "created_by")

    total_sources = data_sources_qs.count()
    total_jobs = import_jobs_qs.count()

    job_stats = import_jobs_qs.aggregate(
        total_rows=Sum("total_rows"),
        successful_rows=Sum("successful_rows"),
        failed_rows=Sum("failed_rows"),
    )
    total_ingested = job_stats["total_rows"] or 0
    total_successful = job_stats["successful_rows"] or 0
    total_failed = job_stats["failed_rows"] or 0
    success_rate = round((total_successful / total_ingested * 100.0), 1) if total_ingested > 0 else 0.0

    recent_sources = data_sources_qs[:5]
    recent_jobs = import_jobs_qs[:8]

    context = {
        "workspace": workspace,
        "total_sources": total_sources,
        "total_jobs": total_jobs,
        "total_ingested": total_ingested,
        "total_successful": total_successful,
        "total_failed": total_failed,
        "success_rate": success_rate,
        "recent_sources": recent_sources,
        "recent_jobs": recent_jobs,
        "active_nav": "integration",
    }
    return render(request, "integration/dashboard.html", context)


@login_required
def data_sources_list_view(request):
    """
    GET, POST /integration/sources/
    Manage workspace data sources (CSV, Excel, Mock API).
    """
    workspace = _get_active_workspace(request)
    if not workspace:
        return redirect("workspace_list")

    if request.method == "POST":
        if not has_workspace_permission(request.user, workspace, "integration.manage_datasource"):
            raise PermissionDenied("Missing workspace permission: integration.manage_datasource")
        name = request.POST.get("name", "").strip()
        source_type = request.POST.get("source_type")
        endpoint_url = request.POST.get("endpoint_url", "").strip()
        sheet_name = request.POST.get("sheet_name", "").strip()
        delimiter = request.POST.get("delimiter", ",").strip()

        config = {}
        if source_type == SourceType.MOCK_API:
            config["url"] = endpoint_url
        elif source_type == SourceType.EXCEL:
            if sheet_name:
                config["sheet_name"] = sheet_name
        elif source_type == SourceType.CSV:
            config["delimiter"] = delimiter or ","

        try:
            ds = create_data_source(
                workspace=workspace,
                user=request.user,
                name=name,
                source_type=source_type,
                connection_config=config,
            )
            messages.success(request, f"Data source '{ds.name}' created successfully.")
            return redirect("integration_sources")
        except ValueError as e:
            messages.error(request, str(e))

    sources = DataSource.objects.for_workspace(workspace).select_related("created_by")
    context = {
        "workspace": workspace,
        "sources": sources,
        "source_types": SourceType.choices,
        "active_nav": "integration_sources",
        "can_manage": request.user.is_superuser or has_workspace_permission(request.user, workspace, "integration.manage_datasource"),
        "can_import": request.user.is_superuser or has_workspace_permission(request.user, workspace, "integration.execute_import"),
    }
    return render(request, "integration/sources.html", context)


@login_required
def import_wizard_view(request):
    """
    GET, POST /integration/import/
    Interactive ingestion wizard with file upload, preview, and execution.
    """
    workspace = _get_active_workspace(request)
    if not workspace:
        return redirect("workspace_list")

    if request.method == "POST":
        if not has_workspace_permission(request.user, workspace, "integration.execute_import"):
            raise PermissionDenied("Missing workspace permission: integration.execute_import")
        data_source_id = request.POST.get("data_source_id")
        entity_type = request.POST.get("entity_type", EntityType.GENERAL)
        sheet_name = request.POST.get("sheet_name")
        file_obj = request.FILES.get("file")

        if not data_source_id:
            messages.error(request, "Please select a Data Source.")
            return redirect("integration_import")

        data_source = get_object_or_404(DataSource.objects.for_workspace(workspace), id=data_source_id)

        try:
            job = execute_import_job(
                workspace=workspace,
                user=request.user,
                data_source=data_source,
                file_obj=file_obj,
                entity_type=entity_type,
                sheet_name=sheet_name,
            )
            if job.status == ImportStatus.COMPLETED:
                messages.success(request, f"Import completed successfully! Staged {job.successful_rows} records.")
            elif job.status == ImportStatus.PARTIAL:
                messages.warning(request, f"Import partially completed: {job.successful_rows} successful, {job.failed_rows} failed.")
            else:
                messages.error(request, f"Import failed: {job.error_summary[0]['message'] if job.error_summary else 'Unknown error'}")

            return redirect("integration_job_detail", pk=job.id)
        except Exception as e:
            messages.error(request, f"Execution failed: {str(e)}")

    sources = DataSource.objects.for_workspace(workspace).filter(is_active=True)
    context = {
        "workspace": workspace,
        "sources": sources,
        "entity_types": EntityType.choices,
        "active_nav": "integration_import",
        "can_import": request.user.is_superuser or has_workspace_permission(request.user, workspace, "integration.execute_import"),
    }
    return render(request, "integration/import.html", context)


@login_required
def import_jobs_list_view(request):
    """
    GET /integration/jobs/
    Full audit log and listing of all import jobs.
    """
    workspace = _get_active_workspace(request)
    if not workspace:
        return redirect("workspace_list")

    jobs = ImportJob.objects.for_workspace(workspace).select_related("data_source", "created_by")

    status_filter = request.GET.get("status")
    if status_filter:
        jobs = jobs.filter(status=status_filter)

    context = {
        "workspace": workspace,
        "jobs": jobs,
        "status_choices": ImportStatus.choices,
        "active_status": status_filter,
        "active_nav": "integration_jobs",
    }
    return render(request, "integration/jobs.html", context)


@login_required
def import_job_detail_view(request, pk):
    """
    GET /integration/jobs/<uuid:pk>/
    Inspect job status, source metadata, staged raw records, and validation errors.
    """
    workspace = _get_active_workspace(request)
    if not workspace:
        return redirect("workspace_list")

    job = get_object_or_404(
        ImportJob.objects.for_workspace(workspace).select_related("data_source", "created_by"),
        id=pk,
    )

    raw_records = job.raw_records.all()[:50]
    errors = get_import_job_errors(job)

    context = {
        "workspace": workspace,
        "job": job,
        "raw_records": raw_records,
        "errors": errors,
        "active_nav": "integration_jobs",
    }
    return render(request, "integration/job_detail.html", context)
