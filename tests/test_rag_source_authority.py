"""Source rank is not document authority; these are offline regressions."""
from types import SimpleNamespace
from unittest.mock import patch
from django.test import SimpleTestCase, override_settings
from apps.knowledge.services import generate_grounded_answer


@override_settings(LLM_API_KEY='', GEMINI_API_KEY='')
class RAGSourceAuthorityTests(SimpleTestCase):
    def chunk(self, title, content, page=1):
        return {'document_title': title, 'content': content, 'heading': 'Bảo hành',
                'page_number': page, 'chunk_id': page, 'similarity': 0.9}

    def test_multiple_documents_do_not_imply_ranked_authority(self):
        chunks = [self.chunk('Policy A', 'Laptop được bảo hành 24 tháng.'),
                  self.chunk('Policy B', 'Laptop được bảo hành 12 tháng.', 2)]
        answer, sources = generate_grounded_answer(SimpleNamespace(name='Demo'), None, 'Bảo hành?', chunks, [])
        self.assertIn('thứ tự tìm kiếm không xác nhận', answer)
        self.assertIn('24 tháng', answer)
        self.assertIn('12 tháng', answer)
        self.assertIn('Có mâu thuẫn số liệu', answer)
        self.assertIn('cần xác nhận tài liệu có hiệu lực', answer)
        self.assertEqual(len(sources), 2)

    def test_different_subjects_are_not_inferred_as_conflicting(self):
        chunks = [self.chunk('A', 'Laptop được bảo hành 24 tháng.'),
                  self.chunk('B', 'Máy in được bảo hành 12 tháng.', 2)]
        answer, _ = generate_grounded_answer(SimpleNamespace(name='Demo'), None, 'Bảo hành?', chunks, [])
        self.assertNotIn('Có mâu thuẫn số liệu', answer)

    def test_distinct_content_in_same_section_is_not_silently_discarded(self):
        chunks = [self.chunk('Policy', 'Laptop được bảo hành 24 tháng.'),
                  self.chunk('Policy', 'Laptop được bảo hành 12 tháng.', 2)]
        answer, _ = generate_grounded_answer(SimpleNamespace(name='Demo'), None, 'Bảo hành?', chunks, [])
        self.assertIn('24 tháng', answer)
        self.assertIn('12 tháng', answer)
        self.assertIn('Trang 2', answer)

    @override_settings(LLM_API_KEY='simulated-test-key')
    def test_provider_prompt_requires_explicit_conflict_and_authority_boundary(self):
        with patch('apps.knowledge.services._call_gemini_chat_api', return_value='simulation') as call:
            generate_grounded_answer(SimpleNamespace(name='Demo'), None, 'Bảo hành?',
                                    [self.chunk('Policy', 'Laptop được bảo hành 24 tháng.')], [])
        self.assertIn('không tự chọn một nguồn', call.call_args.args[0])
        self.assertIn('yêu cầu người dùng xác nhận', call.call_args.args[0])
