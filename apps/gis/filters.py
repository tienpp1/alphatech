"""
Query Parameter Parsers & Validators for Spatial GIS Endpoints.
"""

from typing import Optional, Tuple
from datetime import datetime, date
from rest_framework.exceptions import ValidationError


def parse_bbox_param(bbox_str: Optional[str]) -> Optional[Tuple[float, float, float, float]]:
    """
    Parses a 'minLon,minLat,maxLon,maxLat' bounding box query parameter.
    Returns (min_lon, min_lat, max_lon, max_lat) tuple or None.
    Raises ValidationError if format is invalid.
    """
    if not bbox_str:
        return None

    parts = bbox_str.strip().split(",")
    if len(parts) != 4:
        raise ValidationError(
            {"bbox": "Invalid bbox format. Expected 'minLon,minLat,maxLon,maxLat' (e.g. '106.65,10.72,106.75,10.82')."}
        )

    try:
        min_lon = float(parts[0])
        min_lat = float(parts[1])
        max_lon = float(parts[2])
        max_lat = float(parts[3])
    except ValueError:
        raise ValidationError({"bbox": "Bounding box coordinates must be floating point numbers."})

    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
        raise ValidationError({"bbox": "Longitude coordinates must be between -180.0 and 180.0."})
    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise ValidationError({"bbox": "Latitude coordinates must be between -90.0 and 90.0."})
    if min_lon > max_lon or min_lat > max_lat:
        raise ValidationError({"bbox": "minLon/minLat must be strictly less than or equal to maxLon/maxLat."})

    return (min_lon, min_lat, max_lon, max_lat)


def parse_date_param(date_str: Optional[str], param_name: str = "date") -> Optional[date]:
    """
    Parses YYYY-MM-DD date string.
    """
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({param_name: f"Invalid date format for '{param_name}'. Expected 'YYYY-MM-DD'."})
