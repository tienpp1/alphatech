"""Status pages are retired; the machine probe remains independent of the UI."""
from django.test import SimpleTestCase
from django.template.loader import render_to_string
from django.urls import resolve, Resolver404


class RetiredStatusSurfaceTests(SimpleTestCase):
    def test_status_and_legacy_health_routes_are_not_registered(self):
        for path in ('/status/', '/noibo/status/', '/health/'):
            with self.subTest(path=path), self.assertRaises(Resolver404):
                resolve(path)

    def test_dashboard_does_not_render_infrastructure_panel_or_status_links(self):
        html = render_to_string('dashboard/main.html', {})
        for value in ('Hạ tầng Kỹ thuật', 'JSON Health API', 'href="/health/"', 'href="/noibo/status/"'):
            self.assertNotIn(value, html)

    def test_machine_probe_remains_registered(self):
        self.assertEqual(resolve('/api/health/').url_name, 'api_health_check')
