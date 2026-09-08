"""
Import Preview & Type Inference Engine.
Analyzes ingested raw tabular structures, infers column datatypes,
generates sample rows, calculates row counts, and detects structural warnings.
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional


def _infer_value_type(val: Any) -> str:
    """Infers the primitive type of a single string/cell value."""
    if val is None:
        return "EMPTY"
    val_str = str(val).strip()
    if not val_str:
        return "EMPTY"

    # Boolean
    if val_str.lower() in ("true", "false", "yes", "no", "có", "không"):
        return "BOOLEAN"

    # Integer
    if re.match(r"^-?\d+$", val_str):
        return "INTEGER"

    # Decimal / Currency (e.g. 1500000.00, 1,500,000, 1.500.000, 150.50)
    cleaned_num = re.sub(r"[^\d.-]", "", val_str)
    if cleaned_num and re.match(r"^-?\d+(\.\d+)?$", cleaned_num):
        # If original was pure digits, we already matched integer, otherwise decimal
        if "." in cleaned_num or "," in val_str:
            return "DECIMAL"

    # Date / Datetime
    date_patterns = [
        r"^\d{4}-\d{2}-\d{2}$",            # YYYY-MM-DD
        r"^\d{2}/\d{2}/\d{4}$",            # DD/MM/YYYY
        r"^\d{2}-\d{2}-\d{4}$",            # DD-MM-YYYY
    ]
    for pat in date_patterns:
        if re.match(pat, val_str):
            return "DATE"

    datetime_patterns = [
        r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2})?.*$",  # ISO Datetime
        r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}(:\d{2})?$",       # DD/MM/YYYY HH:MM:SS
    ]
    for pat in datetime_patterns:
        if re.match(pat, val_str):
            return "DATETIME"

    return "STRING"


def infer_column_types(columns: List[str], rows: List[Dict[str, Any]], sample_size: int = 50) -> Dict[str, str]:
    """
    Infers dominant data type for each column based on sample rows.
    """
    column_types = {}
    sample_rows = rows[:sample_size]

    for col in columns:
        type_counts = {}
        for r in sample_rows:
            raw_data = r.get("raw_data", {}) if isinstance(r, dict) else {}
            val = raw_data.get(col)
            t = _infer_value_type(val)
            if t != "EMPTY":
                type_counts[t] = type_counts.get(t, 0) + 1

        if not type_counts:
            column_types[col] = "STRING"
        else:
            # Pick dominant type
            dominant_type = max(type_counts.items(), key=lambda x: x[1])[0]
            column_types[col] = dominant_type

    return column_types


def generate_preview_metadata(
    parse_result: Dict[str, Any],
    sample_count: int = 5,
) -> Dict[str, Any]:
    """
    Generates preview contract response from raw parser result.

    Returns:
    {
        "is_valid": bool,
        "error_message": Optional[str],
        "columns": List[str],
        "detected_types": Dict[str, str],
        "total_rows": int,
        "sample_rows": List[Dict[str, Any]],
        "warnings": List[str],
        "metadata": Dict[str, Any],
    }
    """
    if not parse_result.get("is_valid", False):
        return {
            "is_valid": False,
            "error_message": parse_result.get("error_message") or "Failed to parse input data.",
            "columns": [],
            "detected_types": {},
            "total_rows": 0,
            "sample_rows": [],
            "warnings": parse_result.get("warnings", []),
            "metadata": {},
        }

    columns = parse_result.get("columns", [])
    rows = parse_result.get("rows", [])
    total_rows = parse_result.get("total_rows", len(rows))
    warnings = list(parse_result.get("warnings", []))

    # Infer column types
    detected_types = infer_column_types(columns, rows)

    # Check for empty columns or formatting warnings
    if total_rows == 0:
        warnings.append("Dataset has headers but contains 0 data rows.")

    # Format sample rows
    sample_rows = []
    for r in rows[:sample_count]:
        sample_rows.append({
            "row_number": r.get("row_number", 1),
            "raw_data": r.get("raw_data", {}),
            "is_valid": r.get("is_valid", True),
            "errors": r.get("errors", []),
        })

    # Record any row-level structural error warnings
    invalid_rows_count = sum(1 for r in rows if not r.get("is_valid", True))
    if invalid_rows_count > 0:
        warnings.append(f"{invalid_rows_count} row(s) contain structural formatting issues or column mismatches.")

    metadata = {}
    for k in ("encoding", "delimiter", "sheet_name", "available_sheets", "source_url"):
        if k in parse_result:
            metadata[k] = parse_result[k]

    return {
        "is_valid": True,
        "error_message": None,
        "columns": columns,
        "detected_types": detected_types,
        "total_rows": total_rows,
        "sample_rows": sample_rows,
        "warnings": warnings,
        "metadata": metadata,
    }
