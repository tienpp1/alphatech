"""
URL Configuration for Retail Application (REST APIs & Web UI).
"""

from django.urls import path
from apps.retail import views
from apps.retail import ui_views

urlpatterns = [
    # =========================================================================
    # REST APIs (/api/v1/retail/...)
    # =========================================================================
    # Categories
    path("categories/", views.CategoryListCreateAPIView.as_view(), name="retail_api_categories"),
    path("categories/<int:pk>/", views.CategoryDetailAPIView.as_view(), name="retail_api_category_detail"),
    # Products
    path("products/", views.ProductListCreateAPIView.as_view(), name="retail_api_products"),
    path("products/trash/", views.ProductTrashAPIView.as_view(), name="retail_api_products_trash"),
    path("products/<int:pk>/", views.ProductDetailAPIView.as_view(), name="retail_api_product_detail"),
    path("products/<int:pk>/restore/", views.ProductRestoreAPIView.as_view(), name="retail_api_product_restore"),
    path("products/<int:pk>/permanent/", views.ProductPermanentDeleteAPIView.as_view(), name="retail_api_product_permanent_delete"),
    path("products/<int:pk>/images/", views.ProductImageUploadAPIView.as_view(), name="retail_api_product_images"),
    path("products/<int:pk>/images/<int:image_id>/", views.ProductImageDeleteAPIView.as_view(), name="retail_api_product_image_delete"),
    path("products/<int:pk>/images/<int:image_id>/primary/", views.ProductImageSetPrimaryAPIView.as_view(), name="retail_api_product_image_set_primary"),
    # Branches
    path("branches/", views.BranchListCreateAPIView.as_view(), name="retail_api_branches"),
    path("branches/<int:pk>/", views.BranchDetailAPIView.as_view(), name="retail_api_branch_detail"),
    # Customers
    path("customers/", views.CustomerListCreateAPIView.as_view(), name="retail_api_customers"),
    path("customers/<int:pk>/", views.CustomerDetailAPIView.as_view(), name="retail_api_customer_detail"),
    # Orders
    path("orders/", views.OrderListCreateAPIView.as_view(), name="retail_api_orders"),
    path("orders/<int:pk>/", views.OrderDetailAPIView.as_view(), name="retail_api_order_detail"),
    path("orders/<int:pk>/confirm/", views.OrderConfirmAPIView.as_view(), name="retail_api_order_confirm"),
    path("orders/<int:pk>/cancel/", views.OrderCancelAPIView.as_view(), name="retail_api_order_cancel"),
    path("orders/<int:pk>/complete/", views.OrderCompleteAPIView.as_view(), name="retail_api_order_complete"),
    # Suppliers
    path("suppliers/", views.SupplierListCreateAPIView.as_view(), name="retail_api_suppliers"),
    path("suppliers/<int:pk>/", views.SupplierDetailAPIView.as_view(), name="retail_api_supplier_detail"),
    # Goods Receiving
    path("goods-receipts/", views.GoodsReceiptListCreateAPIView.as_view(), name="retail_api_goods_receipts"),
    path("goods-receipts/<int:pk>/", views.GoodsReceiptDetailAPIView.as_view(), name="retail_api_goods_receipt_detail"),
    path("goods-receipts/<int:pk>/confirm/", views.GoodsReceiptConfirmAPIView.as_view(), name="retail_api_goods_receipt_confirm"),
    path("goods-receipts/<int:pk>/receive/", views.GoodsReceiptReceiveAPIView.as_view(), name="retail_api_goods_receipt_receive"),
    path("goods-receipts/<int:pk>/cancel/", views.GoodsReceiptCancelAPIView.as_view(), name="retail_api_goods_receipt_cancel"),
    # Stock Balances
    path("stock-balances/", views.StockBalanceListAPIView.as_view(), name="retail_api_stock_balances"),
    # Stockout Prediction & Analytics
    path("analytics/stockout-risk/", views.StockoutRiskAPIView.as_view(), name="retail_api_stockout_risk"),
    path("analytics/revenue/", views.RevenueSummaryAPIView.as_view(), name="retail_api_analytics_revenue"),
    path("analytics/orders/", views.RevenueTimeseriesAPIView.as_view(), name="retail_api_analytics_timeseries"),
    path("analytics/top-products/", views.TopProductsAPIView.as_view(), name="retail_api_analytics_top_products"),
    path("analytics/branch-breakdown/", views.BranchBreakdownAPIView.as_view(), name="retail_api_analytics_branch_breakdown"),
]


# Web UI URL patterns
ui_urlpatterns = [
    path("", ui_views.retail_dashboard_view, name="retail_dashboard"),
    path("products/", ui_views.retail_products_view, name="retail_products"),
    path("orders/", ui_views.retail_orders_view, name="retail_orders"),
    path("orders/<int:pk>/", ui_views.retail_order_detail_view, name="retail_order_detail"),
    path("customers/", ui_views.retail_customers_view, name="retail_customers"),
    path("branches/", ui_views.retail_branches_view, name="retail_branches"),
]
