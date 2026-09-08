"""
Tests for health check endpoints (JSON API and UI view).
"""

from django.test import TestCase, Client
from django.urls import reverse
import json


class HealthCheckEndpointTest(TestCase):
    """Test suite for health check API and UI endpoints."""

    def setUp(self):
        self.client = Client()

    def test_health_check_api_json_response(self):
        """Verify GET /health/ returns 200 OK and expected schema."""
        response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")

        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")
        self.assertIn("platform", data)
        self.assertIn("environment", data)
        self.assertIn("database", data)
        self.assertEqual(data["database"]["status"], "connected")
        self.assertEqual(data["version"], "1.0.0-final")
        self.assertIn("phase", data)
        self.assertEqual(data["phase"]["current"], "Production readiness baseline (local verified)")
        self.assertEqual(data["phase"]["status"], "LOCAL VERIFIED / EXTERNAL GATES PENDING")

    def test_api_health_check_alias(self):
        """Verify GET /api/health/ alias route works identically."""
        response = self.client.get(reverse("api_health_check"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["phase"]["current"], "Production readiness baseline (local verified)")

    def test_health_redacts_database_configuration_and_failures(self):
        from unittest.mock import patch
        with patch("config.views.connection.cursor", side_effect=RuntimeError("private-db-password")):
            response = self.client.get(reverse("health_check"))
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, "private-db-password", status_code=503)
        database = response.json()["database"]
        self.assertEqual(database["error"], "database_unavailable")
        for field in ("name", "host", "port"):
            self.assertEqual(database[field], "redacted")

    def test_health_check_ui_html_response(self):
        """Verify GET / renders the HTML status dashboard with final Phase 0–12 info in Vietnamese."""
        response = self.client.get(reverse("health_check_ui"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nền tảng Doanh nghiệp AI")
        self.assertContains(response, "HOẠT ĐỘNG TỐT")
        self.assertContains(response, "Baseline cục bộ đã được kiểm chứng")
        self.assertNotContains(response, "Phase 1 Gate")
        self.assertNotContains(response, "Ready for Phase 2")
        self.assertNotContains(response, "Phase 4 — Service Operations")

    def test_health_metadata_no_stale_regression(self):
        """Regression test ensuring health endpoint does not report stale phases."""
        response = self.client.get(reverse("health_check"))
        data = json.loads(response.content.decode("utf-8"))
        self.assertNotEqual(data["phase"]["current"], "Phase 0 - Bootstrap & Environment Inspection")
        self.assertNotEqual(data["phase"]["current"], "Phase 1 COMPLETE / Phase 2 READY")
