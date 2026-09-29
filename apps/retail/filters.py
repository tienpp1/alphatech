"""
Reusable filtering and search helpers for Retail queries.
"""

from django.db.models import Q
from django.utils.dateparse import parse_date


def filter_products(queryset, params):
    """Filters product queryset by category, active flag, trash/deleted status, sorting, and search query."""
    category_id = params.get("category_id") or params.get("category")
    is_active = params.get("is_active")
    search = params.get("search") or params.get("q")
    include_deleted = params.get("include_deleted")
    trash_only = params.get("trash_only")
    sort = params.get("sort")

    # Soft-delete filtering
    if str(trash_only).lower() in ("true", "1"):
        queryset = queryset.filter(deleted_at__isnull=False)
    elif str(include_deleted).lower() not in ("true", "1"):
        queryset = queryset.filter(deleted_at__isnull=True)

    if category_id:
        try:
            queryset = queryset.filter(category_id=int(category_id))
        except (ValueError, TypeError):
            pass
    if is_active is not None and is_active != "":
        if str(is_active).lower() in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        elif str(is_active).lower() in ("false", "0"):
            queryset = queryset.filter(is_active=False)
    if search:
        search = search.strip()
        queryset = queryset.filter(Q(name__icontains=search) | Q(sku__icontains=search) | Q(description__icontains=search))

    # Sorting
    if sort == "name_asc":
        queryset = queryset.order_by("name")
    elif sort == "name_desc":
        queryset = queryset.order_by("-name")
    elif sort == "price_asc":
        queryset = queryset.order_by("unit_price")
    elif sort == "price_desc":
        queryset = queryset.order_by("-unit_price")
    elif sort == "created_asc":
        queryset = queryset.order_by("created_at")
    elif sort == "updated_desc":
        queryset = queryset.order_by("-updated_at")
    else:
        queryset = queryset.order_by("-created_at")

    return queryset


def filter_customers(queryset, params):
    """Filters customer queryset by segment, active flag, and search query."""
    segment = params.get("customer_segment") or params.get("segment")
    is_active = params.get("is_active")
    search = params.get("search")

    if segment:
        queryset = queryset.filter(customer_segment=segment.upper())
    if is_active is not None:
        if str(is_active).lower() in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        elif str(is_active).lower() in ("false", "0"):
            queryset = queryset.filter(is_active=False)
    if search:
        search = search.strip()
        queryset = queryset.filter(
            Q(name__icontains=search)
            | Q(code__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
        )
    return queryset


def filter_branches(queryset, params):
    """Filters branch queryset by region, active flag, and search query."""
    region = params.get("region")
    is_active = params.get("is_active")
    search = params.get("search")

    if region:
        queryset = queryset.filter(region__icontains=region)
    if is_active is not None:
        if str(is_active).lower() in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        elif str(is_active).lower() in ("false", "0"):
            queryset = queryset.filter(is_active=False)
    if search:
        search = search.strip()
        queryset = queryset.filter(Q(name__icontains=search) | Q(code__icontains=search) | Q(address__icontains=search))
    return queryset


def filter_orders(queryset, params):
    """Filters order queryset by status, branch, customer, date range, and search query."""
    status_val = params.get("status")
    branch_id = params.get("branch_id")
    customer_id = params.get("customer_id")
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    search = params.get("search")

    if status_val:
        queryset = queryset.filter(status=status_val.upper())
    if branch_id:
        try:
            queryset = queryset.filter(branch_id=int(branch_id))
        except (ValueError, TypeError):
            pass
    if customer_id:
        try:
            queryset = queryset.filter(customer_id=int(customer_id))
        except (ValueError, TypeError):
            pass
    if start_date:
        parsed_start = parse_date(str(start_date).strip()) if isinstance(start_date, (str, bytes)) else start_date
        if parsed_start:
            queryset = queryset.filter(order_date__gte=parsed_start)
    if end_date:
        parsed_end = parse_date(str(end_date).strip()) if isinstance(end_date, (str, bytes)) else end_date
        if parsed_end:
            queryset = queryset.filter(order_date__lte=parsed_end)
    if search:
        search = search.strip()
        queryset = queryset.filter(Q(order_number__icontains=search) | Q(customer__name__icontains=search))
    return queryset
