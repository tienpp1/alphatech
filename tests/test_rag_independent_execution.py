"""Recorded existing IND cases on real offline services; NOT human quality grades."""
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Permission, Role, User
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.retail.models import Customer, Order
from apps.service_ops.models import Service, ServiceRequest
from apps.knowledge.evaluation import run_benchmark_evaluation
from apps.knowledge.human_review import create_review, summarize_review
from apps.knowledge.independent_benchmark import INDEPENDENT_BENCHMARK_QUESTIONS
from apps.knowledge.services import create_knowledge_base, upload_and_ingest_document


@override_settings(LLM_API_KEY='', GEMINI_API_KEY='')
class IndependentRAGExecutionTests(TestCase):
    def test_external_scope_guard_preserves_business_forecasts_and_ticket_paraphrases(self):
        from apps.knowledge.intent_router import classify_business_intent
        workspace = Workspace(workspace_type='SERVICE')
        for question in ('Dự đoán giá vàng quốc tế tuần tới?', 'Giá cổ phiếu Tesla trên Nasdaq?'):
            routed = classify_business_intent(question, workspace)
            self.assertFalse(routed['allow_document_retrieval'])
            self.assertEqual(routed['tools'], [])
        routed = classify_business_intent('Dự báo doanh thu tuần tới', Workspace(workspace_type='RETAIL'))
        self.assertEqual(routed['tools'], ['get_forecast'])
        routed = classify_business_intent('Còn bao nhiêu yêu cầu kỹ thuật chưa xử lý?', workspace)
        self.assertEqual(routed['tools'], ['get_service_ticket_summary'])

    def test_record_preexisting_cases_without_mocking_answers_or_grading_them(self):
        role = Role.objects.create(name='IND_EVIDENCE_READER')
        for code in ('ai.chat', 'knowledge.view_knowledge', 'knowledge.manage_knowledge',
                     'retail.view_order', 'service.view_request'):
            permission, _ = Permission.objects.get_or_create(
                codename=code, defaults={'name': code, 'module': code.split('.')[0]})
            role.permissions.add(permission)
        actor = User.objects.create_user(username='ind-evidence', email='ind@example.test')
        details = []
        policy = 'Laptop bảo hành 24 tháng. Đổi 1 đổi 1 trong 30 ngày đầu khi lỗi kỹ thuật.'
        # Questions already exist in the repository; no tuning after observing answers.
        with patch('urllib.request.urlopen', side_effect=AssertionError('Network forbidden')), patch(
            'config.provider_http.build_opener', side_effect=AssertionError('Network forbidden')
        ):
            for kind in ('RETAIL', 'SERVICE'):
                workspace = Workspace.objects.create(code='ind-' + kind, name=kind, workspace_type=kind)
                WorkspaceMembership.objects.create(workspace=workspace, user=actor, role=role)
                customer = Customer.objects.create(workspace=workspace, code='IND-C', name='Synthetic customer')
                if kind == 'RETAIL':
                    kb = create_knowledge_base(workspace, actor, 'IND synthetic policy')
                    upload_and_ingest_document(workspace=workspace, user=actor, knowledge_base=kb,
                        title='Chính Sách Bảo Hành Thiết Bị', file_type='TXT',
                        file_obj=SimpleUploadedFile('ind.txt', policy.encode(), content_type='text/plain'))
                    Order.objects.create(workspace=workspace, customer=customer, order_number='IND-ORDER',
                        status='COMPLETED', total_amount='15000000.00', order_date=timezone.localdate(),
                        order_timestamp=timezone.now())
                    reference = {'documents': [{'title': 'Chính Sách Bảo Hành Thiết Bị', 'text': policy}],
                                 'facts': {'completed_orders': 1, 'revenue_vnd': 15000000}}
                else:
                    service = Service.objects.create(workspace=workspace, code='IND-S', name='Synthetic service')
                    ServiceRequest.objects.create(workspace=workspace, customer=customer, service=service,
                        request_number='IND-TICKET', title='Synthetic overdue ticket', status='OPEN',
                        resolution_deadline_at=timezone.now() - timedelta(days=1))
                    reference = {'documents': [], 'facts': {'total_tickets': 1, 'open_tickets': 1,
                                                          'overdue_sla_tickets': 1}}
                selected = [c for c in INDEPENDENT_BENCHMARK_QUESTIONS if c['workspace_type'] == kind]
                result = run_benchmark_evaluation(workspace, actor, cases=selected)
                self.assertEqual(len(result['details']), len(selected))
                for row in result['details']:
                    self.assertEqual(row['status'], 'SCORED')
                    self.assertIsNone(row['semantic_correctness'])
                    self.assertTrue(row['answer'])
                    row['reference_documents'] = reference['documents']
                    row['expected'] = reference['facts'] if not row['should_fallback'] else 'Refuse unsupported facts.'
                    row['environment'] = 'OFFLINE_SYNTHETIC_NO_LIVE_PROVIDER'
                    details.append(row)
        self.assertEqual({r['id'] for r in details}, {c['id'] for c in INDEPENDENT_BENCHMARK_QUESTIONS})
        indexed = {row['id']: row for row in details}
        self.assertTrue(indexed['IND-OOD-01']['refused'])
        self.assertEqual(indexed['IND-OOD-01']['sources'], [])
        self.assertEqual(indexed['IND-OOD-01']['tools_used'], [])
        self.assertTrue(indexed['IND-DATA-01']['tool_ok'])
        self.assertIn('1 phiếu yêu cầu', indexed['IND-DATA-01']['answer'])
        self.assertIn('1 quá hạn SLA', indexed['IND-DATA-01']['answer'])
        self.assertTrue(indexed['IND-HYB-01']['tool_ok'])
        self.assertTrue(indexed['IND-HYB-01']['citation_ok'])
        report = {'details': details, 'scope': 'Actual offline answers; preexisting questions, not a blinded holdout.',
                  'cases_sha256': hashlib.sha256(Path('apps/knowledge/independent_benchmark.py').read_bytes()).hexdigest()}
        review = create_review(report)
        summary = summarize_review(report, review)
        self.assertEqual(summary['reviewed_cases'], 0)
        evidence = getattr(settings, 'EVIDENCE_REPORT_DIR', None)
        if evidence:
            folder = evidence / 'independent_rag'
            folder.mkdir(parents=True, exist_ok=False)
            for name, value in [('report.json', report), ('review.json', review), ('initial_summary.json', summary)]:
                (folder / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
