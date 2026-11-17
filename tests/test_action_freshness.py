"""Synthetic PostGIS regressions for live action freshness; no providers."""
import datetime
from unittest.mock import patch
from dataclasses import replace
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from apps.accounts.models import User, Permission
from apps.workspaces.models import WorkspaceMembership
from apps.approvals.executor import execute_tool, process_approval_decision
from apps.approvals.models import ApprovalRequest
from apps.approvals.registry import ToolRegistry, ToolValidationError, ToolPermissionDenied
from apps.recommendations.models import Recommendation, RecommendationType
from apps.recommendations.rules import evaluate_service_recommendations
from apps.recommendations.services import accept_recommendation
from apps.service_ops.models import Task, Employee, ServiceRequest
from apps.service_ops.services import assign_service_request
from apps.audit.models import AuditLog
from tests import test_recommendations as recommendation_tests


class ActionFreshnessTests(TestCase):
    setUp = recommendation_tests.RecommendationEngineTests.setUp

    def generated_approval(self):
        now = timezone.now()
        ServiceRequest.objects.filter(pk=self.ticket.pk).update(
            location=Point(106.7, 10.775, srid=4326),
            response_deadline_at=now-datetime.timedelta(minutes=30))
        self.employee.current_location = Point(106.701, 10.775, srid=4326)
        self.employee.save()
        rec = next(r for r in evaluate_service_recommendations(self.workspace_service)
                   if r.recommendation_type == RecommendationType.SERVICE_NEARBY_TECHNICIAN)
        rec = accept_recommendation(rec, self.user_manager)
        perm, _ = Permission.objects.get_or_create(codename='approvals.manage_approval',
                                                   defaults={'name': 'Review', 'module': 'approvals'})
        self.role_manager.permissions.add(perm)
        reviewer = User.objects.create_user(username='TEST-independent', password=None)
        WorkspaceMembership.objects.create(user=reviewer, workspace=self.workspace_service, role=self.role_manager)
        return rec, rec.approval_request, reviewer

    def assert_blocked(self, approval, reviewer):
        with self.assertRaises(ToolValidationError):
            process_approval_decision(approval, reviewer, 'APPROVED')
        approval.refresh_from_db()
        self.ticket.refresh_from_db()
        self.assertEqual(approval.status, 'PENDING')
        self.assertIsNone(approval.executed_at)
        self.assertFalse(AuditLog.objects.filter(action='MUTATION_EXECUTED').exists())

    def test_generated_expired_evidence_blocks_independent_approval(self):
        rec, approval, reviewer = self.generated_approval()
        Recommendation.objects.filter(pk=rec.pk).update(expires_at=timezone.now()-datetime.timedelta(seconds=1))
        self.assert_blocked(approval, reviewer)
        self.assertFalse(Task.objects.exists())

    def test_generated_unavailable_employee_blocks_independent_approval(self):
        rec, approval, reviewer = self.generated_approval()
        Employee.objects.filter(pk=self.employee.pk).update(is_available=False)
        self.assert_blocked(approval, reviewer)
        self.assertFalse(Task.objects.exists())

    def test_generated_changed_workload_blocks_independent_approval(self):
        rec, approval, reviewer = self.generated_approval()
        Task.objects.create(service_request=self.ticket, assigned_to=self.employee, title='TEST changed workload')
        self.assert_blocked(approval, reviewer)

    def test_generated_changed_location_blocks_independent_approval(self):
        rec, approval, reviewer = self.generated_approval()
        Employee.objects.filter(pk=self.employee.pk).update(current_location=Point(106.71, 10.775, srid=4326))
        self.assert_blocked(approval, reviewer)

    def test_requester_revoked_after_acceptance_blocks_execution(self):
        rec, approval, reviewer = self.generated_approval()
        WorkspaceMembership.objects.filter(user=self.user_manager, workspace=self.workspace_service).update(is_active=False)
        self.assert_blocked(approval, reviewer)

    def test_reviewer_disabled_after_instance_load_is_denied(self):
        rec, approval, reviewer = self.generated_approval()
        User.objects.filter(pk=reviewer.pk).update(is_active=False)
        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(approval, reviewer, 'APPROVED')
        self.assertFalse(Task.objects.exists())

    def test_revoked_superuser_flag_cannot_keep_self_approval_exemption(self):
        rec, approval, reviewer = self.generated_approval()
        self.user_manager.is_superuser = True
        self.user_manager.save(update_fields=['is_superuser'])
        User.objects.filter(pk=self.user_manager.pk).update(is_superuser=False)
        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(approval, self.user_manager, 'APPROVED')
        self.assertFalse(Task.objects.exists())

    def test_generated_terminal_ticket_does_not_resurrect(self):
        rec, approval, reviewer = self.generated_approval()
        ServiceRequest.objects.filter(pk=self.ticket.pk).update(status='CLOSED')
        self.assert_blocked(approval, reviewer)
        self.assertEqual(self.ticket.status, 'CLOSED')

    def test_changed_linked_parameters_cannot_execute(self):
        rec, approval, reviewer = self.generated_approval()
        Recommendation.objects.filter(pk=rec.pk).update(proposed_parameters={'ticket_id': self.ticket.pk, 'employee_id': 999999})
        self.assert_blocked(approval, reviewer)

    def test_pending_accepted_dispatch_is_not_generated_twice(self):
        rec, approval, reviewer = self.generated_approval()
        evaluate_service_recommendations(self.workspace_service)
        self.assertEqual(Recommendation.objects.filter(recommendation_type=RecommendationType.SERVICE_NEARBY_TECHNICIAN).count(), 1)

    def test_dispatch_preserves_completed_task_and_sets_canonical_timestamps(self):
        rec, approval, reviewer = self.generated_approval()
        old = Task.objects.create(service_request=self.ticket, assigned_to=self.employee,
                                  title='TEST completed history', status='COMPLETED')
        result = process_approval_decision(approval, reviewer, 'APPROVED')
        old.refresh_from_db()
        self.ticket.refresh_from_db()
        self.employee.refresh_from_db()
        self.assertEqual(old.status, 'COMPLETED')
        self.assertNotEqual(result['result']['task_id'], old.pk)
        self.assertIsNotNone(self.ticket.responded_at)
        live = Task.objects.get(pk=result['result']['task_id'])
        self.assertEqual(live.status, 'IN_PROGRESS')
        self.assertIsNotNone(live.started_at)
        self.assertGreaterEqual(self.employee.current_workload_score, 1)
        self.assertTrue(AuditLog.objects.filter(action='REQUEST_ASSIGNED').exists())
        self.assertTrue(AuditLog.objects.filter(action='TASK_STATUS_CHANGED').exists())

    def test_canonical_assignment_reloads_terminal_ticket(self):
        ServiceRequest.objects.filter(pk=self.ticket.pk).update(status='CLOSED')
        with self.assertRaises(ValidationError):
            assign_service_request(self.ticket, self.employee, self.user_manager)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'CLOSED')

    def test_canonical_assignment_reloads_employee_availability(self):
        Employee.objects.filter(pk=self.employee.pk).update(is_available=False)
        with self.assertRaises(ValidationError):
            assign_service_request(self.ticket, self.employee, self.user_manager)

    def test_read_reclassified_contract_cannot_execute_as_mutation(self):
        rec, approval, reviewer = self.generated_approval()
        definition = ToolRegistry.get('dispatch_technician')
        try:
            ToolRegistry.register(replace(definition, classification='READ'))
            self.assert_blocked(approval, reviewer)
        finally:
            ToolRegistry.register(definition)

    def test_current_queues_exclude_stale_without_get_writes(self):
        rec, approval, reviewer = self.generated_approval()
        Recommendation.objects.filter(pk=rec.pk).update(expires_at=timezone.now()-datetime.timedelta(seconds=1))
        for codename in ('approvals.view_approval', 'recommendations.view_recommendation'):
            perm, _ = Permission.objects.get_or_create(codename=codename, defaults={'name': codename, 'module': codename.split('.')[0]})
            self.role_manager.permissions.add(perm)
        self.client.force_authenticate(user=reviewer)
        for path in ('approvals', 'recommendations'):
            suffix = f'&recommendation_type={RecommendationType.SERVICE_NEARBY_TECHNICIAN}' if path == 'recommendations' else ''
            current = self.client.get(f'/api/v1/{path}/?queue=current{suffix}', HTTP_X_WORKSPACE_ID=str(self.workspace_service.pk))
            self.assertEqual(current.status_code, 200)
            self.assertEqual(current.data['data'], [])
            history = self.client.get(f'/api/v1/{path}/?queue=history{suffix}', HTTP_X_WORKSPACE_ID=str(self.workspace_service.pk))
            self.assertEqual(len(history.data['data']), 1)
            self.assertTrue(history.data['data'][0]['review_state']['stale'])
        approval.refresh_from_db()
        rec.refresh_from_db()
        self.assertEqual(approval.status, 'PENDING')
        self.assertEqual(rec.status, 'ACCEPTED')

    def test_executed_transfer_replays_after_source_stock_depleted(self):
        from apps.retail.models import Branch, Category, Product, StockBalance
        perm, _ = Permission.objects.get_or_create(codename='retail.manage_product', defaults={'name': 'Stock', 'module': 'retail'})
        review, _ = Permission.objects.get_or_create(codename='approvals.manage_approval', defaults={'name': 'Review', 'module': 'approvals'})
        self.role_manager.permissions.add(perm, review)
        reviewer = User.objects.create_user(username='TEST-stock-reviewer', password=None)
        WorkspaceMembership.objects.create(user=reviewer, workspace=self.workspace_retail, role=self.role_manager)
        source = Branch.objects.create(workspace=self.workspace_retail, code='TEST-A', name='TEST source')
        target = Branch.objects.create(workspace=self.workspace_retail, code='TEST-B', name='TEST destination')
        category = Category.objects.create(workspace=self.workspace_retail, code='TEST-CAT', name='TEST category')
        product = Product.objects.create(workspace=self.workspace_retail, category=category, sku='TEST-REPLAY', name='TEST replay', unit_price=10)
        stock = StockBalance.objects.create(workspace=self.workspace_retail, branch=source, product=product, quantity_on_hand=3)
        payload = {'source_branch_id': source.pk, 'destination_branch_id': target.pk, 'product_id': product.pk, 'quantity': 2}
        created = execute_tool('create_stock_transfer', self.workspace_retail, self.user_manager, payload, 'TEST-transfer')
        approval = ApprovalRequest.objects.get(pk=created['approval_request_id'])
        original = process_approval_decision(approval, reviewer, 'APPROVED')
        stock.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 1)
        replay = execute_tool('create_stock_transfer', self.workspace_retail, self.user_manager, payload, 'TEST-transfer')
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(replay['result'], original['result'])
        with self.assertRaises(ToolValidationError):
            execute_tool('create_stock_transfer', self.workspace_retail, self.user_manager, {**payload, 'quantity': 1}, 'TEST-transfer')
        with self.assertRaises(ToolValidationError):
            execute_tool('create_stock_transfer', self.workspace_retail, reviewer, payload, 'TEST-transfer')


class GeneratedDispatchConcurrencyTests(TransactionTestCase):
    setUp = recommendation_tests.RecommendationEngineTests.setUp
    generated_approval = ActionFreshnessTests.generated_approval

    def parallel(self, operation):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connection, connections, close_old_connections
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

    def test_generated_dispatch_concurrent_independent_review_executes_once(self):
        rec, approval, reviewer = self.generated_approval()
        results = self.parallel(lambda: process_approval_decision(approval, reviewer, 'APPROVED'))
        self.assertEqual(sum(bool(row.get('idempotent_replay')) for row in results), 1)
        self.assertEqual(Task.objects.filter(service_request=self.ticket).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='MUTATION_EXECUTED', entity_id=str(approval.pk)).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='TECHNICIAN_DISPATCHED').count(), 1)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'IN_PROGRESS')
        self.assertIsNotNone(self.ticket.responded_at)

    def test_concurrent_service_rule_generation_creates_one_live_dispatch(self):
        ServiceRequest.objects.filter(pk=self.ticket.pk).update(
            location=Point(106.7, 10.775, srid=4326),
            response_deadline_at=timezone.now()-datetime.timedelta(minutes=30))
        Employee.objects.filter(pk=self.employee.pk).update(current_location=Point(106.701, 10.775, srid=4326))
        results = self.parallel(lambda: evaluate_service_recommendations(self.workspace_service))
        self.assertEqual(sum(len(rows) for rows in results), 2)
        self.assertEqual(Recommendation.objects.filter(recommendation_type=RecommendationType.SERVICE_NEARBY_TECHNICIAN).count(), 1)

    def test_generated_canonical_audit_failure_rolls_back_mutation_and_retains_failure_audit(self):
        rec, approval, reviewer = self.generated_approval()
        from apps.service_ops.services import log_action
        def fail_after_assignment(**kwargs):
            if kwargs.get('action') == 'REQUEST_STATUS_CHANGED':
                raise RuntimeError('TEST injected canonical audit failure')
            return log_action(**kwargs)
        with patch('apps.service_ops.services.log_action', side_effect=fail_after_assignment):
            with self.assertRaises(ToolValidationError):
                process_approval_decision(approval, reviewer, 'APPROVED')
        approval.refresh_from_db()
        self.ticket.refresh_from_db()
        self.employee.refresh_from_db()
        self.assertEqual(approval.status, 'PENDING')
        self.assertEqual(self.ticket.status, 'OPEN')
        self.assertIsNone(self.ticket.responded_at)
        self.assertIsNone(self.ticket.assigned_employee_id)
        self.assertEqual(self.employee.current_workload_score, 0)
        self.assertFalse(Task.objects.exists())
        self.assertFalse(AuditLog.objects.filter(action='REQUEST_ASSIGNED').exists())
        self.assertFalse(AuditLog.objects.filter(action='MUTATION_EXECUTED').exists())
        self.assertEqual(AuditLog.objects.filter(action='MUTATION_FAILED', entity_id=str(approval.pk)).count(), 1)

    def test_task_completion_and_reassignment_share_lock_order_without_deadlock(self):
        """Events expose the former Task→Employee / Employee→Task ABBA."""
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from django.db import connection, connections, close_old_connections
        from apps.service_ops.services import transition_task_status
        ServiceRequest.objects.filter(pk=self.ticket.pk).update(
            status='IN_PROGRESS', assigned_employee=self.employee)
        task = Task.objects.create(service_request=self.ticket, assigned_to=self.employee,
                                   title='TEST completing concurrently', status='IN_PROGRESS')
        task_locked, assignment_lock_attempt = Event(), Event()
        def complete():
            close_old_connections()
            def observe(execute, sql, params, many, context):
                result = execute(sql, params, many, context)
                if 'FOR UPDATE' in sql and Task._meta.db_table in sql and not task_locked.is_set():
                    task_locked.set()
                    if not assignment_lock_attempt.wait(10):
                        raise AssertionError('Assignment did not reach competing lock')
                return result
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '15s'")
                with connection.execute_wrapper(observe):
                    return transition_task_status(task, 'COMPLETED', self.user_manager).pk
            finally:
                connections.close_all()
        def reassign():
            close_old_connections()
            if not task_locked.wait(10):
                raise AssertionError('Completion did not lock task')
            def observe(execute, sql, params, many, context):
                if ('FOR UPDATE' in sql or 'FOR NO KEY UPDATE' in sql) and (Task._meta.db_table in sql or
                                            self.workspace_service._meta.db_table in sql):
                    assignment_lock_attempt.set()
                return execute(sql, params, many, context)
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '15s'")
                with connection.execute_wrapper(observe):
                    return assign_service_request(self.ticket, self.employee, self.user_manager).pk
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            completed = pool.submit(complete)
            reassigned = pool.submit(reassign)
            self.assertEqual(completed.result(timeout=25), task.pk)
            self.assertEqual(reassigned.result(timeout=25), self.ticket.pk)
        task.refresh_from_db()
        self.employee.refresh_from_db()
        self.assertEqual(task.status, 'COMPLETED')
        self.assertEqual(Task.objects.filter(service_request=self.ticket, status='PENDING').count(), 1)
        self.assertEqual(self.employee.current_workload_score, 1)
        self.assertEqual(AuditLog.objects.filter(action='TASK_STATUS_CHANGED', entity_id=str(task.pk)).count(), 1)

    def test_approval_transfer_and_rollback_lock_balances_in_shared_branch_order(self):
        """PK order deliberately opposes branch order; real SQL/mutations."""
        import re
        from django.db import connection, transaction
        from apps.approvals.registry import lock_action_resources
        from apps.retail.models import Branch, Category, Product, StockBalance, StockTransfer
        from apps.retail.services import execute_stock_transfer, rollback_stock_transfer
        source = Branch.objects.create(workspace=self.workspace_retail, code='TEST-LOCK-A', name='TEST source')
        destination = Branch.objects.create(workspace=self.workspace_retail, code='TEST-LOCK-B', name='TEST destination')
        category = Category.objects.create(workspace=self.workspace_retail, code='TEST-LOCK', name='TEST')
        product = Product.objects.create(workspace=self.workspace_retail, category=category,
                                         sku='TEST-LOCK', name='TEST', unit_price=10)
        dest_stock = StockBalance.objects.create(workspace=self.workspace_retail, branch=destination,
                                                 product=product, quantity_on_hand=0)
        source_stock = StockBalance.objects.create(workspace=self.workspace_retail, branch=source,
                                                   product=product, quantity_on_hand=3)
        self.assertLess(source.pk, destination.pk)
        self.assertGreater(source_stock.pk, dest_stock.pk)
        payload = {'source_branch_id': source.pk, 'destination_branch_id': destination.pk,
                   'product_id': product.pk, 'quantity': 2, 'idempotency_key': 'TEST-LOCK-TRANSFER'}
        orders, transfer_locks = [], []
        def observe(execute, sql, params, many, context):
            if StockBalance._meta.db_table in sql and 'FOR UPDATE' in sql:
                orders.append(re.search(r'ORDER BY (.*?) FOR UPDATE', sql).group(1))
            if StockTransfer._meta.db_table in sql and 'FOR UPDATE' in sql:
                transfer_locks.append(sql.rsplit(' FOR UPDATE', 1)[1])
            return execute(sql, params, many, context)
        with connection.execute_wrapper(observe):
            with transaction.atomic():
                lock_action_resources('create_stock_transfer', self.workspace_retail, payload)
            transfer = execute_stock_transfer(self.workspace_retail, self.user_manager, payload)
            rollback_stock_transfer(transfer, self.user_manager, 'TEST lock-order regression')
        self.assertEqual(len(orders), 3)
        self.assertEqual(orders[0], orders[1])
        self.assertEqual(orders[0], orders[2])
        self.assertIn('branch_id', orders[0])
        self.assertEqual(transfer_locks, [' OF "retail_stocktransfer"'])
        source_stock.refresh_from_db()
        dest_stock.refresh_from_db()
        self.assertEqual(source_stock.quantity_on_hand, 3)
        self.assertEqual(dest_stock.quantity_on_hand, 0)

    def test_direct_transfer_and_approval_do_not_deadlock_workspace_foreign_keys(self):
        """Balances held first by canonical retail; approval holds workspace."""
        from apps.retail.models import StockTransfer
        reviewer, stock, destination, payload = self.stock_transfer_review_fixture('retail.manage_product')
        proposed = execute_tool('create_stock_transfer', self.workspace_retail, self.user_manager,
                                payload, 'TEST-FK-APPROVAL')
        approval = ApprovalRequest.objects.get(pk=proposed['approval_request_id'])
        direct_id, result = self.run_transfer_during_stock_review(approval, reviewer, payload)
        self.assertEqual(result['status'], 'EXECUTED')
        self.assertNotEqual(direct_id, result['result']['transfer_id'])
        self.assertEqual(StockTransfer.objects.for_workspace(self.workspace_retail).count(), 2)
        stock.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(stock.quantity_on_hand, 1)
        self.assertEqual(destination.quantity_on_hand, 2)
        self.assertEqual(AuditLog.objects.filter(action='STOCK_TRANSFER_EXECUTED').count(), 2)
        self.assertEqual(AuditLog.objects.filter(action='MUTATION_EXECUTED').count(), 1)
        replay = process_approval_decision(approval, reviewer, 'APPROVED')
        self.assertTrue(replay['idempotent_replay'])
        self.assertEqual(StockTransfer.objects.for_workspace(self.workspace_retail).count(), 2)

    def test_direct_transfer_and_approved_cancellation_do_not_deadlock_workspace_foreign_keys(self):
        from apps.retail.models import OrderItem, OrderStatus
        reviewer, stock, destination, payload = self.stock_transfer_review_fixture('retail.manage_order')
        order = self.make_retail_order(branch=stock.branch, fulfillment_stock_reserved=True)
        OrderItem.objects.create(order=order, product=stock.product, quantity=2, unit_price=10, subtotal=20)
        proposed = execute_tool('update_order_status', self.workspace_retail, self.user_manager,
                                {'order_id': order.pk, 'new_status': OrderStatus.CANCELLED},
                                'TEST-FK-CANCELLATION')
        approval = ApprovalRequest.objects.get(pk=proposed['approval_request_id'])

        direct_id, result = self.run_transfer_during_stock_review(approval, reviewer, payload)

        self.assertIsNotNone(direct_id)
        self.assertEqual(result['status'], 'EXECUTED')
        order.refresh_from_db()
        stock.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertIsNotNone(order.fulfillment_stock_released_at)
        self.assertEqual(stock.quantity_on_hand, 4)
        self.assertEqual(destination.quantity_on_hand, 1)
        for action in ('STOCK_TRANSFER_EXECUTED', 'ORDER_FULFILLMENT_STOCK_RELEASED',
                       'ORDER_CANCELLED', 'MUTATION_EXECUTED'):
            self.assertEqual(AuditLog.objects.filter(workspace=self.workspace_retail, action=action).count(), 1)

    def test_order_transition_for_update_locks_only_order(self):
        from django.db import connection
        from apps.retail.models import OrderStatus
        from apps.retail.services import transition_order_status
        order = self.make_retail_order()
        order_locks = []

        def observe(execute, sql, params, many, context):
            if order._meta.db_table in sql and ' FOR UPDATE' in sql:
                order_locks.append(sql.rsplit(' FOR UPDATE', 1)[1])
            return execute(sql, params, many, context)

        with connection.execute_wrapper(observe):
            transitioned = transition_order_status(order, OrderStatus.CONFIRMED, self.user_manager)
        self.assertEqual(transitioned.status, OrderStatus.CONFIRMED)
        self.assertEqual(order_locks, [' OF "retail_order"'])

    def make_retail_order(self, **kwargs):
        from apps.retail.models import Customer, Order
        customer = Customer.objects.create(workspace=self.workspace_retail, code='TEST-ORDER',
                                           name='TEST customer')
        return Order.objects.create(workspace=self.workspace_retail, customer=customer,
                                    order_number='TEST-ORDER', order_date=timezone.localdate(),
                                    order_timestamp=timezone.now(), **kwargs)

    def stock_transfer_review_fixture(self, capability):
        from apps.retail.models import Branch, Category, Product, StockBalance
        for code in (capability, 'approvals.manage_approval'):
            permission, _ = Permission.objects.get_or_create(codename=code,
                defaults={'name': code, 'module': code.split('.')[0]})
            self.role_manager.permissions.add(permission)
        reviewer = User.objects.create_user(username='TEST-fk-reviewer', password=None)
        WorkspaceMembership.objects.create(user=reviewer, workspace=self.workspace_retail, role=self.role_manager)
        source = Branch.objects.create(workspace=self.workspace_retail, code='TEST-FK-A', name='TEST source')
        target = Branch.objects.create(workspace=self.workspace_retail, code='TEST-FK-B', name='TEST target')
        category = Category.objects.create(workspace=self.workspace_retail, code='TEST-FK', name='TEST')
        product = Product.objects.create(workspace=self.workspace_retail, category=category,
                                         sku='TEST-FK', name='TEST', unit_price=10)
        stock = StockBalance.objects.create(workspace=self.workspace_retail, branch=source,
                                            product=product, quantity_on_hand=3)
        destination = StockBalance.objects.create(workspace=self.workspace_retail, branch=target,
                                                  product=product, quantity_on_hand=0)
        payload = {'source_branch_id': source.pk, 'destination_branch_id': target.pk,
                   'product_id': product.pk, 'quantity': 1}
        return reviewer, stock, destination, payload

    def run_transfer_during_stock_review(self, approval, reviewer, payload):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from django.db import connection, connections, close_old_connections, transaction
        from apps.retail.models import StockBalance
        from apps.retail.services import execute_stock_transfer
        balances_locked, approval_waiting_for_stock = Event(), Event()

        def locks_stock(sql):
            return StockBalance._meta.db_table in sql and ' FOR UPDATE' in sql

        def direct():
            close_old_connections()
            def observe(execute, sql, params, many, context):
                result = execute(sql, params, many, context)
                if locks_stock(sql):
                    balances_locked.set()
                    if not approval_waiting_for_stock.wait(10):
                        raise AssertionError('Approval did not reach the competing stock lock')
                return result
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '15s'")
                with connection.execute_wrapper(observe), transaction.atomic():
                    transfer = execute_stock_transfer(self.workspace_retail, self.user_manager,
                                                      {**payload, 'idempotency_key': 'TEST-FK-DIRECT'})
                    # Exercise the actual deferred workspace/requester audit FK
                    # checks while holding balance locks, before outer commit.
                    with connection.cursor() as cursor:
                        cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
                    return transfer.pk
            finally:
                connections.close_all()
        def review():
            close_old_connections()
            if not balances_locked.wait(10):
                raise AssertionError('Direct transfer did not lock balances')
            def observe(execute, sql, params, many, context):
                # Once this statement starts, approval already holds the
                # workspace and any Order locks, but direct still owns stock.
                if locks_stock(sql):
                    approval_waiting_for_stock.set()
                return execute(sql, params, many, context)
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '10s'")
                    cursor.execute("SET statement_timeout = '15s'")
                with connection.execute_wrapper(observe):
                    return process_approval_decision(approval, reviewer, 'APPROVED')
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            direct_result = pool.submit(direct)
            reviewed = pool.submit(review)
            return direct_result.result(timeout=25), reviewed.result(timeout=25)
