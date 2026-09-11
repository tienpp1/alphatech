"""Public map serialization regressions; no external geocoder/routing mocks imply live success."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.template.loader import render_to_string

from apps.public_web.views import public_branches_view


class PublicBranchFinderTests(SimpleTestCase):
    def branch(self, **kwargs):
        values = dict(pk=1, name="Cửa hàng </script>", address="Địa chỉ", phone="0123456789",
                      latitude=Decimal("10.7725"), longitude=Decimal("106.6980"), location=None)
        values.update(kwargs)
        return SimpleNamespace(**values)

    def context_for(self, branches):
        with patch("apps.public_web.views.Branch.objects.filter") as query, patch("apps.public_web.views.render") as render:
            query.return_value.order_by.return_value = branches
            public_branches_view(RequestFactory().get("/chi-nhanh/"))
            query.assert_called_once_with(is_active=True, workspace__workspace_type="RETAIL")
            return render.call_args.args[2]

    def test_only_public_fields_and_numeric_coordinates(self):
        data = self.context_for([self.branch()])["map_branches"][0]
        self.assertEqual(set(data), {"id", "name", "address", "phone", "lat", "lng"})
        self.assertEqual(data["lat"], 10.7725)
        self.assertEqual(data["lng"], 106.698)

    def test_zero_missing_invalid_and_gis_fallback(self):
        branches = [self.branch(latitude=0, longitude=0), self.branch(latitude=None),
                    self.branch(latitude=91),
                    self.branch(latitude=None, longitude=None, location=SimpleNamespace(y=10, x=106))]
        data = self.context_for(branches)["map_branches"]
        self.assertEqual((data[0]["lat"], data[0]["lng"]), (0, 0))
        self.assertIsNone(data[1]["lat"])
        self.assertIsNone(data[2]["lat"])
        self.assertEqual((data[3]["lat"], data[3]["lng"]), (10, 106))

    def test_json_escapes_markup_and_controls_have_labels(self):
        context = self.context_for([self.branch()])
        html = render_to_string("public/branches.html", context)
        self.assertIn(r"\u003C/script\u003E", html)
        self.assertNotIn("Cửa hàng </script>", html)
        for control in ("bf-address", "bf-radius", "bf-radius-mode", "bf-locate", "bf-nearest"):
            self.assertIn(f'id="{control}"', html)
        self.assertIn('min="1" max="10"', html)
        self.assertIn('aria-live="polite"', html)
