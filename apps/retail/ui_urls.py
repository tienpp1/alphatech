"""
Web UI URL Configuration for Retail Domain.
"""

from django.urls import path
from apps.retail import ui_views

urlpatterns = [
    path("", ui_views.retail_dashboard_view, name="retail_dashboard"),
    path("products/", ui_views.retail_products_view, name="retail_products"),
    path("products/create/", ui_views.retail_product_create_view, name="retail_product_create"),
    path("products/trash/", ui_views.retail_product_trash_view, name="retail_product_trash"),
    path("products/<int:pk>/", ui_views.retail_product_detail_view, name="retail_product_detail"),
    path("products/<int:pk>/edit/", ui_views.retail_product_edit_view, name="retail_product_edit"),
    path("products/<int:pk>/delete/", ui_views.retail_product_delete_view, name="retail_product_delete"),
    path("products/<int:pk>/restore/", ui_views.retail_product_restore_view, name="retail_product_restore"),
    path("products/<int:pk>/permanent-delete/", ui_views.retail_product_permanent_delete_view, name="retail_product_permanent_delete"),
    path("products/<int:pk>/images/upload/", ui_views.retail_product_image_upload_view, name="retail_product_image_upload"),
    path("products/<int:pk>/images/<int:image_id>/delete/", ui_views.retail_product_image_delete_view, name="retail_product_image_delete"),
    path("products/<int:pk>/images/<int:image_id>/primary/", ui_views.retail_product_image_set_primary_view, name="retail_product_image_set_primary"),
    path("orders/", ui_views.retail_orders_view, name="retail_orders"),
    path("orders/<int:pk>/", ui_views.retail_order_detail_view, name="retail_order_detail"),
    path("goods-receiving/", ui_views.retail_goods_receiving_list_view, name="retail_goods_receiving_list"),
    path("goods-receiving/create/", ui_views.retail_goods_receiving_create_view, name="retail_goods_receiving_create"),
    path("goods-receiving/<int:pk>/", ui_views.retail_goods_receiving_detail_view, name="retail_goods_receiving_detail"),
    path("stockout-risk/", ui_views.retail_stockout_risk_view, name="retail_stockout_risk"),
    path("customers/", ui_views.retail_customers_view, name="retail_customers"),
    path("branches/", ui_views.retail_branches_view, name="retail_branches"),
]

