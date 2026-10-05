"""Draft ERD contract checks; not a review of a future submitted Word file."""
import re
from pathlib import Path

from django.apps import apps
from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[1]


class AcademicDiagramContractTests(SimpleTestCase):
    def test_every_draft_erd_edge_is_a_declared_fk_with_correct_optionality(self):
        text = (ROOT / 'docs/THUYET_MINH_DO_AN_CHUONG_3_4_5.md').read_text(encoding='utf-8')
        diagram = re.search(r'```mermaid\s+erDiagram\s+(.*?)```', text, re.S).group(1)
        models = {model._meta.label.replace('.', '_'): model for model in apps.get_models()}
        edges = re.findall(r'^\s*(\w+)\s+(\|\||\|o)--o\{\s+(\w+)\s+:\s+"(\w+)"', diagram, re.M)
        self.assertEqual(len(edges), 22, 'Review every diagram edge, not only those matching the regex.')
        meaningful = [line for line in diagram.splitlines() if line.strip()]
        self.assertEqual(len(meaningful), len(edges), 'Unparsed diagram content must be reviewed.')
        for parent, cardinality, child, field_name in edges:
            with self.subTest(parent=parent, child=child, field=field_name):
                self.assertIn(parent, models)
                self.assertIn(child, models)
                field = models[child]._meta.get_field(field_name)
                self.assertTrue(field.many_to_one)
                self.assertIs(field.remote_field.model, models[parent])
                self.assertEqual(cardinality, '|o' if field.null else '||')

    def test_sequence_and_architecture_do_not_invent_runtime_components(self):
        text = (ROOT / 'docs/THUYET_MINH_DO_AN_CHUONG_3_4_5.md').read_text(encoding='utf-8')
        for withdrawn in ('WorkspaceIsolationMiddleware', 'AuditLoggingMiddleware',
                          'SELECT chunk_text FROM chunks', 'System Context + Gold Chunks',
                          "INSERT INTO retail_order (status='CONFIRMED'",
                          'request.user.role in [ADMIN, MANAGER]',
                          'Brevo SMTP Relay', 'KNOWLEDGE_EMBEDDING', 'TEAM_CHAT_CHANNEL',
                          'prevent_audit_tampering()', 'Django 5.1.x'):
            with self.subTest(withdrawn=withdrawn):
                self.assertNotIn(withdrawn, text)
        for boundary in ('status=PENDING', 'polling 3 giây', 'không có global ORM filter',
                         'forecasting.view_forecast', 'Google-linked identity',
                         'không có FK Order hoặc ApprovalRequest'):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, text)

    def test_related_work_uses_verified_closer_edition_not_unverified_springer_metadata(self):
        text = (ROOT / 'docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md').read_text(encoding='utf-8')
        entry = next(line for line in text.splitlines() if line.startswith('[4] '))
        self.assertIn('2012', entry)
        self.assertIn('426–431', entry)
        self.assertIn('10.5220/0003957604260431', entry)
        self.assertNotIn('Springer', entry)
        third = next(line for line in text.splitlines() if line.startswith('[3] '))
        self.assertIn('Maintenance dream or nightmare?', third)
        self.assertIn('IWPSE-EVOL', third)
        self.assertIn('88–92', third)
        self.assertNotIn('Maintenance Expenses to be Shared by All', third)

    def test_results_keep_run_boundaries_and_implemented_routing(self):
        text = (ROOT / 'docs/THUYET_MINH_DO_AN_CHUONG_3_4_5.md').read_text(encoding='utf-8')
        for required in ('snapshot lịch sử Batch 44', 'forecast_recursive_20261005/results.json',
                         '156688.50', '153742.36', 'không phải holdout',
                         '1201 tests', '414.870s', '0 failure/error/skip', '58%',
                         'OSRM route/table', 'requester_id', 'bypass superuser tường minh'):
            with self.subTest(required=required):
                self.assertIn(required, text)
        self.assertNotIn('assert request.user != action_request.created_by', text)
        self.assertNotIn('được giải thích bởi 4 nguyên nhân cụ thể', text)
