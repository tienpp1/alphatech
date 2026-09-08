"""
tests.test_gis_retail - Retail Spatial Layers, Branch Revenue GIS Analytics & Customer Density Tests.
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.retail.models import Branch, Customer, CustomerSegment, Order, OrderStatus


class RetailGISAnalyticsTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Retail GIS Store",
            code="retail-gis-store",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.user = User.objects.create_user(
            username="retail_manager",
            email="manager@retailgis.com",
            password="Password123!",
            is_superuser=True,
        )

        # Branches
        self.branch_d1 = Branch.objects.create(
            workspace=self.workspace,
            code="BR-D1",
            name="Flagship D1",
            region="District 1",
            location=Point(106.7032, 10.7745, srid=4326),
        )
        self.branch_d7 = Branch.objects.create(
            workspace=self.workspace,
            code="BR-D7",
            name="Phu My Hung D7",
            region="District 7",
            location=Point(106.7196, 10.7288, srid=4326),
        )

        # Customers
        self.cust_vip = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-001",
            name="VIP Nguyen",
            customer_segment=CustomerSegment.VIP,
            location=Point(106.7000, 10.7700, srid=4326),
        )
        self.cust_std = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-002",
            name="Standard Tran",
            customer_segment=CustomerSegment.STANDARD,
            location=Point(106.7100, 10.7300, srid=4326),
        )

        # Orders to generate revenue
        now_date = timezone.now().date()
        now_time = timezone.now()
        Order.objects.create(
            workspace=self.workspace,
            order_number="ORD-D1-01",
            customer=self.cust_vip,
            branch=self.branch_d1,
            order_date=now_date,
            order_timestamp=now_time,
            total_amount=Decimal("1500000.00"),
            status=OrderStatus.COMPLETED,
        )
        Order.objects.create(
            workspace=self.workspace,
            order_number="ORD-D7-01",
            customer=self.cust_std,
            branch=self.branch_d7,
            order_date=now_date - timedelta(days=5),
            order_timestamp=now_time - timedelta(days=5),
            total_amount=Decimal("500000.00"),
            status=OrderStatus.COMPLETED,
        )
        # Cancelled order (must not count towards revenue)
        Order.objects.create(
            workspace=self.workspace,
            order_number="ORD-D1-CANCEL",
            customer=self.cust_vip,
            branch=self.branch_d1,
            order_date=now_date,
            order_timestamp=now_time,
            total_amount=Decimal("999999.00"),
            status=OrderStatus.CANCELLED,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retail_branches_geojson_api(self):
        """Verifies GET /api/v1/gis/retail/branches/ returns GeoJSON with sales KPIs."""
        url = "/api/v1/gis/retail/branches/"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]

        self.assertEqual(data["type"], "FeatureCollection")
        self.assertEqual(len(data["features"]), 2)
        self.assertEqual(data["metadata"]["total_spatial_revenue"], 2000000.0)
        self.assertEqual(data["metadata"]["total_orders"], 2)

        # Inspect D1 feature
        feat_d1 = next(f for f in data["features"] if f["properties"]["code"] == "BR-D1")
        self.assertEqual(feat_d1["properties"]["revenue"], 1500000.0)
        self.assertEqual(feat_d1["properties"]["order_count"], 1)

    def test_retail_customers_geojson_api(self):
        """Verifies GET /api/v1/gis/retail/customers/ with segment filtering."""
        url = "/api/v1/gis/retail/customers/?segment=VIP"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]

        self.assertEqual(len(data["features"]), 1)
        self.assertEqual(data["features"][0]["properties"]["code"], "CUST-001")
        self.assertEqual(data["features"][0]["properties"]["customer_segment"], "VIP")

    def test_retail_spatial_revenue_analytics_api(self):
        """Verifies GET /api/v1/gis/retail/revenue/ spatial rankings and revenue share."""
        url = "/api/v1/gis/retail/revenue/"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]

        self.assertEqual(data["total_revenue"], 2000000.0)
        self.assertEqual(data["branch_count"], 2)

        rankings = data["branch_rankings"]
        # Rank 1: D1 with 75.0% revenue share
        self.assertEqual(rankings[0]["code"], "BR-D1")
        self.assertEqual(rankings[0]["revenue"], 1500000.0)
        self.assertEqual(rankings[0]["revenue_share_pct"], 75.0)

        # Rank 2: D7 with 25.0% revenue share
        self.assertEqual(rankings[1]["code"], "BR-D7")
        self.assertEqual(rankings[1]["revenue"], 500000.0)
        self.assertEqual(rankings[1]["revenue_share_pct"], 25.0)

    def test_retail_gis_ui_view(self):
        """Verifies /retail/gis/ renders 200 OK."""
        self.client.force_login(self.user)
        # Set active workspace in session
        session = self.client.session
        session["active_workspace_id"] = str(self.workspace.id)
        session.save()

        resp = self.client.get("/retail/gis/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertContains(resp, "Retail Spatial Business Analytics")
        self.assertContains(resp, "retail-map")
