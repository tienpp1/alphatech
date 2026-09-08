"""
Value and Categorical Enum Mapping Engine for Data Mapping.
Translates external status codes, localized tags, or boolean keys into canonical choices.
"""

from typing import Dict, Any, Optional


def apply_value_mapping(
    val: Any,
    value_map: Dict[str, Any],
    default_val: Optional[Any] = None,
) -> Any:
    """
    Translates an incoming value using a dictionary lookup table.
    Performs case-insensitive matching and handles integer/string type parity.

    Example:
      value_map = {
          "da_thanh_toan": "COMPLETED",
          "1": "COMPLETED",
          "cho_xu_ly": "PENDING",
          "da_huy": "CANCELLED"
      }
    """
    if val is None:
        return default_val

    # Exact match first
    if val in value_map:
        return value_map[val]

    # String normalization match
    str_val = str(val).strip()
    if str_val in value_map:
        return value_map[str_val]

    lower_val = str_val.lower()
    # Check case-insensitive
    for k, v in value_map.items():
        if str(k).strip().lower() == lower_val:
            return v

    # Fallback to default
    return default_val
