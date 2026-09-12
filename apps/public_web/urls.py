"""
URL Configuration for Public Business Website & Customer Authentication.
"""

from django.urls import path
from apps.public_web.geocoding import public_geocode_view
from apps.public_web.views import (
    public_home_view,
    public_products_view,
    public_product_detail_view,
    public_services_view,
    public_service_detail_view,
    public_service_request_view,
    public_branches_view,
    public_about_view,
    public_contact_view,
    public_login_view,
    public_register_view,
    public_resend_verification_view,
    public_verify_email_view,
    public_verify_registration_code_view,
    public_logout_view,
    public_forgot_password_view,
    public_password_reset_confirm_view,
    public_password_reset_complete_view,
    public_customer_account_view,
    public_customer_email_resend_view,
    public_google_auth_view,
    public_google_callback_view,
    public_cart_view,
    public_cart_json_view,
    public_cart_add_view,
    public_cart_update_view,
    public_cart_remove_view,
    public_cart_clear_view,
    public_checkout_view,
    public_checkout_place_order_view,
    public_order_success_view,
    public_customer_orders_view,
    public_customer_order_detail_view,
    public_copilot_api_view,
)

urlpatterns = [
    path("chi-nhanh/tim-dia-diem/", public_geocode_view, name="public_geocode"),
    # 1. Homepage & Discovery
    path("", public_home_view, name="public_home"),
    # 2. Public Retail Products
    path("san-pham/", public_products_view, name="public_products"),
    path("san-pham/<int:pk>/", public_product_detail_view, name="public_product_detail"),
    # 3. Public Technical Services
    path("dich-vu/", public_services_view, name="public_services"),
    path("dich-vu/<int:pk>/", public_service_detail_view, name="public_service_detail"),
    path("yeu-cau-dich-vu/", public_service_request_view, name="public_service_request"),
    # 4. Public Branch Locations
    path("chi-nhanh/", public_branches_view, name="public_branches"),
    # 5. About & Contact
    path("gioi-thieu/", public_about_view, name="public_about"),
    path("lien-he/", public_contact_view, name="public_contact"),
    # 6. Public Customer Authentication Flow
    path("dang-nhap/", public_login_view, name="public_login"),
    path("dang-ky/", public_register_view, name="public_register"),
    path("dang-ky/xac-minh-ma/", public_verify_registration_code_view, name="public_verify_registration_code"),
    path("dang-ky/gui-lai-xac-minh/", public_resend_verification_view, name="public_resend_verification"),
    path("xac-minh-email/<str:token>/", public_verify_email_view, name="public_verify_email"),
    path("dang-xuat/", public_logout_view, name="public_logout"),
    path("quen-mat-khau/", public_forgot_password_view, name="public_forgot_password"),
    path("quen-mat-khau/xac-nhan/<str:uidb64>/<str:token>/", public_password_reset_confirm_view, name="public_password_reset_confirm"),
    path("quen-mat-khau/hoan-tat/", public_password_reset_complete_view, name="public_password_reset_complete"),
    # 7. Public Customer Account Portal & Order History
    path("tai-khoan/", public_customer_account_view, name="public_customer_account"),
    path("tai-khoan/email/<uuid:public_id>/gui-lai/", public_customer_email_resend_view, name="public_customer_email_resend"),
    path("tai-khoan/don-hang/", public_customer_orders_view, name="public_customer_orders"),
    path("tai-khoan/don-hang/<str:order_number>/", public_customer_order_detail_view, name="public_customer_order_detail"),
    # 8. Public Shopping Cart Flow
    path("gio-hang/", public_cart_view, name="public_cart"),
    path("gio-hang/api/", public_cart_json_view, name="public_cart_json"),
    path("gio-hang/them/<int:pk>/", public_cart_add_view, name="public_cart_add"),
    path("gio-hang/cap-nhat/<int:pk>/", public_cart_update_view, name="public_cart_update"),
    path("gio-hang/xoa/<int:pk>/", public_cart_remove_view, name="public_cart_remove"),
    path("gio-hang/xoa-tat-ca/", public_cart_clear_view, name="public_cart_clear"),
    # 9. Public Checkout & Order Creation Flow
    path("thanh-toan/", public_checkout_view, name="public_checkout"),
    path("thanh-toan/dat-hang/", public_checkout_place_order_view, name="public_checkout_place_order"),
    path("dat-hang-thanh-cong/<str:order_number>/", public_order_success_view, name="public_order_success"),
    # 10. Google Sign-In Endpoints
    path("accounts/google/", public_google_auth_view, name="public_google_auth"),
    path("accounts/google/callback/", public_google_callback_view, name="public_google_callback"),
    # 11. Public AI Copilot Widget Endpoint
    path("api/v1/public/copilot/", public_copilot_api_view, name="public_copilot_api"),
]
