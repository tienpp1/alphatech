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

    def test_api_health_check_alias(self):
        """Verify GET /api/health/ alias route works identically."""
        response = self.client.get(reverse("api_health_check"))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content.decode("utf-8"))
        self.assertEqual(data["status"], "healthy")

    def test_health_check_ui_html_response(self):
        """Verify GET / renders the HTML status dashboard."""
        response = self.client.get(reverse("health_check_ui"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Business Platform")
        self.assertContains(response, "HEALTHY")
