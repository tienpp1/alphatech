"""
Spatial Services & PostGIS Computation Utilities.
Encapsulates all GeoDjango geometric operations, spatial lookups, distance measurements,
and GeoJSON format serialization.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional, Sequence
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import D
from django.db.models import QuerySet


def find_objects_within_radius(
    queryset: QuerySet,
    point: Point,
    radius_km: float,
    location_field: str = "location",
) -> QuerySet:
    """
    Filters a GeoDjango queryset for entities located within radius_km from an origin point.
    Calculates spheroidal geodesic distance on SRID 4326 geometries.
    """
    if not isinstance(point, Point):
        raise ValueError("Origin point must be a valid GeoDjango Point instance.")

    if radius_km <= 0:
        raise ValueError("Radius must be greater than zero.")

    return queryset.annotate(
        _spatial_dist=Distance(location_field, point)
    ).filter(_spatial_dist__lte=D(km=radius_km))


def calculate_distances(
    queryset: QuerySet,
    origin_point: Point,
    location_field: str = "location",
    order_by_distance: bool = True,
) -> QuerySet:
    """
    Annotates queryset items with spheroidal geodesic distance (ST_Distance) to origin_point.
    Returns annotated QuerySet with 'distance' attribute (Distance object).
    """
    if not isinstance(origin_point, Point):
        raise ValueError("Origin point must be a valid GeoDjango Point instance.")

    annotated_qs = queryset.annotate(
        distance=Distance(location_field, origin_point)
    )

    if order_by_distance:
        annotated_qs = annotated_qs.order_by("distance")

    return annotated_qs


def filter_by_bounding_box(
    queryset: QuerySet,
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float,
    location_field: str = "location",
) -> QuerySet:
    """
    Filters queryset for entities contained within a 2D bounding box (ST_MakeEnvelope / ST_Within).
    """
    # Validation
    if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
        raise ValueError("Longitude must be between -180.0 and 180.0.")
    if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
        raise ValueError("Latitude must be between -90.0 and 90.0.")
    if min_lon > max_lon or min_lat > max_lat:
        raise ValueError("Invalid bounding box: min coordinates must be <= max coordinates.")

    bbox_poly = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))
    bbox_poly.srid = 4326
    filter_kwargs = {f"{location_field}__within": bbox_poly}
    return queryset.filter(**filter_kwargs)


def serialize_to_geojson(
    features: Sequence[Dict[str, Any]],
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Formats a sequence of feature dictionaries into standard RFC 7946 GeoJSON FeatureCollection.
    Each feature dict in `features` should have:
      - 'id': entity identifier (optional)
      - 'coordinates': (longitude, latitude) tuple or Point instance
      - 'properties': dict of non-spatial properties
    """
    geojson_features = []

    for item in features:
        coords = item.get("coordinates")
        if coords is None:
            continue

        if isinstance(coords, Point):
            coord_list = [round(float(coords.x), 6), round(float(coords.y), 6)]
        elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
            coord_list = [round(float(coords[0]), 6), round(float(coords[1]), 6)]
        else:
            continue

        feature_dict = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": coord_list,
            },
            "properties": item.get("properties", {}),
        }

        if "id" in item:
            feature_dict["id"] = item["id"]

        geojson_features.append(feature_dict)

    collection = {
        "type": "FeatureCollection",
        "features": geojson_features,
    }

    if metadata:
        collection["metadata"] = metadata

    return collection


def build_coverage_circles(
    centers: Sequence[Dict[str, Any]],
    radius_km: float = 5.0,
) -> Dict[str, Any]:
    """
    Builds a GeoJSON FeatureCollection of technician service coverage points & radius envelopes.
    Each center provides: id, name, coordinates (lon, lat), status, workload, and coverage_radius_km.
    """
    features = []

    for item in centers:
        coords = item.get("coordinates")
        if coords is None:
            continue

        if isinstance(coords, Point):
            coord_list = [round(float(coords.x), 6), round(float(coords.y), 6)]
        elif isinstance(coords, (list, tuple)) and len(coords) >= 2:
            coord_list = [round(float(coords[0]), 6), round(float(coords[1]), 6)]
        else:
            continue

        item_radius = item.get("radius_km", radius_km)

        # Center point feature
        features.append({
            "type": "Feature",
            "id": item.get("id"),
            "geometry": {
                "type": "Point",
                "coordinates": coord_list,
            },
            "properties": {
                **item.get("properties", {}),
                "is_coverage_center": True,
                "coverage_radius_km": item_radius,
                "coverage_radius_meters": item_radius * 1000,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "default_radius_km": radius_km,
            "total_coverage_nodes": len(features),
        },
    }


def find_nearby_technicians(
    workspace: Workspace,
    service_request_id: Optional[int] = None,
    origin_point: Optional[Point] = None,
    radius_km: float = 25.0,
) -> Dict[str, Any]:
    """
    Finds field technicians within radius_km of a service request location or origin point.
    Annotates distance in kilometers and current active task counts.
    """
    from apps.service_ops.models import ServiceRequest, Employee, Task, TaskStatus
    from django.db.models import Count, Q

    target_point = origin_point

    if not target_point and service_request_id:
        sr = ServiceRequest.objects.for_workspace(workspace).filter(id=service_request_id).first()
        if sr and sr.location:
            target_point = sr.location
        elif sr and sr.latitude is not None and sr.longitude is not None:
            target_point = Point(float(sr.longitude), float(sr.latitude), srid=4326)

    # Fallback to default Hanoi origin if no point available
    if not target_point:
        target_point = Point(105.854444, 21.028500, srid=4326)

    loc_field = "current_location" if hasattr(Employee, "current_location") else "location"
    emp_qs = Employee.objects.for_workspace(workspace).filter(
        **{f"{loc_field}__isnull": False},
        is_active=True,
    )

    nearby_qs = calculate_distances(emp_qs, target_point, location_field=loc_field)
    nearby_qs = nearby_qs.filter(distance__lte=D(km=radius_km)).annotate(
        active_tasks=Count("assigned_tasks", filter=Q(assigned_tasks__status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]))
    )

    candidates = []
    for emp in nearby_qs:
        dist_km = round(float(emp.distance.km), 2) if hasattr(emp, "distance") and emp.distance else 0.0
        candidates.append({
            "id": emp.id,
            "code": emp.code,
            "name": emp.full_name,
            "distance_km": dist_km,
            "active_tasks": getattr(emp, "active_tasks", 0),
            "skills": emp.skills if hasattr(emp, "skills") else [],
            "hourly_labor_rate": float(emp.hourly_labor_rate) if hasattr(emp, "hourly_labor_rate") else 0.0,
        })

    candidates.sort(key=lambda x: (x["distance_km"], x["active_tasks"]))

    return {
        "workspace": workspace.code,
        "service_request_id": service_request_id,
        "origin_coordinates": [float(target_point.x), float(target_point.y)],
        "radius_km": radius_km,
        "candidates_count": len(candidates),
        "candidates": candidates,
    }
