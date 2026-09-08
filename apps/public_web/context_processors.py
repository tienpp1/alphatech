"""
Context processors for public website.
"""

from apps.public_web.cart import SESSION_CART_KEY


def cart_context(request):
    """
    Exposes cart_items_count to all public templates without extra DB queries.
    """
    raw_cart = request.session.get(SESSION_CART_KEY)
    if isinstance(raw_cart, dict):
        count = sum(max(0, int(v)) for v in raw_cart.values() if isinstance(v, (int, str)))
    else:
        count = 0

    return {
        "cart_items_count": count,
    }
