"""Retired technical/admin UIs must not reappear as routes or navigation."""
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.template.loader import render_to_string
from django.urls import resolve, Resolver404


class RetiredStatusSurfaceTests(SimpleTestCase):
    def test_retired_admin_and_telemetry_paths_are_unregistered_and_return_404(self):
        for path in ('/noibo/telemetry/', '/admin/', '/admin/login/',
                     '/admin/accounts/user/', '/admin/workspaces/workspace/'):
            with self.subTest(path=path):
                with self.assertRaises(Resolver404):
                    resolve(path)
                self.assertEqual(self.client.get(path).status_code, 404)
                self.assertEqual(self.client.post(path, {}).status_code, 404)

    def test_internal_templates_have_no_retired_links_even_for_superusers(self):
        request = SimpleNamespace(user=SimpleNamespace(
            is_authenticated=True, is_staff=True, is_superuser=True, username='admin'))
        for template in ('dashboard/main.html', 'retail/no_workspace.html'):
            with self.subTest(template=template):
                html = render_to_string(template, {'request': request})
                for value in ('href="/admin/', 'href="/noibo/telemetry/',
                              'Giám sát AI & GIS', 'Django Admin'):
                    self.assertNotIn(value, html)
                self.assertIn('href="/noibo/"', html)

    def test_command_center_is_independent_and_remains_registered(self):
        self.assertEqual(resolve('/noibo/ai-command-center/').url_name,
                         'noibo_ai_command_center')

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
