"""
tests.test_gis_spatial - Core PostGIS Spatial Queries, Geodesic Distances & GeoJSON Serialization Tests.
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.gis.geos import Point

from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import Branch, Customer, CustomerSegment
from apps.gis.services import (
    find_objects_within_radius,
    calculate_distances,
    filter_by_bounding_box,
    serialize_to_geojson,
    build_coverage_circles,
)


class PostGISSpatialServicesTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Spatial Test Retail",
            code="spatial-test-retail",
            workspace_type=WorkspaceType.RETAIL,
        )

        # Create branches at known coordinates in Ho Chi Minh City
        # Landmark 1: District 1 (Ben Nghe) - [106.7032, 10.7745]
        self.branch_d1 = Branch.objects.create(
            workspace=self.workspace,
            code="BR-D1",
            name="D1 Flagship Store",
            address="68 Nguyen Hue, D1",
            region="District 1",
            location=Point(106.7032, 10.7745, srid=4326),
        )

        # Landmark 2: Binh Thanh (Pearl Plaza) - ~3.3 km from D1 - [106.7185, 10.7997]
        self.branch_bt = Branch.objects.create(
            workspace=self.workspace,
            code="BR-BT",
            name="Binh Thanh Outlet",
            address="561A Dien Bien Phu",
            region="Binh Thanh",
            location=Point(106.7185, 10.7997, srid=4326),
        )

        # Landmark 3: District 7 (Phu My Hung) - ~5.3 km from D1 - [106.7196, 10.7288]
        self.branch_d7 = Branch.objects.create(
            workspace=self.workspace,
            code="BR-D7",
            name="D7 South Outlet",
            address="101 Ton Dat Tien",
            region="District 7",
            location=Point(106.7196, 10.7288, srid=4326),
        )

    def test_pointfield_srid_and_storage(self):
        """Verifies PointField persists coordinates correctly with SRID 4326."""
        self.assertEqual(self.branch_d1.location.srid, 4326)
        self.assertAlmostEqual(self.branch_d1.location.x, 106.7032, places=4)
        self.assertAlmostEqual(self.branch_d1.location.y, 10.7745, places=4)

    def test_find_objects_within_radius_st_dwithin(self):
        """Verifies find_objects_within_radius using PostGIS ST_DWithin."""
        origin = Point(106.7032, 10.7745, srid=4326)  # At Branch D1

        # Within 4.0 km radius: should find D1 and BT (~3.3km), but NOT D7 (~5.3km)
        qs_4km = find_objects_within_radius(
            queryset=Branch.objects.filter(workspace=self.workspace),
            point=origin,
            radius_km=4.0,
            location_field="location",
        )
        codes_4km = set(qs_4km.values_list("code", flat=True))
        self.assertIn("BR-D1", codes_4km)
        self.assertIn("BR-BT", codes_4km)
        self.assertNotIn("BR-D7", codes_4km)

        # Within 10.0 km radius: should find all 3 branches
        qs_10km = find_objects_within_radius(
            queryset=Branch.objects.filter(workspace=self.workspace),
            point=origin,
            radius_km=10.0,
            location_field="location",
        )
        self.assertEqual(qs_10km.count(), 3)

        # Within 0.5 km radius: should find only D1 itself
        qs_500m = find_objects_within_radius(
            queryset=Branch.objects.filter(workspace=self.workspace),
            point=origin,
            radius_km=0.5,
            location_field="location",
        )
        self.assertEqual(qs_500m.count(), 1)
        self.assertEqual(qs_500m.first().code, "BR-D1")

    def test_calculate_distances_st_distance(self):
        """Verifies spheroidal distance calculation and ordering (ST_Distance)."""
        origin = Point(106.7032, 10.7745, srid=4326)

        ordered_qs = calculate_distances(
            queryset=Branch.objects.filter(workspace=self.workspace),
            origin_point=origin,
            location_field="location",
            order_by_distance=True,
        )

        results = list(ordered_qs)
        self.assertEqual(len(results), 3)
        # Closest is D1 (distance 0)
        self.assertEqual(results[0].code, "BR-D1")
        self.assertAlmostEqual(results[0].distance.m, 0.0, delta=1.0)

        # Second closest is Binh Thanh (~3.3 km = ~3300m)
        self.assertEqual(results[1].code, "BR-BT")
        self.assertTrue(3000 <= results[1].distance.m <= 3800)

        # Furthest is District 7 (~5.3 km = ~5300m)
        self.assertEqual(results[2].code, "BR-D7")
        self.assertTrue(5000 <= results[2].distance.m <= 5800)

    def test_filter_by_bounding_box(self):
        """Verifies polygon bounding box filtering (ST_Within)."""
        # Bounding box covering District 1 and Binh Thanh, excluding District 7
        # minLon: 106.69, minLat: 10.76, maxLon: 106.73, maxLat: 10.82
        bbox_qs = filter_by_bounding_box(
            queryset=Branch.objects.filter(workspace=self.workspace),
            min_lon=106.69,
            min_lat=10.76,
            max_lon=106.73,
            max_lat=10.82,
            location_field="location",
        )
        codes = set(bbox_qs.values_list("code", flat=True))
        self.assertIn("BR-D1", codes)
        self.assertIn("BR-BT", codes)
        self.assertNotIn("BR-D7", codes)

    def test_serialize_to_geojson_format(self):
        """Validates standard RFC 7946 GeoJSON schema."""
        features = [
            {
                "id": self.branch_d1.id,
                "coordinates": self.branch_d1.location,
                "properties": {
                    "code": self.branch_d1.code,
                    "name": self.branch_d1.name,
                    "region": self.branch_d1.region,
                },
            }
        ]

        geojson = serialize_to_geojson(features, metadata={"workspace": "test"})
        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertEqual(len(geojson["features"]), 1)
        feat = geojson["features"][0]
        self.assertEqual(feat["type"], "Feature")
        self.assertEqual(feat["geometry"]["type"], "Point")
        self.assertEqual(feat["geometry"]["coordinates"], [106.7032, 10.7745])
        self.assertEqual(feat["properties"]["code"], "BR-D1")
        self.assertEqual(geojson["metadata"]["workspace"], "test")

    def test_build_coverage_circles(self):
        """Validates coverage circles GeoJSON feature generation."""
        centers = [
            {
                "id": 101,
                "coordinates": Point(106.70, 10.77, srid=4326),
                "radius_km": 5.0,
                "properties": {"name": "Technician Minh"},
            }
        ]
        res = build_coverage_circles(centers, radius_km=5.0)
        self.assertEqual(res["type"], "FeatureCollection")
        self.assertEqual(len(res["features"]), 1)
        self.assertEqual(res["features"][0]["properties"]["coverage_radius_meters"], 5000)
        self.assertEqual(res["metadata"]["default_radius_km"], 5.0)
