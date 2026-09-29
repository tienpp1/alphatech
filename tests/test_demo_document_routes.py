"""Documentation route smoke checks: resolution only, not browser acceptance."""
import re
from pathlib import Path
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import resolve


class DemoDocumentRouteTests(SimpleTestCase):
    def test_live_demo_links_resolve(self):
        guide = (Path(settings.BASE_DIR) / "docs/HOI_DONG_DEMO_GUIDE.md").read_text(encoding="utf-8")
        paths = set(re.findall(r"http://127\.0\.0\.1:8000([^`\s)]+)", guide))
        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            with self.subTest(path=path):
                self.assertIsNotNone(resolve(path).func)

    def test_canonical_internal_routes_use_expected_views(self):
        expected = {
            "/noibo/services/": "dashboard_view",
            "/noibo/services/requests/": "requests_view",
            "/noibo/services/gis/": "service_gis_view",
            "/noibo/retail/gis/": "retail_gis_view",
            "/noibo/ai/": "ai_assistant_ui_view",
            "/noibo/integration/import/": "import_wizard_view",
        }
        for path, view in expected.items():
            with self.subTest(path=path):
                self.assertEqual(resolve(path).func.__name__, view)
