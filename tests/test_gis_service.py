"""
tests.test_gis_service - Service Incident Tickets GIS, Technician Spatial Tracking & Proximity Dispatch Tests.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import Customer, CustomerSegment
from apps.service_ops.models import (
    Service,
    ServiceCategory,
    Employee,
    SLA,
    SLAPriority,
    ServiceRequest,
    ServiceRequestPriority,
    ServiceRequestStatus,
)


class ServiceGISOperationsTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Service GIS Ops",
            code="service-gis-ops",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.user = User.objects.create_user(
            username="service_admin",
            email="admin@servicegis.com",
            password="Password123!",
            is_superuser=True,
        )

        self.sla = SLA.objects.create(
            workspace=self.workspace,
            name="Critical 2h SLA",
            priority=SLAPriority.CRITICAL,
            response_time_hours=2,
            resolution_time_hours=4,
        )

        self.service_db = Service.objects.create(
            workspace=self.workspace,
            code="DB-OPT",
            name="Database Query Optimization",
            category=ServiceCategory.DATABASE_CONSULTING,
            base_fee=Decimal("1200000.00"),
        )

        self.service_net = Service.objects.create(
            workspace=self.workspace,
            code="NET-SETUP",
            name="VLAN & Firewall Setup",
            category=ServiceCategory.INSTALLATION,
            base_fee=Decimal("800000.00"),
        )

        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-SVC-01",
            name="Bitexco Financial Tower",
            customer_segment=CustomerSegment.ENTERPRISE,
            location=Point(106.7044, 10.7716, srid=4326),  # Bitexco D1
        )

        # Technicians at different distances from Bitexco D1 [106.7044, 10.7716]
        # Tech 1: ~1.0 km away (Nguyen Hue / Le Duan)
        self.tech_close = Employee.objects.create(
            workspace=self.workspace,
            code="TECH-001",
            full_name="Minh Near",
            hourly_labor_rate=Decimal("200000.00"),
            skills=["DATABASE", "SERVER"],
            current_location=Point(106.7000, 10.7760, srid=4326),
            is_available=True,
            current_workload_score=20.0,
        )

        # Tech 2: ~3.5 km away (Binh Thanh)
        self.tech_med = Employee.objects.create(
            workspace=self.workspace,
            code="TECH-002",
            full_name="Ha Medium",
            hourly_labor_rate=Decimal("250000.00"),
            skills=["DATABASE", "QUERY_OPTIMIZATION"],
            current_location=Point(106.7185, 10.7997, srid=4326),
            is_available=True,
            current_workload_score=35.0,
        )

        # Tech 3: ~12.0 km away (Thu Duc / Hi-Tech Park)
        self.tech_far = Employee.objects.create(
            workspace=self.workspace,
            code="TECH-003",
            full_name="Bao Far",
            hourly_labor_rate=Decimal("180000.00"),
            skills=["NETWORK"],
            current_location=Point(106.7900, 10.8520, srid=4326),
            is_available=True,
            current_workload_score=10.0,
        )

        # Tech 4: Close (~1.2 km) but Busy (is_available=False)
        self.tech_busy = Employee.objects.create(
            workspace=self.workspace,
            code="TECH-004",
            full_name="Duc Busy",
            hourly_labor_rate=Decimal("150000.00"),
            skills=["DEVICE_REPAIR"],
            current_location=Point(106.7020, 10.7780, srid=4326),
            is_available=False,
            current_workload_score=90.0,
        )

        # Incident Ticket at Bitexco D1
        self.ticket = ServiceRequest.objects.create(
            workspace=self.workspace,
            request_number="SR-20260826-0001",
            customer=self.customer,
            service=self.service_db,
            sla=self.sla,
            assigned_employee=self.tech_close,
            title="Production DB connection pool exhausted",
            description="High latency on checkout",
            location=self.customer.location,
            priority=ServiceRequestPriority.CRITICAL,
            status=ServiceRequestStatus.IN_PROGRESS,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_service_tickets_geojson_api(self):
        """Verifies GET /api/v1/gis/service/tickets/ returns tickets with categories and SLA status."""
        url = "/api/v1/gis/service/tickets/?category=DATABASE_CONSULTING&priority=CRITICAL"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]

        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 1)
        feat = data["features"][0]
        self.assertEqual(feat["properties"]["request_number"], "SR-20260826-0001")
        self.assertEqual(feat["properties"]["category"], "DATABASE_CONSULTING")
        self.assertEqual(feat["properties"]["priority"], "CRITICAL")
        self.assertEqual(feat["properties"]["customer_name"], "Bitexco Financial Tower")

    def test_service_technicians_geojson_api(self):
        """Verifies GET /api/v1/gis/service/technicians/ with available_only filter."""
        url = "/api/v1/gis/service/technicians/?available_only=true"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]

        # Tech 1, Tech 2, Tech 3 are available; Tech 4 is busy
        self.assertEqual(len(data["features"]), 3)
        codes = [f["properties"]["code"] for f in data["features"]]
        self.assertIn("TECH-001", codes)
        self.assertIn("TECH-002", codes)
        self.assertIn("TECH-003", codes)
        self.assertNotIn("TECH-004", codes)

    def test_nearby_technicians_proximity_api(self):
        """
        Verifies GET /api/v1/gis/service/nearby-technicians/?request_id=<id>&radius_km=5
        Calculates exact PostGIS geodesic distances (ST_Distance) within 5km radius.
        """
        url = f"/api/v1/gis/service/nearby-technicians/?request_id={self.ticket.id}&radius_km=5.0&available_only=true"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]

        self.assertEqual(data["ticket_id"], self.ticket.id)
        self.assertEqual(data["search_radius_km"], 5.0)

        # Within 5km: Tech 1 (~1km) and Tech 2 (~3.5km) are returned.
        # Tech 3 (~12km) is outside radius. Tech 4 is busy (available_only=True).
        self.assertEqual(data["total_candidates"], 2)
        candidates = data["candidates"]

        # Ordered strictly by proximity (closest first)
        self.assertEqual(candidates[0]["code"], "TECH-001")
        self.assertTrue(0.5 <= candidates[0]["distance_km"] <= 1.5)
        self.assertEqual(candidates[0]["hourly_labor_rate"], 200000.0)

        self.assertEqual(candidates[1]["code"], "TECH-002")
        self.assertTrue(3.0 <= candidates[1]["distance_km"] <= 4.2)
        self.assertEqual(candidates[1]["hourly_labor_rate"], 250000.0)

    def test_service_coverage_api(self):
        """Verifies GET /api/v1/gis/service/coverage/ returns coverage envelopes."""
        url = "/api/v1/gis/service/coverage/?radius_km=5.0"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]

        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 4)  # All 4 technicians
        self.assertEqual(data["metadata"]["default_radius_km"], 5.0)

    def test_service_gis_ui_view(self):
        """Verifies /services/gis/ renders 200 OK."""
        self.client.force_login(self.user)
        session = self.client.session
        session["active_workspace_id"] = str(self.workspace.id)
        session.save()

        resp = self.client.get("/services/gis/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertContains(resp, "Service GIS Operations")
        self.assertContains(resp, "service-map")
        self.assertContains(resp, "Proximity Dispatch Inspector")
