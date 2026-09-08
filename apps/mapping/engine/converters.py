"""
Type Sanitization and Type Conversion Primitives for Data Mapping.
Robustly parses Vietnamese and international business formats.
"""

import re
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from typing import Any, Optional, List, Union
from zoneinfo import ZoneInfo
from django.utils import timezone

DEFAULT_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")

COMMON_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%m/%d/%Y",
)

COMMON_DATETIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d %H:%M",
)


def to_string(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def to_decimal(val: Any, default: Optional[Decimal] = None) -> Optional[Decimal]:
    """
    Cleans currency strings into Decimal:
    Handles: "1,500,000 VND", "1.500.000 đ", "1500000.50", "$ 1,200.00", "(500.00)"
    """
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    if isinstance(val, Decimal):
        return val

    s = str(val).strip()
    if not s:
        return default

    # Check for negative in parentheses: (100) -> -100
    is_negative = False
    if s.startswith("(") and s.endswith(")"):
        is_negative = True
        s = s[1:-1].strip()

    # Remove currency symbols and non-numeric characters except separators and minus
    # Keep digits, minus, dot, comma
    cleaned = re.sub(r"[^\d.,\-]", "", s)
    if not cleaned:
        return default

    # Detect separator style:
    # Vietnamese/European style: 1.500.000,50 -> dot is thousand, comma is decimal
    # US/UK style: 1,500,000.50 -> comma is thousand, dot is decimal
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            # Dot is thousand, comma is decimal
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            # Comma is thousand, dot is decimal
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # If comma followed by 3 digits (1,000 or 1,500,000), it's thousand separator
        parts = cleaned.split(",")
        if len(parts) > 1 and all(len(p) == 3 for p in parts[1:]):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        # If multiple dots (1.500.000) or dot followed by exactly 3 digits at end and integer,
        # often thousand separator in Vietnam
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = cleaned.replace(".", "")
        elif len(parts) == 2 and len(parts[1]) == 3 and int(parts[0]) > 0:
            # E.g. "150.000" VND (no cents in VND)
            cleaned = cleaned.replace(".", "")

    try:
        dec_val = Decimal(cleaned)
        return -dec_val if is_negative else dec_val
    except InvalidOperation:
        raise ValueError(f"Cannot convert '{val}' to Decimal.")


def to_integer(val: Any, default: Optional[int] = None) -> Optional[int]:
    """Parses value to standard integer, handling float strings like '5.0'."""
    if val is None:
        return default
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)

    s = str(val).strip().replace(",", "")
    if not s:
        return default

    try:
        f = float(s)
        return int(f)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert '{val}' to Integer.")


def to_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Parses coordinate or numeric value to float."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)

    s = str(val).strip().replace(",", "")
    if not s:
        return default

    try:
        return float(s)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert '{val}' to Float.")


def to_boolean(val: Any, default: Optional[bool] = None) -> Optional[bool]:
    """
    Normalizes diverse representations of boolean flags:
    Truthy: true, 1, yes, có, active, hoạt động, t, y
    Falsy: false, 0, no, không, inactive, ngưng hoạt động, f, n
    """
    if val is None:
        return default
    if isinstance(val, bool):
        return val

    s = str(val).strip().lower()
    if not s:
        return default

    truthy = {"1", "true", "yes", "có", "co", "t", "y", "active", "hoat dong", "hoạt động", "dang hoat dong"}
    falsy = {"0", "false", "no", "không", "khong", "f", "n", "inactive", "ngưng", "ngung"}

    if s in truthy:
        return True
    if s in falsy:
        return False

    return default if default is not None else False


def to_date(val: Any, custom_format: Optional[str] = None) -> Optional[date]:
    """
    Parses date strings across common formats into datetime.date.
    """
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()

    s = str(val).strip()
    if not s:
        return None

    # Try custom format if supplied
    if custom_format:
        try:
            return datetime.strptime(s, custom_format).date()
        except ValueError:
            pass

    # Try standard formats
    for fmt in COMMON_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    # Attempt ISO format parsing
    try:
        return datetime.fromisoformat(s).date()
    except (ValueError, TypeError):
        pass

    raise ValueError(f"Cannot parse date from value '{val}'.")


def to_datetime(val: Any, custom_format: Optional[str] = None) -> Optional[datetime]:
    """
    Parses datetime strings and ensures timezone awareness.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        if timezone.is_naive(val):
            return timezone.make_aware(val, DEFAULT_TIMEZONE)
        return val
    if isinstance(val, date):
        dt = datetime(val.year, val.month, val.day, 0, 0, 0)
        return timezone.make_aware(dt, DEFAULT_TIMEZONE)

    s = str(val).strip()
    if not s:
        return None

    if custom_format:
        try:
            dt = datetime.strptime(s, custom_format)
            if timezone.is_naive(dt):
                return timezone.make_aware(dt, DEFAULT_TIMEZONE)
            return dt
        except ValueError:
            pass

    for fmt in COMMON_DATETIME_FORMATS:
        try:
            dt = datetime.strptime(s, fmt)
            if timezone.is_naive(dt):
                return timezone.make_aware(dt, DEFAULT_TIMEZONE)
            return dt
        except ValueError:
            continue

    try:
        dt = datetime.fromisoformat(s)
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, DEFAULT_TIMEZONE)
        return dt
    except (ValueError, TypeError):
        pass

    raise ValueError(f"Cannot parse datetime from value '{val}'.")


def to_list(val: Any) -> List[str]:
    """Parses a comma or semicolon delimited string or JSON array into a list of strings."""
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [str(x).strip() for x in val if str(x).strip()]

    s = str(val).strip()
    if not s:
        return []

    # Check if comma/semicolon delimited
    tokens = re.split(r"[,;]\s*", s)
    return [t.strip() for t in tokens if t.strip()]
