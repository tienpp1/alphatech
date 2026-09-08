"""
Spatial Query Selectors & GIS Business Analytics.
Connects spatial PostGIS queries directly to Retail and IT Service business data models.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from datetime import date
from django.db.models import Sum, Count, Avg, F, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D

from apps.retail.models import Branch, Customer, Order, OrderStatus
from apps.service_ops.models import Employee, ServiceRequest, ServiceRequestStatus, ServiceCategory
from apps.gis.services import (
    find_objects_within_radius,
    calculate_distances,
    filter_by_bounding_box,
    serialize_to_geojson,
    build_coverage_circles,
)


def get_retail_branches_geojson(
    workspace,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Returns GeoJSON FeatureCollection of retail branches annotated with realized revenue,
    order counts, and regional metrics.
    """
    branches_qs = Branch.objects.for_workspace(workspace).filter(
        is_active=True,
        location__isnull=False,
    )

    orders_qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
    if start_date:
        orders_qs = orders_qs.filter(order_date__gte=start_date)
    if end_date:
        orders_qs = orders_qs.filter(order_date__lte=end_date)

    features = []
    total_network_revenue = Decimal("0.00")
    total_network_orders = 0

    for branch in branches_qs:
        branch_orders = orders_qs.filter(branch=branch)
        agg = branch_orders.aggregate(
            revenue=Coalesce(
                Sum("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            order_count=Count("id"),
            avg_order_value=Coalesce(
                Avg("total_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        )

        rev_val = agg["revenue"]
        ord_val = agg["order_count"]
        total_network_revenue += rev_val
        total_network_orders += ord_val

        features.append({
            "id": branch.id,
            "coordinates": branch.location,
            "properties": {
                "branch_id": branch.id,
                "code": branch.code,
                "name": branch.name,
                "address": branch.address,
                "region": branch.region,
                "phone": branch.phone,
                "revenue": float(rev_val),
                "formatted_revenue": f"{rev_val:,.0f} VND",
                "order_count": ord_val,
                "average_order_value": float(agg["avg_order_value"]),
                "is_active": branch.is_active,
            },
        })

    metadata = {
        "workspace_id": str(workspace.id),
        "total_branches": len(features),
        "total_spatial_revenue": float(total_network_revenue),
        "total_orders": total_network_orders,
        "date_range": {
            "start_date": str(start_date) if start_date else None,
            "end_date": str(end_date) if end_date else None,
        },
    }

    return serialize_to_geojson(features, metadata=metadata)


def get_retail_customers_geojson(
    workspace,
    segment: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    can_view_pii: bool = False,
) -> Dict[str, Any]:
    """
    Returns GeoJSON FeatureCollection of retail customer locations with privacy masking.
    """
    customers_qs = Customer.objects.for_workspace(workspace).filter(
        is_active=True,
        location__isnull=False,
    )

    if segment:
        customers_qs = customers_qs.filter(customer_segment=segment)

    if bbox:
        customers_qs = filter_by_bounding_box(
            customers_qs,
            min_lon=bbox[0],
            min_lat=bbox[1],
            max_lon=bbox[2],
            max_lat=bbox[3],
            location_field="location",
        )

    features = []
    for cust in customers_qs:
        props = {
            "customer_id": cust.id,
            "code": cust.code,
            "name": cust.name if can_view_pii else f"Customer {cust.code}",
            "customer_segment": cust.customer_segment,
            "address": cust.address if can_view_pii else "Restricted (Address Protected)",
        }

        if can_view_pii:
            props["phone"] = cust.phone
            props["email"] = cust.email

        features.append({
            "id": cust.id,
            "coordinates": cust.location,
            "properties": props,
        })

    metadata = {
        "workspace_id": str(workspace.id),
        "total_customers": len(features),
        "segment_filter": segment,
        "pii_masked": not can_view_pii,
    }

    return serialize_to_geojson(features, metadata=metadata)


def get_retail_spatial_revenue_analytics(
    workspace,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Computes spatial revenue distribution analytics across all physical branches.
    """
    branches_qs = Branch.objects.for_workspace(workspace).filter(
        is_active=True,
        location__isnull=False,
    )

    orders_qs = Order.objects.for_workspace(workspace).exclude(status=OrderStatus.CANCELLED)
    if start_date:
        orders_qs = orders_qs.filter(order_date__gte=start_date)
    if end_date:
        orders_qs = orders_qs.filter(order_date__lte=end_date)

    branch_analytics = []
    total_rev = Decimal("0.00")
    total_orders = 0

    for b in branches_qs:
        agg = orders_qs.filter(branch=b).aggregate(
            rev=Coalesce(Sum("total_amount"), Value(Decimal("0.00")), output_field=DecimalField(max_digits=14, decimal_places=2)),
            cnt=Count("id"),
        )
        r = agg["rev"]
        c = agg["cnt"]
        total_rev += r
        total_orders += c

        branch_analytics.append({
            "branch_id": b.id,
            "code": b.code,
            "name": b.name,
            "region": b.region,
            "coordinates": [float(b.location.x), float(b.location.y)] if b.location else None,
            "revenue": float(r),
            "order_count": c,
        })

    # Add revenue share percentage
    for item in branch_analytics:
        if total_rev > 0:
            item["revenue_share_pct"] = round((Decimal(str(item["revenue"])) / total_rev) * 100, 1)
        else:
            item["revenue_share_pct"] = 0.0

    branch_analytics.sort(key=lambda x: x["revenue"], reverse=True)

    return {
        "workspace_id": str(workspace.id),
        "total_revenue": float(total_rev),
        "total_orders": total_orders,
        "branch_count": len(branch_analytics),
        "branch_rankings": branch_analytics,
    }


def get_service_tickets_geojson(
    workspace,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> Dict[str, Any]:
    """
    Returns GeoJSON FeatureCollection of IT service incident tickets for the active workspace.
    """
    tickets_qs = ServiceRequest.objects.for_workspace(workspace).filter(
        location__isnull=False,
    ).select_related("customer", "service", "sla", "assigned_employee")

    if status:
        tickets_qs = tickets_qs.filter(status=status)
    if priority:
        tickets_qs = tickets_qs.filter(priority=priority)
    if category:
        tickets_qs = tickets_qs.filter(service__category=category)

    if bbox:
        tickets_qs = filter_by_bounding_box(
            tickets_qs,
            min_lon=bbox[0],
            min_lat=bbox[1],
            max_lon=bbox[2],
            max_lat=bbox[3],
            location_field="location",
        )

    now = timezone.now()
    features = []

    for ticket in tickets_qs:
        is_breached = False
        if ticket.status not in [ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED, ServiceRequestStatus.CANCELLED]:
            if ticket.resolution_deadline_at and ticket.resolution_deadline_at < now:
                is_breached = True

        features.append({
            "id": ticket.id,
            "coordinates": ticket.location,
            "properties": {
                "ticket_id": ticket.id,
                "request_number": ticket.request_number,
                "title": ticket.title,
                "category": ticket.service.category,
                "category_display": ticket.service.get_category_display(),
                "priority": ticket.priority,
                "status": ticket.status,
                "status_display": ticket.get_status_display(),
                "customer_name": ticket.customer.name if ticket.customer else "Unknown",
                "customer_address": ticket.customer.address if ticket.customer else "",
                "assigned_employee_name": ticket.assigned_employee.full_name if ticket.assigned_employee else "Unassigned",
                "service_name": ticket.service.name,
                "service_code": ticket.service.code,
                "base_fee": float(ticket.service.base_fee),
                "sla_name": ticket.sla.name if ticket.sla else "None",
                "response_deadline_at": ticket.response_deadline_at.isoformat() if ticket.response_deadline_at else None,
                "resolution_deadline_at": ticket.resolution_deadline_at.isoformat() if ticket.resolution_deadline_at else None,
                "is_breached": is_breached,
                "created_at": ticket.created_at.isoformat(),
            },
        })

    metadata = {
        "workspace_id": str(workspace.id),
        "total_tickets": len(features),
        "filters": {
            "status": status,
            "priority": priority,
            "category": category,
        },
    }

    return serialize_to_geojson(features, metadata=metadata)


def get_service_technicians_geojson(
    workspace,
    available_only: bool = False,
    skill: Optional[str] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
) -> Dict[str, Any]:
    """
    Returns GeoJSON FeatureCollection of field technicians with skills, hourly rates, and workload.
    """
    techs_qs = Employee.objects.for_workspace(workspace).filter(
        is_active=True,
        current_location__isnull=False,
    )

    if available_only:
        techs_qs = techs_qs.filter(is_available=True)

    if bbox:
        techs_qs = filter_by_bounding_box(
            techs_qs,
            min_lon=bbox[0],
            min_lat=bbox[1],
            max_lon=bbox[2],
            max_lat=bbox[3],
            location_field="current_location",
        )

    features = []
    for emp in techs_qs:
        # If skill filter applied, check JSON list
        if skill and skill.upper() not in [s.upper() for s in (emp.skills or [])]:
            continue

        features.append({
            "id": emp.id,
            "coordinates": emp.current_location,
            "properties": {
                "employee_id": emp.id,
                "code": emp.code,
                "full_name": emp.full_name,
                "phone": emp.phone,
                "email": emp.email,
                "skills": emp.skills or [],
                "hourly_labor_rate": float(emp.hourly_labor_rate),
                "formatted_rate": f"{emp.hourly_labor_rate:,.0f} VND/h",
                "current_workload_score": emp.current_workload_score,
                "is_available": emp.is_available,
                "location_updated_at": emp.location_updated_at.isoformat() if emp.location_updated_at else None,
            },
        })

    metadata = {
        "workspace_id": str(workspace.id),
        "total_technicians": len(features),
        "available_only": available_only,
        "skill_filter": skill,
    }

    return serialize_to_geojson(features, metadata=metadata)


def get_nearby_technicians_for_ticket(
    ticket: ServiceRequest,
    radius_km: float = 5.0,
    available_only: bool = True,
    required_skill: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Performs spatial proximity search to find qualified field technicians within radius_km
    from the ticket's incident location, ordered by distance (ST_Distance).
    """
    if not ticket.location:
        return {
            "ticket_id": ticket.id,
            "request_number": ticket.request_number,
            "has_location": False,
            "candidates": [],
            "message": "Service ticket does not have spatial coordinates.",
        }

    # Fetch technicians in the same workspace with known location
    base_qs = Employee.objects.for_workspace(ticket.workspace).filter(
        is_active=True,
        current_location__isnull=False,
    )

    if available_only:
        base_qs = base_qs.filter(is_available=True)

    # 1. PostGIS Geodesic Distance Calculation & Ordering (ST_Distance)
    ordered_qs = calculate_distances(
        queryset=base_qs,
        origin_point=ticket.location,
        location_field="current_location",
        order_by_distance=True,
    )

    # 2. Filter within radius
    radius_qs = ordered_qs.filter(distance__lte=D(km=radius_km))

    candidates = []
    for emp in radius_qs:
        # Check skill if requested
        if required_skill and required_skill.upper() not in [s.upper() for s in (emp.skills or [])]:
            continue

        # Distance attribute attached by GeoDjango Distance() function
        dist_meters = float(emp.distance.m) if hasattr(emp, "distance") else 0.0
        dist_km = round(dist_meters / 1000.0, 2)

        candidates.append({
            "employee_id": emp.id,
            "code": emp.code,
            "full_name": emp.full_name,
            "phone": emp.phone,
            "email": emp.email,
            "skills": emp.skills or [],
            "hourly_labor_rate": float(emp.hourly_labor_rate),
            "formatted_rate": f"{emp.hourly_labor_rate:,.0f} VND/h",
            "current_workload_score": emp.current_workload_score,
            "is_available": emp.is_available,
            "distance_meters": round(dist_meters, 1),
            "distance_km": dist_km,
            "coordinates": [float(emp.current_location.x), float(emp.current_location.y)],
        })

    return {
        "ticket_id": ticket.id,
        "request_number": ticket.request_number,
        "ticket_title": ticket.title,
        "ticket_coordinates": [float(ticket.location.x), float(ticket.location.y)],
        "search_radius_km": radius_km,
        "available_only": available_only,
        "required_skill": required_skill,
        "total_candidates": len(candidates),
        "candidates": candidates,
    }


def get_service_coverage_geojson(
    workspace,
    radius_km: float = 5.0,
) -> Dict[str, Any]:
    """
    Generates GeoJSON coverage representations for all active technicians in workspace.
    """
    techs_qs = Employee.objects.for_workspace(workspace).filter(
        is_active=True,
        current_location__isnull=False,
    )

    nodes = []
    for emp in techs_qs:
        nodes.append({
            "id": emp.id,
            "coordinates": emp.current_location,
            "radius_km": radius_km,
            "properties": {
                "employee_id": emp.id,
                "code": emp.code,
                "full_name": emp.full_name,
                "skills": emp.skills or [],
                "is_available": emp.is_available,
                "workload_score": emp.current_workload_score,
            },
        })

    return build_coverage_circles(nodes, radius_km=radius_km)
