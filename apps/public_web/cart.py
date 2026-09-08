"""
Session-Backed Shopping Cart Engine for Public E-Commerce.
Reuses canonical Product, Category, and Branch models from apps.retail.
Guarantees 100% server-side price computation and quantity validation (quantity >= 1).
"""

from decimal import Decimal
from typing import Dict, List, Optional, Any
from django.http import HttpRequest
from apps.retail.models import Product, Branch, StockBalance
from apps.workspaces.models import Workspace, WorkspaceType


SESSION_CART_KEY = "public_shopping_cart"
STANDARD_SHIPPING_FEE = Decimal("30000.00")  # 30,000 VND standard fixed fee
FREE_SHIPPING_THRESHOLD = Decimal("5000000.00")  # Free shipping for orders >= 5,000,000 VND


class CartItem:
    """
    Encapsulates a single cart line item evaluated against the live database.
    """

    def __init__(self, product: Product, quantity: int):
        self.product = product
        self.quantity = max(1, int(quantity))
        self.unit_price = Decimal(str(product.unit_price))
        self.line_total = self.unit_price * Decimal(self.quantity)

    @property
    def image_url(self) -> Optional[str]:
        primary = self.product.primary_image
        if primary and primary.image:
            return primary.image.url
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product_id": self.product.id,
            "name": self.product.name,
            "sku": self.product.sku,
            "unit": self.product.unit,
            "unit_price": self.unit_price,
            "quantity": self.quantity,
            "line_total": self.line_total,
            "image_url": self.image_url,
            "category_name": self.product.category.name if self.product.category else "",
        }


class ShoppingCart:
    """
    Session-backed Shopping Cart manager.
    Session storage schema: { "<product_id_str>": <quantity_int> }
    """

    def __init__(self, request: HttpRequest):
        self.request = request
        self.session = request.session
        raw_cart = self.session.get(SESSION_CART_KEY)
        if not isinstance(raw_cart, dict):
            raw_cart = {}
            self.session[SESSION_CART_KEY] = raw_cart
        self.cart_data: Dict[str, int] = raw_cart

    def add(self, product_id: int, quantity: int = 1) -> bool:
        """
        Adds or increments quantity of an active, non-deleted product.
        Returns True if successfully added, False otherwise.
        """
        qty = max(1, int(quantity))
        product = Product.objects.filter(
            id=product_id,
            is_active=True,
            deleted_at__isnull=True,
            workspace__workspace_type=WorkspaceType.RETAIL,
        ).first()

        if not product:
            return False

        key = str(product_id)
        current_qty = self.cart_data.get(key, 0)
        self.cart_data[key] = current_qty + qty
        self._save()
        return True

    def set_quantity(self, product_id: int, quantity: int) -> bool:
        """
        Directly updates item quantity. If quantity <= 0, item is removed.
        """
        key = str(product_id)
        qty = int(quantity)
        if qty <= 0:
            return self.remove(product_id)

        # Verify product is still active
        if not Product.objects.filter(
            id=product_id,
            is_active=True,
            deleted_at__isnull=True,
            workspace__workspace_type=WorkspaceType.RETAIL,
        ).exists():
            return self.remove(product_id)

        self.cart_data[key] = qty
        self._save()
        return True

    def remove(self, product_id: int) -> bool:
        """
        Removes an item from cart.
        """
        key = str(product_id)
        if key in self.cart_data:
            del self.cart_data[key]
            self._save()
            return True
        return False

    def clear(self):
        """
        Clears the entire shopping cart from session.
        """
        self.cart_data = {}
        self.session[SESSION_CART_KEY] = {}
        self.session.modified = True

    @property
    def total_items_count(self) -> int:
        """
        Total quantity of all items in cart.
        """
        return sum(max(0, int(v)) for v in self.cart_data.values())

    @property
    def is_empty(self) -> bool:
        return len(self.cart_data) == 0

    def get_items(self) -> List[CartItem]:
        """
        Fetches live Product records from database and returns a list of CartItems.
        Automatically cleans up items referencing inactive or deleted products.
        """
        if not self.cart_data:
            return []

        product_ids = []
        for pid_str in list(self.cart_data.keys()):
            try:
                product_ids.append(int(pid_str))
            except (ValueError, TypeError):
                del self.cart_data[pid_str]
                self._save()

        if not product_ids:
            return []

        products = Product.objects.filter(
            id__in=product_ids,
            is_active=True,
            deleted_at__isnull=True,
            workspace__workspace_type=WorkspaceType.RETAIL,
        ).select_related("category").prefetch_related("images")

        product_map = {p.id: p for p in products}
        items = []
        stale_keys = []

        for key, qty in list(self.cart_data.items()):
            pid = int(key)
            product = product_map.get(pid)
            if product:
                items.append(CartItem(product=product, quantity=qty))
            else:
                stale_keys.append(key)

        # Clean stale products from session
        if stale_keys:
            for k in stale_keys:
                del self.cart_data[k]
            self._save()

        return items

    def get_subtotal(self) -> Decimal:
        """
        Computes subtotal from live database product prices.
        """
        items = self.get_items()
        return sum((item.line_total for item in items), Decimal("0.00"))

    def calculate_shipping_fee(self, delivery_method: str = "HOME_DELIVERY") -> Decimal:
        """
        Calculates deterministic shipping fee:
        - STORE_PICKUP: 0 VND
        - HOME_DELIVERY: 30,000 VND (0 VND if subtotal >= 5,000,000 VND)
        """
        if delivery_method == "STORE_PICKUP":
            return Decimal("0.00")
        subtotal = self.get_subtotal()
        if subtotal >= FREE_SHIPPING_THRESHOLD:
            return Decimal("0.00")
        return STANDARD_SHIPPING_FEE

    def get_summary(self, delivery_method: str = "HOME_DELIVERY") -> Dict[str, Any]:
        """
        Returns full cart summary with server-calculated totals.
        """
        items = self.get_items()
        subtotal = sum((item.line_total for item in items), Decimal("0.00"))
        shipping_fee = self.calculate_shipping_fee(delivery_method)
        total_amount = subtotal + shipping_fee

        return {
            "items": items,
            "items_count": len(items),
            "total_quantity": sum(item.quantity for item in items),
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total_amount": total_amount,
            "is_free_shipping": (shipping_fee == Decimal("0.00")),
            "free_shipping_threshold": FREE_SHIPPING_THRESHOLD,
            "delivery_method": delivery_method,
        }

    def _save(self):
        self.session[SESSION_CART_KEY] = self.cart_data
        self.session.modified = True


def get_cart(request: HttpRequest) -> ShoppingCart:
    """Helper to get or initialize ShoppingCart for request."""
    return ShoppingCart(request)
