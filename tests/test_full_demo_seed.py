"""Full local demo smoke test with synthetic data and provider calls forbidden."""
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase, override_settings
from apps.accounts.models import User
from apps.workspaces.models import Workspace
from apps.retail.models import Product, Order
from apps.service_ops.models import ServiceRequest
from apps.knowledge.models import Document
from apps.forecasting.models import ForecastRun


@override_settings(DEBUG=True, LLM_API_KEY="", GEMINI_API_KEY="")
class FullDemoSeedTests(TestCase):
    def test_seed_completes_with_retail_service_and_ingested_documents(self):
        output = StringIO()
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden in demo test")) as network, patch('config.provider_http.build_opener', side_effect=AssertionError('Network forbidden in demo test')) as provider:
            call_command("seed_demo", confirm_empty_demo=True, stdout=output)
        network.assert_not_called()
        provider.assert_not_called()
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(Workspace.objects.count(), 2)
        self.assertTrue(Product.objects.exists())
        self.assertTrue(Order.objects.exists())
        self.assertTrue(ServiceRequest.objects.exists())
        self.assertTrue(Document.objects.exists())
        self.assertFalse(Document.objects.exclude(status="READY").exists())
        self.assertEqual(ForecastRun.objects.count(), 3)
        self.assertFalse(ForecastRun.objects.exclude(status="COMPLETED").exists())
        self.assertIn("DEMO COMPLETE:", output.getvalue())
        self.assertNotIn("DEMO PARTIAL:", output.getvalue())
        for ticket in ServiceRequest.objects.select_related("customer", "service"):
            self.assertEqual(ticket.customer.workspace_id, ticket.workspace_id)
            self.assertEqual(ticket.service.workspace_id, ticket.workspace_id)
