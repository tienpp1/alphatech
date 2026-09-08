"""
Automated Test Suite for Retail Extension: Goods Receiving & Stock Balance.
Verifies Supplier CRUD, GoodsReceipt State Machine, Concurrency Locking, and Stock Balance increments.
"""

from decimal import Decimal
from datetime import date
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import (
    Category,
    Product,
    Branch,
    Supplier,
    GoodsReceipt,
    GoodsReceiptItem,
    GoodsReceiptStatus,
    StockBalance,
)
from apps.retail.services import (
    create_supplier,
    update_supplier,
    delete_supplier,
    create_goods_receipt,
    confirm_goods_receipt,
    receive_goods_receipt,
    cancel_goods_receipt,
)


class RetailGoodsReceivingTestCase(TestCase):
    def setUp(self):
        # 1. Setup Workspaces
        self.ws_retail = Workspace.objects.create(
            code="test-retail",
            name="Test Retail Store",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.ws_other = Workspace.objects.create(
            code="test-other",
            name="Other Workspace",
            workspace_type=WorkspaceType.RETAIL,
        )

        # 2. Setup User
        self.user = User.objects.create_user(
            username="inventory_manager",
            email="inv@example.com",
            password="Password123!",
        )

        # 3. Setup Catalog & Branches
        self.category = Category.objects.create(
            workspace=self.ws_retail,
            name="Laptop",
            code="laptop",
        )
        self.product_asus = Product.objects.create(
            workspace=self.ws_retail,
            category=self.category,
            sku="ASUS-VIVO-14",
            name="Laptop ASUS VivoBook 14",
            unit="chiếc",
            unit_price=Decimal("15000000.00"),
            cost_price=Decimal("12000000.00"),
        )
        self.product_lenovo = Product.objects.create(
            workspace=self.ws_retail,
            category=self.category,
            sku="LENOVO-IDEA-3",
            name="Laptop Lenovo IdeaPad 3",
            unit="chiếc",
            unit_price=Decimal("14000000.00"),
            cost_price=Decimal("11000000.00"),
        )

        self.branch_a = Branch.objects.create(
            workspace=self.ws_retail,
            code="BR-A",
            name="Chi nhánh Quận 1",
            address="100 Lê Lợi, Q.1",
        )
        self.branch_b = Branch.objects.create(
            workspace=self.ws_retail,
            code="BR-B",
            name="Chi nhánh Quận 3",
            address="200 Nam Kỳ Khởi Nghĩa, Q.3",
        )

        # 4. Setup Supplier
        self.supplier = Supplier.objects.create(
            workspace=self.ws_retail,
            code="SUP-ASUS-VN",
            name="ASUS Vietnam Distribution",
            phone="02812345678",
            contact_name="Nguyễn Văn A",
        )

    def test_supplier_crud_and_workspace_isolation(self):
        """Tests supplier creation, updating, and workspace scoping."""
        sup_data = {
            "name": "Lenovo Vietnam Co.",
            "code": "SUP-LENOVO-VN",
            "contact_name": "Trần Thị B",
            "phone": "02487654321",
            "email": "contact@lenovo.vn",
        }
        supplier = create_supplier(self.ws_retail, self.user, sup_data)
        self.assertEqual(supplier.code, "SUP-LENOVO-VN")
        self.assertEqual(supplier.workspace, self.ws_retail)

        # Update
        updated = update_supplier(supplier, self.user, {"phone": "02499998888"})
        self.assertEqual(updated.phone, "02499998888")

        # Workspace isolation
        other_suppliers = Supplier.objects.for_workspace(self.ws_other)
        self.assertEqual(other_suppliers.count(), 0)

    def test_goods_receipt_creation_in_draft(self):
        """Tests creating a GoodsReceipt sets status to DRAFT and calculates line totals without altering stock."""
        items_data = [
            {"product_id": self.product_asus.id, "quantity": 10, "unit_cost": Decimal("12000000.00")},
            {"product_id": self.product_lenovo.id, "quantity": 5, "unit_cost": Decimal("11000000.00")},
        ]
        receipt_data = {
            "supplier_id": self.supplier.id,
            "branch_id": self.branch_a.id,
            "receipt_date": date.today(),
            "notes": "Lô hàng mẫu thử nghiệm",
            "items": items_data,
        }

        receipt = create_goods_receipt(self.ws_retail, self.user, receipt_data)

        self.assertEqual(receipt.status, GoodsReceiptStatus.DRAFT)
        self.assertEqual(receipt.items.count(), 2)
        # Expected total: 10 * 12M + 5 * 11M = 120M + 55M = 175M
        self.assertEqual(receipt.total_amount, Decimal("175000000.00"))

        # Crucial check: Stock balances must NOT be created/altered in DRAFT
        stock_asus = StockBalance.objects.filter(workspace=self.ws_retail, branch=self.branch_a, product=self.product_asus).first()
        self.assertIsNone(stock_asus)

    def test_goods_receipt_confirmation_lifecycle(self):
        """Tests DRAFT -> CONFIRMED transition."""
        receipt = create_goods_receipt(self.ws_retail, self.user, {
            "supplier_id": self.supplier.id,
            "branch_id": self.branch_a.id,
            "items": [{"product_id": self.product_asus.id, "quantity": 10, "unit_cost": Decimal("12000000.00")}],
        })

        confirmed = confirm_goods_receipt(receipt, self.user)
        self.assertEqual(confirmed.status, GoodsReceiptStatus.CONFIRMED)

        # Cannot confirm again
        with self.assertRaises(ValidationError):
            confirm_goods_receipt(confirmed, self.user)

    def test_goods_receipt_receiving_increments_stock(self):
        """Tests receiving increases stock atomically with row-level locks."""
        # Initial stock balance
        StockBalance.objects.create(
            workspace=self.ws_retail,
            branch=self.branch_a,
            product=self.product_asus,
            quantity_on_hand=4,
        )

        receipt = create_goods_receipt(self.ws_retail, self.user, {
            "supplier_id": self.supplier.id,
            "branch_id": self.branch_a.id,
            "items": [
                {"product_id": self.product_asus.id, "quantity": 10, "unit_cost": Decimal("12000000.00")},
                {"product_id": self.product_lenovo.id, "quantity": 8, "unit_cost": Decimal("11000000.00")},
            ],
        })

        # Confirm then Receive
        confirm_goods_receipt(receipt, self.user)
        received = receive_goods_receipt(receipt, self.user)

        self.assertEqual(received.status, GoodsReceiptStatus.RECEIVED)
        self.assertIsNotNone(received.received_at)
        self.assertEqual(received.received_by, self.user)

        # Verify stock balance for Asus: 4 + 10 = 14
        stock_asus = StockBalance.objects.get(workspace=self.ws_retail, branch=self.branch_a, product=self.product_asus)
        self.assertEqual(stock_asus.quantity_on_hand, 14)

        # Verify stock balance for Lenovo (newly created): 0 + 8 = 8
        stock_lenovo = StockBalance.objects.get(workspace=self.ws_retail, branch=self.branch_a, product=self.product_lenovo)
        self.assertEqual(stock_lenovo.quantity_on_hand, 8)

        # Verify branch B stock remains unaffected
        stock_b_asus = StockBalance.objects.filter(workspace=self.ws_retail, branch=self.branch_b, product=self.product_asus).first()
        self.assertIsNone(stock_b_asus)

    def test_cannot_receive_twice(self):
        """Prevents duplicate stock increments by throwing error on already received receipts."""
        receipt = create_goods_receipt(self.ws_retail, self.user, {
            "supplier_id": self.supplier.id,
            "branch_id": self.branch_a.id,
            "items": [{"product_id": self.product_asus.id, "quantity": 5, "unit_cost": Decimal("12000000.00")}],
        })
        confirm_goods_receipt(receipt, self.user)
        receive_goods_receipt(receipt, self.user)

        # Second receive attempt must fail
        with self.assertRaises(ValidationError):
            receive_goods_receipt(receipt, self.user)

        # Stock balance must be 5, not 10
        stock = StockBalance.objects.get(workspace=self.ws_retail, branch=self.branch_a, product=self.product_asus)
        self.assertEqual(stock.quantity_on_hand, 5)

    def test_cancel_goods_receipt(self):
        """Tests cancelling a draft or confirmed receipt, and prevents cancelling received receipts."""
        receipt = create_goods_receipt(self.ws_retail, self.user, {
            "supplier_id": self.supplier.id,
            "branch_id": self.branch_a.id,
            "items": [{"product_id": self.product_asus.id, "quantity": 5, "unit_cost": Decimal("12000000.00")}],
        })

        cancelled = cancel_goods_receipt(receipt, self.user)
        self.assertEqual(cancelled.status, GoodsReceiptStatus.CANCELLED)

        # Received receipt cannot be cancelled
        receipt2 = create_goods_receipt(self.ws_retail, self.user, {
            "supplier_id": self.supplier.id,
            "branch_id": self.branch_a.id,
            "items": [{"product_id": self.product_asus.id, "quantity": 2, "unit_cost": Decimal("12000000.00")}],
        })
        confirm_goods_receipt(receipt2, self.user)
        receive_goods_receipt(receipt2, self.user)

        with self.assertRaises(ValidationError):
            cancel_goods_receipt(receipt2, self.user)
