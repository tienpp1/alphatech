"""
REST API Views for Retail Operations, Catalog, Orders, and Sales Analytics.
Adheres strictly to docs/api-conventions.md and workspace isolation rules.
"""

from rest_framework.views import APIView as DRFAPIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404

from apps.accounts.services import has_workspace_permission
from apps.workspaces.permissions import IsWorkspaceMember
from apps.retail.models import (
    Category,
    Product,
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
from apps.retail.filters import filter_products, filter_customers, filter_branches, filter_orders
from apps.retail.serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    BranchSerializer,
    CustomerSerializer,
    OrderListSerializer,
    OrderDetailSerializer,
    OrderCreateSerializer,
    SupplierSerializer,
    GoodsReceiptListSerializer,
    GoodsReceiptDetailSerializer,
    GoodsReceiptCreateInputSerializer,
    StockBalanceSerializer,
)
from apps.retail.services import (
    create_category,
    update_category,
    delete_category,
    create_product,
    update_product,
    soft_delete_product,
    restore_product,
    permanent_delete_product,
    delete_product,
    create_branch,
    create_customer,
    create_order,
    transition_order_status,
    create_supplier,
    update_supplier,
    delete_supplier,
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
from apps.retail.models import ProductImage
from apps.retail.selectors import (
    get_revenue_summary,
    get_revenue_timeseries,
    get_branch_revenue_breakdown,
    get_top_products,
    get_customer_sales_summary,
)
from apps.retail.stockout_services import (
    get_stockout_risk_dashboard_data,
    evaluate_product_stockout_risk,
)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def check_permission(request, perm_codename: str) -> bool:
    """Verifies that the caller possesses the specified workspace-scoped RBAC permission."""
    if not request.user or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    ws = getattr(request, "active_workspace", None)
    if not ws:
        return False
    return has_workspace_permission(request.user, ws, perm_codename)


class APIView(DRFAPIView):
    """Apply granular read permissions consistently to Retail API reads."""

    def check_permissions(self, request):
        super().check_permissions(request)
        if request.method not in ("GET", "HEAD"):
            return

        name = self.__class__.__name__
        if name.startswith(("Category", "Product", "Supplier", "GoodsReceipt", "StockBalance")):
            codename = "retail.view_product"
        elif name.startswith("Branch"):
            codename = "retail.view_branch"
        elif name.startswith("Customer"):
            codename = "retail.view_customer"
        elif name.startswith("Order"):
            codename = "retail.view_order"
        else:
            codename = "retail.view_analytics"

        if not check_permission(request, codename):
            raise PermissionDenied(f"Missing workspace permission: {codename}")


# ==============================================================================
# Category Endpoints
# ==============================================================================

class CategoryListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        categories = Category.objects.for_workspace(request.active_workspace)
        search = request.query_params.get("search")
        if search:
            categories = categories.filter(name__icontains=search.strip())
        serializer = CategorySerializer(categories, many=True)
        return Response({"success": True, "count": categories.count(), "data": serializer.data})

    def post(self, request):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            category = create_category(
                workspace=request.active_workspace,
                user=request.user,
                data=serializer.validated_data,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": "Category created.", "data": CategorySerializer(category).data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CategoryDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get_object(self, request, pk):
        return get_object_or_404(Category.objects.for_workspace(request.active_workspace), pk=pk)

    def get(self, request, pk):
        category = self.get_object(request, pk)
        return Response({"success": True, "data": CategorySerializer(category).data})

    def patch(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        category = self.get_object(request, pk)
        try:
            updated = update_category(
                category=category,
                user=request.user,
                data=request.data,
                ip_address=get_client_ip(request),
            )
            return Response({"success": True, "data": CategorySerializer(updated).data})
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        category = self.get_object(request, pk)
        try:
            delete_category(category, request.user, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Category deleted successfully."})
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "PROTECTED_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==============================================================================
# Product Endpoints
# ==============================================================================

class ProductListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Product.objects.for_workspace(request.active_workspace).select_related("category")
        qs = filter_products(qs, request.query_params)
        serializer = ProductSerializer(qs, many=True)
        return Response({"success": True, "count": qs.count(), "data": serializer.data})

    def post(self, request):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ProductSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            payload = serializer.validated_data.copy()
            if "category" in payload:
                payload["category_id"] = payload.pop("category").id
            product = create_product(
                workspace=request.active_workspace,
                user=request.user,
                data=payload,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": "Product created.", "data": ProductSerializer(product).data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProductDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get_object(self, request, pk):
        return get_object_or_404(Product.objects.for_workspace(request.active_workspace), pk=pk)

    def get(self, request, pk):
        product = self.get_object(request, pk)
        return Response({"success": True, "data": ProductSerializer(product).data})

    def patch(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = self.get_object(request, pk)
        try:
            updated = update_product(
                product=product,
                user=request.user,
                data=request.data,
                ip_address=get_client_ip(request),
            )
            return Response({"success": True, "data": ProductSerializer(updated).data})
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = self.get_object(request, pk)
        try:
            soft_delete_product(product, request.user, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Sản phẩm đã được chuyển vào thùng rác."})
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProductTrashAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Product.objects.for_workspace(request.active_workspace).filter(deleted_at__isnull=False).select_related("category")
        search = request.query_params.get("search") or request.query_params.get("q")
        if search:
            qs = qs.filter(Q(name__icontains=search.strip()) | Q(sku__icontains=search.strip()))
        serializer = ProductSerializer(qs.order_by("-deleted_at"), many=True)
        return Response({"success": True, "count": qs.count(), "data": serializer.data})


class ProductRestoreAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = get_object_or_404(Product.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            restored = restore_product(product, request.user, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Sản phẩm đã được khôi phục thành công.", "data": ProductSerializer(restored).data})
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "SKU_CONFLICT", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProductPermanentDeleteAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def delete(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = get_object_or_404(Product.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            permanent_delete_product(product, request.user, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Sản phẩm đã được xóa vĩnh viễn."})
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "PROTECTED_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ProductImageUploadAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = get_object_or_404(Product.objects.for_workspace(request.active_workspace), pk=pk)
        files = request.FILES.getlist("images") or ([request.FILES["image"]] if "image" in request.FILES else [])

        if not files:
            return Response(
                {"success": False, "error": {"code": "NO_FILE", "message": "Vui lòng chọn ít nhất một tệp ảnh để tải lên."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        saved_images = []
        is_primary_requested = request.data.get("is_primary") in (True, "true", "1")

        for idx, file in enumerate(files):
            try:
                img_obj = save_product_image(
                    workspace=request.active_workspace,
                    product=product,
                    uploaded_file=file,
                    alt_text=request.data.get("alt_text", ""),
                    is_primary=(is_primary_requested if idx == 0 else False),
                )
                saved_images.append(img_obj)
            except ValidationError as e:
                return Response(
                    {"success": False, "error": {"code": "INVALID_IMAGE", "message": str(e)}},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            {
                "success": True,
                "message": f"Đã tải lên {len(saved_images)} ảnh thành công.",
                "data": ProductImageSerializer(saved_images, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ProductImageDeleteAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def delete(self, request, pk, image_id):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = get_object_or_404(Product.objects.for_workspace(request.active_workspace), pk=pk)
        img = get_object_or_404(ProductImage.objects.filter(workspace=request.active_workspace, product=product), pk=image_id)
        delete_product_image(img)
        return Response({"success": True, "message": "Đã xóa ảnh sản phẩm thành công."})


class ProductImageSetPrimaryAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk, image_id):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        product = get_object_or_404(Product.objects.for_workspace(request.active_workspace), pk=pk)
        img = get_object_or_404(ProductImage.objects.filter(workspace=request.active_workspace, product=product), pk=image_id)
        set_primary_product_image(product, img)
        return Response({"success": True, "message": "Đã đặt làm ảnh đại diện chính thành công."})


# ==============================================================================
# Branch Endpoints
# ==============================================================================

class BranchListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Branch.objects.for_workspace(request.active_workspace)
        qs = filter_branches(qs, request.query_params)
        serializer = BranchSerializer(qs, many=True)
        return Response({"success": True, "count": qs.count(), "data": serializer.data})

    def post(self, request):
        if not check_permission(request, "retail.manage_branch"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_branch' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = BranchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            branch = create_branch(
                workspace=request.active_workspace,
                user=request.user,
                data=serializer.validated_data,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": "Branch created.", "data": BranchSerializer(branch).data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BranchDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get_object(self, request, pk):
        return get_object_or_404(Branch.objects.for_workspace(request.active_workspace), pk=pk)

    def get(self, request, pk):
        branch = self.get_object(request, pk)
        return Response({"success": True, "data": BranchSerializer(branch).data})


# ==============================================================================
# Customer Endpoints
# ==============================================================================

class CustomerListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Customer.objects.for_workspace(request.active_workspace)
        qs = filter_customers(qs, request.query_params)
        serializer = CustomerSerializer(qs, many=True)
        return Response({"success": True, "count": qs.count(), "data": serializer.data})

    def post(self, request):
        if not check_permission(request, "retail.manage_customer"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_customer' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CustomerSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            customer = create_customer(
                workspace=request.active_workspace,
                user=request.user,
                data=serializer.validated_data,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": "Customer created.", "data": CustomerSerializer(customer).data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CustomerDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get_object(self, request, pk):
        return get_object_or_404(Customer.objects.for_workspace(request.active_workspace), pk=pk)

    def get(self, request, pk):
        customer = self.get_object(request, pk)
        summary = get_customer_sales_summary(request.active_workspace, customer.id)
        data = CustomerSerializer(customer).data
        data["purchase_summary"] = summary
        return Response({"success": True, "data": data})


# ==============================================================================
# Order Endpoints
# ==============================================================================

class OrderListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = Order.objects.for_workspace(request.active_workspace).select_related("customer", "branch")
        qs = filter_orders(qs, request.query_params)
        serializer = OrderListSerializer(qs, many=True)
        return Response({"success": True, "count": qs.count(), "data": serializer.data})

    def post(self, request):
        if not check_permission(request, "retail.create_order"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.create_order' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = OrderCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            order = create_order(
                workspace=request.active_workspace,
                user=request.user,
                data=serializer.validated_data,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": "Order created successfully.", "data": OrderDetailSerializer(order).data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "ORDER_CREATION_FAILED", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class OrderDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get_object(self, request, pk):
        return get_object_or_404(
            Order.objects.for_workspace(request.active_workspace).select_related("customer", "branch", "created_by").prefetch_related("items__product"),
            pk=pk,
        )

    def get(self, request, pk):
        order = self.get_object(request, pk)
        return Response({"success": True, "data": OrderDetailSerializer(order).data})


class OrderConfirmAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "retail.manage_order"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_order' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = get_object_or_404(Order.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            updated = transition_order_status(
                order=order,
                new_status=OrderStatus.CONFIRMED,
                user=request.user,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": f"Order #{updated.order_number} confirmed.", "data": OrderDetailSerializer(updated).data}
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "INVALID_STATE_TRANSITION", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class OrderCancelAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "retail.manage_order"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_order' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = get_object_or_404(Order.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            updated = transition_order_status(
                order=order,
                new_status=OrderStatus.CANCELLED,
                user=request.user,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": f"Order #{updated.order_number} cancelled.", "data": OrderDetailSerializer(updated).data}
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "INVALID_STATE_TRANSITION", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


class OrderCompleteAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not check_permission(request, "retail.manage_order"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_order' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        order = get_object_or_404(Order.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            updated = transition_order_status(
                order=order,
                new_status=OrderStatus.COMPLETED,
                user=request.user,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": f"Order #{updated.order_number} completed.", "data": OrderDetailSerializer(updated).data}
            )
        except ValidationError as e:
            return Response(
                {"success": False, "error": {"code": "INVALID_STATE_TRANSITION", "message": str(e)}},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ==============================================================================
# Analytics Endpoints
# ==============================================================================

class RevenueSummaryAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        summary = get_revenue_summary(
            workspace=request.active_workspace,
            start_date=start_date,
            end_date=end_date,
            branch_id=branch_id,
        )
        return Response({"success": True, "data": summary})


class RevenueTimeseriesAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        interval = request.query_params.get("interval", "day")

        timeseries = get_revenue_timeseries(
            workspace=request.active_workspace,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            branch_id=branch_id,
        )
        return Response({"success": True, "count": len(timeseries), "data": timeseries})


class TopProductsAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        top_products = get_top_products(
            workspace=request.active_workspace,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
        )
        return Response({"success": True, "count": len(top_products), "data": top_products})


class BranchBreakdownAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        breakdown = get_branch_revenue_breakdown(
            workspace=request.active_workspace,
            start_date=start_date,
            end_date=end_date,
        )
        return Response({"success": True, "count": len(breakdown), "data": breakdown})


# ==============================================================================
# Supplier Endpoints
# ==============================================================================

class SupplierListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        suppliers = Supplier.objects.for_workspace(request.active_workspace)
        search = request.query_params.get("search")
        if search:
            suppliers = suppliers.filter(name__icontains=search.strip()) | suppliers.filter(code__icontains=search.strip())
        serializer = SupplierSerializer(suppliers, many=True)
        return Response({"success": True, "count": suppliers.count(), "data": serializer.data})

    def post(self, request):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SupplierSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            supplier = create_supplier(
                workspace=request.active_workspace,
                user=request.user,
                data=serializer.validated_data,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": "Supplier created.", "data": SupplierSerializer(supplier).data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class SupplierDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        supplier = get_object_or_404(Supplier.objects.for_workspace(request.active_workspace), pk=pk)
        return Response({"success": True, "data": SupplierSerializer(supplier).data})

    def put(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        supplier = get_object_or_404(Supplier.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            updated = update_supplier(supplier, request.user, request.data, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Supplier updated.", "data": SupplierSerializer(updated).data})
        except ValidationError as e:
            return Response({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if not check_permission(request, "retail.manage_product"):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission 'retail.manage_product' required."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        supplier = get_object_or_404(Supplier.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            delete_supplier(supplier, request.user, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Supplier deleted."})
        except ValidationError as e:
            return Response({"success": False, "error": {"code": "CONFLICT", "message": str(e)}}, status=status.HTTP_409_CONFLICT)


# ==============================================================================
# Goods Receiving Endpoints
# ==============================================================================

class GoodsReceiptListCreateAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        receipts = GoodsReceipt.objects.for_workspace(request.active_workspace).select_related("supplier", "branch", "created_by")
        
        status_filter = request.query_params.get("status")
        if status_filter:
            receipts = receipts.filter(status=status_filter)
        branch_id = request.query_params.get("branch_id")
        if branch_id:
            receipts = receipts.filter(branch_id=branch_id)
        supplier_id = request.query_params.get("supplier_id")
        if supplier_id:
            receipts = receipts.filter(supplier_id=supplier_id)

        serializer = GoodsReceiptListSerializer(receipts, many=True)
        return Response({"success": True, "count": receipts.count(), "data": serializer.data})

    def post(self, request):
        if not (check_permission(request, "retail.manage_product") or check_permission(request, "retail.manage_order")):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission required to create goods receipts."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = GoodsReceiptCreateInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            receipt = create_goods_receipt(
                workspace=request.active_workspace,
                user=request.user,
                data=serializer.validated_data,
                ip_address=get_client_ip(request),
            )
            return Response(
                {"success": True, "message": "Goods receipt created in DRAFT.", "data": GoodsReceiptDetailSerializer(receipt).data},
                status=status.HTTP_201_CREATED,
            )
        except ValidationError as e:
            return Response({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class GoodsReceiptDetailAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request, pk):
        receipt = get_object_or_404(
            GoodsReceipt.objects.for_workspace(request.active_workspace).select_related("supplier", "branch", "created_by", "received_by").prefetch_related("items__product"),
            pk=pk,
        )
        return Response({"success": True, "data": GoodsReceiptDetailSerializer(receipt).data})


class GoodsReceiptConfirmAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not (check_permission(request, "retail.manage_product") or check_permission(request, "retail.manage_order")):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission required to confirm goods receipts."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        receipt = get_object_or_404(GoodsReceipt.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            confirmed = confirm_goods_receipt(receipt, request.user, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Goods receipt CONFIRMED.", "data": GoodsReceiptDetailSerializer(confirmed).data})
        except ValidationError as e:
            return Response({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class GoodsReceiptReceiveAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not (check_permission(request, "retail.manage_product") or check_permission(request, "retail.manage_order")):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission required to finalize goods receipts."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        receipt = get_object_or_404(GoodsReceipt.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            received = receive_goods_receipt(receipt, request.user, ip_address=get_client_ip(request))
            return Response({
                "success": True,
                "message": "Goods receipt RECEIVED. Branch stock balances updated successfully.",
                "data": GoodsReceiptDetailSerializer(received).data,
            })
        except ValidationError as e:
            return Response({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


class GoodsReceiptCancelAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def post(self, request, pk):
        if not (check_permission(request, "retail.manage_product") or check_permission(request, "retail.manage_order")):
            return Response(
                {"success": False, "error": {"code": "FORBIDDEN", "message": "Permission required to cancel goods receipts."}},
                status=status.HTTP_403_FORBIDDEN,
            )
        receipt = get_object_or_404(GoodsReceipt.objects.for_workspace(request.active_workspace), pk=pk)
        try:
            cancelled = cancel_goods_receipt(receipt, request.user, ip_address=get_client_ip(request))
            return Response({"success": True, "message": "Goods receipt CANCELLED.", "data": GoodsReceiptDetailSerializer(cancelled).data})
        except ValidationError as e:
            return Response({"success": False, "error": {"code": "VALIDATION_ERROR", "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)


# ==============================================================================
# Stock Balance & AI Stockout Prediction Endpoints
# ==============================================================================

class StockBalanceListAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        qs = StockBalance.objects.for_workspace(request.active_workspace).select_related("product", "branch", "product__category")
        branch_id = request.query_params.get("branch_id")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        category_id = request.query_params.get("category_id")
        if category_id:
            qs = qs.filter(product__category_id=category_id)

        serializer = StockBalanceSerializer(qs, many=True)
        return Response({"success": True, "count": qs.count(), "data": serializer.data})


class StockoutRiskAPIView(APIView):
    permission_classes = [IsWorkspaceMember]

    def get(self, request):
        branch_id = request.query_params.get("branch_id")
        category_code = request.query_params.get("category")
        limit = int(request.query_params.get("limit", 50))

        data = get_stockout_risk_dashboard_data(
            workspace=request.active_workspace,
            branch_id=int(branch_id) if branch_id else None,
            category_code=category_code,
            limit=limit,
        )
        return Response({"success": True, "data": data})
