import os
from typing import Dict, Any, List, Optional, Tuple
from django.core.files.base import File
from django.db import transaction
from django.utils import timezone
from django.utils.text import get_valid_filename
from apps.audit.services import log_action
from apps.integration.models import (
    DataSource,
    ImportJob,
    RawImportRecord,
    SourceType,
    ImportStatus,
    EntityType,
)
from apps.integration.parsers.csv_parser import parse_csv_file
from apps.integration.parsers.excel_parser import parse_excel_file
from apps.integration.parsers.api_parser import fetch_and_parse_api
from apps.integration.parsers.preview_engine import generate_preview_metadata

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_FILE_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def validate_uploaded_file(file_obj: Any) -> Tuple[bool, Optional[str]]:
    """
    Validates uploaded file size and extension safety.
    """
    if not file_obj:
        return True, None

    size = getattr(file_obj, "size", None)
    if size is not None and size > MAX_UPLOAD_SIZE:
        return False, f"File size ({size / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of 10 MB."

    fname = getattr(file_obj, "name", "")
    ext = os.path.splitext(fname)[1].lower()
    if ext and ext not in ALLOWED_FILE_EXTENSIONS:
        return False, f"Unsupported file extension '{ext}'. Allowed extensions: .csv, .xlsx, .xls"

    return True, None


def create_data_source(
    workspace,
    user,
    name: str,
    source_type: str,
    connection_config: Optional[Dict[str, Any]] = None,
    is_active: bool = True,
) -> DataSource:
    """
    Creates and registers a new workspace-scoped DataSource.
    """
    if source_type not in SourceType.values:
        raise ValueError(f"Invalid source_type '{source_type}'. Allowed: {SourceType.values}")

    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Data source name cannot be empty.")

    if DataSource.objects.for_workspace(workspace).filter(name__iexact=clean_name).exists():
        raise ValueError(f"Data source with name '{clean_name}' already exists in this workspace.")

    ds = DataSource.objects.create(
        workspace=workspace,
        name=clean_name,
        source_type=source_type,
        connection_config=connection_config or {},
        is_active=is_active,
        created_by=user,
    )

    log_action(
        workspace=workspace,
        actor_user=user,
        action="CREATE",
        entity_type="DataSource",
        entity_id=str(ds.id),
        changes={"name": clean_name, "source_type": source_type},
    )

    return ds


def update_data_source(
    data_source: DataSource,
    user,
    name: Optional[str] = None,
    connection_config: Optional[Dict[str, Any]] = None,
    is_active: Optional[bool] = None,
) -> DataSource:
    """
    Updates an existing DataSource configuration.
    """
    changes = {}
    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Data source name cannot be empty.")
        if (
            clean_name.lower() != data_source.name.lower()
            and DataSource.objects.for_workspace(data_source.workspace)
            .filter(name__iexact=clean_name)
            .exclude(id=data_source.id)
            .exists()
        ):
            raise ValueError(f"Data source with name '{clean_name}' already exists in this workspace.")
        changes["name"] = {"old": data_source.name, "new": clean_name}
        data_source.name = clean_name

    if connection_config is not None:
        changes["connection_config"] = {"old": data_source.connection_config, "new": connection_config}
        data_source.connection_config = connection_config

    if is_active is not None:
        changes["is_active"] = {"old": data_source.is_active, "new": is_active}
        data_source.is_active = is_active

    if changes:
        data_source.save()
        log_action(
            workspace=data_source.workspace,
            actor_user=user,
            action="UPDATE",
            entity_type="DataSource",
            entity_id=str(data_source.id),
            changes=changes,
        )

    return data_source


def generate_import_preview(
    file_obj: Optional[Any] = None,
    data_source: Optional[DataSource] = None,
    source_type: Optional[str] = None,
    sheet_name: Optional[str] = None,
    endpoint_url: Optional[str] = None,
    sample_count: int = 5,
) -> Dict[str, Any]:
    """
    Generates preview metadata (columns, data types, sample rows, warnings)
    before committing an import.
    """
    effective_type = source_type
    if data_source:
        effective_type = data_source.source_type

    if file_obj:
        is_safe, error_msg = validate_uploaded_file(file_obj)
        if not is_safe:
            return {"is_valid": False, "error_message": error_msg, "columns": [], "sample_rows": [], "detected_types": {}, "total_rows": 0, "warnings": [], "metadata": {}}

        fname = getattr(file_obj, "name", "").lower()
        if not effective_type:
            if fname.endswith(".csv"):
                effective_type = SourceType.CSV
            elif fname.endswith(".xlsx") or fname.endswith(".xls"):
                effective_type = SourceType.EXCEL
            else:
                effective_type = SourceType.CSV

    if effective_type == SourceType.CSV:
        if not file_obj:
            return {"is_valid": False, "error_message": "CSV file upload is required for preview.", "columns": [], "sample_rows": [], "detected_types": {}, "total_rows": 0, "warnings": [], "metadata": {}}
        parse_result = parse_csv_file(file_obj)

    elif effective_type == SourceType.EXCEL:
        if not file_obj:
            return {"is_valid": False, "error_message": "Excel file upload is required for preview.", "columns": [], "sample_rows": [], "detected_types": {}, "total_rows": 0, "warnings": [], "metadata": {}}
        parse_result = parse_excel_file(file_obj, sheet_name=sheet_name)

    elif effective_type == SourceType.MOCK_API:
        url = endpoint_url
        headers = None
        params = None
        if data_source and isinstance(data_source.connection_config, dict):
            url = url or data_source.connection_config.get("url") or data_source.connection_config.get("endpoint_url")
            headers = data_source.connection_config.get("headers")
            params = data_source.connection_config.get("params")

        if not url:
            return {"is_valid": False, "error_message": "API endpoint URL is required for preview.", "columns": [], "sample_rows": [], "detected_types": {}, "total_rows": 0, "warnings": [], "metadata": {}}

        parse_result = fetch_and_parse_api(url, headers=headers, params=params)

    else:
        return {"is_valid": False, "error_message": f"Unsupported source type '{effective_type}'.", "columns": [], "sample_rows": [], "detected_types": {}, "total_rows": 0, "warnings": [], "metadata": {}}

    return generate_preview_metadata(parse_result, sample_count=sample_count)


def execute_import_job(
    workspace,
    user,
    data_source: DataSource,
    file_obj: Optional[Any] = None,
    entity_type: str = EntityType.GENERAL,
    sheet_name: Optional[str] = None,
) -> ImportJob:
    """
    Executes the ingestion pipeline:
    1. Validates uploaded file safety (extension & size limit).
    2. Instantiates ImportJob in RUNNING state.
    3. Parses raw source data (CSV, Excel, or API).
    4. Stages raw records into RawImportRecord.
    5. Aggregates row statistics and error summaries without fatal crashes.
    6. Updates ImportJob status (COMPLETED, PARTIAL, or FAILED) and writes AuditLog.
    """
    now = timezone.now()

    # Validate file upload safety before creating/running job
    if file_obj:
        is_safe, error_msg = validate_uploaded_file(file_obj)
        if not is_safe:
            job = ImportJob.objects.create(
                workspace=workspace,
                data_source=data_source,
                entity_type=entity_type,
                status=ImportStatus.FAILED,
                started_at=now,
                completed_at=now,
                error_summary=[{"row": 0, "error_type": "SECURITY_VALIDATION_ERROR", "message": error_msg, "raw": {}}],
                created_by=user,
            )
            log_action(
                workspace=workspace,
                actor_user=user,
                action="IMPORT_FAILED",
                entity_type="ImportJob",
                entity_id=str(job.id),
                changes={"reason": error_msg},
            )
            return job

    # Create job in RUNNING status
    job = ImportJob.objects.create(
        workspace=workspace,
        data_source=data_source,
        entity_type=entity_type,
        status=ImportStatus.RUNNING,
        started_at=now,
        created_by=user,
    )

    if file_obj:
        raw_name = getattr(file_obj, "name", "import_data")
        clean_name = get_valid_filename(os.path.basename(raw_name))
        job.source_file.save(clean_name, file_obj, save=False)

    log_action(
        workspace=workspace,
        actor_user=user,
        action="IMPORT_STARTED",
        entity_type="ImportJob",
        entity_id=str(job.id),
        changes={"data_source_id": str(data_source.id), "entity_type": entity_type},
    )

    # 1. Parse source data
    parse_result = {}
    try:
        if data_source.source_type == SourceType.CSV:
            if not file_obj and not job.source_file:
                raise ValueError("No CSV file provided for ingestion.")
            f = file_obj or job.source_file
            parse_result = parse_csv_file(f)

        elif data_source.source_type == SourceType.EXCEL:
            if not file_obj and not job.source_file:
                raise ValueError("No Excel file provided for ingestion.")
            f = file_obj or job.source_file
            target_sheet = sheet_name or data_source.connection_config.get("sheet_name")
            parse_result = parse_excel_file(f, sheet_name=target_sheet)

        elif data_source.source_type == SourceType.MOCK_API:
            url = data_source.connection_config.get("url") or data_source.connection_config.get("endpoint_url")
            headers = data_source.connection_config.get("headers")
            params = data_source.connection_config.get("params")
            if not url:
                raise ValueError("DataSource connection_config is missing 'url' parameter.")
            parse_result = fetch_and_parse_api(url, headers=headers, params=params)

        else:
            raise ValueError(f"Unsupported source_type: {data_source.source_type}")

    except Exception as e:
        job.status = ImportStatus.FAILED
        job.completed_at = timezone.now()
        job.error_summary = [{"row": 0, "error_type": "FATAL_ERROR", "message": str(e), "raw": {}}]
        job.save()

        log_action(
            workspace=workspace,
            actor_user=user,
            action="IMPORT_FAILED",
            entity_type="ImportJob",
            entity_id=str(job.id),
            changes={"reason": str(e)},
        )
        return job

    if not parse_result.get("is_valid", False):
        err_msg = parse_result.get("error_message") or "Failed to parse data source."
        job.status = ImportStatus.FAILED
        job.completed_at = timezone.now()
        job.error_summary = [{"row": 0, "error_type": "PARSE_ERROR", "message": err_msg, "raw": {}}]
        job.save()

        log_action(
            workspace=workspace,
            actor_user=user,
            action="IMPORT_FAILED",
            entity_type="ImportJob",
            entity_id=str(job.id),
            changes={"reason": err_msg},
        )
        return job

    # 2. Stage raw records in bulk
    raw_rows = parse_result.get("rows", [])
    total_count = len(raw_rows)
    successful_count = 0
    failed_count = 0
    error_summary = []

    records_to_create = []
    for r in raw_rows:
        row_num = r.get("row_number", 1)
        raw_data = r.get("raw_data", {})
        is_row_valid = r.get("is_valid", True)
        row_errors = r.get("errors", [])

        if not is_row_valid or row_errors:
            failed_count += 1
            for err in row_errors:
                error_summary.append({
                    "row": row_num,
                    "error_type": "ROW_VALIDATION_ERROR",
                    "message": err,
                    "raw": raw_data,
                })
        else:
            successful_count += 1

        records_to_create.append(
            RawImportRecord(
                workspace=workspace,
                import_job=job,
                row_number=row_num,
                raw_data=raw_data,
                is_valid=is_row_valid and len(row_errors) == 0,
                validation_errors=row_errors,
            )
        )

    # Bulk insert raw records
    with transaction.atomic():
        if records_to_create:
            RawImportRecord.objects.bulk_create(records_to_create, batch_size=500)

    # 3. Determine final status
    if total_count == 0:
        final_status = ImportStatus.FAILED
        error_summary.append({"row": 0, "error_type": "EMPTY_DATASET", "message": "Source dataset contained 0 records.", "raw": {}})
    elif failed_count == 0:
        final_status = ImportStatus.COMPLETED
    elif successful_count > 0:
        final_status = ImportStatus.PARTIAL
    else:
        final_status = ImportStatus.FAILED

    meta = {}
    for k in ("encoding", "delimiter", "sheet_name", "source_url", "columns"):
        if k in parse_result:
            meta[k] = parse_result[k]

    job.status = final_status
    job.total_rows = total_count
    job.successful_rows = successful_count
    job.failed_rows = failed_count
    job.error_summary = error_summary
    job.source_metadata = meta
    job.completed_at = timezone.now()
    job.save()

    log_action(
        workspace=workspace,
        actor_user=user,
        action=f"IMPORT_{final_status}",
        entity_type="ImportJob",
        entity_id=str(job.id),
        changes={
            "status": final_status,
            "total_rows": total_count,
            "successful_rows": successful_count,
            "failed_rows": failed_count,
        },
    )

    return job


def get_import_job_errors(import_job: ImportJob, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Returns the list of error records from error_summary or failed RawImportRecords.
    """
    if import_job.error_summary:
        return import_job.error_summary[:limit]

    failed_records = import_job.raw_records.filter(is_valid=False)[:limit]
    errors = []
    for rec in failed_records:
        errors.append({
            "row": rec.row_number,
            "error_type": "INVALID_RECORD",
            "message": "; ".join(rec.validation_errors) if rec.validation_errors else "Validation failed",
            "raw": rec.raw_data,
        })
    return errors
