"""
DRF Serializers for Retail Entities, Orders, and Analytics.
Adheres to docs/api-conventions.md.
"""

from decimal import Decimal
from rest_framework import serializers

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
    CustomerSegment,
    Supplier,
    GoodsReceipt,
    GoodsReceiptItem,
    GoodsReceiptStatus,
    StockBalance,
)


class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)
    products_count = serializers.IntegerField(source="products.count", read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "code",
            "parent",
            "parent_name",
            "description",
            "is_active",
            "products_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "product",
            "image",
            "image_url",
            "sort_order",
            "is_primary",
            "alt_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "image_url", "created_at", "updated_at"]

    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class ProductSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source="category",
        write_only=True,
    )
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_code = serializers.CharField(source="category.code", read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    primary_image_url = serializers.SerializerMethodField()
    is_deleted = serializers.BooleanField(read_only=True)
    days_until_permanent_delete = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "sku",
            "name",
            "category_id",
            "category_name",
            "category_code",
            "description",
            "unit",
            "unit_price",
            "cost_price",
            "is_active",
            "is_deleted",
            "deleted_at",
            "days_until_permanent_delete",
            "images",
            "primary_image_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_deleted", "deleted_at", "days_until_permanent_delete", "images", "primary_image_url", "created_at", "updated_at"]

    def get_primary_image_url(self, obj):
        primary = obj.primary_image
        if primary and primary.image:
            return primary.image.url
        return None


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = [
            "id",
            "code",
            "name",
            "address",
            "region",
            "latitude",
            "longitude",
            "phone",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "code",
            "name",
            "email",
            "phone",
            "address",
            "latitude",
            "longitude",
            "customer_segment",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.id", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "quantity",
            "unit_price",
            "discount",
            "subtotal",
        ]
        read_only_fields = ["id", "subtotal"]


class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(required=True, min_value=1)
    discount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )


class OrderCreateSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=True)
    branch_id = serializers.IntegerField(required=False, allow_null=True)
    order_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    order_date = serializers.DateField(required=False)
    order_timestamp = serializers.DateTimeField(required=False)
    status = serializers.ChoiceField(choices=OrderStatus.choices, default=OrderStatus.PENDING)
    discount_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )
    tax_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )
    payment_method = serializers.ChoiceField(
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = OrderItemInputSerializer(many=True, required=True, allow_empty=False)


class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="Direct")
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer_id",
            "customer_code",
            "customer_name",
            "branch_id",
            "branch_name",
            "order_date",
            "order_timestamp",
            "status",
            "total_amount",
            "items_count",
            "payment_method",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class OrderDetailSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default="System")

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "customer",
            "branch",
            "order_date",
            "order_timestamp",
            "status",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "payment_method",
            "created_by_username",
            "notes",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplierSerializer(serializers.ModelSerializer):
    goods_receipts_count = serializers.IntegerField(source="goods_receipts.count", read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id",
            "code",
            "name",
            "contact_name",
            "email",
            "phone",
            "address",
            "is_active",
            "goods_receipts_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GoodsReceiptItemSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    unit = serializers.CharField(source="product.unit", read_only=True)

    class Meta:
        model = GoodsReceiptItem
        fields = [
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "unit",
            "quantity",
            "unit_cost",
            "line_total",
        ]
        read_only_fields = ["id", "line_total"]


class GoodsReceiptItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=True)
    quantity = serializers.IntegerField(min_value=1, required=True)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.00"), required=False)


class GoodsReceiptCreateInputSerializer(serializers.Serializer):
    supplier_id = serializers.IntegerField(required=True)
    branch_id = serializers.IntegerField(required=True)
    receipt_number = serializers.CharField(max_length=50, required=False, allow_blank=True)
    receipt_date = serializers.DateField(required=False)
    expected_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = GoodsReceiptItemInputSerializer(many=True, required=True, allow_empty=False)


class GoodsReceiptListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    supplier_code = serializers.CharField(source="supplier.code", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    items_count = serializers.IntegerField(source="items.count", read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default="System")

    class Meta:
        model = GoodsReceipt
        fields = [
            "id",
            "receipt_number",
            "supplier_id",
            "supplier_code",
            "supplier_name",
            "branch_id",
            "branch_name",
            "receipt_date",
            "expected_date",
            "status",
            "total_amount",
            "items_count",
            "created_by_username",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class GoodsReceiptDetailSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    items = GoodsReceiptItemSerializer(many=True, read_only=True)
    created_by_username = serializers.CharField(source="created_by.username", read_only=True, default="System")
    received_by_username = serializers.CharField(source="received_by.username", read_only=True, default=None)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id",
            "receipt_number",
            "supplier",
            "branch",
            "receipt_date",
            "expected_date",
            "status",
            "total_amount",
            "notes",
            "created_by_username",
            "received_by_username",
            "received_at",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class StockBalanceSerializer(serializers.ModelSerializer):
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)
    category_name = serializers.CharField(source="product.category.name", read_only=True)
    branch_code = serializers.CharField(source="branch.code", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = StockBalance
        fields = [
            "id",
            "product_id",
            "product_sku",
            "product_name",
            "product_unit",
            "category_name",
            "branch_id",
            "branch_code",
            "branch_name",
            "quantity_on_hand",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
