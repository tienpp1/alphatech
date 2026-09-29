"""Concurrent PostgreSQL connections; real price mutation and injected failure."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.db import connection, connections, close_old_connections
from django.test import TransactionTestCase
from django.core.exceptions import PermissionDenied
from apps.accounts.models import User
from apps.workspaces.models import Workspace
from apps.retail.models import Product, Category
from apps.approvals.models import ApprovalRequest
from apps.approvals.registry import ToolRegistry, ToolValidationError, ToolPermissionDenied
from apps.approvals.executor import execute_tool, process_approval_decision
from apps.audit.models import AuditLog


class ApprovalConcurrencyEvidenceTests(TransactionTestCase):
    def setUp(self):
        self.assertEqual(connection.vendor, 'postgresql')
        self.ws = Workspace.objects.create(code='concurrency', name='Concurrency', workspace_type='RETAIL')
        self.user = User.objects.create_superuser(username='concurrency', email='test@example.com', password=None)
        category = Category.objects.create(workspace=self.ws, code='EVIDENCE', name='Test')
        self.product = Product.objects.create(workspace=self.ws, category=category, sku='EVIDENCE', name='Test', unit_price=100)
        self.params = {'product_id': self.product.pk, 'new_price': 120}

    def propose(self):
        return execute_tool('adjust_product_price', self.ws, self.user, self.params, idempotency_key='same-key')

    def parallel(self, operation):
        barrier = Barrier(2, timeout=15)
        def run():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '15s'")
                barrier.wait()
                return operation()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_simultaneous_proposals_create_one_record(self):
        results = self.parallel(self.propose)
        self.assertEqual(ApprovalRequest.objects.count(), 1)
        self.assertEqual(results[0]['approval_request_id'], results[1]['approval_request_id'])
        self.assertEqual(sum(bool(r.get('idempotent_replay')) for r in results), 1)
        self.assertEqual(AuditLog.objects.filter(action='APPROVAL_CREATED').count(), 1)

    def test_simultaneous_approval_executes_handler_once(self):
        req = ApprovalRequest.objects.get(pk=self.propose()['approval_request_id'])
        tool = ToolRegistry.get('adjust_product_price')
        with patch.object(tool, 'handler', wraps=tool.handler) as handler:
            results = self.parallel(lambda: process_approval_decision(req, self.user, 'APPROVED'))
            self.assertEqual(handler.call_count, 1)
        self.assertEqual(sum(bool(r.get('idempotent_replay')) for r in results), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.unit_price, 120)
        req.refresh_from_db()
        self.assertEqual(req.status, 'EXECUTED')
        event = AuditLog.objects.get(action='MUTATION_EXECUTED', entity_id=str(req.pk))
        self.assertEqual(event.actor_user_id, self.user.pk)
        self.assertEqual(event.workspace_id, self.ws.pk)
        self.assertIsNotNone(event.timestamp)
        self.assertEqual(event.changes['result']['product_id'], self.product.pk)
        self.assertEqual(event.changes['result']['old_price'], 100)
        self.assertEqual(event.changes['result']['new_price'], 120)

    def test_unauthorized_tool_records_denial_without_proposal(self):
        outsider = User.objects.create_user(username='outsider', password=None)
        with patch.object(ToolRegistry.get('adjust_product_price'), 'handler') as handler:
            with self.assertRaises(ToolPermissionDenied):
                execute_tool('adjust_product_price', self.ws, outsider, self.params)
            handler.assert_not_called()
        self.assertFalse(ApprovalRequest.objects.exists())
        event = AuditLog.objects.get(action='TOOL_PERMISSION_DENIED')
        self.assertEqual(event.actor_user_id, outsider.pk)
        self.assertEqual(event.workspace_id, self.ws.pk)
        self.assertEqual(event.changes, {'error_code': 'PERMISSION_DENIED'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.unit_price, 100)

    def test_unauthorized_review_records_denial_without_mutation(self):
        req = ApprovalRequest.objects.get(pk=self.propose()['approval_request_id'])
        outsider = User.objects.create_user(username='outsider', password=None)
        with patch.object(ToolRegistry.get('adjust_product_price'), 'handler') as handler:
            with self.assertRaises(ToolPermissionDenied):
                process_approval_decision(req, outsider, 'APPROVED')
            handler.assert_not_called()
        event = AuditLog.objects.get(action='APPROVAL_PERMISSION_DENIED')
        self.assertEqual(event.actor_user_id, outsider.pk)
        self.assertEqual(event.workspace_id, self.ws.pk)
        self.assertEqual(event.entity_id, str(req.pk))
        self.assertEqual(event.changes, {'approval_id': req.pk, 'error_code': 'PERMISSION_DENIED'})
        req.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(req.status, 'PENDING')
        self.assertEqual(self.product.unit_price, 100)
        self.assertFalse(AuditLog.objects.filter(action='MUTATION_EXECUTED').exists())

    def test_failure_after_write_rolls_back_then_retry_succeeds(self):
        req = ApprovalRequest.objects.get(pk=self.propose()['approval_request_id'])
        tool = ToolRegistry.get('adjust_product_price')
        real_handler = tool.handler
        def failing_handler(*args):
            real_handler(*args)
            raise RuntimeError('injected failure after domain write')
        with patch.object(tool, 'handler', side_effect=failing_handler):
            with self.assertRaises(ToolValidationError):
                process_approval_decision(req, self.user, 'APPROVED')
        self.product.refresh_from_db()
        req.refresh_from_db()
        self.assertEqual(self.product.unit_price, 100)
        self.assertEqual(req.status, 'PENDING')
        self.assertIsNone(req.executed_at)
        self.assertFalse(AuditLog.objects.filter(action='MUTATION_EXECUTED').exists())
        event = AuditLog.objects.get(action='MUTATION_FAILED', entity_id=str(req.pk))
        self.assertEqual(event.actor_user_id, self.user.pk)
        self.assertEqual(event.workspace_id, self.ws.pk)
        self.assertIsNotNone(event.timestamp)
        self.assertEqual(event.changes, {
            'approval_id': req.pk, 'error_code': 'HANDLER_EXECUTION_FAILED',
            'business_transaction': 'ROLLED_BACK',
        })
        result = process_approval_decision(req, self.user, 'APPROVED')
        self.assertEqual(result['status'], 'EXECUTED')
        self.product.refresh_from_db()
        self.assertEqual(self.product.unit_price, 120)
        self.assertEqual(AuditLog.objects.filter(action='MUTATION_EXECUTED').count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='MUTATION_FAILED').count(), 1)

    def test_database_error_audited_after_transaction_recovers(self):
        req = ApprovalRequest.objects.get(pk=self.propose()['approval_request_id'])
        def broken_sql(*args):
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1 / 0')
        with patch.object(ToolRegistry.get('adjust_product_price'), 'handler', side_effect=broken_sql):
            with self.assertRaises(ToolValidationError) as error:
                process_approval_decision(req, self.user, 'APPROVED')
        self.assertNotIn('division', str(error.exception))
        self.assertEqual(AuditLog.objects.filter(action='MUTATION_FAILED').count(), 1)
        req.refresh_from_db()
        self.assertEqual(req.status, 'PENDING')

    def test_permission_denied_is_not_converted_to_validation_error(self):
        req = ApprovalRequest.objects.get(pk=self.propose()['approval_request_id'])
        with patch.object(ToolRegistry.get('adjust_product_price'), 'handler', side_effect=PermissionDenied):
            with self.assertRaises(PermissionDenied):
                process_approval_decision(req, self.user, 'APPROVED')
        self.assertFalse(AuditLog.objects.filter(action='MUTATION_FAILED').exists())
        req.refresh_from_db()
        self.assertEqual(req.status, 'PENDING')
