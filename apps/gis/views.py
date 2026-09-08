"""
REST API Views for Spatial GIS Layers & Business Proximity Analytics.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from apps.workspaces.permissions import IsWorkspaceMember, require_permission
from apps.service_ops.models import ServiceRequest
from apps.gis.selectors import (
    get_retail_branches_geojson,
    get_retail_customers_geojson,
    get_retail_spatial_revenue_analytics,
    get_service_tickets_geojson,
    get_service_technicians_geojson,
    get_nearby_technicians_for_ticket,
    get_service_coverage_geojson,
)
from apps.gis.filters import parse_bbox_param, parse_date_param


def _resolve_request_workspace(request):
    """Safely retrieves the validated active workspace from request context."""
    ws = getattr(request, "active_workspace", None)
    if ws is None and hasattr(request, "_request"):
        ws = getattr(request._request, "active_workspace", None)
    return ws


class RetailBranchesGeoJSONAPIView(APIView):
    """
    GET /api/v1/gis/retail/branches/
    Returns GeoJSON FeatureCollection of retail branches with sales and order KPIs.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("gis.view_spatial_layers")]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_date_param(request.query_params.get("start_date"), "start_date")
        end_date = parse_date_param(request.query_params.get("end_date"), "end_date")

        geojson_data = get_retail_branches_geojson(
            workspace=workspace,
            start_date=start_date,
            end_date=end_date,
        )
        return Response({"status": "success", "data": geojson_data}, status=status.HTTP_200_OK)


class RetailCustomersGeoJSONAPIView(APIView):
    """
    GET /api/v1/gis/retail/customers/
    Returns GeoJSON FeatureCollection of retail customer locations with PII protection.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("gis.view_spatial_layers")]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        segment = request.query_params.get("segment")
        bbox = parse_bbox_param(request.query_params.get("bbox"))

        # Check PII permission
        can_view_pii = False
        if request.user.is_superuser or request.user.is_staff:
            can_view_pii = True
        else:
            membership = getattr(request, "active_membership", None) or (
                getattr(request._request, "active_membership", None) if hasattr(request, "_request") else None
            )
            if membership and membership.role:
                if membership.role.permissions.filter(
                    codename__in=["gis.view_customer_locations", "retail.manage_customer"]
                ).exists():
                    can_view_pii = True

        geojson_data = get_retail_customers_geojson(
            workspace=workspace,
            segment=segment,
            bbox=bbox,
            can_view_pii=can_view_pii,
        )
        return Response({"status": "success", "data": geojson_data}, status=status.HTTP_200_OK)


class RetailSpatialRevenueAPIView(APIView):
    """
    GET /api/v1/gis/retail/revenue/
    Returns spatial revenue aggregations, rankings, and share percentages by branch.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("gis.view_spatial_layers")]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_date_param(request.query_params.get("start_date"), "start_date")
        end_date = parse_date_param(request.query_params.get("end_date"), "end_date")

        analytics_data = get_retail_spatial_revenue_analytics(
            workspace=workspace,
            start_date=start_date,
            end_date=end_date,
        )
        return Response({"status": "success", "data": analytics_data}, status=status.HTTP_200_OK)


class ServiceTicketsGeoJSONAPIView(APIView):
    """
    GET /api/v1/gis/service/tickets/
    Returns GeoJSON FeatureCollection of IT service incident tickets.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("gis.view_spatial_layers")]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        status_filter = request.query_params.get("status")
        priority_filter = request.query_params.get("priority")
        category_filter = request.query_params.get("category")
        bbox = parse_bbox_param(request.query_params.get("bbox"))

        geojson_data = get_service_tickets_geojson(
            workspace=workspace,
            status=status_filter,
            priority=priority_filter,
            category=category_filter,
            bbox=bbox,
        )
        return Response({"status": "success", "data": geojson_data}, status=status.HTTP_200_OK)


class ServiceTechniciansGeoJSONAPIView(APIView):
    """
    GET /api/v1/gis/service/technicians/
    Returns GeoJSON FeatureCollection of field technicians with skills and hourly rates.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("gis.view_spatial_layers")]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        available_only = request.query_params.get("available_only", "false").lower() in ("true", "1", "t")
        skill = request.query_params.get("skill")
        bbox = parse_bbox_param(request.query_params.get("bbox"))

        geojson_data = get_service_technicians_geojson(
            workspace=workspace,
            available_only=available_only,
            skill=skill,
            bbox=bbox,
        )
        return Response({"status": "success", "data": geojson_data}, status=status.HTTP_200_OK)


class NearbyTechniciansAPIView(APIView):
    """
    GET /api/v1/gis/service/nearby-technicians/
    Spatial proximity query for a service ticket: finds technicians within radius_km,
    calculates exact geodesic distance (km), and orders candidate technicians.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("gis.view_spatial_layers")]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        request_id = request.query_params.get("request_id")
        if not request_id:
            return Response(
                {"status": "error", "message": "Missing required 'request_id' query parameter."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ticket = get_object_or_404(
            ServiceRequest.objects.for_workspace(workspace),
            id=request_id,
        )

        try:
            radius_km = float(request.query_params.get("radius_km", 5.0))
            if radius_km <= 0:
                raise ValueError()
        except ValueError:
            return Response(
                {"status": "error", "message": "'radius_km' must be a positive float number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        available_only = request.query_params.get("available_only", "true").lower() in ("true", "1", "t")
        required_skill = request.query_params.get("required_skill")

        candidates_data = get_nearby_technicians_for_ticket(
            ticket=ticket,
            radius_km=radius_km,
            available_only=available_only,
            required_skill=required_skill,
        )

        return Response({"status": "success", "data": candidates_data}, status=status.HTTP_200_OK)


class ServiceCoverageGeoJSONAPIView(APIView):
    """
    GET /api/v1/gis/service/coverage/
    Returns GeoJSON FeatureCollection of technician service coverage envelopes.
    """

    permission_classes = [IsAuthenticated, IsWorkspaceMember, require_permission("gis.view_spatial_layers")]

    def get(self, request):
        workspace = _resolve_request_workspace(request)
        if not workspace:
            return Response({"status": "error", "message": "No active workspace."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            radius_km = float(request.query_params.get("radius_km", 5.0))
            if radius_km <= 0:
                raise ValueError()
        except ValueError:
            radius_km = 5.0

        geojson_data = get_service_coverage_geojson(
            workspace=workspace,
            radius_km=radius_km,
        )
        return Response({"status": "success", "data": geojson_data}, status=status.HTTP_200_OK)
