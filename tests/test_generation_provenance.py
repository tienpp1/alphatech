"""Application-path tests using simulated provider responses, not live Gemini evidence."""
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from apps.knowledge.services import generate_grounded_answer, FALLBACK_NO_CONTEXT_MESSAGE
from apps.knowledge.evaluation_scoring import score_case


class GenerationProvenanceTests(SimpleTestCase):
    def generate(self, tools=None):
        metadata = {}
        answer, _ = generate_grounded_answer(SimpleNamespace(name="Fixture"), None, "Doanh thu?", [],
            tools_data=tools, generation_metadata=metadata)
        return answer, metadata

    def facts(self):
        return [{"tool": "get_sales_summary", "total_revenue": "100 VND", "total_orders": 1, "completed_orders": 1}]

    @override_settings(LLM_API_KEY="")
    @patch("apps.knowledge.services._call_gemini_chat_api")
    def test_offline_answer_records_actual_path(self, provider):
        answer, metadata = self.generate(self.facts())
        self.assertIn("100 VND", answer)
        self.assertEqual(metadata["mode"], "DETERMINISTIC")
        self.assertEqual(metadata["reason"], "NO_API_KEY")
        provider.assert_not_called()

    @override_settings(LLM_API_KEY="fixture-only", LLM_MODEL="fixture-model")
    @patch("apps.knowledge.services._call_gemini_chat_api", return_value=None)
    def test_provider_failure_falls_back_with_truthful_metadata(self, provider):
        answer, metadata = self.generate(self.facts())
        self.assertIn("100 VND", answer)
        self.assertEqual(metadata["reason"], "PROVIDER_UNAVAILABLE")
        self.assertIsNone(metadata["model"])

    @override_settings(LLM_API_KEY="fixture-only")
    @patch("config.provider_http.open_provider_request", side_effect=TimeoutError("fixture timeout"))
    def test_transport_timeout_returns_business_fallback(self, transport):
        answer, metadata = self.generate(self.facts())
        self.assertIn("100 VND", answer)
        self.assertEqual(metadata["reason"], "PROVIDER_UNAVAILABLE")
        transport.assert_called_once()

    @override_settings(LLM_API_KEY="fixture-only")
    @patch("config.provider_http.open_provider_request")
    def test_invalid_provider_json_returns_business_fallback(self, transport):
        response = transport.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = b"not-json"
        answer, metadata = self.generate(self.facts())
        self.assertIn("100 VND", answer)
        self.assertEqual(metadata["reason"], "PROVIDER_UNAVAILABLE")

    @override_settings(LLM_API_KEY="fixture-only", LLM_MODEL="fixture-model")
    @patch("apps.knowledge.services._call_gemini_chat_api", return_value="Provider fixture answer")
    def test_success_records_used_model_and_scorer_preserves_it(self, provider):
        answer, metadata = self.generate(self.facts())
        self.assertEqual(metadata["mode"], "LLM_RESPONSE")
        self.assertEqual(metadata["model"], "fixture-model")
        case = {"id": "P", "category": "STRUCTURED_ONLY", "should_fallback": False}
        result = score_case(case, {"answer": answer, "generation_metadata": metadata}, FALLBACK_NO_CONTEXT_MESSAGE)
        self.assertEqual(result["generation_mode"], "LLM_RESPONSE")
        self.assertNotIn("fixture-only", str(result))

    @override_settings(LLM_API_KEY="fixture-only")
    @patch("apps.knowledge.services._call_gemini_chat_api")
    def test_no_context_does_not_invoke_provider(self, provider):
        answer, metadata = self.generate()
        self.assertEqual(answer, FALLBACK_NO_CONTEXT_MESSAGE)
        self.assertEqual(metadata["mode"], "NO_CONTEXT")
        provider.assert_not_called()

    @override_settings(LLM_API_KEY="fixture-only")
    @patch("apps.knowledge.services._call_gemini_chat_api")
    def test_simulation_reports_deterministic_mode(self, provider):
        _, metadata = self.generate([{"tool": "simulate_what_if_scenario"}])
        self.assertEqual(metadata["reason"], "SIMULATION")
        provider.assert_not_called()
