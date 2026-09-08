"""
Retail Domain Business Logic & Mutation Services.
Enforces transactional safety, server-side revenue calculation, state transitions, and audit logging.
"""

import uuid
from decimal import Decimal
from datetime import date, datetime
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point

from apps.audit.services import log_action
from apps.retail.models import (
    Category,
    Product,
    ProductImage,
    Branch,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    Supplier,
    GoodsReceipt,
    GoodsReceiptItem,
    GoodsReceiptStatus,
    StockBalance,
    StockTransfer,
    StockTransferStatus,
)


def execute_stock_transfer(workspace, user, data: Dict[str, Any]) -> StockTransfer:
    """Atomically move stock with deterministic locking and idempotency."""
    source_id = data.get("source_branch_id")
    destination_id = data.get("destination_branch_id")
    product_id = data.get("product_id")
    quantity = int(data.get("quantity", 0))
    idempotency_key = str(data.get("idempotency_key") or "").strip()
    if quantity <= 0 or not idempotency_key:
        raise ValidationError("quantity and idempotency_key are required.")
    if source_id == destination_id:
        raise ValidationError("Source and destination branches must be different.")

    with transaction.atomic():
        existing = StockTransfer.objects.for_workspace(workspace).filter(idempotency_key=idempotency_key).first()
        if existing:
            if existing.source_branch_id != source_id or existing.destination_branch_id != destination_id or existing.product_id != product_id or existing.quantity != quantity:
                raise ValidationError("Idempotency key is already bound to a different stock transfer.")
            return existing

        source = Branch.objects.for_workspace(workspace).filter(id=source_id, is_active=True).first()
        destination = Branch.objects.for_workspace(workspace).filter(id=destination_id, is_active=True).first()
        product = Product.objects.for_workspace(workspace).filter(id=product_id, is_active=True, deleted_at__isnull=True).first()
        if not source or not destination or not product:
            raise ValidationError("Stock-transfer entities must belong to the active workspace.")

        balances = list(StockBalance.objects.select_for_update().filter(
            workspace=workspace, branch_id__in=[source.id, destination.id], product_id=product.id
        ).order_by("branch_id"))
        balance_by_branch = {row.branch_id: row for row in balances}
        source_balance = balance_by_branch.get(source.id)
        if not source_balance or source_balance.quantity_on_hand < quantity:
            raise ValidationError("Source stock is insufficient for this transfer.")
        destination_balance = balance_by_branch.get(destination.id)
        if not destination_balance:
            destination_balance = StockBalance.objects.create(workspace=workspace, branch=destination, product=product, quantity_on_hand=0)

        source_balance.quantity_on_hand -= quantity
        destination_balance.quantity_on_hand += quantity
        source_balance.save(update_fields=["quantity_on_hand", "updated_at"])
        destination_balance.save(update_fields=["quantity_on_hand", "updated_at"])
        transfer = StockTransfer.objects.create(
            workspace=workspace,
            reference_number=f"TR-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}",
            source_branch=source,
            destination_branch=destination,
            product=product,
            quantity=quantity,
            status=StockTransferStatus.EXECUTED,
            idempotency_key=idempotency_key,
            requested_by=user,
            executed_by=user,
            executed_at=timezone.now(),
        )
        log_action(workspace=workspace, actor_user=user, action="STOCK_TRANSFER_EXECUTED", entity_type="StockTransfer", entity_id=transfer.id, changes={"source_branch_id": source.id, "destination_branch_id": destination.id, "product_id": product.id, "quantity": quantity})
        return transfer


def rollback_stock_transfer(transfer: StockTransfer, user, reason: str) -> StockTransfer:
    """Compensate an executed transfer exactly once."""
    with transaction.atomic():
        transfer = StockTransfer.objects.select_for_update().select_related("workspace").get(pk=transfer.pk)
        if transfer.status == StockTransferStatus.ROLLED_BACK:
            return transfer
        if transfer.status != StockTransferStatus.EXECUTED:
            raise ValidationError("Only an executed transfer can be rolled back.")
        balances = list(StockBalance.objects.select_for_update().filter(workspace=transfer.workspace, branch_id__in=[transfer.source_branch_id, transfer.destination_branch_id], product_id=transfer.product_id).order_by("branch_id"))
        by_branch = {row.branch_id: row for row in balances}
        source = by_branch.get(transfer.source_branch_id)
        destination = by_branch.get(transfer.destination_branch_id)
        if not source or not destination or destination.quantity_on_hand < transfer.quantity:
            raise ValidationError("Destination stock is insufficient to compensate this transfer.")
        source.quantity_on_hand += transfer.quantity
        destination.quantity_on_hand -= transfer.quantity
        source.save(update_fields=["quantity_on_hand", "updated_at"])
        destination.save(update_fields=["quantity_on_hand", "updated_at"])
        transfer.status = StockTransferStatus.ROLLED_BACK
        transfer.rollback_reason = reason.strip()[:2000]
        transfer.rolled_back_at = timezone.now()
        transfer.save(update_fields=["status", "rollback_reason", "rolled_back_at"])
        log_action(workspace=transfer.workspace, actor_user=user, action="STOCK_TRANSFER_ROLLED_BACK", entity_type="StockTransfer", entity_id=transfer.id, changes={"reason": transfer.rollback_reason})
        return transfer


def create_category(workspace, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Category:
    """Creates a new category under the active workspace."""
    parent_id = data.get("parent_id")
    parent = None
    if parent_id:
        parent = Category.objects.for_workspace(workspace).filter(id=parent_id).first()
        if not parent:
            raise ValidationError({"parent_id": "Parent category does not exist in this workspace."})

    category = Category.objects.create(
        workspace=workspace,
        name=data["name"],
        code=data["code"].strip().lower(),
        parent=parent,
        description=data.get("description", ""),
        is_active=data.get("is_active", True),
    )
    log_action(
        workspace=workspace,
        actor_user=user,
        action="CATEGORY_CREATED",
        entity_type="Category",
        entity_id=category.id,
        changes={"name": category.name, "code": category.code},
        ip_address=ip_address,
    )
    return category


def update_category(category: Category, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Category:
    """Updates an existing category with audit trail."""
    before = {"name": category.name, "is_active": category.is_active}
    if "name" in data:
        category.name = data["name"]
    if "description" in data:
        category.description = data["description"]
    if "is_active" in data:
        category.is_active = data["is_active"]
    if "parent_id" in data:
        parent_id = data["parent_id"]
        if parent_id is None:
            category.parent = None
        else:
            parent = Category.objects.for_workspace(category.workspace).filter(id=parent_id).first()
            if not parent:
                raise ValidationError({"parent_id": "Parent category does not exist in this workspace."})
            if parent.id == category.id:
                raise ValidationError({"parent_id": "A category cannot be its own parent."})
            category.parent = parent
    category.save()
    log_action(
        workspace=category.workspace,
        actor_user=user,
        action="CATEGORY_UPDATED",
        entity_type="Category",
        entity_id=category.id,
        changes={"before": before, "after": {"name": category.name, "is_active": category.is_active}},
        ip_address=ip_address,
    )
    return category


def delete_category(category: Category, user, ip_address: Optional[str] = None) -> None:
    """Safely deletes a category or raises error if referenced by products."""
    if category.products.exists():
        raise ValidationError(
            f"Cannot delete category '{category.name}' because {category.products.count()} products reference it. Deactivate instead."
        )
    cat_id = category.id
    ws = category.workspace
    category.delete()
    log_action(
        workspace=ws,
        actor_user=user,
        action="CATEGORY_DELETED",
        entity_type="Category",
        entity_id=cat_id,
        ip_address=ip_address,
    )


def create_product(workspace, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Product:
    """Creates a new sales product with price and SKU validation."""
    category_id = data.get("category_id")
    category = Category.objects.for_workspace(workspace).filter(id=category_id).first()
    if not category:
        raise ValidationError({"category_id": "Danh mục không tồn tại trong không gian làm việc này."})

    sku = data["sku"].strip().upper()
    if Product.objects.filter(workspace=workspace, sku=sku, deleted_at__isnull=True).exists():
        raise ValidationError({"sku": f"Mã SKU '{sku}' đã tồn tại trong không gian làm việc này."})

    unit_price = Decimal(str(data.get("unit_price", "0")))
    cost_price = Decimal(str(data.get("cost_price", "0")))
    if unit_price < Decimal("0.00"):
        raise ValidationError({"unit_price": "Giá bán không được là số âm."})
    if cost_price < Decimal("0.00"):
        raise ValidationError({"cost_price": "Giá vốn không được là số âm."})

    product = Product.objects.create(
        workspace=workspace,
        category=category,
        sku=sku,
        name=data["name"].strip(),
        description=data.get("description", ""),
        unit=data.get("unit", "cái"),
        unit_price=unit_price,
        cost_price=cost_price,
        is_active=data.get("is_active", True),
    )
    log_action(
        workspace=workspace,
        actor_user=user,
        action="PRODUCT_CREATED",
        entity_type="Product",
        entity_id=product.id,
        changes={"sku": product.sku, "name": product.name, "unit_price": str(product.unit_price)},
        ip_address=ip_address,
    )
    return product


def update_product(product: Product, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Product:
    """Updates an existing product with audit trail."""
    before = {
        "name": product.name,
        "sku": product.sku,
        "unit_price": str(product.unit_price),
        "cost_price": str(product.cost_price),
        "is_active": product.is_active,
    }
    if "sku" in data:
        new_sku = data["sku"].strip().upper()
        if new_sku != product.sku:
            if Product.objects.filter(workspace=product.workspace, sku=new_sku, deleted_at__isnull=True).exclude(id=product.id).exists():
                raise ValidationError({"sku": f"Mã SKU '{new_sku}' đã được sử dụng bởi sản phẩm khác."})
            product.sku = new_sku
    if "name" in data:
        product.name = data["name"].strip()
    if "description" in data:
        product.description = data["description"]
    if "unit" in data:
        product.unit = data["unit"]
    if "unit_price" in data:
        up = Decimal(str(data["unit_price"]))
        if up < Decimal("0.00"):
            raise ValidationError({"unit_price": "Giá bán không được là số âm."})
        product.unit_price = up
    if "cost_price" in data:
        cp = Decimal(str(data["cost_price"]))
        if cp < Decimal("0.00"):
            raise ValidationError({"cost_price": "Giá vốn không được là số âm."})
        product.cost_price = cp
    if "is_active" in data:
        product.is_active = data["is_active"]
    if "category_id" in data:
        category = Category.objects.for_workspace(product.workspace).filter(id=data["category_id"]).first()
        if not category:
            raise ValidationError({"category_id": "Danh mục không tồn tại trong không gian làm việc này."})
        product.category = category

    product.save()
    log_action(
        workspace=product.workspace,
        actor_user=user,
        action="PRODUCT_UPDATED",
        entity_type="Product",
        entity_id=product.id,
        changes={
            "before": before,
            "after": {
                "name": product.name,
                "sku": product.sku,
                "unit_price": str(product.unit_price),
                "cost_price": str(product.cost_price),
                "is_active": product.is_active,
            },
        },
        ip_address=ip_address,
    )
    return product


def soft_delete_product(product: Product, user, ip_address: Optional[str] = None) -> Product:
    """
    Soft-deletes a product, removing it from active catalogs while preserving historical references.
    """
    if product.is_deleted:
        return product

    product.deleted_at = timezone.now()
    product.deleted_by = user
    product.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    log_action(
        workspace=product.workspace,
        actor_user=user,
        action="PRODUCT_SOFT_DELETED",
        entity_type="Product",
        entity_id=product.id,
        changes={"sku": product.sku, "name": product.name, "deleted_at": str(product.deleted_at)},
        ip_address=ip_address,
    )
    return product


def restore_product(product: Product, user, ip_address: Optional[str] = None) -> Product:
    """
    Restores a soft-deleted product from trash back into the active catalog.
    Validates SKU uniqueness against existing non-deleted products in the workspace.
    """
    if not product.is_deleted:
        return product

    # Check for SKU conflict with live products
    if Product.objects.filter(workspace=product.workspace, sku=product.sku, deleted_at__isnull=True).exclude(id=product.id).exists():
        raise ValidationError(
            f"Không thể khôi phục vì mã SKU '{product.sku}' hiện đã được sử dụng bởi một sản phẩm khác đang hoạt động."
        )

    deleted_at_prev = str(product.deleted_at)
    product.deleted_at = None
    product.deleted_by = None
    product.save(update_fields=["deleted_at", "deleted_by", "updated_at"])

    log_action(
        workspace=product.workspace,
        actor_user=user,
        action="PRODUCT_RESTORED",
        entity_type="Product",
        entity_id=product.id,
        changes={"sku": product.sku, "name": product.name, "previous_deleted_at": deleted_at_prev},
        ip_address=ip_address,
    )
    return product


@transaction.atomic
def permanent_delete_product(product: Product, user, ip_address: Optional[str] = None) -> None:
    """
    Permanently destroys a product record and its associated physical images.
    Enforces referential integrity check for historical order items.
    """
    if product.order_items.exists():
        raise ValidationError(
            f"Không thể xóa vĩnh viễn sản phẩm '{product.name}' ({product.sku}) vì có {product.order_items.count()} mục đơn hàng lịch sử liên kết. Vui lòng giữ sản phẩm trong thùng rác hoặc hủy kích hoạt."
        )

    prod_id = product.id
    prod_sku = product.sku
    prod_name = product.name
    ws = product.workspace

    # Safely clean physical image files
    for img in product.images.all():
        try:
            if img.image and hasattr(img.image, "path") and os.path.isfile(img.image.path):
                img.image.delete(save=False)
        except Exception:
            pass

    product.delete()

    log_action(
        workspace=ws,
        actor_user=user,
        action="PRODUCT_PERMANENTLY_DELETED",
        entity_type="Product",
        entity_id=prod_id,
        changes={"sku": prod_sku, "name": prod_name},
        ip_address=ip_address,
    )


def delete_product(product: Product, user, ip_address: Optional[str] = None) -> None:
    """Default delete action delegating to soft delete."""
    soft_delete_product(product, user, ip_address=ip_address)


def create_branch(workspace, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Branch:
    """Creates a physical outlet branch with coordinate validation."""
    lat = data.get("latitude")
    lon = data.get("longitude")
    loc = None
    if lat is not None and lon is not None:
        lat_dec = Decimal(str(lat))
        lon_dec = Decimal(str(lon))
        if not (-90 <= lat_dec <= 90):
            raise ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if not (-180 <= lon_dec <= 180):
            raise ValidationError({"longitude": "Longitude must be between -180 and 180."})
        loc = Point(float(lon_dec), float(lat_dec), srid=4326)

    branch = Branch.objects.create(
        workspace=workspace,
        code=data["code"].strip().upper(),
        name=data["name"].strip(),
        address=data["address"].strip(),
        region=data["region"].strip(),
        location=loc,
        latitude=Decimal(str(lat)) if lat is not None else None,
        longitude=Decimal(str(lon)) if lon is not None else None,
        phone=data.get("phone", ""),
        is_active=data.get("is_active", True),
    )
    log_action(
        workspace=workspace,
        actor_user=user,
        action="BRANCH_CREATED",
        entity_type="Branch",
        entity_id=branch.id,
        changes={"code": branch.code, "name": branch.name},
        ip_address=ip_address,
    )
    return branch


def create_customer(workspace, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Customer:
    """Creates a customer profile."""
    lat = data.get("latitude")
    lon = data.get("longitude")
    loc = None
    if lat is not None and lon is not None:
        lat_dec = Decimal(str(lat))
        lon_dec = Decimal(str(lon))
        if not (-90 <= lat_dec <= 90):
            raise ValidationError({"latitude": "Latitude must be between -90 and 90."})
        if not (-180 <= lon_dec <= 180):
            raise ValidationError({"longitude": "Longitude must be between -180 and 180."})
        loc = Point(float(lon_dec), float(lat_dec), srid=4326)

    customer = Customer.objects.create(
        workspace=workspace,
        code=data["code"].strip().upper(),
        name=data["name"].strip(),
        email=data.get("email"),
        phone=data.get("phone", ""),
        address=data.get("address", ""),
        location=loc,
        latitude=Decimal(str(lat)) if lat is not None else None,
        longitude=Decimal(str(lon)) if lon is not None else None,
        customer_segment=data.get("customer_segment", "STANDARD"),
        is_active=data.get("is_active", True),
    )
    log_action(
        workspace=workspace,
        actor_user=user,
        action="CUSTOMER_CREATED",
        entity_type="Customer",
        entity_id=customer.id,
        changes={"code": customer.code, "name": customer.name},
        ip_address=ip_address,
    )
    return customer


@transaction.atomic
def create_order(workspace, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Order:
    """
    Creates an atomic order with server-side pricing snapshots and total computation.
    Validates workspace isolation for all referenced entities (customer, branch, products).
    Rejects inactive products, negative quantities, or invalid entities.
    """
    # 1. Validate Customer
    customer_id = data.get("customer_id")
    if not customer_id:
        raise ValidationError({"customer_id": "Customer is required."})
    customer = Customer.objects.for_workspace(workspace).filter(id=customer_id).first()
    if not customer:
        raise ValidationError({"customer_id": "Customer not found in active workspace."})
    if not customer.is_active:
        raise ValidationError({"customer_id": "Cannot create order for an inactive customer."})

    # 2. Validate Branch (optional)
    branch = None
    branch_id = data.get("branch_id")
    if branch_id:
        branch = Branch.objects.for_workspace(workspace).filter(id=branch_id).first()
        if not branch:
            raise ValidationError({"branch_id": "Branch not found in active workspace."})
        if not branch.is_active:
            raise ValidationError({"branch_id": "Cannot place order at an inactive branch."})

    # 3. Validate Line Items
    raw_items: List[Dict[str, Any]] = data.get("items", [])
    if not raw_items:
        raise ValidationError({"items": "Order must contain at least one item."})

    validated_items = []
    subtotal_sum = Decimal("0.00")

    for idx, item_data in enumerate(raw_items):
        product_id = item_data.get("product_id")
        quantity = int(item_data.get("quantity", 0))
        item_discount = Decimal(str(item_data.get("discount", "0.00")))

        if not product_id:
            raise ValidationError({"items": f"Item at index {idx} is missing product_id."})
        if quantity <= 0:
            raise ValidationError({"items": f"Item at index {idx} has invalid quantity {quantity}. Must be > 0."})
        if item_discount < Decimal("0.00"):
            raise ValidationError({"items": f"Item at index {idx} has negative discount."})

        product = Product.objects.for_workspace(workspace).filter(id=product_id).first()
        if not product:
            raise ValidationError({"items": f"Product #{product_id} at index {idx} does not exist in this workspace."})
        if not product.is_active:
            raise ValidationError({"items": f"Product '{product.name}' ({product.sku}) is inactive and cannot be ordered."})

        # Snapshot unit price at current product price (or custom authorized line price if provided)
        unit_price = product.unit_price
        line_total = max(Decimal("0.00"), (Decimal(quantity) * unit_price) - item_discount)
        subtotal_sum += line_total

        validated_items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "discount": item_discount,
                "subtotal": line_total,
            }
        )

    # 4. Compute Order Totals Server-Side
    order_discount = Decimal(str(data.get("discount_amount", "0.00")))
    tax_amount = Decimal(str(data.get("tax_amount", "0.00")))
    if order_discount < Decimal("0.00"):
        raise ValidationError({"discount_amount": "Discount amount cannot be negative."})
    if tax_amount < Decimal("0.00"):
        raise ValidationError({"tax_amount": "Tax amount cannot be negative."})

    total_amount = max(Decimal("0.00"), (subtotal_sum - order_discount) + tax_amount)

    # 5. Order Number & Timestamp
    order_number = data.get("order_number")
    if not order_number:
        today_str = timezone.now().strftime("%Y%m%d")
        rand_suffix = uuid.uuid4().hex[:6].upper()
        order_number = f"ORD-{today_str}-{rand_suffix}"

    # Verify order_number uniqueness in workspace
    if Order.objects.for_workspace(workspace).filter(order_number=order_number).exists():
        raise ValidationError({"order_number": f"Order number '{order_number}' already exists in this workspace."})

    order_timestamp = data.get("order_timestamp") or timezone.now()
    order_date = data.get("order_date") or order_timestamp.date() if isinstance(order_timestamp, datetime) else date.today()

    initial_status = data.get("status", OrderStatus.PENDING)
    if initial_status not in OrderStatus.values:
        initial_status = OrderStatus.PENDING

    payment_method = data.get("payment_method", PaymentMethod.CASH)
    if payment_method not in PaymentMethod.values:
        payment_method = PaymentMethod.CASH

    # 6. Create Order Header
    order = Order.objects.create(
        workspace=workspace,
        order_number=order_number,
        customer=customer,
        branch=branch,
        order_date=order_date,
        order_timestamp=order_timestamp,
        status=initial_status,
        subtotal_amount=subtotal_sum,
        discount_amount=order_discount,
        tax_amount=tax_amount,
        total_amount=total_amount,
        payment_method=payment_method,
        created_by=user if user and user.is_authenticated else None,
        notes=data.get("notes", ""),
    )

    # 7. Create Line Items
    for item in validated_items:
        OrderItem.objects.create(
            order=order,
            product=item["product"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            discount=item["discount"],
            subtotal=item["subtotal"],
        )

    # 8. Emit Audit Log
    log_action(
        workspace=workspace,
        actor_user=user,
        action="ORDER_CREATED",
        entity_type="Order",
        entity_id=order.id,
        changes={
            "order_number": order.order_number,
            "total_amount": str(order.total_amount),
            "items_count": len(validated_items),
            "customer": customer.code,
        },
        ip_address=ip_address,
    )

    return order


def transition_order_status(
    order: Order,
    new_status: str,
    user,
    ip_address: Optional[str] = None,
) -> Order:
    """
    Controlled State Machine transition for orders:
    - PENDING -> CONFIRMED, CANCELLED
    - CONFIRMED -> COMPLETED, CANCELLED
    - COMPLETED -> [Terminal]
    - CANCELLED -> [Terminal]
    """
    valid_transitions = {
        OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
        OrderStatus.CONFIRMED: [OrderStatus.COMPLETED, OrderStatus.CANCELLED],
        OrderStatus.COMPLETED: [],
        OrderStatus.CANCELLED: [],
    }

    current = order.status
    allowed_targets = valid_transitions.get(current, [])

    if new_status not in allowed_targets:
        raise ValidationError(
            f"Invalid order transition from '{current}' to '{new_status}'. Allowed transitions: {allowed_targets or 'None (Terminal state)'}."
        )

    before_status = order.status
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    action_name = f"ORDER_{new_status}"
    log_action(
        workspace=order.workspace,
        actor_user=user,
        action=action_name,
        entity_type="Order",
        entity_id=order.id,
        changes={"before_status": before_status, "after_status": new_status},
        ip_address=ip_address,
    )

    return order


# =============================================================================
# SUPPLIER SERVICES
# =============================================================================

def create_supplier(workspace, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Supplier:
    """Creates a new supplier under the active workspace."""
    code = data.get("code", "").strip().upper()
    if not code:
        code = f"SUP-{uuid.uuid4().hex[:6].upper()}"

    supplier = Supplier.objects.create(
        workspace=workspace,
        code=code,
        name=data["name"].strip(),
        contact_name=data.get("contact_name", "").strip(),
        email=data.get("email", "").strip() or None,
        phone=data.get("phone", "").strip(),
        address=data.get("address", "").strip(),
        is_active=data.get("is_active", True),
    )
    log_action(
        workspace=workspace,
        actor_user=user,
        action="SUPPLIER_CREATED",
        entity_type="Supplier",
        entity_id=supplier.id,
        changes={"code": supplier.code, "name": supplier.name},
        ip_address=ip_address,
    )
    return supplier


def update_supplier(supplier: Supplier, user, data: Dict[str, Any], ip_address: Optional[str] = None) -> Supplier:
    """Updates supplier information with audit trail."""
    before = {"name": supplier.name, "is_active": supplier.is_active, "phone": supplier.phone}
    if "name" in data:
        supplier.name = data["name"].strip()
    if "contact_name" in data:
        supplier.contact_name = data["contact_name"].strip()
    if "email" in data:
        supplier.email = data["email"].strip() or None
    if "phone" in data:
        supplier.phone = data["phone"].strip()
    if "address" in data:
        supplier.address = data["address"].strip()
    if "is_active" in data:
        supplier.is_active = data["is_active"]
    supplier.save()
    log_action(
        workspace=supplier.workspace,
        actor_user=user,
        action="SUPPLIER_UPDATED",
        entity_type="Supplier",
        entity_id=supplier.id,
        changes={"before": before, "after": {"name": supplier.name, "is_active": supplier.is_active, "phone": supplier.phone}},
        ip_address=ip_address,
    )
    return supplier


def delete_supplier(supplier: Supplier, user, ip_address: Optional[str] = None) -> None:
    """Safely deletes a supplier or prevents deletion if receipts exist."""
    if supplier.goods_receipts.exists():
        raise ValidationError(
            f"Cannot delete supplier '{supplier.name}' because {supplier.goods_receipts.count()} goods receipts reference it. Deactivate instead."
        )
    sup_id = supplier.id
    ws = supplier.workspace
    supplier.delete()
    log_action(
        workspace=ws,
        actor_user=user,
        action="SUPPLIER_DELETED",
        entity_type="Supplier",
        entity_id=sup_id,
        changes={"deleted": True},
        ip_address=ip_address,
    )


# =============================================================================
# GOODS RECEIPT SERVICES (INBOUND INVENTORY WORKFLOW)
# =============================================================================

@transaction.atomic
def create_goods_receipt(
    workspace,
    user,
    data: Dict[str, Any],
    ip_address: Optional[str] = None,
) -> GoodsReceipt:
    """
    Creates a new Goods Receipt in DRAFT state.
    Stock balance is NOT altered at this stage.
    """
    # 1. Validate Supplier
    supplier_id = data.get("supplier_id")
    supplier = Supplier.objects.for_workspace(workspace).filter(id=supplier_id).first()
    if not supplier:
        raise ValidationError({"supplier_id": "Supplier does not exist in this workspace."})

    # 2. Validate Branch
    branch_id = data.get("branch_id")
    branch = Branch.objects.for_workspace(workspace).filter(id=branch_id).first()
    if not branch:
        raise ValidationError({"branch_id": "Branch does not exist in this workspace."})

    # 3. Receipt Number Generation
    receipt_number = data.get("receipt_number", "").strip().upper()
    if not receipt_number:
        today_str = timezone.now().strftime("%Y%m%d")
        rand_suffix = uuid.uuid4().hex[:4].upper()
        receipt_number = f"PN-{today_str}-{rand_suffix}"

    # 4. Receipt Dates
    receipt_date_val = data.get("receipt_date")
    if not receipt_date_val:
        receipt_date_val = timezone.now().date()
    elif isinstance(receipt_date_val, str):
        receipt_date_val = datetime.strptime(receipt_date_val, "%Y-%m-%d").date()

    expected_date_val = data.get("expected_date")
    if expected_date_val and isinstance(expected_date_val, str):
        expected_date_val = datetime.strptime(expected_date_val, "%Y-%m-%d").date()

    # 5. Validate Line Items
    raw_items = data.get("items", [])
    if not raw_items:
        raise ValidationError({"items": "A goods receipt must contain at least 1 item."})

    validated_items = []
    total_amount = Decimal("0.00")

    for idx, item in enumerate(raw_items):
        product_id = item.get("product_id")
        product = Product.objects.for_workspace(workspace).filter(id=product_id).first()
        if not product:
            raise ValidationError({f"items[{idx}].product_id": f"Product id {product_id} not found in workspace."})

        qty = int(item.get("quantity", 1))
        if qty <= 0:
            raise ValidationError({f"items[{idx}].quantity": "Quantity must be greater than 0."})

        unit_cost_val = Decimal(str(item.get("unit_cost", product.cost_price or product.unit_price)))
        if unit_cost_val < Decimal("0.00"):
            raise ValidationError({f"items[{idx}].unit_cost": "Unit cost cannot be negative."})

        line_total = Decimal(qty) * unit_cost_val
        total_amount += line_total
        validated_items.append({
            "product": product,
            "quantity": qty,
            "unit_cost": unit_cost_val,
            "line_total": line_total,
        })

    # 6. Create GoodsReceipt in DRAFT status
    receipt = GoodsReceipt.objects.create(
        workspace=workspace,
        receipt_number=receipt_number,
        supplier=supplier,
        branch=branch,
        receipt_date=receipt_date_val,
        expected_date=expected_date_val,
        status=GoodsReceiptStatus.DRAFT,
        total_amount=total_amount,
        notes=data.get("notes", ""),
        created_by=user if user and user.is_authenticated else None,
    )

    # 7. Create Line Items
    for item in validated_items:
        GoodsReceiptItem.objects.create(
            receipt=receipt,
            product=item["product"],
            quantity=item["quantity"],
            unit_cost=item["unit_cost"],
            line_total=item["line_total"],
        )

    # 8. Audit Log
    log_action(
        workspace=workspace,
        actor_user=user,
        action="GOODS_RECEIPT_CREATED",
        entity_type="GoodsReceipt",
        entity_id=receipt.id,
        changes={
            "receipt_number": receipt.receipt_number,
            "supplier": supplier.code,
            "branch": branch.code,
            "total_amount": str(receipt.total_amount),
            "items_count": len(validated_items),
        },
        ip_address=ip_address,
    )

    return receipt


def confirm_goods_receipt(
    receipt: GoodsReceipt,
    user,
    ip_address: Optional[str] = None,
) -> GoodsReceipt:
    """
    Transitions GoodsReceipt from DRAFT to CONFIRMED.
    """
    if receipt.status != GoodsReceiptStatus.DRAFT:
        raise ValidationError(
            f"Cannot confirm goods receipt with status '{receipt.status}'. Expected 'DRAFT'."
        )

    receipt.status = GoodsReceiptStatus.CONFIRMED
    receipt.save(update_fields=["status", "updated_at"])

    log_action(
        workspace=receipt.workspace,
        actor_user=user,
        action="GOODS_RECEIPT_CONFIRMED",
        entity_type="GoodsReceipt",
        entity_id=receipt.id,
        changes={"before_status": GoodsReceiptStatus.DRAFT, "after_status": GoodsReceiptStatus.CONFIRMED},
        ip_address=ip_address,
    )
    return receipt


@transaction.atomic
def receive_goods_receipt(
    receipt: GoodsReceipt,
    user,
    ip_address: Optional[str] = None,
) -> GoodsReceipt:
    """
    Finalizes goods receipt: transitions to RECEIVED and increments StockBalance.
    Uses row-level locking (select_for_update) on both receipt and StockBalance
    to prevent duplicate receiving and race conditions.
    """
    # 1. Lock receipt and verify status
    locked_receipt = GoodsReceipt.objects.select_for_update().get(id=receipt.id)
    if locked_receipt.status == GoodsReceiptStatus.RECEIVED:
        raise ValidationError("This goods receipt has already been received and stock was already updated.")
    if locked_receipt.status == GoodsReceiptStatus.CANCELLED:
        raise ValidationError("Cannot receive a cancelled goods receipt.")

    # 2. Update stock balances for each item with row-level locking
    workspace = locked_receipt.workspace
    branch = locked_receipt.branch

    for item in locked_receipt.items.select_related("product").all():
        stock_balance, created = StockBalance.objects.select_for_update().get_or_create(
            workspace=workspace,
            branch=branch,
            product=item.product,
            defaults={"quantity_on_hand": 0},
        )
        stock_balance.quantity_on_hand += item.quantity
        stock_balance.save(update_fields=["quantity_on_hand", "updated_at"])

    # 3. Transition receipt status to RECEIVED
    locked_receipt.status = GoodsReceiptStatus.RECEIVED
    locked_receipt.received_by = user if user and user.is_authenticated else None
    locked_receipt.received_at = timezone.now()
    locked_receipt.save(update_fields=["status", "received_by", "received_at", "updated_at"])

    # Sync caller's in-memory object
    receipt.status = GoodsReceiptStatus.RECEIVED
    receipt.received_by = locked_receipt.received_by
    receipt.received_at = locked_receipt.received_at

    # 4. Audit Log
    log_action(
        workspace=workspace,
        actor_user=user,
        action="GOODS_RECEIPT_RECEIVED",
        entity_type="GoodsReceipt",
        entity_id=locked_receipt.id,
        changes={
            "receipt_number": locked_receipt.receipt_number,
            "branch": branch.code,
            "status": GoodsReceiptStatus.RECEIVED,
            "items_count": locked_receipt.items.count(),
        },
        ip_address=ip_address,
    )

    return locked_receipt


def cancel_goods_receipt(
    receipt: GoodsReceipt,
    user,
    ip_address: Optional[str] = None,
) -> GoodsReceipt:
    """
    Cancels a DRAFT or CONFIRMED goods receipt.
    RECEIVED receipts cannot be cancelled to maintain inventory integrity.
    """
    receipt.refresh_from_db()
    if receipt.status == GoodsReceiptStatus.RECEIVED:
        raise ValidationError("Cannot cancel a goods receipt that has already been RECEIVED.")
    if receipt.status == GoodsReceiptStatus.CANCELLED:
        return receipt

    before_status = receipt.status
    receipt.status = GoodsReceiptStatus.CANCELLED
    receipt.save(update_fields=["status", "updated_at"])

    log_action(
        workspace=receipt.workspace,
        actor_user=user,
        action="GOODS_RECEIPT_CANCELLED",
        entity_type="GoodsReceipt",
        entity_id=receipt.id,
        changes={"before_status": before_status, "after_status": GoodsReceiptStatus.CANCELLED},
        ip_address=ip_address,
    )
    return receipt
