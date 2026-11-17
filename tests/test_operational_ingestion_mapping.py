"""Synthetic operational ingestion/mapping regressions; no live provider traffic."""
import hashlib
import io
import json
from unittest.mock import patch
from urllib.request import Request
from urllib.error import HTTPError

from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.integration.models import DataSource
from apps.integration.serializers import DataSourceSerializer, DataSourceCreateSerializer
from apps.integration.parsers.api_parser import fetch_and_parse_api, SafeRedirectHandler
from apps.integration.services import execute_import_job, generate_import_preview, update_data_source
from apps.mapping.ai_suggester import suggest_mappings_for_fields
from apps.mapping.models import MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.engine.transformer import transform_single_record
from apps.mapping.services import (create_mapping_profile, add_mapping_rule,
    apply_mapping_to_domain, generate_mapping_preview, accept_ai_mapping_rule)
from apps.retail.models import Customer


class ResponseBytes(io.BytesIO):
    status = 200


class OperationalSchemaUnitTests(SimpleTestCase):
    def test_preview_preserves_legitimate_inferred_types_while_masking_credentials(self):
        from apps.integration.parsers.preview_engine import generate_preview_metadata
        parsed = {'is_valid': True, 'columns': ['name', 'password'], 'rows': [{'row_number': 1, 'raw_data': {'name': 'Visible legitimate', 'password': 'SYNTHETIC-PREVIEW-SECRET'}, 'is_valid': True, 'errors': []}], 'total_rows': 1}
        preview = generate_preview_metadata(parsed)
        self.assertEqual(preview['detected_types']['name'], 'STRING')
        self.assertEqual(preview['sample_rows'][0]['raw_data']['name'], 'Visible legitimate')
        self.assertNotIn('SYNTHETIC-PREVIEW-SECRET', json.dumps(preview))
        self.assertEqual(parsed['rows'][0]['raw_data']['password'], 'SYNTHETIC-PREVIEW-SECRET')

    def test_consumed_empty_http_payload_keeps_a_receipt_without_fabricating_rows(self):
        content = b'{"data":[]}'
        with patch('apps.integration.parsers.api_parser.validate_safe_remote_url', return_value=(True, None)), patch('apps.integration.parsers.api_parser.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = ResponseBytes(content)
            result = fetch_and_parse_api('https://partner.example/feed?token=SYNTHETIC-SECRET')
        self.assertEqual(result.get('ingestion_provenance', {}).get('sha256'), hashlib.sha256(content).hexdigest())
        self.assertEqual(result['rows'], [])
        self.assertNotIn('SYNTHETIC-SECRET', json.dumps(result))

    @override_settings(GROQ_API_KEY='synthetic-provider-key', GROQ_MODEL='openai/gpt-oss-120b')
    def test_groq_schema_request_sends_platform_user_agent(self):
        from apps.mapping.schema_suggestions import _groq
        raw = json.dumps({
            'model': 'openai/gpt-oss-120b',
            'choices': [{'message': {'content': '{"mappings":[]}'}, 'finish_reason': 'stop'}],
        }).encode()
        with patch('config.provider_http.open_provider_request', return_value=ResponseBytes(raw)) as transport:
            self.assertEqual(_groq(['name'], 'Customer'), ([], ''))
        transport.assert_called_once()
        request = transport.call_args.args[0]
        self.assertEqual(request.get_header('User-agent'), 'AlphaTech/1.0')

    @override_settings(GROQ_API_KEY='synthetic-provider-key')
    def test_malformed_provider_shapes_refusal_truncation_and_size_are_safe(self):
        from apps.mapping.schema_suggestions import _groq
        base = {'model': 'openai/gpt-oss-120b', 'choices': [{'message': {'content': '{"mappings":[]}'}, 'finish_reason': 'stop'}]}
        malformed = [[], {'model': base['model'], 'choices': ['wrong']}, {'model': base['model'], 'choices': [{'message': [], 'finish_reason': 'stop'}]}, {'model': base['model'], 'choices': [{'message': {'content': '{}', 'refusal': 'No'}, 'finish_reason': 'stop'}]}, {'model': base['model'], 'choices': [{'message': {'content': '{"mappings":[]}'}, 'finish_reason': 'length'}]}]
        for envelope in malformed:
            with self.subTest(envelope=envelope), patch('config.provider_http.open_provider_request', return_value=ResponseBytes(json.dumps(envelope).encode())):
                self.assertEqual(_groq(['name'], 'Customer'), (None, 'invalid_provider_response'))
        with patch('config.provider_http.open_provider_request', return_value=ResponseBytes(b' ' * 17000)):
            self.assertEqual(_groq(['name'], 'Customer'), (None, 'invalid_provider_response'))

    @override_settings(GROQ_API_KEY='synthetic-provider-key')
    def test_unsafe_schema_names_and_duplicate_or_oversized_columns_never_leave_server(self):
        from apps.mapping.schema_suggestions import _groq
        for columns in (['synthetic@example.test'], ['0912345678'], ['api_key'], ['name', 'name'], ['a'] * 101, ['a' * 101], 'name', [None]):
            with self.subTest(columns=columns), patch('config.provider_http.open_provider_request') as transport:
                self.assertEqual(_groq(columns, 'Customer'), (None, 'unsafe_schema_names'))
                transport.assert_not_called()

    def test_invalid_rule_config_cannot_crash_transformation(self):
        rule = MappingRule(source_field='name', target_field='name', rule_type='TYPE_CONVERSION', transformation_config='bad')
        canonical, errors = transform_single_record({'name': 'Synthetic'}, [rule], 'Customer')
        self.assertNotIn('name', canonical)
        self.assertTrue(errors)


class OperationalParserTests(TestCase):
    def fetch(self, content, params=None):
        response = ResponseBytes(content)
        with patch('apps.integration.parsers.api_parser.validate_safe_remote_url', return_value=(True, None)), patch('apps.integration.parsers.api_parser.urllib.request.build_opener') as opener:
            opener.return_value.open.return_value = response
            result = fetch_and_parse_api('https://partner.example/feed?existing=1', params=params)
            request = opener.return_value.open.call_args.args[0]
        return result, request

    def test_empty_envelopes_never_become_staged_rows(self):
        for content in (b'{"data":[]}', b'{"records":[]}', b'[]'):
            with self.subTest(content=content):
                result, _ = self.fetch(content)
                self.assertFalse(result['is_valid'])
                self.assertEqual(result['rows'], [])

    def test_remote_query_and_consumed_bytes_receipt(self):
        content = b'{"data":[{"sku":"SYNTHETIC-1"}]}'
        result, request = self.fetch(content, {'page': 2, 'tag': ['a', 'b']})
        self.assertIn('existing=1&page=2&tag=a&tag=b', request.full_url)
        receipt = result.get('ingestion_provenance', {})
        self.assertEqual(receipt.get('sha256'), hashlib.sha256(content).hexdigest())
        self.assertEqual(receipt.get('byte_count'), len(content))
        self.assertEqual(receipt.get('classification'), 'UNKNOWN')

    def test_arbitrary_relative_route_never_uses_django_client(self):
        with patch('apps.integration.parsers.api_parser.Client') as client:
            result = fetch_and_parse_api('/api/v1/retail/orders/')
        self.assertFalse(result['is_valid'])
        client.assert_not_called()

    def test_cross_origin_redirect_cannot_forward_credentials(self):
        request = Request('https://partner.example/feed', headers={'Authorization': 'Bearer synthetic-only'})
        with patch('apps.integration.parsers.api_parser.validate_safe_remote_url', return_value=(True, None)):
            with self.assertRaises(HTTPError):
                SafeRedirectHandler().redirect_request(request, None, 302, 'Moved', {}, 'https://other.example/feed')

    def test_invalid_transport_shapes_fail_safely(self):
        for kwargs in ({'endpoint_url': []}, {'endpoint_url': '/api/v1/mock-external/retail/orders/', 'headers': []}, {'endpoint_url': '/api/v1/mock-external/retail/orders/', 'params': []}, {'endpoint_url': '/api/v1/mock-external/retail/orders/', 'timeout': 'bad'}):
            with self.subTest(kwargs=kwargs):
                result = fetch_and_parse_api(**kwargs)
                self.assertFalse(result['is_valid'])

    def test_chosen_candidate_keeps_decimal_configuration(self):
        suggestion = suggest_mappings_for_fields(['thanh_toan'], 'Order', {'thanh_toan': ['100 VND']})[0]
        self.assertEqual(suggestion['suggested_target_field'], 'total_amount')
        self.assertEqual(suggestion['suggested_rule_type'], 'TYPE_CONVERSION')
        self.assertEqual(suggestion['transformation_config'], {'target_type': 'DECIMAL'})

    def test_duplicate_alias_cannot_reuse_target(self):
        suggestions = suggest_mappings_for_fields(['ma_kh', 'customer_id'], 'Customer')
        targets = [s['suggested_target_field'] for s in suggestions]
        self.assertEqual(len(targets), len(set(targets)))

    def test_enum_suggestion_never_invents_completed(self):
        suggestion = suggest_mappings_for_fields(['trang_thai_don'], 'Order')[0]
        self.assertNotIn('default', suggestion['transformation_config'])
        rule = MappingRule(source_field='trang_thai_don', target_field='status', rule_type=suggestion['suggested_rule_type'], transformation_config=suggestion['transformation_config'], ai_status=AIConfirmationStatus.ACCEPTED)
        canonical, errors = transform_single_record({'trang_thai_don': 'UNKNOWN-STATE'}, [rule], 'Order')
        self.assertNotEqual(canonical.get('status'), 'COMPLETED')
        self.assertTrue(errors)

    def test_pending_and_rejected_gate_every_rule_type(self):
        for rule_type in RuleType.values:
            for state in (AIConfirmationStatus.PENDING, AIConfirmationStatus.REJECTED):
                with self.subTest(rule_type=rule_type, state=state):
                    rule = MappingRule(source_field='name', target_field='name', rule_type=rule_type, ai_status=state, transformation_config={'expression': '1'})
                    canonical, _ = transform_single_record({'name': 'SYNTHETIC'}, [rule], 'Customer')
                    self.assertNotIn('name', canonical)

    def test_recursive_config_redaction_and_validation(self):
        ds = DataSource(name='Synthetic', source_type='MOCK_API', connection_config={'headers': {'Authorization': 'SYNTHETIC-SECRET'}, 'params': {'token': 'SYNTHETIC-SECRET'}, 'url': 'https://user:SYNTHETIC-SECRET@partner.example/feed?api_key=SYNTHETIC-SECRET', 'nested': [{'password': 'SYNTHETIC-SECRET'}]})
        self.assertNotIn('SYNTHETIC-SECRET', json.dumps(DataSourceSerializer(ds).data))
        for config in ([], 'bad', {'headers': []}, {'params': []}, {'delimiter': '||'}):
            with self.subTest(config=config):
                serializer = DataSourceCreateSerializer(data={'name': 'Synthetic', 'source_type': 'CSV', 'connection_config': config})
                self.assertFalse(serializer.is_valid())


class OperationalMappingFlowTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code='op-map-test', name='Synthetic TEST', workspace_type='RETAIL')
        self.user = User.objects.create_user(username='op-map-test', email='synthetic@example.test')
        role = Role.objects.create(name='MANAGER')
        for code in ('mapping.view_mapping', 'mapping.manage_mapping', 'mapping.apply_mapping', 'integration.execute_import', 'integration.manage_datasource', 'integration.view_datasource'):
            permission, _ = Permission.objects.get_or_create(codename=code, defaults={'name': code, 'module': code.split('.')[0]})
            role.permissions.add(permission)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role=role, is_default=True)
        self.source = DataSource.objects.create(workspace=self.ws, name='Synthetic CSV', source_type='CSV', connection_config={'delimiter': '|'})
        self.profile = create_mapping_profile(self.ws, self.user, 'Synthetic profile', 'Customer', self.source)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.client.force_login(self.user)
        self.headers = {'HTTP_X_WORKSPACE_ID': str(self.ws.pk)}

    def ingest(self):
        self.content = b'code|name,extra\nSYNTHETIC1|Synthetic Person,only\n'
        return execute_import_job(self.ws, self.user, self.source, SimpleUploadedFile('synthetic.csv', self.content))

    def test_configured_delimiter_and_exact_ingestion_receipt(self):
        job = self.ingest()
        self.assertEqual(job.source_metadata['columns'], ['code', 'name,extra'])
        receipt = job.source_metadata.get('ingestion_provenance', {})
        self.assertEqual(receipt.get('sha256'), hashlib.sha256(self.content).hexdigest())
        self.assertEqual(receipt.get('byte_count'), len(self.content))
        self.assertEqual(receipt.get('classification'), 'UNKNOWN')
        preview = generate_import_preview(SimpleUploadedFile('synthetic.csv', self.content), self.source)
        self.assertEqual(preview['columns'], ['code', 'name,extra'])

    def test_same_workspace_foreign_source_job_denied_in_apply_and_preview(self):
        other = DataSource.objects.create(workspace=self.ws, name='Other synthetic', source_type='CSV')
        job = execute_import_job(self.ws, self.user, other, SimpleUploadedFile('synthetic.csv', b'code,name\nS1,Synthetic\n'))
        with self.assertRaises(PermissionDenied):
            apply_mapping_to_domain(self.ws, self.user, self.profile, job)
        with self.assertRaises(PermissionDenied):
            generate_mapping_preview(self.ws, self.profile, import_job=job)
        self.assertFalse(Customer.objects.exists())

    def test_nested_config_secrets_absent_from_audit_and_html(self):
        update_data_source(self.source, self.user, connection_config={'delimiter': '|', 'headers': {'Authorization': 'SYNTHETIC-SECRET'}})
        from apps.audit.models import AuditLog
        self.assertNotIn('SYNTHETIC-SECRET', str(list(AuditLog.objects.values_list('changes', flat=True))))
        response = self.client.get('/integration/sources/', **self.headers)
        self.assertNotContains(response, 'SYNTHETIC-SECRET')

    def test_invalid_preview_request_returns_400_not_500(self):
        response = self.client.post('/api/v1/integration/imports/preview/', {'sample_count': 'not-number'}, format='json', **self.headers)
        self.assertEqual(response.status_code, 400)

    def test_groq_requires_explicit_schema_consent_and_profile(self):
        response = self.client.post('/api/v1/mapping/ai-suggest/', {'target_entity': 'Customer', 'source_columns': ['code'], 'mode': 'groq_schema'}, format='json', **self.headers)
        self.assertEqual(response.status_code, 400)

    def test_schema_mode_missing_key_truthfully_falls_back_with_signed_confirmation(self):
        payload = {'target_entity': 'Customer', 'source_columns': ['customer_id', 'name'], 'mode': 'groq_schema', 'allow_schema_export': True, 'profile_id': str(self.profile.pk)}
        with override_settings(GROQ_API_KEY=''):
            response = self.client.post('/api/v1/mapping/ai-suggest/', payload, format='json', **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('provenance', {}).get('provider'), 'heuristic')
        self.assertEqual(response.data.get('provenance', {}).get('fallback_reason'), 'missing_api_key')
        suggestion = response.data['suggestions'][0]
        self.assertTrue(suggestion.get('confirmation_token'))
        confirm = self.client.post(f'/api/v1/mapping/profiles/{self.profile.pk}/rules/', {'confirmation_token': suggestion['confirmation_token'], 'human_confirmed': True}, format='json', **self.headers)
        self.assertEqual(confirm.status_code, 201)
        rule = MappingRule.objects.get(pk=confirm.data['data']['id'])
        self.assertEqual(rule.ai_status, 'ACCEPTED')

    def test_staging_to_human_confirmation_to_canonical_synthetic_e2e(self):
        job = self.ingest()
        rules = [add_mapping_rule(self.profile, self.user, source, target, ai_status=AIConfirmationStatus.PENDING) for source, target in (('code', 'customer_id'), ('name,extra', 'name'))]
        self.assertFalse(Customer.objects.exists())
        result = apply_mapping_to_domain(self.ws, self.user, self.profile, job, strict=True)
        self.assertEqual(result['status'], 'FAILED')
        for rule in rules:
            accept_ai_mapping_rule(rule, self.user)
        result = apply_mapping_to_domain(self.ws, self.user, self.profile, job, strict=True)
        self.assertEqual(result['status'], 'COMPLETED')
        self.assertEqual(list(Customer.objects.values_list('code', 'name')), [('SYNTHETIC1', 'Synthetic Person,only')])

    def schema_request(self):
        return {'target_entity': 'Customer', 'source_columns': ['customer_id', 'name'], 'mode': 'groq_schema', 'allow_schema_export': True, 'profile_id': str(self.profile.pk), 'sample_values': {'name': ['SYNTHETIC-PRIVATE-NOT-EXPORT']}}

    @override_settings(GROQ_API_KEY='synthetic-provider-key')
    def test_groq_transport_exports_schema_only_and_builds_rule_server_side(self):
        raw = json.dumps({'model': 'openai/gpt-oss-120b', 'choices': [{'message': {'content': json.dumps({'mappings': [{'source_index': 0, 'target_field': 'customer_id'}]})}, 'finish_reason': 'stop'}]}).encode()
        with patch('config.provider_http.open_provider_request', return_value=ResponseBytes(raw)) as transport:
            response = self.client.post('/api/v1/mapping/ai-suggest/', self.schema_request(), format='json', **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('provenance', {}).get('provider'), 'groq')
        sent = transport.call_args.args[0].data.decode()
        self.assertNotIn('SYNTHETIC-PRIVATE-NOT-EXPORT', sent)
        self.assertNotIn(str(self.ws.pk), sent)
        payload = json.loads(sent)
        self.assertTrue(payload['response_format']['json_schema']['strict'])
        self.assertEqual(payload['model'], 'openai/gpt-oss-120b')
        suggestion = response.data['suggestions'][0]
        self.assertEqual(suggestion['transformation_config'], {})
        self.assertEqual(suggestion['ai_status'], 'PENDING')

    @override_settings(GROQ_API_KEY='synthetic-provider-key')
    def test_invalid_provider_indexes_targets_formulas_and_duplicates_fallback(self):
        invalid = ([{'source_index': 99, 'target_field': 'name'}], [{'source_index': 0, 'target_field': 'workspace_id'}], [{'source_index': 0, 'target_field': 'name', 'expression': '1'}], [{'source_index': 0, 'target_field': 'name'}, {'source_index': 1, 'target_field': 'name'}])
        for mappings in invalid:
            with self.subTest(mappings=mappings):
                raw = json.dumps({'model': 'openai/gpt-oss-120b', 'choices': [{'message': {'content': json.dumps({'mappings': mappings})}, 'finish_reason': 'stop'}]}).encode()
                with patch('config.provider_http.open_provider_request', return_value=ResponseBytes(raw)):
                    response = self.client.post('/api/v1/mapping/ai-suggest/', self.schema_request(), format='json', **self.headers)
                self.assertEqual(response.data.get('provenance', {}).get('fallback_reason'), 'invalid_provider_response')

    def test_confirmation_tampering_foreign_profile_expiry_and_human_flag_denied(self):
        with override_settings(GROQ_API_KEY=''):
            response = self.client.post('/api/v1/mapping/ai-suggest/', self.schema_request(), format='json', **self.headers)
        token = response.data['suggestions'][0].get('confirmation_token', '')
        self.assertTrue(token)
        other = create_mapping_profile(self.ws, self.user, 'Other profile', 'Customer')
        requests = [(self.profile, {'confirmation_token': token + 'tamper', 'human_confirmed': True}), (other, {'confirmation_token': token, 'human_confirmed': True}), (self.profile, {'confirmation_token': token, 'human_confirmed': False}), (self.profile, {'confirmation_token': token, 'human_confirmed': True, 'transformation_config': {'expression': '1'}})]
        for profile, body in requests:
            with self.subTest(body=body):
                result = self.client.post(f'/api/v1/mapping/profiles/{profile.pk}/rules/', body, format='json', **self.headers)
                self.assertEqual(result.status_code, 400)
        with patch('django.core.signing.time.time', return_value=9999999999):
            result = self.client.post(f'/api/v1/mapping/profiles/{self.profile.pk}/rules/', {'confirmation_token': token, 'human_confirmed': True}, format='json', **self.headers)
        self.assertEqual(result.status_code, 400)
        self.assertFalse(MappingRule.objects.exists())

    @override_settings(GROQ_API_KEY='synthetic-provider-key')
    def test_provider_envelope_model_choices_and_tool_calls_are_rejected(self):
        choice = {'message': {'content': '{"mappings":[{"source_index":0,"target_field":"name"}]}'}, 'finish_reason': 'stop'}
        envelopes = [{'model': 'foreign-model', 'choices': [choice]}, {'model': 'openai/gpt-oss-120b', 'choices': [choice, choice]}]
        for tool_key in ('tool_calls', 'function_call'):
            envelopes.append({'model': 'openai/gpt-oss-120b', 'choices': [{**choice, 'message': {**choice['message'], tool_key: [{'name': 'execute'}]}}]})
        for envelope in envelopes:
            with self.subTest(envelope=envelope):
                with patch('config.provider_http.open_provider_request', return_value=ResponseBytes(json.dumps(envelope).encode())):
                    response = self.client.post('/api/v1/mapping/ai-suggest/', self.schema_request(), format='json', **self.headers)
                self.assertEqual(response.data['provenance']['fallback_reason'], 'invalid_provider_response')

    def test_nonempty_staging_schema_cannot_be_replaced_by_client_column_names(self):
        self.ingest()
        with override_settings(GROQ_API_KEY='synthetic-provider-key'), patch('config.provider_http.open_provider_request') as transport:
            response = self.client.post('/api/v1/mapping/ai-suggest/', self.schema_request(), format='json', **self.headers)
        self.assertEqual(response.status_code, 400)
        transport.assert_not_called()

    def test_pending_optional_rule_blocks_canonical_apply_even_with_required_fields(self):
        job = self.ingest()
        for source, target in (('code', 'customer_id'), ('name,extra', 'name')):
            add_mapping_rule(self.profile, self.user, source, target)
        add_mapping_rule(self.profile, self.user, 'segment', 'segment', ai_status=AIConfirmationStatus.PENDING)
        result = apply_mapping_to_domain(self.ws, self.user, self.profile, job, strict=True)
        self.assertEqual(result['status'], 'FAILED')
        self.assertFalse(Customer.objects.exists())

    def test_error_endpoint_and_preview_hide_nested_credentials(self):
        job = self.ingest()
        job.error_summary = [{'raw': {'nested': {'password': 'SYNTHETIC-SECRET'}}}]
        job.save(update_fields=['error_summary'])
        response = self.client.get(f'/api/v1/integration/import-jobs/{job.pk}/errors/', **self.headers)
        self.assertNotIn('SYNTHETIC-SECRET', json.dumps(response.data))

    def test_invalid_rule_config_is_rejected_before_persisting(self):
        response = self.client.post(f'/api/v1/mapping/profiles/{self.profile.pk}/rules/', {'source_field': 'code', 'target_field': 'customer_id', 'transformation_config': []}, format='json', **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(MappingRule.objects.exists())

    def test_signed_api_import_staging_confirmation_canonical_and_audit_e2e(self):
        response = self.client.post('/api/v1/integration/import-jobs/', {'data_source_id': str(self.source.pk), 'file': SimpleUploadedFile('synthetic.csv', b'customer_id|name\nSYNTHETIC2|Synthetic API Person\n')}, format='multipart', **self.headers)
        self.assertEqual(response.status_code, 201)
        job_id = response.data['data']['id']
        self.assertFalse(Customer.objects.exists())
        suggestion_response = self.client.post('/api/v1/mapping/ai-suggest/', {'target_entity': 'Customer', 'profile_id': str(self.profile.pk), 'source_columns': ['customer_id', 'name']}, format='json', **self.headers)
        self.assertEqual(suggestion_response.status_code, 200, suggestion_response.data)
        self.assertEqual(suggestion_response.data['provenance']['source_schema_binding'], 'CURRENT_STAGING_SCHEMA')
        for suggestion in suggestion_response.data['suggestions']:
            confirmed = self.client.post(f'/api/v1/mapping/profiles/{self.profile.pk}/rules/', {'confirmation_token': suggestion['confirmation_token'], 'human_confirmed': True}, format='json', **self.headers)
            self.assertEqual(confirmed.status_code, 201)
        applied = self.client.post('/api/v1/mapping/apply/', {'profile_id': str(self.profile.pk), 'import_job_id': job_id, 'strict': True}, format='json', **self.headers)
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.data['data']['inserted_count'], 1)
        self.assertEqual(Customer.objects.get(workspace=self.ws).name, 'Synthetic API Person')
        from apps.audit.models import AuditLog
        applied_audit = AuditLog.objects.get(action='MAPPING_APPLIED')
        self.assertEqual(applied_audit.changes['ingestion_provenance']['classification'], 'UNKNOWN')

    def test_legacy_receipt_is_read_only_unknown_not_inferred_from_label(self):
        job = self.ingest()
        job.source_metadata = {}
        job.save(update_fields=['source_metadata'])
        response = self.client.get(f'/api/v1/integration/import-jobs/{job.pk}/', **self.headers)
        self.assertEqual(response.data['data']['source_metadata'].get('ingestion_provenance', {}).get('classification'), 'UNKNOWN')
        job.refresh_from_db()
        self.assertEqual(job.source_metadata, {})

    def test_malformed_foreign_workspace_staging_never_leaks_through_discovery_or_preview(self):
        job = self.ingest()
        other = Workspace.objects.create(code='op-map-other', name='Other Synthetic TEST', workspace_type='RETAIL')
        job.raw_records.update(workspace=other)
        with self.assertRaises(PermissionDenied):
            generate_mapping_preview(self.ws, self.profile, import_job=job)
        from apps.mapping.services import discover_source_fields
        with self.assertRaises(PermissionDenied):
            discover_source_fields(data_source=self.source)

    def test_partial_apply_response_redacts_nested_credentials_and_echoed_validation_values(self):
        source = DataSource.objects.create(workspace=self.ws, name='Synthetic response protection', source_type='MOCK_API', connection_config={'url': 'https://configured.example/customers'})
        profile = create_mapping_profile(self.ws, self.user, 'Synthetic response protection', 'Customer', source)
        for field in ('customer_id', 'name', 'segment'):
            add_mapping_rule(profile, self.user, field, field)
        payload = [{'customer_id': 'SYNTHETIC-VALID', 'name': 'Visible legitimate', 'segment': 'STANDARD'}, {'customer_id': 'SYNTHETIC-INVALID', 'name': 'Visible invalid', 'segment': 'SYNTHETIC-APPLY-SECRET', 'nested': [{'password': 'SYNTHETIC-APPLY-SECRET'}]}]
        with patch('apps.integration.parsers.api_parser.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]), patch('apps.integration.parsers.api_parser.urllib.request.build_opener') as transport:
            transport.return_value.open.return_value = ResponseBytes(json.dumps(payload).encode())
            job = execute_import_job(self.ws, self.user, source)
        response = self.client.post('/api/v1/mapping/apply/', {'profile_id': str(profile.pk), 'import_job_id': str(job.pk), 'strict': False}, format='json', **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['status'], 'PARTIAL')
        self.assertEqual(response.data['data']['inserted_count'], 1)
        self.assertNotIn('SYNTHETIC-APPLY-SECRET', json.dumps(response.data))
        self.assertEqual(Customer.objects.get(workspace=self.ws).name, 'Visible legitimate')
        invalid = job.raw_records.get(row_number=2)
        self.assertEqual(invalid.raw_data['nested'][0]['password'], 'SYNTHETIC-APPLY-SECRET')
        from apps.audit.models import AuditLog
        self.assertNotIn('SYNTHETIC-APPLY-SECRET', str(list(AuditLog.objects.values_list('changes', flat=True))))


class OperationalPreviewCredentialBindingTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code='preview-boundary-test', name='Synthetic preview TEST', workspace_type='RETAIL')
        self.user = User.objects.create_user(username='preview-execute-only', email='preview-only@example.test')
        role = Role.objects.create(name='EMPLOYEE')
        permission, _ = Permission.objects.get_or_create(codename='integration.execute_import', defaults={'name': 'Execute import', 'module': 'integration'})
        role.permissions.add(permission)
        WorkspaceMembership.objects.create(workspace=self.ws, user=self.user, role=role, is_default=True)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.headers = {'HTTP_X_WORKSPACE_ID': str(self.ws.pk)}
        self.source = DataSource.objects.create(workspace=self.ws, name='Synthetic protected feed', source_type='MOCK_API', connection_config={
            'url': 'https://configured.example/orders', 'headers': {'Authorization': 'Bearer SYNTHETIC-STORED-SECRET'}, 'params': {'api_key': 'SYNTHETIC-STORED-SECRET', 'page': 1}})

    def test_execute_only_actor_cannot_override_registered_preview_endpoint(self):
        from apps.accounts.services import has_workspace_permission
        self.assertTrue(has_workspace_permission(self.user, self.ws, 'integration.execute_import'))
        self.assertFalse(has_workspace_permission(self.user, self.ws, 'integration.manage_datasource'))
        for endpoint in ('https://attacker.example/collect', 'https://configured.example/other-path', 'https://configured.example/orders?new=query'):
            with self.subTest(endpoint=endpoint), patch('apps.integration.parsers.api_parser.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]) as dns, patch('apps.integration.parsers.api_parser.urllib.request.build_opener') as transport:
                transport.return_value.open.return_value = ResponseBytes(b'[{"customer_id":"SYNTHETIC"}]')
                response = self.client.post('/api/v1/integration/imports/preview/', {'data_source_id': str(self.source.pk), 'endpoint_url': endpoint}, format='json', **self.headers)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.data['data']['is_valid'])
                self.assertNotIn('SYNTHETIC-STORED-SECRET', json.dumps(response.data))
                self.assertNotIn(endpoint, json.dumps(response.data))
                dns.assert_not_called()
                transport.assert_not_called()

    def test_same_source_preview_and_execute_preserve_configured_endpoint_and_options(self):
        from urllib.parse import urlsplit, parse_qs
        for action in ('preview', 'execute'):
            with self.subTest(action=action), patch('apps.integration.parsers.api_parser.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]), patch('apps.integration.parsers.api_parser.urllib.request.build_opener') as transport:
                transport.return_value.open.return_value = ResponseBytes(b'[{"customer_id":"SYNTHETIC"}]')
                if action == 'preview':
                    response = self.client.post('/api/v1/integration/imports/preview/', {'data_source_id': str(self.source.pk), 'endpoint_url': self.source.connection_config['url']}, format='json', **self.headers)
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.data['data']['is_valid'])
                    self.assertNotIn('SYNTHETIC-STORED-SECRET', json.dumps(response.data))
                else:
                    response = self.client.post('/api/v1/integration/import-jobs/', {'data_source_id': str(self.source.pk)}, format='json', **self.headers)
                    self.assertEqual(response.status_code, 201)
                    self.assertEqual(response.data['data']['total_rows'], 1)
                    self.assertNotIn('SYNTHETIC-STORED-SECRET', json.dumps(response.data))
                request = transport.return_value.open.call_args.args[0]
                self.assertEqual(urlsplit(request.full_url).hostname, 'configured.example')
                self.assertEqual(urlsplit(request.full_url).path, '/orders')
                self.assertEqual(parse_qs(urlsplit(request.full_url).query), {'api_key': ['SYNTHETIC-STORED-SECRET'], 'page': ['1']})
                self.assertEqual(request.get_header('Authorization'), 'Bearer SYNTHETIC-STORED-SECRET')

    def test_actual_preview_response_redacts_nested_credentials_and_echoed_values(self):
        payload = [{'customer_id': 'SYNTHETIC', 'name': 'Visible legitimate', 'nested': [{'password': 'SYNTHETIC-PREVIEW-SECRET'}], 'note': 'echo SYNTHETIC-PREVIEW-SECRET'}]
        with patch('apps.integration.parsers.api_parser.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]), patch('apps.integration.parsers.api_parser.urllib.request.build_opener') as transport:
            transport.return_value.open.return_value = ResponseBytes(json.dumps(payload).encode())
            response = self.client.post('/api/v1/integration/imports/preview/', {'data_source_id': str(self.source.pk)}, format='json', **self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['is_valid'])
        self.assertNotIn('SYNTHETIC-PREVIEW-SECRET', json.dumps(response.data))
        self.assertEqual(response.data['data']['sample_rows'][0]['raw_data']['name'], 'Visible legitimate')
        self.assertEqual(payload[0]['nested'][0]['password'], 'SYNTHETIC-PREVIEW-SECRET')
