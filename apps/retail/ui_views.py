"""
UI Template Views for Retail Dashboard, Catalog, Orders, and Customers.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.contrib import messages

from apps.retail.models import (
    Category,
    Product,
    ProductImage,
    Branch,
    Customer,
    Order,
    OrderStatus,
    Supplier,
    GoodsReceipt,
    GoodsReceiptItem,
    GoodsReceiptStatus,
    StockBalance,
)
from apps.retail.selectors import (
    get_revenue_summary,
    get_revenue_timeseries,
    get_top_products,
    get_branch_revenue_breakdown,
)
from apps.retail.services import (
    create_product,
    update_product,
    soft_delete_product,
    restore_product,
    permanent_delete_product,
    transition_order_status,
    create_goods_receipt,
    confirm_goods_receipt,
    receive_goods_receipt,
    cancel_goods_receipt,
)
from apps.retail.image_services import (
    save_product_image,
    delete_product_image,
    set_primary_product_image,
)
from apps.audit.models import AuditLog
from apps.accounts.services import has_workspace_permission
from apps.workspaces.models import WorkspaceType
from apps.workspaces.services import resolve_authorized_ui_workspace
from apps.retail.stockout_services import get_stockout_risk_dashboard_data


def _retail_workspace(request, permission_codename):
    return resolve_authorized_ui_workspace(request, WorkspaceType.RETAIL, permission_codename)


@login_required
def retail_dashboard_view(request):
    """Retail Sales, Operational Performance, and AI Stockout Prediction Dashboard."""
    workspace = _retail_workspace(request, "retail.view_analytics")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    summary = get_revenue_summary(workspace)
    top_products = get_top_products(workspace, limit=5)
    branch_breakdown = get_branch_revenue_breakdown(workspace)
    recent_orders = (
        Order.objects.for_workspace(workspace)
        .select_related("customer", "branch")
        .order_by("-order_timestamp")[:10]
    )

    timeseries = get_revenue_timeseries(workspace, interval="day")
    stockout_data = get_stockout_risk_dashboard_data(workspace, limit=8)

    context = {
        "summary": summary,
        "top_products": top_products,
        "branch_breakdown": branch_breakdown,
        "recent_orders": recent_orders,
        "timeseries": timeseries,
        "stockout_data": stockout_data,
        "active_tab": "retail_dashboard",
    }
    return render(request, "retail/dashboard.html", context)


@login_required
def retail_products_view(request):
    """Product Catalog Listing View with Search, Category & Status Filter, Sorting, and Trash Counter."""
    workspace = _retail_workspace(request, "retail.view_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")

    category_id = request.GET.get("category", "").strip()
    status_filter = request.GET.get("status", "").strip()
    search_q = request.GET.get("q", "").strip()
    sort_option = request.GET.get("sort", "").strip()

    qs = Product.objects.for_workspace(workspace).filter(deleted_at__isnull=True).select_related("category").prefetch_related("images")

    if category_id:
        qs = qs.filter(category_id=category_id)
    if status_filter == "active":
        qs = qs.filter(is_active=True)
    elif status_filter == "inactive":
        qs = qs.filter(is_active=False)
    if search_q:
        qs = qs.filter(Q(name__icontains=search_q) | Q(sku__icontains=search_q) | Q(description__icontains=search_q))

    if sort_option == "name_asc":
        qs = qs.order_by("name")
    elif sort_option == "name_desc":
        qs = qs.order_by("-name")
    elif sort_option == "price_asc":
        qs = qs.order_by("unit_price")
    elif sort_option == "price_desc":
        qs = qs.order_by("-unit_price")
    elif sort_option == "created_asc":
        qs = qs.order_by("created_at")
    elif sort_option == "updated_desc":
        qs = qs.order_by("-updated_at")
    else:
        qs = qs.order_by("-created_at")

    categories = Category.objects.for_workspace(workspace).filter(is_active=True).order_by("name")
    trash_count = Product.objects.for_workspace(workspace).filter(deleted_at__isnull=False).count()

    context = {
        "products": qs,
        "categories": categories,
        "selected_category": category_id,
        "selected_status": status_filter,
        "search_q": search_q,
        "sort_option": sort_option,
        "trash_count": trash_count,
        "can_manage": can_manage,
        "active_tab": "retail_products",
    }
    return render(request, "retail/products.html", context)


@login_required
def retail_product_create_view(request):
    """Create a new technology product with optional image upload."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền thêm mới sản phẩm trong không gian làm việc này.")

    categories = Category.objects.for_workspace(workspace).filter(is_active=True).order_by("name")
    error_message = None

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        sku = request.POST.get("sku", "").strip().upper()
        category_id = request.POST.get("category_id")
        unit = request.POST.get("unit", "cái").strip()
        unit_price = request.POST.get("unit_price", "0").strip()
        cost_price = request.POST.get("cost_price", "0").strip()
        description = request.POST.get("description", "").strip()
        is_active = request.POST.get("is_active") in ("on", "true", "1")

        if not name or not sku or not category_id:
            error_message = "Vui lòng nhập đầy đủ các trường bắt buộc (Tên sản phẩm, Mã SKU, Danh mục)."
        else:
            try:
                product = create_product(
                    workspace=workspace,
                    user=request.user,
                    data={
                        "name": name,
                        "sku": sku,
                        "category_id": category_id,
                        "unit": unit,
                        "unit_price": unit_price,
                        "cost_price": cost_price,
                        "description": description,
                        "is_active": is_active,
                    },
                    ip_address=request.META.get("REMOTE_ADDR"),
                )

                # Process uploaded images
                uploaded_files = request.FILES.getlist("images")
                for idx, file in enumerate(uploaded_files):
                    try:
                        save_product_image(
                            workspace=workspace,
                            product=product,
                            uploaded_file=file,
                            alt_text=product.name,
                            is_primary=(idx == 0),
                        )
                    except Exception as img_err:
                        messages.warning(request, f"Không thể lưu một số hình ảnh: {str(img_err)}")

                messages.success(request, f"Tạo sản phẩm '{product.name}' thành công!")
                return redirect(f"/retail/products/{product.id}/")
            except ValidationError as e:
                if isinstance(e.message_dict if hasattr(e, "message_dict") else None, dict):
                    err_msgs = [f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()]
                    error_message = " ".join(err_msgs)
                else:
                    error_message = str(e)
            except Exception as ex:
                error_message = f"Đã xảy ra lỗi khi tạo sản phẩm: {str(ex)}"

    context = {
        "categories": categories,
        "error_message": error_message,
        "can_manage": can_manage,
        "active_tab": "retail_products",
    }
    return render(request, "retail/product_create.html", context)


@login_required
def retail_product_detail_view(request, pk):
    """Detailed view for a single product including specifications, images, and audit logs."""
    workspace = _retail_workspace(request, "retail.view_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    product = get_object_or_404(
        Product.objects.for_workspace(workspace).select_related("category", "deleted_by").prefetch_related("images"),
        pk=pk,
    )

    categories = Category.objects.for_workspace(workspace).filter(is_active=True).order_by("name")
    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")

    # Fetch recent audit history
    audit_logs = AuditLog.objects.filter(
        workspace=workspace,
        entity_type="Product",
        entity_id=str(product.id),
    ).order_by("-timestamp")[:10]

    context = {
        "product": product,
        "categories": categories,
        "audit_logs": audit_logs,
        "can_manage": can_manage,
        "active_tab": "retail_products",
    }
    return render(request, "retail/product_detail.html", context)


@login_required
def retail_product_edit_view(request, pk):
    """Save changes to product attributes."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền chỉnh sửa sản phẩm.")

    product = get_object_or_404(Product.objects.for_workspace(workspace), pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        sku = request.POST.get("sku", "").strip().upper()
        category_id = request.POST.get("category_id")
        unit = request.POST.get("unit", "cái").strip()
        unit_price = request.POST.get("unit_price", "0").strip()
        cost_price = request.POST.get("cost_price", "0").strip()
        description = request.POST.get("description", "").strip()
        is_active = request.POST.get("is_active") in ("on", "true", "1")

        try:
            update_data = {
                "name": name,
                "sku": sku,
                "category_id": category_id,
                "unit": unit,
                "unit_price": unit_price,
                "cost_price": cost_price,
                "description": description,
                "is_active": is_active,
            }
            update_product(product, request.user, update_data, ip_address=request.META.get("REMOTE_ADDR"))
            messages.success(request, f"Cập nhật thông tin sản phẩm '{product.name}' thành công!")
        except ValidationError as e:
            if hasattr(e, "message_dict"):
                err_msgs = [f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()]
                messages.error(request, " ".join(err_msgs))
            else:
                messages.error(request, str(e))
        except Exception as ex:
            messages.error(request, f"Lỗi cập nhật: {str(ex)}")

    return redirect(f"/retail/products/{product.id}/")


@login_required
def retail_product_delete_view(request, pk):
    """Soft delete a product and send it to Trash."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền xóa sản phẩm.")

    product = get_object_or_404(Product.objects.for_workspace(workspace), pk=pk)

    if request.method == "POST":
        soft_delete_product(product, request.user, ip_address=request.META.get("REMOTE_ADDR"))
        messages.success(request, f"Sản phẩm '{product.name}' đã được chuyển vào Thùng rác. Sản phẩm sẽ được giữ trong 7 ngày.")

    return redirect("/retail/products/")


@login_required
def retail_product_trash_view(request):
    """View soft-deleted products in Trash with retention countdown."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")

    search_q = request.GET.get("q", "").strip()
    qs = Product.objects.for_workspace(workspace).filter(deleted_at__isnull=False).select_related("category", "deleted_by").prefetch_related("images").order_by("-deleted_at")

    if search_q:
        qs = qs.filter(Q(name__icontains=search_q) | Q(sku__icontains=search_q))

    context = {
        "deleted_products": qs,
        "search_q": search_q,
        "can_manage": can_manage,
        "active_tab": "retail_products",
    }
    return render(request, "retail/product_trash.html", context)


@login_required
def retail_product_restore_view(request, pk):
    """Restore a product from Trash."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền khôi phục sản phẩm.")

    product = get_object_or_404(Product.objects.for_workspace(workspace), pk=pk)

    if request.method == "POST":
        try:
            restore_product(product, request.user, ip_address=request.META.get("REMOTE_ADDR"))
            messages.success(request, f"Khôi phục sản phẩm '{product.name}' ({product.sku}) thành công!")
            return redirect(f"/retail/products/{product.id}/")
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect("/retail/products/trash/")

    return redirect("/retail/products/trash/")


@login_required
def retail_product_permanent_delete_view(request, pk):
    """Permanently delete a product (requires manager/admin)."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền xóa vĩnh viễn sản phẩm.")

    product = get_object_or_404(Product.objects.for_workspace(workspace), pk=pk)

    if request.method == "POST":
        try:
            name = product.name
            sku = product.sku
            permanent_delete_product(product, request.user, ip_address=request.META.get("REMOTE_ADDR"))
            messages.success(request, f"Đã xóa vĩnh viễn sản phẩm '{name}' [{sku}] khỏi hệ thống.")
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as ex:
            messages.error(request, f"Lỗi khi xóa vĩnh viễn: {str(ex)}")

    return redirect("/retail/products/trash/")


@login_required
def retail_product_image_upload_view(request, pk):
    """Upload one or multiple images for a product."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền quản lý ảnh sản phẩm.")

    product = get_object_or_404(Product.objects.for_workspace(workspace), pk=pk)

    if request.method == "POST":
        files = request.FILES.getlist("images") or ([request.FILES["image"]] if "image" in request.FILES else [])
        if not files:
            messages.error(request, "Vui lòng chọn ít nhất một tệp ảnh để tải lên.")
        else:
            saved_count = 0
            for idx, file in enumerate(files):
                try:
                    save_product_image(
                        workspace=workspace,
                        product=product,
                        uploaded_file=file,
                        alt_text=product.name,
                    )
                    saved_count += 1
                except ValidationError as e:
                    messages.error(request, f"Lỗi tệp '{file.name}': {str(e)}")
                except Exception as ex:
                    messages.error(request, f"Lỗi xử lý ảnh '{file.name}': {str(ex)}")

            if saved_count > 0:
                messages.success(request, f"Đã tải lên {saved_count} ảnh thành công cho sản phẩm '{product.name}'.")

    return redirect(f"/retail/products/{product.id}/")


@login_required
def retail_product_image_delete_view(request, pk, image_id):
    """Delete an individual product image."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền xóa ảnh sản phẩm.")

    product = get_object_or_404(Product.objects.for_workspace(workspace), pk=pk)
    img = get_object_or_404(ProductImage.objects.filter(workspace=workspace, product=product), pk=image_id)

    if request.method == "POST":
        delete_product_image(img)
        messages.success(request, "Đã xóa ảnh sản phẩm thành công.")

    return redirect(f"/retail/products/{product.id}/")


@login_required
def retail_product_image_set_primary_view(request, pk, image_id):
    """Set an image as the primary image."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    can_manage = request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product")
    if not can_manage:
        raise PermissionDenied("Bạn không có quyền quản lý ảnh sản phẩm.")

    product = get_object_or_404(Product.objects.for_workspace(workspace), pk=pk)
    img = get_object_or_404(ProductImage.objects.filter(workspace=workspace, product=product), pk=image_id)

    if request.method == "POST":
        set_primary_product_image(product, img)
        messages.success(request, "Đã đặt làm ảnh đại diện chính thành công.")

    return redirect(f"/retail/products/{product.id}/")


@login_required
def retail_orders_view(request):
    """Orders Operational List View."""
    workspace = _retail_workspace(request, "retail.view_order")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    status_filter = request.GET.get("status")
    search_q = request.GET.get("q")

    qs = Order.objects.for_workspace(workspace).select_related("customer", "branch").order_by("-order_timestamp")
    if status_filter:
        qs = qs.filter(status=status_filter.upper())
    if search_q:
        qs = qs.filter(order_number__icontains=search_q.strip())

    context = {
        "orders": qs,
        "status_filter": status_filter or "",
        "statuses": OrderStatus.values,
        "search_q": search_q or "",
        "active_tab": "retail_orders",
    }
    return render(request, "retail/orders.html", context)


@login_required
def retail_order_detail_view(request, pk):
    """Order Detail & State Management View."""
    workspace = _retail_workspace(request, "retail.view_order")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    order = get_object_or_404(
        Order.objects.for_workspace(workspace).select_related("customer", "branch", "created_by").prefetch_related("items__product"),
        pk=pk,
    )

    if request.method == "POST":
        if not has_workspace_permission(request.user, workspace, "retail.manage_order"):
            raise PermissionDenied("Missing workspace permission: retail.manage_order")
        action = request.POST.get("action")
        if action == "confirm":
            transition_order_status(order, OrderStatus.CONFIRMED, request.user)
        elif action == "complete":
            transition_order_status(order, OrderStatus.COMPLETED, request.user)
        elif action == "cancel":
            transition_order_status(order, OrderStatus.CANCELLED, request.user)
        return redirect("retail_order_detail", pk=order.pk)

    context = {
        "order": order,
        "items": order.items.all(),
        "active_tab": "retail_orders",
        "can_manage": request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_order"),
    }
    return render(request, "retail/order_detail.html", context)


@login_required
def retail_customers_view(request):
    """Customer Directory View."""
    workspace = _retail_workspace(request, "retail.view_customer")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    qs = Customer.objects.for_workspace(workspace).order_by("name")
    search_q = request.GET.get("q")
    if search_q:
        qs = qs.filter(name__icontains=search_q.strip())

    context = {
        "customers": qs,
        "search_q": search_q or "",
        "active_tab": "retail_customers",
    }
    return render(request, "retail/customers.html", context)


@login_required
def retail_branches_view(request):
    """Branch Outlets View."""
    workspace = _retail_workspace(request, "retail.view_branch")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    branches = Branch.objects.for_workspace(workspace).order_by("region", "name")
    context = {
        "branches": branches,
        "active_tab": "retail_branches",
    }
    return render(request, "retail/branches.html", context)


# ==============================================================================
# Goods Receiving (Nhập Hàng) UI Views
# ==============================================================================

@login_required
def retail_goods_receiving_list_view(request):
    """Goods Receiving Documents (Phiếu Nhập Hàng) List View."""
    workspace = _retail_workspace(request, "retail.view_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    status_filter = request.GET.get("status")
    branch_id = request.GET.get("branch_id")
    supplier_id = request.GET.get("supplier_id")
    search_q = request.GET.get("q")

    qs = GoodsReceipt.objects.for_workspace(workspace).select_related("supplier", "branch", "created_by").order_by("-receipt_date", "-created_at")

    if status_filter:
        qs = qs.filter(status=status_filter.upper())
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if supplier_id:
        qs = qs.filter(supplier_id=supplier_id)
    if search_q:
        qs = qs.filter(receipt_number__icontains=search_q.strip())

    # Summary KPI counts
    all_receipts = GoodsReceipt.objects.for_workspace(workspace)
    draft_count = all_receipts.filter(status=GoodsReceiptStatus.DRAFT).count()
    confirmed_count = all_receipts.filter(status=GoodsReceiptStatus.CONFIRMED).count()
    received_count = all_receipts.filter(status=GoodsReceiptStatus.RECEIVED).count()

    suppliers = Supplier.objects.for_workspace(workspace).filter(is_active=True)
    branches = Branch.objects.for_workspace(workspace).filter(is_active=True)

    context = {
        "receipts": qs,
        "status_filter": status_filter or "",
        "statuses": GoodsReceiptStatus.values,
        "suppliers": suppliers,
        "branches": branches,
        "selected_branch": int(branch_id) if branch_id else None,
        "selected_supplier": int(supplier_id) if supplier_id else None,
        "search_q": search_q or "",
        "draft_count": draft_count,
        "confirmed_count": confirmed_count,
        "received_count": received_count,
        "active_tab": "retail_goods_receiving",
        "can_manage": request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product"),
    }
    return render(request, "retail/goods_receiving_list.html", context)


@login_required
def retail_goods_receiving_create_view(request):
    """Create New Goods Receipt Document View."""
    workspace = _retail_workspace(request, "retail.manage_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    suppliers = Supplier.objects.for_workspace(workspace).filter(is_active=True)
    branches = Branch.objects.for_workspace(workspace).filter(is_active=True)
    products = Product.objects.for_workspace(workspace).filter(is_active=True).order_by("name")

    if request.method == "POST":
        try:
            supplier_id = int(request.POST.get("supplier_id"))
            branch_id = int(request.POST.get("branch_id"))
            receipt_date = request.POST.get("receipt_date")
            expected_date = request.POST.get("expected_date") or None
            notes = request.POST.get("notes", "").strip()

            product_ids = request.POST.getlist("item_product_id[]")
            quantities = request.POST.getlist("item_quantity[]")
            unit_costs = request.POST.getlist("item_unit_cost[]")

            items = []
            for p_id, qty, cost in zip(product_ids, quantities, unit_costs):
                if p_id and int(qty) > 0:
                    items.append({
                        "product_id": int(p_id),
                        "quantity": int(qty),
                        "unit_cost": cost,
                    })

            data = {
                "supplier_id": supplier_id,
                "branch_id": branch_id,
                "receipt_date": receipt_date,
                "expected_date": expected_date,
                "notes": notes,
                "items": items,
            }

            receipt = create_goods_receipt(workspace, request.user, data)
            return redirect("retail_goods_receiving_detail", pk=receipt.pk)
        except Exception as e:
            context = {
                "suppliers": suppliers,
                "branches": branches,
                "products": products,
                "error_message": str(e),
                "active_tab": "retail_goods_receiving",
            }
            return render(request, "retail/goods_receiving_create.html", context)

    context = {
        "suppliers": suppliers,
        "branches": branches,
        "products": products,
        "active_tab": "retail_goods_receiving",
    }
    return render(request, "retail/goods_receiving_create.html", context)


@login_required
def retail_goods_receiving_detail_view(request, pk):
    """Goods Receipt Detail View with Lifecycle Action Handlers."""
    workspace = _retail_workspace(request, "retail.view_product")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    receipt = get_object_or_404(
        GoodsReceipt.objects.for_workspace(workspace).select_related("supplier", "branch", "created_by", "received_by").prefetch_related("items__product"),
        pk=pk,
    )

    if request.method == "POST":
        if not has_workspace_permission(request.user, workspace, "retail.manage_product"):
            raise PermissionDenied("Missing workspace permission: retail.manage_product")
        action = request.POST.get("action")
        try:
            if action == "confirm":
                confirm_goods_receipt(receipt, request.user)
            elif action == "receive":
                receive_goods_receipt(receipt, request.user)
            elif action == "cancel":
                cancel_goods_receipt(receipt, request.user)
            return redirect("retail_goods_receiving_detail", pk=receipt.pk)
        except Exception as e:
            context = {
                "receipt": receipt,
                "items": receipt.items.all(),
                "error_message": str(e),
                "active_tab": "retail_goods_receiving",
            }
            return render(request, "retail/goods_receiving_detail.html", context)

    context = {
        "receipt": receipt,
        "items": receipt.items.all(),
        "active_tab": "retail_goods_receiving",
        "can_manage": request.user.is_superuser or has_workspace_permission(request.user, workspace, "retail.manage_product"),
    }
    return render(request, "retail/goods_receiving_detail.html", context)


@login_required
def retail_stockout_risk_view(request):
    """Comprehensive Stockout Risk Prediction and Reorder Recommendation View."""
    workspace = _retail_workspace(request, "retail.view_analytics")
    if not workspace:
        return render(request, "retail/no_workspace.html")

    branch_id = request.GET.get("branch_id")
    category = request.GET.get("category")

    stockout_data = get_stockout_risk_dashboard_data(
        workspace=workspace,
        branch_id=int(branch_id) if branch_id else None,
        category_code=category,
        limit=100,
    )

    branches = Branch.objects.for_workspace(workspace).filter(is_active=True)
    categories = Category.objects.for_workspace(workspace).filter(is_active=True)

    context = {
        "stockout_data": stockout_data,
        "branches": branches,
        "categories": categories,
        "selected_branch": int(branch_id) if branch_id else None,
        "selected_category": category or "",
        "active_tab": "retail_goods_receiving",
    }
    return render(request, "retail/stockout_risk.html", context)
