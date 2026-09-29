from django.db import IntegrityError, transaction
from django.test import TestCase
from apps.accounts.models import User
from apps.workspaces.models import Workspace
from apps.approvals.models import ApprovalRequest
from apps.approvals.executor import execute_tool, process_approval_decision
from apps.approvals.registry import ToolPermissionDenied, ToolValidationError
from apps.retail.models import Branch, Category, Product, StockBalance, StockTransferStatus
from apps.retail.services import rollback_stock_transfer
from apps.audit.models import AuditLog
from apps.retail.models import Customer, Order
from apps.service_ops.models import Service, ServiceRequest, Employee
from django.utils import timezone


class ApprovalStateIntegrityTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code="approval-integrity", name="Retail", workspace_type="RETAIL")
        self.user = User.objects.create_superuser(username="admin-integrity", email="admin@example.com", password="test")
        self.params = {"promotion_name": "Test", "discount_pct": 10}

    def propose(self):
        result = execute_tool("create_promotion_request", self.ws, self.user, self.params, idempotency_key="stable-key")
        return ApprovalRequest.objects.get(pk=result["approval_request_id"])

    def test_unique_key_is_database_enforced(self):
        self.propose()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ApprovalRequest.objects.create(workspace=self.ws, requester=self.user, proposed_action="different", idempotency_key="stable-key")

    def test_same_key_cannot_change_payload(self):
        self.propose()
        with self.assertRaises(ToolValidationError):
            execute_tool("create_promotion_request", self.ws, self.user, {**self.params, "discount_pct": 90}, idempotency_key="stable-key")

    def test_rejected_proposal_cannot_be_replayed_or_stale_approved(self):
        request = self.propose()
        process_approval_decision(request, self.user, "REJECTED")
        with self.assertRaises(ToolValidationError):
            process_approval_decision(request, self.user, "APPROVED")
        with self.assertRaises(ToolValidationError):
            self.propose()
        self.assertEqual(ApprovalRequest.objects.count(), 1)

    def test_cached_result_requires_permission(self):
        request = self.propose()
        process_approval_decision(request, self.user, "APPROVED")
        outsider = User.objects.create_user(username="outsider", email="outsider@example.com")
        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(request, outsider, "APPROVED")

    def test_mutation_contract_rejects_unscoped_entity_before_approval(self):
        with self.assertRaises(ToolValidationError):
            execute_tool(
                "adjust_product_price",
                self.ws,
                self.user,
                {"product_id": 999999, "new_price": 1000},
            )
        self.assertFalse(ApprovalRequest.objects.filter(workspace=self.ws).exists())

    def test_mutation_contract_rejects_invalid_numeric_type(self):
        with self.assertRaises(ToolValidationError):
            execute_tool(
                "adjust_product_price",
                self.ws,
                self.user,
                {"product_id": "not-an-integer", "new_price": 1000},
            )

    def test_stock_transfer_approval_executes_and_can_be_compensated(self):
        category = Category.objects.create(workspace=self.ws, name="Hardware", code="HW")
        product = Product.objects.create(
            workspace=self.ws, category=category, sku="SKU-TRANSFER", name="Transfer laptop",
            unit_price=1000, cost_price=500, is_active=True,
        )
        source = Branch.objects.create(workspace=self.ws, code="SRC", name="Source", address="A", region="R")
        destination = Branch.objects.create(workspace=self.ws, code="DST", name="Destination", address="B", region="R")
        StockBalance.objects.create(workspace=self.ws, branch=source, product=product, quantity_on_hand=5)
        StockBalance.objects.create(workspace=self.ws, branch=destination, product=product, quantity_on_hand=1)

        proposal = execute_tool(
            "create_stock_transfer", self.ws, self.user,
            {"source_branch_id": source.id, "destination_branch_id": destination.id, "product_id": product.id, "quantity": 2},
            idempotency_key="transfer-approval-1",
        )
        approval = ApprovalRequest.objects.get(pk=proposal["approval_request_id"])
        result = process_approval_decision(approval, self.user, "APPROVED")
        self.assertEqual(result["status"], "EXECUTED")
        transfer = approval.__class__.objects.get(pk=approval.id).execution_result
        self.assertEqual(transfer["quantity"], 2)
        self.assertEqual(StockBalance.objects.get(branch=source, product=product).quantity_on_hand, 3)
        self.assertEqual(StockBalance.objects.get(branch=destination, product=product).quantity_on_hand, 3)

        # Replaying the approved proposal must return the cached execution
        # result and must not move stock a second time.
        replay = execute_tool(
            "create_stock_transfer", self.ws, self.user,
            {"source_branch_id": source.id, "destination_branch_id": destination.id, "product_id": product.id, "quantity": 2},
            idempotency_key="transfer-approval-1",
        )
        self.assertEqual(replay["status"], "EXECUTED")
        self.assertTrue(replay.get("idempotent_replay"))
        self.assertEqual(StockBalance.objects.get(branch=source, product=product).quantity_on_hand, 3)
        self.assertEqual(StockBalance.objects.get(branch=destination, product=product).quantity_on_hand, 3)

        from apps.retail.models import StockTransfer
        row = StockTransfer.objects.get(workspace=self.ws, idempotency_key="APPROVAL-%s" % approval.id)
        rollback_stock_transfer(row, self.user, "Test compensation")
        row.refresh_from_db()
        self.assertEqual(row.status, StockTransferStatus.ROLLED_BACK)
        self.assertEqual(StockBalance.objects.get(branch=source, product=product).quantity_on_hand, 5)
        self.assertEqual(StockBalance.objects.get(branch=destination, product=product).quantity_on_hand, 1)
        executed = AuditLog.objects.get(action="STOCK_TRANSFER_EXECUTED", entity_id=str(row.pk))
        compensated = AuditLog.objects.get(action="STOCK_TRANSFER_ROLLED_BACK", entity_id=str(row.pk))
        for event in (executed, compensated):
            self.assertEqual(event.actor_user_id, self.user.pk)
            self.assertEqual(event.workspace_id, self.ws.pk)
            self.assertIsNotNone(event.timestamp)
        self.assertEqual(executed.changes["before"], {"source_quantity": 5, "destination_quantity": 1})
        self.assertEqual(executed.changes["after"], {"source_quantity": 3, "destination_quantity": 3})
        self.assertEqual(compensated.changes["before"], executed.changes["after"])
        self.assertEqual(compensated.changes["after"], executed.changes["before"])

    def test_order_audit_matches_real_transition_and_replay(self):
        customer = Customer.objects.create(workspace=self.ws, code="C", name="Test")
        order = Order.objects.create(workspace=self.ws, customer=customer, order_number="O",
                                     order_date=timezone.now().date(), order_timestamp=timezone.now())
        result = execute_tool("update_order_status", self.ws, self.user,
                              {"order_id": order.pk, "new_status": "CONFIRMED"})
        req = ApprovalRequest.objects.get(pk=result["approval_request_id"])
        process_approval_decision(req, self.user, "APPROVED")
        process_approval_decision(req, self.user, "APPROVED")
        order.refresh_from_db()
        event = AuditLog.objects.get(action="MUTATION_EXECUTED", entity_id=str(req.pk))
        self.assertEqual(event.actor_user_id, self.user.pk)
        self.assertEqual(event.workspace_id, self.ws.pk)
        self.assertIsNotNone(event.timestamp)
        self.assertEqual(event.changes["result"]["old_status"], "PENDING")
        self.assertEqual(event.changes["result"]["new_status"], order.status)
        self.assertEqual(order.status, "CONFIRMED")

    def test_dispatch_audit_matches_assignment_and_replay(self):
        ws = Workspace.objects.create(code="service-audit", name="Service", workspace_type="SERVICE")
        customer = Customer.objects.create(workspace=ws, code="C", name="Test")
        service = Service.objects.create(workspace=ws, code="S", name="Test")
        employee = Employee.objects.create(workspace=ws, code="E", full_name="Tech")
        ticket = ServiceRequest.objects.create(workspace=ws, customer=customer, service=service,
                                               request_number="T", title="Test", description="Test")
        result = execute_tool("dispatch_technician", ws, self.user,
                              {"ticket_id": ticket.pk, "employee_id": employee.pk})
        req = ApprovalRequest.objects.get(pk=result["approval_request_id"])
        process_approval_decision(req, self.user, "APPROVED")
        process_approval_decision(req, self.user, "APPROVED")
        ticket.refresh_from_db()
        event = AuditLog.objects.get(action="TECHNICIAN_DISPATCHED", entity_id=str(ticket.pk))
        self.assertEqual(event.actor_user_id, self.user.pk)
        self.assertEqual(event.workspace_id, ws.pk)
        self.assertIsNotNone(event.timestamp)
        self.assertEqual(event.changes["before"], {"status": "OPEN", "assigned_employee_id": None})
        self.assertEqual(event.changes["after"], {"status": ticket.status, "assigned_employee_id": ticket.assigned_employee_id})
        self.assertEqual(ticket.status, "IN_PROGRESS")
        self.assertEqual(ticket.assigned_employee_id, employee.pk)
