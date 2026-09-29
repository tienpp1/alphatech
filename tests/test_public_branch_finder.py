"""Public map serialization regressions; no external geocoder/routing mocks imply live success."""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase
from django.template.loader import render_to_string
from pathlib import Path

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

    def test_route_copy_states_provider_scope_without_absolute_claim(self):
        context = self.context_for([self.branch()])
        html = render_to_string("public/branches.html", context)
        self.assertIn("không phải khoảng cách đường chim bay", html)
        self.assertIn("Bán kính tính theo đường chim bay", html)
        self.assertIn("tuyến ô tô", html)
        self.assertIn("OSRM", html)
        self.assertIn("Dịch vụ công cộng có giới hạn", html)
        js = Path("static/public/js/branch-finder.js").read_text(encoding="utf-8")
        self.assertIn("theo tuyến ô tô được cung cấp", js)
        self.assertIn("chưa so sánh được tất cả", js)
        self.assertIn("Không bảo đảm ngắn nhất tuyệt đối", html)

    def test_gps_error_codes_and_accuracy_tiers(self):
        js = Path("static/public/js/branch-finder.js").read_text(encoding="utf-8")
        # Assert Vietnamese error messages for GPS codes 1 (permission denied), 2 (unavailable), 3 (timeout)
        self.assertIn("Bạn chưa cho phép truy cập vị trí", js)
        self.assertIn("Thiết bị chưa xác định được vị trí", js)
        self.assertIn("Lấy vị trí quá thời gian chờ", js)
        self.assertIn("Không lấy được vị trí", js)

        # Assert accuracy thresholds in JS logic
        self.assertIn("Thiết bị chưa cung cấp sai số", js)
        self.assertIn("Vị trí chỉ gần đúng (sai số khoảng", js)
        self.assertIn("Sai số thiết bị báo khoảng", js)

        # Test pure JS functions via Node if available
        import shutil, subprocess, json
        node_bin = shutil.which("node")
        if node_bin:
            script = (
                "const {accuracyMessage, distanceKm, inRadius, validPoint} = require('./static/public/js/branch-finder.js');\n"
                "console.log(JSON.stringify({\n"
                "  normal: accuracyMessage(45),\n"
                "  degraded: accuracyMessage(250),\n"
                "  missing: accuracyMessage(-1),\n"
                "  dist: distanceKm({lat:10.7,lng:106.7},{lat:10.8,lng:106.8})\n"
                "}));\n"
            )
            res = subprocess.run([node_bin, "-e", script], capture_output=True, text=True, encoding="utf-8", check=True)
            data = json.loads(res.stdout.strip())
            self.assertIn("Sai số thiết bị báo khoảng 45 m", data["normal"])
            self.assertIn("Vị trí chỉ gần đúng (sai số khoảng 250 m)", data["degraded"])
            self.assertIn("Thiết bị chưa cung cấp sai số", data["missing"])
            self.assertGreater(data["dist"], 15.0)
            self.assertLess(data["dist"], 16.0)
