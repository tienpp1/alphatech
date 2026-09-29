"""Offline application observations, not a mocked LLM quality benchmark."""
import json
from unittest.mock import patch
from django.conf import settings
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.knowledge.adversarial_cases import ADVERSARIAL_CASES
from apps.knowledge.services import create_knowledge_base, upload_and_ingest_document, answer_grounded_query
from apps.knowledge.tools import ToolPermissionDenied
from apps.knowledge.models import DocumentChunk
from apps.knowledge.retrieval import search_relevant_chunks
from apps.knowledge.evidence_metrics import chunk_metrics, numeric_fact_metrics


@override_settings(LLM_API_KEY='', GEMINI_API_KEY='')
class AdversarialRAGExecutionTests(TestCase):
    def test_record_real_offline_pipeline_for_all_scenarios(self):
        role = Role.objects.create(name='ADVERSARIAL_READER')
        for codename in ('ai.chat', 'knowledge.manage_knowledge', 'knowledge.view_knowledge'):
            permission, _ = Permission.objects.get_or_create(codename=codename,
                defaults={'name': codename, 'module': 'knowledge'})
            role.permissions.add(permission)
        no_chat = Role.objects.create(name='ADVERSARIAL_NO_CHAT')
        rows = []
        with patch('urllib.request.urlopen', side_effect=AssertionError('External provider forbidden')), patch('config.provider_http.build_opener', side_effect=AssertionError('External provider forbidden')):
            for index, case in enumerate(ADVERSARIAL_CASES):
                workspace = Workspace.objects.create(code=f'adv-{index}', name=case['id'], workspace_type='RETAIL')
                author = User.objects.create_user(username=f'adv-author-{index}', email=f'adv-author-{index}@example.test')
                WorkspaceMembership.objects.create(workspace=workspace, user=author, role=role)
                actor = author
                if case['kind'] in ('missing_permission', 'wrong_workspace'):
                    actor = User.objects.create_user(username=f'adv-actor-{index}', email=f'adv-actor-{index}@example.test')
                    if case['kind'] == 'missing_permission':
                        WorkspaceMembership.objects.create(workspace=workspace, user=actor, role=no_chat)
                    else:
                        other = Workspace.objects.create(code=f'adv-other-{index}', name='Other', workspace_type='RETAIL')
                        WorkspaceMembership.objects.create(workspace=other, user=actor, role=role)
                kb = create_knowledge_base(workspace, author, case['id'])
                gold_chunks = []
                for number, document in enumerate(case['documents']):
                    doc = upload_and_ingest_document(workspace=workspace, user=author,
                        knowledge_base=kb, title=document['title'], file_type='TXT',
                        file_obj=SimpleUploadedFile(f'case-{index}-{number}.txt', document['text'].encode(), content_type='text/plain'))
                    self.assertEqual(doc.status, 'READY')
                    stored = DocumentChunk.objects.get(document=doc)
                    self.assertEqual(stored.metadata['embedding_provenance']['mode'], 'DETERMINISTIC')
                    # Select expected evidence from authored fixtures BEFORE querying,
                    # never by copying the response's own citations into the gold set.
                    gold_chunks.append(stored.pk)
                for question in case['questions']:
                    row = {'id': case['id'], 'kind': case['kind'], 'question': question,
                           'expected': case['expected'], 'fixture_documents': case['documents'],
                           'semantic_pass': None, 'environment': 'OFFLINE_SYNTHETIC'}
                    try:
                        response = answer_grounded_query(workspace, actor, question)
                    except ToolPermissionDenied:
                        self.assertIn(case['kind'], ('missing_permission', 'wrong_workspace'))
                        row.update(status='DENIED', response=None)
                    else:
                        self.assertNotIn(case['kind'], ('missing_permission', 'wrong_workspace'))
                        self.assertTrue(response['answer'])
                        self.assertEqual(response['retrieval_metadata']['query_embedding']['mode'], 'DETERMINISTIC')
                        row.update(status='ANSWERED', response=response)
                        if case['kind'] in ('paraphrase', 'conflicting_documents'):
                            row['gold_chunk_metrics'] = chunk_metrics(
                                {'expected_chunk_ids': gold_chunks}, response['sources'])
                            self.assertEqual(row['gold_chunk_metrics']['chunk_recall'], 1.0)
                            self.assertEqual(row['gold_chunk_metrics']['chunk_precision'], 1.0)
                        if case['kind'] == 'paraphrase':
                            row['numeric_fact_metrics'] = numeric_fact_metrics(
                                {'required_numeric_facts': [{'id': 'warranty_months', 'expected': '24',
                                    'pattern': r'bảo hành\s+(?P<value>\d+)\s+tháng'}]}, response['answer'])
                            self.assertTrue(row['numeric_fact_metrics']['numeric_facts_ok'])
                    rows.append(row)
        self.assertEqual(len(rows), 6)
        self.assertEqual(sum(row['status'] == 'DENIED' for row in rows), 2)
        # Legacy vectors retain UNKNOWN provenance; never backfill from current settings.
        legacy = DocumentChunk.objects.get(document__title='Tenant B fixture')
        legacy.metadata.pop('embedding_provenance')
        legacy.save(update_fields=['metadata'])
        retrieved = search_relevant_chunks(legacy.workspace, legacy.content, threshold=0)
        self.assertEqual(retrieved[0]['embedding_provenance'], {'mode': 'UNKNOWN'})
        evidence = getattr(settings, 'EVIDENCE_REPORT_DIR', None)
        if evidence:
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / 'adversarial_rag_observations.json').write_text(
                json.dumps({'limitations': 'Actual local pipeline; no live LLM; semantic judgments remain unmeasured.',
                            'details': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
