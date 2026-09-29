"""Independent reference cases, not a claim of universal GIS accuracy.

Wellington/Salamanca WGS84: GeographicLib's published inverse example:
https://geographiclib.sourceforge.io/html/python/examples.html
Equatorial arcs are a * delta_longitude_rad, a=6378137m (WGS84).
"""
import math
from django.test import TestCase
from django.contrib.gis.geos import Point
from apps.workspaces.models import Workspace
from apps.retail.models import Branch
from apps.gis.services import calculate_distances, find_objects_within_radius


class GISReferenceDistanceTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code="geo-reference", name="Reference", workspace_type="RETAIL")

    def measure(self, origin, destination):
        branch = Branch.objects.create(workspace=self.ws, code="REF", name="Reference", location=Point(*destination, srid=4326))
        point = Point(*origin, srid=4326)
        qs = Branch.objects.filter(pk=branch.pk, workspace=self.ws)
        return calculate_distances(qs, point).get().distance.m, qs, point

    def test_published_near_antipodal_wgs84_reference(self):
        measured, _, _ = self.measure((174.81, -41.32), (-5.50, 40.96))
        self.assertAlmostEqual(measured, 19959679.26735382, delta=0.01)

    def test_equatorial_arc_and_radius_use_same_spheroid(self):
        expected = 6378137 * math.pi / 180
        measured, qs, point = self.measure((0, 0), (1, 0))
        self.assertAlmostEqual(measured, expected, delta=0.01)
        self.assertFalse(find_objects_within_radius(qs, point, (expected - 1) / 1000).exists())
        self.assertTrue(find_objects_within_radius(qs, point, (expected + 1) / 1000).exists())

    def test_antimeridian_uses_short_equatorial_arc(self):
        measured, _, _ = self.measure((179, 0), (-179, 0))
        self.assertAlmostEqual(measured, 6378137 * 2 * math.pi / 180, delta=0.01)
