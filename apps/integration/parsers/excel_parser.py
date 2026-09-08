"""
Excel Spreadsheet Ingestion Parser (.xlsx).
Handles multi-sheet selection, header detection, datatype preservation (datetime, decimal, bool),
empty row handling, and fault-tolerant row isolation using openpyxl.
"""

import io
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
import openpyxl


def _read_bytes_content(file_obj_or_path: Any) -> bytes:
    """Reads raw bytes from file object, InMemoryUploadedFile, or filesystem path."""
    if hasattr(file_obj_or_path, "read"):
        if hasattr(file_obj_or_path, "seek"):
            file_obj_or_path.seek(0)
        content = file_obj_or_path.read()
        if hasattr(file_obj_or_path, "seek"):
            file_obj_or_path.seek(0)
        if isinstance(content, str):
            return content.encode("utf-8")
        return content
    elif isinstance(file_obj_or_path, str):
        with open(file_obj_or_path, "rb") as f:
            return f.read()
    elif isinstance(file_obj_or_path, bytes):
        return file_obj_or_path
    else:
        raise ValueError(f"Unsupported file object type: {type(file_obj_or_path)}")


def _format_cell_value(val: Any) -> Any:
    """Converts openpyxl cell primitives into clean JSON-serializable types."""
    if val is None:
        return ""
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, (int, float, Decimal)):
        return val
    if isinstance(val, bool):
        return val
    return str(val).strip()


def parse_excel_file(
    file_obj_or_path: Any,
    sheet_name: Optional[str] = None,
    max_rows: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Parses an Excel spreadsheet (.xlsx) into structured raw dictionary rows.

    Returns:
    {
        "columns": List[str],
        "rows": List[{
            "row_number": int,
            "raw_data": Dict[str, Any],
            "is_valid": bool,
            "errors": List[str],
        }],
        "total_rows": int,
        "sheet_name": str,
        "available_sheets": List[str],
        "warnings": List[str],
        "is_valid": bool,
        "error_message": Optional[str],
    }
    """
    try:
        raw_bytes = _read_bytes_content(file_obj_or_path)
    except Exception as e:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "sheet_name": sheet_name or "",
            "available_sheets": [],
            "warnings": [],
            "is_valid": False,
            "error_message": f"Failed to read file bytes: {str(e)}",
        }

    if not raw_bytes or len(raw_bytes) == 0:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "sheet_name": sheet_name or "",
            "available_sheets": [],
            "warnings": ["Excel file is completely empty."],
            "is_valid": False,
            "error_message": "Excel file is empty.",
        }

    try:
        stream = io.BytesIO(raw_bytes)
        wb = openpyxl.load_workbook(stream, data_only=True, read_only=True)
    except Exception as e:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "sheet_name": sheet_name or "",
            "available_sheets": [],
            "warnings": [],
            "is_valid": False,
            "error_message": f"Invalid or corrupted Excel file (.xlsx required): {str(e)}",
        }

    available_sheets = wb.sheetnames
    if not available_sheets:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "sheet_name": "",
            "available_sheets": [],
            "warnings": ["Workbook contains no worksheets."],
            "is_valid": False,
            "error_message": "Excel workbook has no sheets.",
        }

    if sheet_name:
        if sheet_name not in available_sheets:
            return {
                "columns": [],
                "rows": [],
                "total_rows": 0,
                "sheet_name": sheet_name,
                "available_sheets": available_sheets,
                "warnings": [f"Sheet '{sheet_name}' not found. Available: {', '.join(available_sheets)}."],
                "is_valid": False,
                "error_message": f"Worksheet '{sheet_name}' does not exist.",
            }
        ws = wb[sheet_name]
        active_sheet_name = sheet_name
    else:
        active_sheet_name = available_sheets[0]
        ws = wb[active_sheet_name]

    # Read rows iteratively
    headers = []
    header_row_idx = 0
    parsed_rows = []
    data_row_counter = 0
    warnings = []

    for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        # Extract headers from first non-empty row
        if not headers:
            non_empty_cells = [c for c in row if c is not None and str(c).strip() != ""]
            if non_empty_cells:
                headers = [str(c).strip() if c is not None else "" for c in row]
                header_row_idx = row_idx
                # Clean headers
                cleaned_headers = []
                seen = set()
                for idx, h in enumerate(headers):
                    col_name = h if h else f"col_{idx + 1}"
                    if col_name in seen:
                        col_name = f"{col_name}_{idx + 1}"
                        warnings.append(f"Duplicate header renamed to '{col_name}'.")
                    seen.add(col_name)
                    cleaned_headers.append(col_name)
                headers = cleaned_headers
            continue

        # Check if entire row is empty
        if not any(c is not None and str(c).strip() != "" for c in row):
            continue

        data_row_counter += 1
        row_errors = []
        is_row_valid = True

        raw_dict = {}
        for col_idx, col_name in enumerate(headers):
            if col_idx < len(row):
                cell_val = _format_cell_value(row[col_idx])
                raw_dict[col_name] = cell_val
            else:
                raw_dict[col_name] = ""

        parsed_rows.append({
            "row_number": data_row_counter,
            "source_line": row_idx,
            "raw_data": raw_dict,
            "is_valid": is_row_valid,
            "errors": row_errors,
        })

        if max_rows and len(parsed_rows) >= max_rows:
            break

    wb.close()

    if not headers:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "sheet_name": active_sheet_name,
            "available_sheets": available_sheets,
            "warnings": ["Worksheet is empty."],
            "is_valid": False,
            "error_message": "No data found in worksheet.",
        }

    return {
        "columns": headers,
        "rows": parsed_rows,
        "total_rows": len(parsed_rows),
        "sheet_name": active_sheet_name,
        "available_sheets": available_sheets,
        "warnings": warnings,
        "is_valid": True,
        "error_message": None,
    }
