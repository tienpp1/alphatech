"""
URL routing configuration for apps.gis (REST APIs & Web UI Map Views).
"""

from django.urls import path
from apps.gis.views import (
    RetailBranchesGeoJSONAPIView,
    RetailCustomersGeoJSONAPIView,
    RetailSpatialRevenueAPIView,
    ServiceTicketsGeoJSONAPIView,
    ServiceTechniciansGeoJSONAPIView,
    NearbyTechniciansAPIView,
    ServiceCoverageGeoJSONAPIView,
)
from apps.gis.ui_views import retail_gis_view, service_gis_view

app_name = "gis"

urlpatterns = [
    # Web UI Pages
    path("retail/gis/", retail_gis_view, name="retail-gis-ui"),
    path("services/gis/", service_gis_view, name="service-gis-ui"),

    # REST APIs - Retail Spatial Layers
    path("api/v1/gis/retail/branches/", RetailBranchesGeoJSONAPIView.as_view(), name="api-retail-branches"),
    path("api/v1/gis/retail/customers/", RetailCustomersGeoJSONAPIView.as_view(), name="api-retail-customers"),
    path("api/v1/gis/retail/revenue/", RetailSpatialRevenueAPIView.as_view(), name="api-retail-revenue"),

    # REST APIs - Service Operations Spatial Layers
    path("api/v1/gis/service/tickets/", ServiceTicketsGeoJSONAPIView.as_view(), name="api-service-tickets"),
    path("api/v1/gis/service/technicians/", ServiceTechniciansGeoJSONAPIView.as_view(), name="api-service-technicians"),
    path("api/v1/gis/service/nearby-technicians/", NearbyTechniciansAPIView.as_view(), name="api-service-nearby-technicians"),
    path("api/v1/gis/service/coverage/", ServiceCoverageGeoJSONAPIView.as_view(), name="api-service-coverage"),
]
