"""
tests.test_audit_trail_evidence
Empirical verification of the AuditLog append-only trail, before/after state snapshots,
actor/workspace provenance, and permission-denial auditing across domain operations.

Fulfills Checklist 97 Gate 67 & Gate 78 requirements.
"""

from decimal import Decimal
from datetime import timedelta
import uuid
from django.db import connection, DatabaseError, transaction
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.audit.models import AuditLog, ActorType
from apps.retail.models import (
    Category,
    Product,
    Branch,
    Customer,
    CustomerSegment,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    StockBalance,
    StockTransfer,
    StockTransferStatus,
    Supplier,
)
from apps.retail.services import (
    create_category,
    update_category,
    delete_category,
    create_supplier,
    update_supplier,
    delete_supplier,
    execute_stock_transfer,
    rollback_stock_transfer,
    transition_order_status,
)
from apps.service_ops.models import (
    Service,
    ServiceCategory,
    Employee,
    SLA,
    SLAPriority,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceRequestPriority,
    Task,
    TaskStatus,
    Schedule,
    ScheduleStatus,
    LaborEntry,
)
from apps.service_ops.services import (
    create_task,
    transition_task_status,
    create_schedule,
    create_labor_entry,
)
from apps.approvals.models import ApprovalRequest, ApprovalStatus, RiskLevel
from apps.approvals.executor import process_approval_decision
from apps.approvals.registry import ToolPermissionDenied


class AuditTrailEvidenceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Retail Workspace & User
        cls.retail_ws = Workspace.objects.create(
            name="ABC Tech Retail",
            code="abc-tech-audit",
            workspace_type=WorkspaceType.RETAIL,
        )
        cls.retail_admin = User.objects.create_user(
            username="retail_audit_admin",
            email="retail_admin@test.com",
            password="Password123!",
            is_superuser=True,
        )

        # 2. Service Workspace & User
        cls.service_ws = Workspace.objects.create(
            name="XYZ IT Services",
            code="xyz-it-audit",
            workspace_type=WorkspaceType.SERVICE,
        )
        cls.service_admin = User.objects.create_user(
            username="service_audit_admin",
            email="service_admin@test.com",
            password="Password123!",
            is_superuser=True,
        )

        # Regular user without management permissions
        cls.regular_user = User.objects.create_user(
            username="regular_viewer",
            email="viewer@test.com",
            password="Password123!",
            is_superuser=False,
        )

        # Retail Entities
        cls.branch_a = Branch.objects.create(
            workspace=cls.retail_ws,
            code="BR-AUDIT-A",
            name="Audit Branch A",
            address="123 Le Loi, Q1, HCMC",
            is_active=True,
        )
        cls.branch_b = Branch.objects.create(
            workspace=cls.retail_ws,
            code="BR-AUDIT-B",
            name="Audit Branch B",
            address="456 Nguyen Hue, Q1, HCMC",
            is_active=True,
        )
        cls.category = Category.objects.create(
            workspace=cls.retail_ws,
            name="Laptop Doanh Nghiep",
            code="LAPTOP-CORP-AUDIT",
        )
        cls.product = Product.objects.create(
            workspace=cls.retail_ws,
            category=cls.category,
            sku="LAPTOP-AUDIT-01",
            name="Laptop ThinkPad T14s Audit",
            unit_price=Decimal("28000000.00"),
            cost_price=Decimal("23000000.00"),
            is_active=True,
        )
        cls.customer = Customer.objects.create(
            workspace=cls.retail_ws,
            code="CUST-AUDIT-01",
            name="Doan Kiem Toan Alpha",
            phone="0909112233",
            customer_segment=CustomerSegment.STANDARD,
        )

        # Service Entities
        cls.service_customer = Customer.objects.create(
            workspace=cls.service_ws,
            code="CUST-SRV-AUDIT",
            name="Cong ty Kiem Toan Doc Lap",
            phone="0911223344",
            customer_segment=CustomerSegment.STANDARD,
        )
        cls.employee = Employee.objects.create(
            workspace=cls.service_ws,
            user=cls.service_admin,
            code="EMP-AUDIT-01",
            full_name="Ky Su Kiem Toan",
            hourly_labor_rate=Decimal("350000.00"),
            is_active=True,
        )
        cls.service_sla = SLA.objects.create(
            workspace=cls.service_ws,
            name="Standard Audit SLA",
            response_time_hours=2,
            resolution_time_hours=8,
            priority=SLAPriority.MEDIUM,
        )
        cls.service = Service.objects.create(
            workspace=cls.service_ws,
            code="SRV-MAINT-AUDIT",
            name="Bao tri dinh ky he thong may chu",
            category=ServiceCategory.MAINTENANCE,
            standard_duration_minutes=120,
            base_fee=Decimal("1000000.00"),
        )
        cls.service_req = ServiceRequest.objects.create(
            workspace=cls.service_ws,
            request_number="SR-AUDIT-0001",
            customer=cls.service_customer,
            service=cls.service,
            sla=cls.service_sla,
            assigned_employee=cls.employee,
            title="Bao tri dinh ky he thong may chu",
            description="Kiem tra logs va bao tri dinh ky",
            priority=ServiceRequestPriority.MEDIUM,
            status=ServiceRequestStatus.OPEN,
        )
        cls.task = Task.objects.create(
            service_request=cls.service_req,
            title="Kiem tra o dia va nguon du phong",
            status=TaskStatus.PENDING,
            estimated_duration_minutes=120,
        )

    # -------------------------------------------------------------------------
    # 1. Service Ops: Labor Entry Audit with Server-side Computed Cost
    # -------------------------------------------------------------------------
    def test_labor_entry_creation_audit_snapshot(self):
        started_at = timezone.now() - timedelta(minutes=90)
        ended_at = timezone.now()
        data = {
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_minutes": 90,
            "notes": "Hoan thanh kiem tra nguon du phong",
        }

        entry = create_labor_entry(self.task, self.employee, self.service_admin, data)
        self.assertIsNotNone(entry.pk)

        # Verify AuditLog created
        audit = AuditLog.objects.filter(
            workspace=self.service_ws,
            action="LABOR_ENTRY_CREATED",
            entity_type="LaborEntry",
            entity_id=str(entry.id),
        ).first()

        self.assertIsNotNone(audit, "AuditLog for LABOR_ENTRY_CREATED must exist")
        self.assertEqual(audit.actor_user, self.service_admin)
        self.assertEqual(audit.actor_type, ActorType.USER)
        self.assertIsNotNone(audit.timestamp)

        # Verify changes payload
        changes = audit.changes
        self.assertEqual(changes["task_id"], str(self.task.id))
        self.assertEqual(changes["employee_id"], str(self.employee.id))
        self.assertEqual(changes["duration_minutes"], 90)
        self.assertEqual(changes["hourly_rate_snapshot"], "350000.00")
        # 90 mins = 1.5 hrs * 350000 = 525000.00
        self.assertEqual(changes["labor_cost"], "525000.00")

    # -------------------------------------------------------------------------
    # 2. Service Ops: Schedule Creation Audit
    # -------------------------------------------------------------------------
    def test_schedule_creation_audit_snapshot(self):
        start_time = timezone.now() + timedelta(days=1, hours=9)
        end_time = timezone.now() + timedelta(days=1, hours=11)
        data = {
            "start_time": start_time,
            "end_time": end_time,
            "notes": "Lich bao tri may chu phong Lab",
        }

        schedule = create_schedule(self.task, self.employee, self.service_admin, data)
        self.assertIsNotNone(schedule.pk)

        audit = AuditLog.objects.filter(
            workspace=self.service_ws,
            action="SCHEDULE_CREATED",
            entity_type="Schedule",
            entity_id=str(schedule.id),
        ).first()

        self.assertIsNotNone(audit, "AuditLog for SCHEDULE_CREATED must exist")
        self.assertEqual(audit.actor_user, self.service_admin)
        self.assertEqual(audit.changes["task_id"], str(self.task.id))
        self.assertEqual(audit.changes["employee_id"], str(self.employee.id))
        self.assertIn("start_time", audit.changes)
        self.assertIn("end_time", audit.changes)

    # -------------------------------------------------------------------------
    # 3. Service Ops: Task Lifecycle Audit (Before / After Snapshot)
    # -------------------------------------------------------------------------
    def test_task_status_transition_before_after_snapshot(self):
        task = Task.objects.create(
            service_request=self.service_req,
            title="Kiem tra luu tru SAN",
            status=TaskStatus.PENDING,
            assigned_to=self.employee,
        )

        # Transition to IN_PROGRESS
        transition_task_status(task, TaskStatus.IN_PROGRESS, self.service_admin)
        task.refresh_from_db()

        in_prog_audit = AuditLog.objects.filter(
            workspace=self.service_ws,
            action="TASK_STATUS_CHANGED",
            entity_type="Task",
            entity_id=str(task.id),
        ).first()

        self.assertIsNotNone(in_prog_audit)
        self.assertEqual(in_prog_audit.changes["before"]["status"], TaskStatus.PENDING)
        self.assertEqual(in_prog_audit.changes["after"]["status"], TaskStatus.IN_PROGRESS)
        self.assertIsNotNone(in_prog_audit.changes["after"]["started_at"])

        # Transition to COMPLETED
        transition_task_status(task, TaskStatus.COMPLETED, self.service_admin, actual_duration_minutes=75)
        task.refresh_from_db()

        completed_audit = AuditLog.objects.filter(
            workspace=self.service_ws,
            action="TASK_STATUS_CHANGED",
            entity_type="Task",
            entity_id=str(task.id),
        ).order_by("-timestamp").first()

        self.assertIsNotNone(completed_audit)
        self.assertEqual(completed_audit.changes["before"]["status"], TaskStatus.IN_PROGRESS)
        self.assertEqual(completed_audit.changes["after"]["status"], TaskStatus.COMPLETED)
        self.assertEqual(completed_audit.changes["after"]["actual_duration_minutes"], 75)
        self.assertIsNotNone(completed_audit.changes["after"]["completed_at"])

    # -------------------------------------------------------------------------
    # 4. Retail Domain: Order Status Lifecycle & Fulfillment Stock Release Audit
    # -------------------------------------------------------------------------
    def test_order_status_transition_audit_and_fulfillment(self):
        now = timezone.now()
        order = Order.objects.create(
            workspace=self.retail_ws,
            order_number=f"ORD-AUDIT-{uuid.uuid4().hex[:6].upper()}",
            customer=self.customer,
            branch=self.branch_a,
            order_date=now.date(),
            order_timestamp=now,
            status=OrderStatus.PENDING,
            total_amount=Decimal("28000000.00"),
            payment_method=PaymentMethod.CASH,
            fulfillment_stock_reserved=True,
        )

        # 1. Confirm Order
        transition_order_status(order, OrderStatus.CONFIRMED, self.retail_admin, ip_address="127.0.0.1")
        order.refresh_from_db()

        confirm_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="ORDER_CONFIRMED",
            entity_type="Order",
            entity_id=str(order.id),
        ).first()

        self.assertIsNotNone(confirm_audit)
        self.assertEqual(confirm_audit.actor_user, self.retail_admin)
        self.assertEqual(confirm_audit.ip_address, "127.0.0.1")
        self.assertEqual(confirm_audit.changes["before_status"], OrderStatus.PENDING)
        self.assertEqual(confirm_audit.changes["after_status"], OrderStatus.CONFIRMED)

        # 2. Cancel Order (Triggers release and cancellation audit)
        transition_order_status(order, OrderStatus.CANCELLED, self.retail_admin, ip_address="127.0.0.1")
        order.refresh_from_db()

        cancel_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="ORDER_CANCELLED",
            entity_type="Order",
            entity_id=str(order.id),
        ).first()

        self.assertIsNotNone(cancel_audit)
        self.assertEqual(cancel_audit.changes["before_status"], OrderStatus.CONFIRMED)
        self.assertEqual(cancel_audit.changes["after_status"], OrderStatus.CANCELLED)

    # -------------------------------------------------------------------------
    # 5. Retail Domain: Stock Transfer & Rollback Before / After Balances
    # -------------------------------------------------------------------------
    def test_stock_transfer_execution_and_rollback_audit(self):
        StockBalance.objects.create(
            workspace=self.retail_ws,
            branch=self.branch_a,
            product=self.product,
            quantity_on_hand=50,
        )
        StockBalance.objects.create(
            workspace=self.retail_ws,
            branch=self.branch_b,
            product=self.product,
            quantity_on_hand=10,
        )

        # Execute Transfer 15 items A -> B
        transfer = execute_stock_transfer(
            workspace=self.retail_ws,
            user=self.retail_admin,
            data={
                "source_branch_id": self.branch_a.id,
                "destination_branch_id": self.branch_b.id,
                "product_id": self.product.id,
                "quantity": 15,
                "idempotency_key": f"audit-transfer-{uuid.uuid4().hex[:8]}",
            },
        )

        exec_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="STOCK_TRANSFER_EXECUTED",
            entity_type="StockTransfer",
            entity_id=str(transfer.id),
        ).first()

        self.assertIsNotNone(exec_audit)
        self.assertEqual(exec_audit.changes["before"]["source_quantity"], 50)
        self.assertEqual(exec_audit.changes["before"]["destination_quantity"], 10)
        self.assertEqual(exec_audit.changes["after"]["source_quantity"], 35)
        self.assertEqual(exec_audit.changes["after"]["destination_quantity"], 25)

        # Rollback Transfer
        rollback_stock_transfer(transfer, self.retail_admin, reason="Khach huy don tai chi nhanh B")

        rollback_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="STOCK_TRANSFER_ROLLED_BACK",
            entity_type="StockTransfer",
            entity_id=str(transfer.id),
        ).first()

        self.assertIsNotNone(rollback_audit)
        self.assertEqual(rollback_audit.changes["reason"], "Khach huy don tai chi nhanh B")
        self.assertEqual(rollback_audit.changes["before"]["source_quantity"], 35)
        self.assertEqual(rollback_audit.changes["before"]["destination_quantity"], 25)
        self.assertEqual(rollback_audit.changes["after"]["source_quantity"], 50)
        self.assertEqual(rollback_audit.changes["after"]["destination_quantity"], 10)

    # -------------------------------------------------------------------------
    # 6. Retail Domain: Category & Supplier Lifecycle Audit
    # -------------------------------------------------------------------------
    def test_category_and_supplier_lifecycle_audit(self):
        # 1. Category
        cat = create_category(
            self.retail_ws,
            self.retail_admin,
            {"name": "Linh kien may chu", "code": "srv-parts"},
        )
        cat_create_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="CATEGORY_CREATED",
            entity_id=str(cat.id),
        ).first()
        self.assertIsNotNone(cat_create_audit)

        update_category(cat, self.retail_admin, {"name": "Linh kien Server Enterprise"})
        cat_update_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="CATEGORY_UPDATED",
            entity_id=str(cat.id),
        ).first()
        self.assertIsNotNone(cat_update_audit)
        self.assertEqual(cat_update_audit.changes["before"]["name"], "Linh kien may chu")
        self.assertEqual(cat_update_audit.changes["after"]["name"], "Linh kien Server Enterprise")

        # 2. Supplier
        sup = create_supplier(
            self.retail_ws,
            self.retail_admin,
            {"name": "Dell Global Logistics", "code": "DELL-AUDIT"},
        )
        sup_create_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="SUPPLIER_CREATED",
            entity_id=str(sup.id),
        ).first()
        self.assertIsNotNone(sup_create_audit)

        update_supplier(sup, self.retail_admin, {"phone": "0988776655"})
        sup_update_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="SUPPLIER_UPDATED",
            entity_id=str(sup.id),
        ).first()
        self.assertIsNotNone(sup_update_audit)
        self.assertEqual(sup_update_audit.changes["after"]["phone"], "0988776655")

    # -------------------------------------------------------------------------
    # 7. Approvals & Tool Execution: Permission Denial Audit Logging
    # -------------------------------------------------------------------------
    def test_permission_denial_audit_logging(self):
        # Create an approval request
        app_req = ApprovalRequest.objects.create(
            workspace=self.retail_ws,
            proposed_action="retail_set_product_price",
            parameters={"product_id": self.product.id, "new_price": "29000000.00"},
            reason="Giam gia san pham 10%",
            risk_level=RiskLevel.MEDIUM,
            status=ApprovalStatus.PENDING,
            requester=self.retail_admin,
            idempotency_key=f"audit-app-{uuid.uuid4().hex[:8]}",
        )

        # Non-permitted user attempts to execute the action directly
        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(app_req, self.regular_user, "APPROVED")

        # Verify that APPROVAL_PERMISSION_DENIED audit log was recorded
        denial_audit = AuditLog.objects.filter(
            workspace=self.retail_ws,
            action="APPROVAL_PERMISSION_DENIED",
            actor_user=self.regular_user,
        ).first()

        self.assertIsNotNone(denial_audit, "Denial audit log must be recorded when permission is denied")
        self.assertEqual(denial_audit.changes.get("error_code"), "PERMISSION_DENIED")

    # -------------------------------------------------------------------------
    # 8. Database Level Immutability (PostgreSQL Trigger Enforcement)
    # -------------------------------------------------------------------------
    def test_postgresql_trigger_immutability_enforcement(self):
        if connection.vendor != "postgresql":
            self.skipTest("Database-level trigger enforcement requires PostgreSQL.")

        audit_row = AuditLog.objects.create(
            workspace=self.retail_ws,
            actor_user=self.retail_admin,
            action="IMMUTABILITY_EVIDENCE",
            entity_type="SecurityVerification",
            entity_id="1",
            changes={"initial": "clean_state"},
        )

        # Raw SQL UPDATE must be rejected by PostgreSQL Trigger
        with self.assertRaisesMessage(DatabaseError, "append-only"), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE audit_auditlog SET action = 'ALTERED_BY_ATTACKER' WHERE id = %s",
                    [audit_row.pk],
                )

        audit_row.refresh_from_db()
        self.assertEqual(audit_row.action, "IMMUTABILITY_EVIDENCE")

        # Raw SQL DELETE must be rejected by PostgreSQL Trigger
        with self.assertRaisesMessage(DatabaseError, "append-only"), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM audit_auditlog WHERE id = %s",
                    [audit_row.pk],
                )

        self.assertTrue(AuditLog.objects.filter(pk=audit_row.pk).exists())
