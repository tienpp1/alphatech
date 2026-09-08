from django.test import Client, SimpleTestCase
from django.urls import resolve


class NoiboRouteConvergenceTests(SimpleTestCase):
    canonical_routes = {
        "/noibo/retail/": "retail_dashboard",
        "/noibo/services/": "services_ui_dashboard",
        "/noibo/retail/gis/": "noibo_retail_gis",
        "/noibo/services/gis/": "noibo_service_gis",
        "/noibo/integration/": "noibo_integration_dashboard",
        "/noibo/mapping/": "noibo_mapping_dashboard",
        "/noibo/ai/": "noibo_ai_assistant",
        "/noibo/knowledge/": "noibo_knowledge_base",
        "/noibo/forecasting/": "noibo_forecasting_dashboard",
        "/noibo/recommendations/": "noibo_recommendations_dashboard",
        "/noibo/approvals/": "noibo_approvals_dashboard",
    }

    def test_all_internal_surfaces_resolve_under_noibo(self):
        for path, url_name in self.canonical_routes.items():
            with self.subTest(path=path):
                self.assertEqual(resolve(path).url_name, url_name)

    def test_canonical_internal_surfaces_require_authentication(self):
        client = Client()
        for path in self.canonical_routes:
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("login", response.url)

    def test_legacy_routes_remain_resolvable_for_compatibility(self):
        for path in ("/retail/", "/services/", "/integration/", "/mapping/", "/ai/", "/knowledge/", "/forecasting/", "/recommendations/", "/approvals/"):
            with self.subTest(path=path):
                self.assertIsNotNone(resolve(path).func)
