from django.contrib import admin
from apps.retail.models import (
    Category,
    Product,
    Branch,
    Customer,
    Order,
    OrderItem,
    Supplier,
    GoodsReceipt,
    GoodsReceiptItem,
    StockBalance,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "workspace", "parent", "is_active", "created_at")
    list_filter = ("workspace", "is_active")
    search_fields = ("name", "code")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "workspace", "category", "unit_price", "cost_price", "is_active")
    list_filter = ("workspace", "category", "is_active")
    search_fields = ("name", "sku")


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "workspace", "region", "phone", "is_active")
    list_filter = ("workspace", "region", "is_active")
    search_fields = ("name", "code", "address")


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "workspace", "customer_segment", "phone", "email", "is_active")
    list_filter = ("workspace", "customer_segment", "is_active")
    search_fields = ("name", "code", "phone", "email")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("subtotal",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "workspace", "customer", "branch", "order_date", "status", "total_amount")
    list_filter = ("workspace", "status", "branch", "payment_method")
    search_fields = ("order_number", "customer__name", "customer__code")
    inlines = [OrderItemInline]
    date_hierarchy = "order_date"


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "workspace", "contact_name", "phone", "email", "is_active")
    list_filter = ("workspace", "is_active")
    search_fields = ("name", "code", "contact_name", "phone")


class GoodsReceiptItemInline(admin.TabularInline):
    model = GoodsReceiptItem
    extra = 0
    readonly_fields = ("line_total",)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "workspace", "supplier", "branch", "receipt_date", "status", "total_amount")
    list_filter = ("workspace", "status", "branch", "supplier")
    search_fields = ("receipt_number", "supplier__name", "supplier__code")
    inlines = [GoodsReceiptItemInline]
    date_hierarchy = "receipt_date"


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("product", "branch", "workspace", "quantity_on_hand", "updated_at")
    list_filter = ("workspace", "branch", "product__category")
    search_fields = ("product__name", "product__sku", "branch__name", "branch__code")

