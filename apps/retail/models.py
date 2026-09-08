"""
Retail Domain Models (Tier 3: Workspace-Scoped Commercial Entities).
Follows docs/erd.md Section 2.3 and docs/standard-data-model.md.
"""

from decimal import Decimal
from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as gis_models

from apps.workspaces.models import WorkspaceScopedModel


class Category(WorkspaceScopedModel):
    """
    Product Category hierarchy, strictly scoped to a Workspace.
    """

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, db_index=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retail_category"
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="unique_workspace_category_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Product(WorkspaceScopedModel):
    """
    Retail Commercial Product Catalog (Sales Product in V1).
    """

    id = models.BigAutoField(primary_key=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.RESTRICT,
        related_name="products",
    )
    sku = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=30, default="cái")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deleted_retail_products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retail_product"
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "sku"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_workspace_active_product_sku",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "is_active"]),
            models.Index(fields=["workspace", "category"]),
            models.Index(fields=["workspace", "deleted_at"]),
        ]

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def days_until_permanent_delete(self) -> int:
        if not self.deleted_at:
            return 7
        from django.utils import timezone
        elapsed_days = (timezone.now() - self.deleted_at).days
        return max(0, 7 - elapsed_days)

    @property
    def primary_image(self):
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary
        return self.images.order_by("sort_order", "created_at").first()

    def __str__(self):
        return f"{self.name} [{self.sku}] - {self.unit_price:,.0f} VND"


class ProductImage(WorkspaceScopedModel):
    """
    Product Gallery Image supporting single/multiple images, primary selection, and safe storage.
    """

    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to="products/%Y/%m/")
    sort_order = models.PositiveIntegerField(default=0)
    is_primary = models.BooleanField(default=False, db_index=True)
    alt_text = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retail_product_image"
        ordering = ["sort_order", "created_at"]
        verbose_name = "Product Image"
        verbose_name_plural = "Product Images"
        indexes = [
            models.Index(fields=["workspace", "product"]),
            models.Index(fields=["product", "is_primary"]),
        ]

    def __str__(self):
        return f"Image for {self.product.name} (Primary: {self.is_primary})"


class Branch(WorkspaceScopedModel):
    """
    Physical Retail Outlet / Store Branch.
    """

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=255)
    region = models.CharField(max_length=100, db_index=True)
    location = gis_models.PointField(srid=4326, spatial_index=True, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retail_branch"
        ordering = ["name"]
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="unique_workspace_branch_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) - {self.region}"


class CustomerSegment(models.TextChoices):
    STANDARD = "STANDARD", "Standard"
    VIP = "VIP", "VIP"
    ENTERPRISE = "ENTERPRISE", "Enterprise"


class Customer(WorkspaceScopedModel):
    """
    Retail Customer Profile.
    """

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="customer_profiles",
    )
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(max_length=254, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    address = models.CharField(max_length=255, blank=True)
    location = gis_models.PointField(srid=4326, spatial_index=True, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    customer_segment = models.CharField(
        max_length=50,
        choices=CustomerSegment.choices,
        default=CustomerSegment.STANDARD,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retail_customer"
        ordering = ["name"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="unique_workspace_customer_code",
            ),
            models.UniqueConstraint(
                fields=["workspace", "user"], name="unique_workspace_customer_user",
            ),
        ]

    @property
    def full_name(self) -> str:
        return self.name

    def __str__(self):
        return f"{self.name} ({self.code}) [{self.customer_segment}]"


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
    CREDIT_CARD = "CREDIT_CARD", "Credit Card"
    E_WALLET = "E_WALLET", "E-Wallet"


class Order(WorkspaceScopedModel):
    """
    Retail Commercial Transaction / Invoice (Canonical Revenue Source).
    """

    id = models.BigAutoField(primary_key=True)
    order_number = models.CharField(max_length=50, db_index=True)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.RESTRICT,
        related_name="orders",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    order_date = models.DateField(db_index=True)
    order_timestamp = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=30,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
    )
    subtotal_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )  # Canonical Revenue
    payment_method = models.CharField(
        max_length=50,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_retail_orders",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retail_order"
        ordering = ["-order_timestamp"]
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "order_number"],
                name="unique_workspace_order_number",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "order_date"]),
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "branch"]),
            models.Index(fields=["workspace", "customer"]),
        ]

    def __str__(self):
        return f"Order #{self.order_number} - {self.total_amount:,.0f} VND ({self.status})"


class OrderItem(models.Model):
    """
    Individual Order Line Item.
    Preserves historical unit price snapshot at transaction time.
    """

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.RESTRICT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )  # Price snapshot at purchase time
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    subtotal = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        db_table = "retail_orderitem"
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"

    @property
    def price(self) -> Decimal:
        return self.unit_price

    def save(self, *args, **kwargs):
        # Always calculate line total accurately: (quantity * unit_price) - discount
        calculated = (Decimal(self.quantity) * self.unit_price) - self.discount
        self.subtotal = max(Decimal("0.00"), calculated)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} @ {self.unit_price:,.0f} = {self.subtotal:,.0f}"


class Supplier(WorkspaceScopedModel):
    """
    Vendor / Wholesale Supplier of Retail Goods.
    """

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(max_length=254, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True, db_index=True)
    address = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retail_supplier"
        ordering = ["name"]
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "code"],
                name="unique_workspace_supplier_code",
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class GoodsReceiptStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    CONFIRMED = "CONFIRMED", "Confirmed"
    RECEIVED = "RECEIVED", "Received"
    CANCELLED = "CANCELLED", "Cancelled"


class GoodsReceipt(WorkspaceScopedModel):
    """
    Inbound Inventory Receipt / Goods Receiving Document.
    Only when status transitions to RECEIVED is branch stock balance increased.
    """

    id = models.BigAutoField(primary_key=True)
    receipt_number = models.CharField(max_length=50, db_index=True)
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.RESTRICT,
        related_name="goods_receipts",
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.RESTRICT,
        related_name="goods_receipts",
    )
    receipt_date = models.DateField(db_index=True)
    expected_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=GoodsReceiptStatus.choices,
        default=GoodsReceiptStatus.DRAFT,
        db_index=True,
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_goods_receipts",
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_goods_receipts",
    )
    received_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retail_goodsreceipt"
        ordering = ["-receipt_date", "-created_at"]
        verbose_name = "Goods Receipt"
        verbose_name_plural = "Goods Receipts"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "receipt_number"],
                name="unique_workspace_receipt_number",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "branch"]),
            models.Index(fields=["workspace", "supplier"]),
            models.Index(fields=["workspace", "receipt_date"]),
        ]

    def __str__(self):
        return f"Receipt #{self.receipt_number} - {self.supplier.name} -> {self.branch.name} ({self.status})"


class GoodsReceiptItem(models.Model):
    """
    Individual item in a Goods Receiving Document.
    """

    id = models.BigAutoField(primary_key=True)
    receipt = models.ForeignKey(
        GoodsReceipt,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.RESTRICT,
        related_name="receipt_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    line_total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    class Meta:
        db_table = "retail_goodsreceiptitem"
        verbose_name = "Goods Receipt Item"
        verbose_name_plural = "Goods Receipt Items"

    def save(self, *args, **kwargs):
        calculated = Decimal(self.quantity) * self.unit_cost
        self.line_total = max(Decimal("0.00"), calculated)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity}x {self.product.name} @ {self.unit_cost:,.0f} = {self.line_total:,.0f}"


class StockBalance(WorkspaceScopedModel):
    """
    Branch-level Product Inventory Balance.
    Tracks on-hand inventory quantity per Product at each Branch.
    """

    id = models.BigAutoField(primary_key=True)
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="stock_balances",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_balances",
    )
    quantity_on_hand = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retail_stockbalance"
        ordering = ["branch", "product"]
        verbose_name = "Stock Balance"
        verbose_name_plural = "Stock Balances"
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "branch", "product"],
                name="unique_workspace_branch_product_stock",
            )
        ]
        indexes = [
            models.Index(fields=["workspace", "branch"]),
            models.Index(fields=["workspace", "product"]),
        ]

    def __str__(self):
        return f"[{self.branch.code}] {self.product.name}: {self.quantity_on_hand} {self.product.unit}"


class StockTransferStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Approval"
    EXECUTED = "EXECUTED", "Executed"
    CANCELLED = "CANCELLED", "Cancelled"
    ROLLED_BACK = "ROLLED_BACK", "Rolled Back"


class StockTransfer(WorkspaceScopedModel):
    """Auditable, idempotent branch-to-branch inventory movement."""

    id = models.BigAutoField(primary_key=True)
    reference_number = models.CharField(max_length=60, db_index=True)
    source_branch = models.ForeignKey(Branch, on_delete=models.RESTRICT, related_name="outgoing_stock_transfers")
    destination_branch = models.ForeignKey(Branch, on_delete=models.RESTRICT, related_name="incoming_stock_transfers")
    product = models.ForeignKey(Product, on_delete=models.RESTRICT, related_name="stock_transfers")
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=StockTransferStatus.choices, default=StockTransferStatus.EXECUTED, db_index=True)
    idempotency_key = models.CharField(max_length=120, db_index=True)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="requested_stock_transfers")
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="executed_stock_transfers")
    rollback_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    rolled_back_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "retail_stocktransfer"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["workspace", "reference_number"], name="unique_workspace_stock_transfer_ref"),
            models.UniqueConstraint(fields=["workspace", "idempotency_key"], name="unique_workspace_stock_transfer_key"),
            models.CheckConstraint(condition=~models.Q(source_branch=models.F("destination_branch")), name="stock_transfer_distinct_branches"),
        ]
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "source_branch"]),
            models.Index(fields=["workspace", "destination_branch"]),
        ]

    def clean(self):
        super().clean()
        related = (self.source_branch, self.destination_branch, self.product)
        if any(obj is not None and obj.workspace_id != self.workspace_id for obj in related):
            from django.core.exceptions import ValidationError
            raise ValidationError("All stock-transfer entities must belong to the same workspace.")
        if self.source_branch_id == self.destination_branch_id:
            from django.core.exceptions import ValidationError
            raise ValidationError("Source and destination branches must be different.")
