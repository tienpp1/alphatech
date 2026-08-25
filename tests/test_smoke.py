"""
Smoke tests for verifying Django setup, settings and database connectivity.
"""

from django.test import SimpleTestCase, TestCase
from django.conf import settings
from django.db import connection


class DjangoBootstrapSmokeTest(SimpleTestCase):
    """Verify Django core bootstrap and configuration."""

    def test_settings_loaded(self):
        """Check essential Django settings are properly loaded."""
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertIn("rest_framework", settings.INSTALLED_APPS)
        self.assertEqual(settings.ROOT_URLCONF, "config.urls")

    def test_template_configuration(self):
        """Check template engine is configured."""
        self.assertTrue(len(settings.TEMPLATES) > 0)
        self.assertEqual(settings.TEMPLATES[0]["BACKEND"], "django.template.backends.django.DjangoTemplates")


class DatabaseConnectionSmokeTest(TestCase):
    """Verify database connectivity in Django test environment."""

    def test_database_connection(self):
        """Verify DB cursor execution."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            self.assertEqual(row[0], 1)
