"""Production startup and public probes must not mutate business state."""
import importlib
from unittest.mock import MagicMock, patch

from django.test import TestCase


class DeploymentBoundaryTests(TestCase):
    def test_wsgi_import_never_runs_management_commands(self):
        with patch("django.core.management.call_command") as command, patch(
            "django.core.wsgi.get_wsgi_application", return_value=object()
        ), patch.dict("os.environ", {"RENDER": "true"}):
            importlib.reload(importlib.import_module("config.wsgi"))
        command.assert_not_called()

    def test_public_health_does_not_query_business_models(self):
        from config.views import get_health_status
        cursor = MagicMock()
        cursor.__enter__.return_value.fetchone.return_value = ("available",)
        with patch("config.views.connection.cursor", return_value=cursor), patch(
            "apps.workspaces.models.Workspace.objects.values"
        ) as workspaces, patch("apps.retail.models.Product.objects.count") as products:
            data = get_health_status()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["metrics"], {})
        workspaces.assert_not_called()
        products.assert_not_called()
