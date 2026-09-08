import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase
from django.test.client import RequestFactory

from config.middleware import RequestCorrelationIdMiddleware, SecurityHeadersMiddleware


class ProductionReadinessTests(SimpleTestCase):
    def test_unknown_migration_state_blocks_readiness(self):
        with patch("apps.accounts.management.commands.platform_readiness.connection") as connection, patch("apps.accounts.management.commands.platform_readiness.MigrationExecutor", side_effect=RuntimeError("private details")):
            output = StringIO()
            call_command("platform_readiness", "--json", stdout=output)
            payload = json.loads(output.getvalue())
            self.assertIn("database", payload["blockers"])
            self.assertNotIn("private details", output.getvalue())

    def test_production_check_rejects_debug_and_does_not_certify_delivery(self):
        with self.settings(DEBUG=True), patch("apps.accounts.management.commands.platform_readiness.connection"), patch("apps.accounts.management.commands.platform_readiness.MigrationExecutor") as executor:
            executor.return_value.migration_plan.return_value = []
            output = StringIO()
            with self.assertRaises(SystemExit):
                call_command("platform_readiness", "--production", "--strict", "--json", stdout=output)
            payload = json.loads(output.getvalue())
            self.assertIn("debug_enabled", payload["blockers"])
            self.assertEqual(payload["live_verification"], "NOT_VERIFIED_BY_THIS_COMMAND")

    def test_correlation_id_is_reused_or_generated_and_returned(self):
        factory = RequestFactory()

        def response(request):
            self.assertTrue(request.correlation_id)
            return __import__("django.http").http.HttpResponse("ok")

        request = factory.get("/health/", HTTP_X_REQUEST_ID="release-123")
        result = RequestCorrelationIdMiddleware(response)(request)
        self.assertEqual(result["X-Request-ID"], "release-123")

        generated = RequestCorrelationIdMiddleware(response)(factory.get("/health/", HTTP_X_REQUEST_ID="bad id"))
        self.assertTrue(generated["X-Request-ID"])
        self.assertNotIn(" ", generated["X-Request-ID"])

    def test_readiness_json_is_redacted(self):
        output = StringIO()
        call_command("platform_readiness", "--json", stdout=output)
        payload = json.loads(output.getvalue())
        self.assertIn(payload["status"], {"READY", "BLOCKED"})
        rendered = output.getvalue()
        self.assertNotIn("EMAIL_HOST_PASSWORD", rendered)
        self.assertIn("username_present", rendered)
        self.assertIn("csp_report_only", rendered)

    def test_csp_is_report_only_by_default(self):
        factory = RequestFactory()

        def response(request):
            return __import__("django.http").http.HttpResponse("ok")

        result = SecurityHeadersMiddleware(response)(factory.get("/health/"))
        self.assertIn("Content-Security-Policy-Report-Only", result)
        self.assertNotIn("Content-Security-Policy", result)
