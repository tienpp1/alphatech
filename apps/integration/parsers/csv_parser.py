"""
CSV Ingestion Parser.
Handles robust CSV file parsing, encoding fallback (utf-8-sig, utf-8, latin-1),
delimiter detection, header extraction, empty row handling, and fault-tolerant row isolation.
"""

import csv
import io
from typing import Dict, Any, List, Optional, Union, Tuple


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


def _decode_bytes_with_fallback(raw_bytes: bytes) -> Tuple[str, str]:
    """Attempts decoding bytes with fallback encodings."""
    encodings = ["utf-8-sig", "utf-8", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            decoded_text = raw_bytes.decode(enc)
            return decoded_text, enc
        except UnicodeDecodeError:
            continue
    # Ultimate fallback: decode with replacement characters
    return raw_bytes.decode("utf-8", errors="replace"), "utf-8-replace"


def parse_csv_file(
    file_obj_or_path: Any,
    max_rows: Optional[int] = None,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parses a CSV file into structured raw dictionary rows.

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
        "encoding": str,
        "delimiter": str,
        "warnings": List[str],
    }
    """
    raw_bytes = _read_bytes_content(file_obj_or_path)
    if not raw_bytes or len(raw_bytes.strip()) == 0:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "encoding": "empty",
            "delimiter": ",",
            "warnings": ["File is completely empty."],
            "is_valid": False,
            "error_message": "CSV file contains no data.",
        }

    if encoding:
        try:
            text = raw_bytes.decode(encoding)
            used_encoding = encoding
        except Exception:
            text, used_encoding = _decode_bytes_with_fallback(raw_bytes)
    else:
        text, used_encoding = _decode_bytes_with_fallback(raw_bytes)

    # Detect delimiter if not provided
    sample_text = text[:4096]
    used_delimiter = delimiter or ","
    if not delimiter:
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_text, delimiters=[",", ";", "\t", "|"])
            used_delimiter = dialect.delimiter
        except Exception:
            # Default to comma
            used_delimiter = ","

    stream = io.StringIO(text)
    reader = csv.reader(stream, delimiter=used_delimiter)

    # Extract header row
    headers = []
    header_row_index = 0
    for row_idx, row in enumerate(reader, start=1):
        # Skip empty lines before header
        non_empty = [c.strip() for c in row if c and c.strip()]
        if non_empty:
            headers = [c.strip() for c in row]
            header_row_index = row_idx
            break

    if not headers:
        return {
            "columns": [],
            "rows": [],
            "total_rows": 0,
            "encoding": used_encoding,
            "delimiter": used_delimiter,
            "warnings": ["No valid header row found."],
            "is_valid": False,
            "error_message": "No header row detected in CSV file.",
        }

    # Clean headers (handle duplicates or empty column headers)
    cleaned_headers = []
    seen_headers = set()
    warnings = []
    for idx, h in enumerate(headers):
        clean_h = h if h else f"col_{idx + 1}"
        if clean_h in seen_headers:
            clean_h = f"{clean_h}_{idx + 1}"
            warnings.append(f"Duplicate header renamed to '{clean_h}'.")
        seen_headers.add(clean_h)
        cleaned_headers.append(clean_h)

    # Parse rows
    parsed_rows = []
    data_row_counter = 0

    for row_idx, row in enumerate(reader, start=header_row_index + 1):
        # Skip purely empty rows
        if not row or not any(c.strip() for c in row if c):
            continue

        data_row_counter += 1
        row_errors = []
        is_row_valid = True

        # Check column count alignment
        if len(row) != len(cleaned_headers):
            row_errors.append(
                f"Row {row_idx} column mismatch: expected {len(cleaned_headers)} columns, got {len(row)}."
            )
            is_row_valid = False

        # Build raw dict
        raw_dict = {}
        for col_idx, col_name in enumerate(cleaned_headers):
            if col_idx < len(row):
                val = row[col_idx].strip() if row[col_idx] else ""
                raw_dict[col_name] = val
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

    return {
        "columns": cleaned_headers,
        "rows": parsed_rows,
        "total_rows": len(parsed_rows),
        "encoding": used_encoding,
        "delimiter": used_delimiter,
        "warnings": warnings,
        "is_valid": True,
        "error_message": None,
    }
