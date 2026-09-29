"""Safe branch allocation for strict home-delivery checkout.

The policy is intentionally opt-in through settings. Existing deployments that
do not yet have complete branch inventory remain on the legacy behavior until
the operator seeds balances and enables strict allocation.
"""

from dataclasses import dataclass
from math import atan2, cos, radians, sin, sqrt
from typing import Iterable, Optional, Sequence, Tuple

from django.conf import settings
from django.db import transaction

from apps.retail.models import Branch, Product, StockBalance
from apps.workspaces.models import Workspace


class FulfillmentError(Exception):
    """Expected customer-facing allocation failure with a safe message."""

    def __init__(self, message: str, code: str = "FULFILLMENT_UNAVAILABLE"):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class DeliveryCoordinate:
    latitude: float
    longitude: float


def parse_delivery_coordinates(latitude, longitude) -> Optional[DeliveryCoordinate]:
    """Validate optional browser coordinates without persisting them."""
    if latitude in (None, "") and longitude in (None, ""):
        return None
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError):
        raise FulfillmentError(
            "Vị trí giao hàng không hợp lệ. Bạn có thể bỏ qua GPS hoặc nhập lại vị trí.",
            code="INVALID_COORDINATES",
        )
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        raise FulfillmentError(
            "Vị trí giao hàng không hợp lệ. Bạn có thể bỏ qua GPS hoặc nhập lại vị trí.",
            code="INVALID_COORDINATES",
        )
    return DeliveryCoordinate(lat, lon)


def _distance_km(branch: Branch, coordinates: DeliveryCoordinate) -> float:
    """Haversine distance used only for deterministic candidate ordering."""
    if branch.latitude is None or branch.longitude is None:
        return float("inf")
    lat1, lon1 = radians(coordinates.latitude), radians(coordinates.longitude)
    lat2, lon2 = radians(float(branch.latitude)), radians(float(branch.longitude))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371.0 * 2 * atan2(sqrt(a), sqrt(max(0.0, 1 - a)))


def _candidate_branches(branches: Sequence[Branch], coordinates: Optional[DeliveryCoordinate]):
    default_code = getattr(settings, "HOME_DELIVERY_DEFAULT_BRANCH_CODE", "BR-D1").strip()
    default = next((branch for branch in branches if branch.code == default_code), None)
    if default is None:
        raise FulfillmentError(
            "Cấu hình kho giao hàng trung tâm chưa sẵn sàng. Vui lòng liên hệ cửa hàng.",
            code="DEFAULT_FULFILLMENT_BRANCH_MISSING",
        )

    fallback_codes = tuple(getattr(settings, "HOME_DELIVERY_FALLBACK_BRANCH_CODES", ()))
    fallback = [branch for branch in branches if branch.pk != default.pk and branch.code in fallback_codes]
    key = (lambda branch: (_distance_km(branch, coordinates), branch.pk)) if coordinates else (lambda branch: (branch.code, branch.pk))
    return [default, *sorted(fallback, key=key)]


def allocate_home_delivery_stock(
    *,
    workspace: Workspace,
    lines: Iterable[Tuple[int, int, str]],
    latitude=None,
    longitude=None,
) -> Branch:
    """Choose one branch and reserve every line atomically.

    ``lines`` contains ``(product_id, quantity, display_name)`` tuples. All
    candidate stock rows are locked before any quantity is changed. A missing
    balance is treated as zero, and a failure leaves every balance untouched.
    """
    coordinates = parse_delivery_coordinates(latitude, longitude)
    normalized_lines = []
    try:
        for product_id, quantity, name in lines:
            # Reject lossy int conversion (1.5 -> 1) and boolean quantities.
            if isinstance(quantity, bool) or not str(quantity).isdigit():
                raise ValueError
            normalized_lines.append((int(product_id), int(quantity), str(name)))
    except (TypeError, ValueError, OverflowError):
        raise FulfillmentError("Giỏ hàng không có số lượng hợp lệ.", code="INVALID_LINES")
    if not normalized_lines or any(quantity <= 0 for _, quantity, _ in normalized_lines):
        raise FulfillmentError("Giỏ hàng không có số lượng hợp lệ.", code="INVALID_LINES")
    combined = {}
    for product_id, quantity, name in normalized_lines:
        previous = combined.get(product_id, (0, name))
        combined[product_id] = (previous[0] + quantity, previous[1])
    normalized_lines = [(pid, qty, name) for pid, (qty, name) in sorted(combined.items())]

    with transaction.atomic():
        product_ids = [pid for pid, _, _ in normalized_lines]
        valid_ids = set(Product.objects.select_for_update().filter(
            workspace=workspace, pk__in=product_ids, is_active=True,
            deleted_at__isnull=True,
        ).order_by('pk').values_list('pk', flat=True))
        if valid_ids != set(product_ids):
            raise FulfillmentError("Sản phẩm không khả dụng trong giỏ hàng.", code="INVALID_LINES")
        branches = list(
            Branch.objects.select_for_update()
            .filter(workspace=workspace, is_active=True)
            .order_by("id")
        )
        candidates = _candidate_branches(branches, coordinates)
        product_ids = [product_id for product_id, _, _ in normalized_lines]
        balances = list(
            StockBalance.objects.select_for_update()
            .filter(workspace=workspace, branch_id__in=[branch.pk for branch in candidates], product_id__in=product_ids)
            .order_by("branch_id", "product_id")
        )
        balance_map = {(balance.branch_id, balance.product_id): balance for balance in balances}

        selected = None
        for branch in candidates:
            if all(
                (balance := balance_map.get((branch.pk, product_id))) is not None
                and balance.quantity_on_hand >= quantity
                for product_id, quantity, _ in normalized_lines
            ):
                selected = branch
                break

        if selected is None:
            shortages = []
            for product_id, requested, display_name in normalized_lines:
                available = sum(
                    max(0, balance_map.get((branch.pk, product_id)).quantity_on_hand)
                    for branch in candidates
                    if balance_map.get((branch.pk, product_id)) is not None
                )
                if available < requested:
                    shortages.append(f"{display_name} hiện chỉ còn {available} sản phẩm khả dụng trong các kho giao hàng đã cấu hình (yêu cầu: {requested})")
            if not shortages:
                raise FulfillmentError(
                    "Hàng đang phân bố ở nhiều kho; chưa có một chi nhánh đủ toàn bộ giỏ hàng. "
                    "Vui lòng điều chỉnh giỏ hàng hoặc liên hệ cửa hàng để được hỗ trợ.",
                    code="NO_SINGLE_BRANCH_STOCK",
                )
            raise FulfillmentError(
                "; ".join(shortages) + ". Quý khách vui lòng giảm số lượng hoặc liên hệ cửa hàng.",
                code="INSUFFICIENT_NETWORK_STOCK",
            )

        for product_id, quantity, _ in normalized_lines:
            balance = balance_map[(selected.pk, product_id)]
            balance.quantity_on_hand -= quantity
            balance.save(update_fields=["quantity_on_hand", "updated_at"])
        return selected
