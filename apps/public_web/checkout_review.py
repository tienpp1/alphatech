"""Bind the public UI review to an expiring, session-scoped commercial snapshot.

This is consent consistency, not order idempotency or a session-write lock.
Placement supplies locked current products before any business writes.
"""
import hashlib
from decimal import Decimal

from django.core import signing


REVIEW_SALT = "public_web.checkout_review.v1"
REVIEW_MAX_AGE = 1800
REVIEW_MAX_LENGTH = 32768
REVIEW_REQUIRED_SESSION_KEY = "public_checkout_review_required"


def _money(value):
    return format(Decimal(value).normalize(), "f")


def review_snapshot(request, *, lines, delivery_method, subtotal, shipping_fee):
    """lines are (trusted product, integer quantity), never posted prices."""
    session_key = request.session.session_key or ""
    return {
        "scope": "public-retail-checkout-v1",
        "session": hashlib.sha256(session_key.encode("utf-8")).hexdigest(),
        "user": str(request.user.pk) if request.user.is_authenticated else None,
        "workspaces": sorted({str(product.workspace_id) for product, _ in lines}),
        "lines": [[product.pk, quantity, _money(product.unit_price)]
                  for product, quantity in sorted(lines, key=lambda row: row[0].pk)],
        "delivery_method": delivery_method,
        "subtotal": _money(subtotal), "shipping_fee": _money(shipping_fee),
        "total_amount": _money(subtotal + shipping_fee),
    }


def issue_checkout_review(request, cart, delivery_method, *, summary=None):
    if not request.session.session_key:
        # A first empty read must not create/save a session. A persisted nonempty
        # cart already has a key; otherwise the strict UI remains fail-closed.
        return ""
    summary = summary or cart.get_summary(delivery_method=delivery_method)
    payload = review_snapshot(request, lines=[(item.product, item.quantity) for item in summary["items"]],
        delivery_method=delivery_method, subtotal=summary["subtotal"], shipping_fee=summary["shipping_fee"])
    token = signing.dumps(payload, salt=REVIEW_SALT, compress=True)
    # Oversized reviews cannot silently fall back to the legacy headless path.
    return token if len(token) <= REVIEW_MAX_LENGTH else ""


def checkout_review_matches(request, *, lines, delivery_method, subtotal, shipping_fee):
    token = request.POST.get("checkout_review_token")
    required = (request.GET.get("review") == "1" or
                request.session.get(REVIEW_REQUIRED_SESSION_KEY) or token is not None)
    if not required:
        # Legacy headless POSTs outside the strict UI keep their prior contract.
        # The actual UI's ?review=1 is strict independently of session markers.
        # Old markers are read for compatibility, never issued/written by GET.
        return True
    if not isinstance(token, str) or not token or len(token) > REVIEW_MAX_LENGTH:
        return False
    try:
        supplied = signing.loads(token, salt=REVIEW_SALT, max_age=REVIEW_MAX_AGE)
    except (signing.BadSignature, ValueError, TypeError):
        return False
    expected = review_snapshot(request, lines=lines, delivery_method=delivery_method,
        subtotal=subtotal, shipping_fee=shipping_fee)
    return supplied == expected
