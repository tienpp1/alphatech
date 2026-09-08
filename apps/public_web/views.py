"""
Public Web Views for Customer-Facing Website & Customer Authentication.
Showcases ABC Tech Store and XYZ IT Technical Services with a Premium Light / White Theme.
Provides Customer Login, Registration, Password Reset, Customer Account, and zero exposure of internal business metrics.
"""

import json
import hashlib
import logging
import random
import secrets
import urllib.parse
import urllib.request
import urllib.error
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.core.paginator import Paginator
import uuid
from django.db import IntegrityError, transaction
from django.db.models import Q, F
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.http import JsonResponse, HttpResponse
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.accounts.services import authenticate_user
from apps.audit.services import log_action
from apps.retail.models import (
    Product,
    Category,
    Branch,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    StockBalance,
)
from apps.service_ops.models import Service, ServiceCategory, ServiceRequest
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.public_web.cart import get_cart
from apps.notifications.services import (
    dispatch_new_customer_notification,
    dispatch_new_order_notification,
    dispatch_new_service_request_notification,
    dispatch_new_contact_notification,
)
from apps.public_web.email_service import (
    deliver_outbox_record,
    public_url,
    resolve_customer_recipients,
    send_email_verification_email,
    send_customer_welcome_email,
    send_customer_login_alert_email,
    send_order_confirmation_email,
    send_service_request_confirmation_email,
    send_contact_confirmation_email,
)
from apps.public_web.models import CustomerEmailDelivery, SocialIdentity

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_SALT = "public_web.email_verification.v1"


def _email_verification_token(user):
    return signing.dumps(
        {"user_id": user.pk, "email": user.email.lower()},
        salt=EMAIL_VERIFICATION_SALT,
        compress=True,
    )


def _send_registration_verification(user, *, defer_delivery=False):
    token = _email_verification_token(user)
    verification_url = public_url(f"xac-minh-email/{token}/")
    return send_email_verification_email(
        user,
        verification_url,
        deduplication_key=f"verify-email:{user.pk}:{token}",
        defer_delivery=defer_delivery,
    )


def _google_urlopen(request, timeout):
    """Open Google endpoints directly unless an environment proxy is explicitly enabled."""
    if getattr(settings, "GOOGLE_OAUTH_USE_ENV_PROXY", False):
        return urllib.request.urlopen(request, timeout=timeout)
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=timeout)


# Vietnamese Display Mapping for IT Service Categories
SERVICE_CATEGORY_VIETNAMESE = {
    "INSTALLATION": "Cài đặt hệ thống",
    "MAINTENANCE": "Bảo trì hệ thống",
    "DATABASE_CONSULTING": "Tư vấn quản trị CSDL",
    "DEVICE_REPAIR": "Sửa chữa thiết bị",
}

SERVICE_CATEGORY_ICONS = {
    "INSTALLATION": "⚙️",
    "MAINTENANCE": "🛡️",
    "DATABASE_CONSULTING": "🗄️",
    "DEVICE_REPAIR": "🔧",
}

SERVICE_CATEGORY_DESCRIPTIONS = {
    "INSTALLATION": "Triển khai hệ điều hành, máy chủ, hạ tầng mạng doanh nghiệp và giải pháp sao lưu an toàn.",
    "MAINTENANCE": "Bảo dưỡng định kỳ hệ thống máy chủ, máy trạm, thiết bị mạng và diễn tập khắc phục sự cố.",
    "DATABASE_CONSULTING": "Thiết kế kiến trúc CSDL, tối ưu hóa truy vấn hiệu năng cao, quản trị và phục hồi dữ liệu.",
    "DEVICE_REPAIR": "Chẩn đoán phần cứng, sửa chữa laptop, máy bàn, máy in, thiết bị mạng và thay thế linh kiện.",
}


# =========================================================================
# 1. PUBLIC WEBSITE CORE VIEWS
# =========================================================================

def public_home_view(request):
    """
    Public Website Homepage (GET /) - Light Theme.
    Introduces ABC Tech Store and XYZ IT Technical Services with featured items.
    """
    featured_products = (
        Product.objects.filter(is_active=True, deleted_at__isnull=True, workspace__workspace_type="RETAIL")
        .select_related("category")
        .prefetch_related("images")
        .order_by("-created_at")[:6]
    )

    services_qs = Service.objects.filter(is_active=True, workspace__workspace_type="SERVICE")
    service_categories_data = []
    for cat_key, cat_label in SERVICE_CATEGORY_VIETNAMESE.items():
        cat_services = services_qs.filter(category=cat_key)
        service_categories_data.append({
            "code": cat_key,
            "label": cat_label,
            "icon": SERVICE_CATEGORY_ICONS.get(cat_key, "⚡"),
            "description": SERVICE_CATEGORY_DESCRIPTIONS.get(cat_key, ""),
            "services_count": cat_services.count(),
            "sample_services": cat_services[:3],
        })

    branches = Branch.objects.filter(is_active=True, workspace__workspace_type="RETAIL").order_by("name")[:3]

    context = {
        "page_title": "Trang chủ | Nền tảng Doanh nghiệp AI",
        "featured_products": featured_products,
        "service_categories": service_categories_data,
        "branches": branches,
        "active_nav": "home",
    }
    return render(request, "public/home.html", context)


def public_products_view(request):
    """
    Public Product Catalog (GET /san-pham/) - Light Theme.
    Provides category filter, search by name/SKU, and price sorting for active technology products.
    """
    products_qs = (
        Product.objects.filter(is_active=True, deleted_at__isnull=True, workspace__workspace_type="RETAIL")
        .select_related("category")
        .prefetch_related("images")
        .order_by("-created_at")
    )

    categories = Category.objects.filter(workspace__workspace_type="RETAIL", is_active=True).order_by("name")

    selected_category = request.GET.get("category", "").strip()
    if selected_category:
        products_qs = products_qs.filter(
            Q(category__code__iexact=selected_category) | Q(category__name__iexact=selected_category)
        )

    search_query = request.GET.get("q", "").strip()
    if search_query:
        products_qs = products_qs.filter(
            Q(name__icontains=search_query) | Q(sku__icontains=search_query) | Q(description__icontains=search_query)
        )

    sort_option = request.GET.get("sort", "").strip()
    if sort_option == "price_asc":
        products_qs = products_qs.order_by("unit_price")
    elif sort_option == "price_desc":
        products_qs = products_qs.order_by("-unit_price")
    elif sort_option == "name_asc":
        products_qs = products_qs.order_by("name")
    else:
        products_qs = products_qs.order_by("-created_at")

    paginator = Paginator(products_qs, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_title": "Sản phẩm công nghệ | ABC Tech Store",
        "page_obj": page_obj,
        "products": page_obj.object_list,
        "categories": categories,
        "selected_category": selected_category,
        "search_query": search_query,
        "sort_option": sort_option,
        "total_results": paginator.count,
        "active_nav": "products",
    }
    return render(request, "public/products.html", context)


def public_product_detail_view(request, pk):
    """
    Public Product Detail (GET /san-pham/<id>/) - Light Theme.
    Shows commercial specifications, selling price, and contact CTA.
    Prevents exposure of cost price, inventory count, supplier, or internal metrics.
    """
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        pk=pk,
        is_active=True,
        deleted_at__isnull=True,
        workspace__workspace_type="RETAIL",
    )

    related_products = (
        Product.objects.filter(category=product.category, is_active=True, deleted_at__isnull=True, workspace=product.workspace)
        .exclude(pk=product.pk)
        .prefetch_related("images")
        .order_by("-created_at")[:4]
    )

    context = {
        "page_title": f"{product.name} | ABC Tech Store",
        "product": product,
        "related_products": related_products,
        "active_nav": "products",
    }
    return render(request, "public/product_detail.html", context)


def public_services_view(request):
    """
    Public Service Catalog (GET /dich-vu/) - Light Theme.
    Displays IT services grouped across the four approved technical service categories.
    """
    services_qs = (
        Service.objects.filter(is_active=True, workspace__workspace_type="SERVICE")
        .order_by("category", "name")
    )

    selected_category = request.GET.get("category", "").strip().upper()
    if selected_category and selected_category in SERVICE_CATEGORY_VIETNAMESE:
        services_qs = services_qs.filter(category=selected_category)

    categorized_services = []
    for cat_key, cat_label in SERVICE_CATEGORY_VIETNAMESE.items():
        if selected_category and selected_category != cat_key:
            continue
        cat_items = services_qs.filter(category=cat_key)
        categorized_services.append({
            "code": cat_key,
            "label": cat_label,
            "icon": SERVICE_CATEGORY_ICONS.get(cat_key, "⚡"),
            "description": SERVICE_CATEGORY_DESCRIPTIONS.get(cat_key, ""),
            "services": cat_items,
        })

    context = {
        "page_title": "Dịch vụ kỹ thuật IT | XYZ IT Technical Services",
        "categorized_services": categorized_services,
        "selected_category": selected_category,
        "service_categories": SERVICE_CATEGORY_VIETNAMESE,
        "active_nav": "services",
    }
    return render(request, "public/services.html", context)


def public_service_detail_view(request, pk):
    """
    Public Service Detail (GET /dich-vu/<id>/) - Light Theme.
    Shows service scope, standard turnaround duration, and base service fee.
    """
    service = get_object_or_404(
        Service.objects.filter(is_active=True, workspace__workspace_type="SERVICE"),
        pk=pk,
    )

    category_label = SERVICE_CATEGORY_VIETNAMESE.get(service.category, service.category)
    category_icon = SERVICE_CATEGORY_ICONS.get(service.category, "⚡")

    related_services = (
        Service.objects.filter(category=service.category, is_active=True, workspace=service.workspace)
        .exclude(pk=service.pk)[:3]
    )

    context = {
        "page_title": f"{service.name} | XYZ IT Technical Services",
        "service": service,
        "category_label": category_label,
        "category_icon": category_icon,
        "related_services": related_services,
        "active_nav": "services",
    }
    return render(request, "public/service_detail.html", context)


def public_service_request_view(request):
    """
    Public Service Request / Inquiry Form (GET & POST /yeu-cau-dich-vu/) - Light Theme.
    Allows customer to submit an operational IT service request safely.
    """
    services = Service.objects.filter(is_active=True, workspace__workspace_type="SERVICE").order_by("category", "name")
    preselected_service_id = request.GET.get("service_id", "").strip()

    success_message = None
    error_message = None
    email_warning = False

    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        service_id_raw = request.POST.get("service_id", "").strip()
        description = request.POST.get("description", "").strip()
        address = request.POST.get("address", "").strip()
        preferred_time = request.POST.get("preferred_time", "").strip()
        submitted_recipients = resolve_customer_recipients(
            request.user if request.user.is_authenticated else None, email
        )

        if not customer_name or not phone or not description:
            error_message = "Vui lòng nhập đầy đủ Họ tên, Số điện thoại và Mô tả yêu cầu dịch vụ."
        else:
            try:
                service_obj = None
                if service_id_raw:
                    try:
                        service_obj = Service.objects.filter(
                            pk=int(service_id_raw),
                            is_active=True,
                            workspace__workspace_type=WorkspaceType.SERVICE,
                        ).first()
                    except (ValueError, TypeError):
                        pass

                if not service_obj:
                    service_obj = Service.objects.filter(
                        is_active=True,
                        workspace__workspace_type=WorkspaceType.SERVICE,
                    ).first()

                service_workspace = service_obj.workspace if service_obj else Workspace.objects.filter(workspace_type="SERVICE").first()
                service_req = None
                recipients = []

                if service_obj and service_workspace:
                    with transaction.atomic():
                        from .customer_identity import customer_for_submission
                        customer_obj = customer_for_submission(
                            workspace=service_workspace, user=request.user,
                            name=customer_name, email=email or "", phone=phone,
                            address=address or "",
                        )

                        if customer_obj:
                            req_num = f"REQ-PUB-{random.randint(10000, 99999)}"
                            req_title = f"Yêu cầu từ {customer_name}: {service_obj.name}"
                            req_desc = (
                                f"Họ tên khách hàng: {customer_name}\n"
                                f"Số điện thoại: {phone}\n"
                                f"Email: {email or 'Không cung cấp'}\n"
                                f"Địa chỉ / Khu vực: {address or 'Chưa xác định'}\n"
                                f"Thời gian mong muốn: {preferred_time or 'Sớm nhất có thể'}\n\n"
                                f"Nội dung yêu cầu:\n{description}"
                            )

                            service_req = ServiceRequest.objects.create(
                                workspace=service_workspace,
                                request_number=req_num,
                                customer=customer_obj,
                                service=service_obj,
                                title=req_title,
                                description=req_desc,
                                status="OPEN",
                                priority="MEDIUM",
                            )

                            transaction.on_commit(lambda s=service_req: dispatch_new_service_request_notification(s))
                            recipients = submitted_recipients
                            delivery_results = [
                                send_service_request_confirmation_email(
                                    service_req,
                                    recipient_email=recipient,
                                    user=request.user if request.user.is_authenticated else None,
                                    deduplication_key=f"service:{service_req.pk}:{recipient}",
                                    defer_delivery=True,
                                )
                                for recipient in recipients
                            ]

                    if service_req:
                        result_ids = [result.public_id for result in delivery_results]
                        email_warning = not recipients or CustomerEmailDelivery.objects.filter(
                            public_id__in=result_ids, status=CustomerEmailDelivery.Status.FAILED
                        ).exists()
                        success_message = "Yêu cầu dịch vụ của quý khách đã được tiếp nhận thành công! Đội ngũ kỹ thuật viên XYZ IT Services sẽ liên hệ lại trong thời gian sớm nhất."
                    else:
                        error_message = "Không thể ghi nhận yêu cầu lúc này. Vui lòng thử lại sau."
            except Exception:
                logger.exception("Unable to create public service request")
                error_message = "Không thể ghi nhận yêu cầu lúc này. Vui lòng thử lại sau."

    context = {
        "page_title": "Yêu cầu dịch vụ IT | XYZ IT Technical Services",
        "services": services,
        "service_categories": SERVICE_CATEGORY_VIETNAMESE,
        "preselected_service_id": preselected_service_id,
        "success_message": success_message,
        "error_message": error_message,
        "email_warning": email_warning,
        "active_nav": "service_request",
    }
    return render(request, "public/service_request.html", context)


def public_branches_view(request):
    """
    Public Branch & Store Locations (GET /chi-nhanh/) - Light Theme.
    Displays physical retail branch locations, GIS coordinates, contact info, and business hours.
    """
    branches = Branch.objects.filter(is_active=True, workspace__workspace_type="RETAIL").order_by("name")

    context = {
        "page_title": "Hệ thống chi nhánh | ABC Tech Store & XYZ Services",
        "branches": branches,
        "active_nav": "branches",
    }
    return render(request, "public/branches.html", context)


def public_about_view(request):
    """
    Public About Page (GET /gioi-thieu/) - Light Theme.
    """
    context = {
        "page_title": "Giới thiệu | Nền tảng Doanh nghiệp AI",
        "active_nav": "about",
    }
    return render(request, "public/about.html", context)


def public_contact_view(request):
    """
    Public Contact Page (GET & POST /lien-he/) - Light Theme.
    """
    success_message = None
    error_message = None
    email_warning = False
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        legacy_contact = request.POST.get("contact", "").strip()
        if legacy_contact and not email and "@" in legacy_contact:
            email = legacy_contact
        elif legacy_contact and not phone:
            phone = legacy_contact
        message_body = request.POST.get("message", "").strip()

        recipients = resolve_customer_recipients(
            request.user if request.user.is_authenticated else None, email
        )
        if name and (phone or email) and message_body:
            retail_ws = Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first() or Workspace.objects.first()
            submission_material = "|".join((
                str(request.user.pk) if request.user.is_authenticated else "guest",
                name, phone, email.lower(), message_body,
            ))
            submission_id = hashlib.sha256(submission_material.encode("utf-8")).hexdigest()
            with transaction.atomic():
                from .models import ContactSubmission
                contact, created = ContactSubmission.objects.get_or_create(
                    deduplication_key=submission_id,
                    defaults=dict(workspace=retail_ws,
                                  user=request.user if request.user.is_authenticated else None,
                                  name=name, phone=phone, email=email, message=message_body),
                )
                if created:
                    dispatch_new_contact_notification(
                        workspace=retail_ws, name=name, phone=phone, email=email,
                    )
                results = [
                    send_contact_confirmation_email(
                        name=name, email=recipient, phone=phone, message_body=message_body,
                        user=request.user if request.user.is_authenticated else None,
                        deduplication_key=f"contact:{submission_id}:{recipient}",
                        defer_delivery=True,
                    )
                    for recipient in recipients
                ]
            result_ids = [result.public_id for result in results]
            email_warning = not recipients or CustomerEmailDelivery.objects.filter(
                public_id__in=result_ids, status=CustomerEmailDelivery.Status.FAILED
            ).exists()
            success_message = "Cảm ơn quý khách đã gửi tin nhắn liên hệ thành công! Bộ phận chăm sóc khách hàng sẽ phản hồi trong 24 giờ làm việc."
        else:
            error_message = "Vui lòng nhập đầy đủ họ tên, thông tin liên hệ và nội dung cần hỗ trợ."

    context = {
        "page_title": "Liên hệ | Nền tảng Doanh nghiệp AI",
        "success_message": success_message,
        "error_message": error_message,
        "email_warning": email_warning,
        "active_nav": "contact",
    }
    return render(request, "public/contact.html", context)


# =========================================================================
# 2. PUBLIC CUSTOMER AUTHENTICATION & ACCOUNT VIEWS
# =========================================================================

def public_login_view(request):
    """
    Public Customer Login View (GET & POST /dang-nhap/).
    Polished standalone light-theme authentication page supporting email or username.
    """
    next_url = request.GET.get("next") or request.POST.get("next") or ""

    if request.user.is_authenticated:
        if (
            next_url
            and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})
            and not next_url.startswith("/dang-nhap")
            and not next_url.startswith("/dang-ky")
            and not next_url.startswith("/dang-xuat")
            and not next_url.startswith("/accounts/login")
        ):
            return redirect(next_url)

        has_staff_role = request.user.is_superuser or WorkspaceMembership.objects.filter(
            user=request.user, is_active=True
        ).exists()
        if has_staff_role:
            return redirect("/noibo/")
        return redirect("/tai-khoan/")

    google_error_messages = {
        "google_denied": "Bạn đã hủy quyền đăng nhập Google.",
        "google_authorization_failed": "Google không thể hoàn tất yêu cầu cấp quyền. Vui lòng thử lại.",
        "google_csrf_invalid": "Phiên đăng nhập Google không hợp lệ hoặc đã hết hạn. Vui lòng bắt đầu lại.",
        "google_config_missing": "Đăng nhập Google chưa được cấu hình đúng cho môi trường này.",
        "google_token_failed": "Google từ chối mã đăng nhập. Vui lòng bắt đầu lại.",
        "google_token_network_error": "Không thể kết nối Google lúc này. Vui lòng thử lại sau.",
        "google_userinfo_error": "Không thể đọc hồ sơ Google an toàn. Vui lòng thử lại.",
        "google_no_email": "Tài khoản Google không cung cấp địa chỉ email hợp lệ.",
        "google_email_unverified": "Email Google chưa được xác minh nên không thể đăng nhập.",
        "google_identity_missing": "Google không cung cấp định danh tài khoản hợp lệ.",
        "google_identity_collision": "Tài khoản Google này xung đột với một liên kết đã tồn tại. Vui lòng liên hệ hỗ trợ.",
    }
    error_message = google_error_messages.get(request.GET.get("error"))
    logged_out_notice = request.GET.get("logged_out") == "1"

    if request.method == "POST":
        username_or_email = request.POST.get("username_or_email", "").strip()
        password = request.POST.get("password", "")

        inactive_user = User.objects.filter(
            Q(email__iexact=username_or_email) | Q(username__iexact=username_or_email),
            is_active=False,
        ).first()
        if inactive_user:
            request.session["pending_verification_user_id"] = inactive_user.pk
            error_message = "Tài khoản chưa xác minh email. Vui lòng kiểm tra Inbox/Spam hoặc gửi lại email xác minh."
            context = {
                "page_title": "Đăng nhập | Nền tảng Doanh nghiệp AI",
                "next": next_url,
                "error": error_message,
                "logged_out": logged_out_notice,
                "pending_verification": True,
                "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
            }
            return render(request, "public/auth_login.html", context)

        user = authenticate_user(username_or_email, password)
        if user:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")

            # Dispatch security login alert to customer email
            if user.email:
                email_result = send_customer_login_alert_email(
                    user_email=user.email,
                    name=user.first_name or user.username,
                    ip_address=get_client_ip(request),
                    login_method="Mật khẩu tài khoản",
                    user=user,
                    deduplication_key=f"login:password:{user.pk}:{uuid.uuid4().hex}",
                )
                if not email_result:
                    request.session["customer_email_warning"] = True

            has_staff_role = user.is_superuser or WorkspaceMembership.objects.filter(
                user=user, is_active=True
            ).exists()

            if (
                next_url
                and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})
                and not next_url.startswith("/dang-nhap")
                and not next_url.startswith("/dang-ky")
                and not next_url.startswith("/dang-xuat")
                and not next_url.startswith("/accounts/login")
            ):
                if next_url.startswith("/noibo") and not has_staff_role:
                    return redirect("/tai-khoan/?notice=customer_only")
                return redirect(next_url)

            if has_staff_role:
                return redirect("/noibo/")
            return redirect("/tai-khoan/")
        else:
            error_message = "Email hoặc mật khẩu không chính xác. Vui lòng kiểm tra lại."

    context = {
        "page_title": "Đăng nhập | Nền tảng Doanh nghiệp AI",
        "next": next_url,
        "error": error_message,
        "logged_out": logged_out_notice,
        "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
    }
    return render(request, "public/auth_login.html", context)


@transaction.atomic
def public_register_view(request):
    """
    Public Customer Registration View (GET & POST /dang-ky/).
    Registers a new public customer with automatic Customer profile linking.
    Never assigns internal staff roles or workspace memberships.
    """
    if request.user.is_authenticated:
        return redirect("/tai-khoan/")

    error_message = None

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        address = request.POST.get("address", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        terms = request.POST.get("terms")

        # Validation rules
        if not name or not email or not phone or not password:
            error_message = "Vui lòng điền đầy đủ các thông tin bắt buộc (Họ tên, Email, SĐT, Mật khẩu)."
        elif "@" not in email or "." not in email:
            error_message = "Địa chỉ email không đúng định dạng."
        elif len(password) < 8:
            error_message = "Mật khẩu phải có ít nhất 8 ký tự để đảm bảo an toàn."
        elif password != confirm_password:
            error_message = "Mật khẩu xác nhận không khớp. Vui lòng nhập lại."
        elif not terms:
            error_message = "Vui lòng xác nhận đồng ý với Điều khoản sử dụng và Chính sách bảo mật."
        elif User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).exists():
            existing_user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
            if existing_user and not existing_user.is_active:
                request.session["pending_verification_user_id"] = existing_user.pk
                error_message = "Email này đã tồn tại nhưng chưa được xác minh. Bạn có thể yêu cầu gửi lại email xác minh."
            else:
                error_message = "Email này đã tồn tại. Vui lòng đăng nhập hoặc sử dụng chức năng quên mật khẩu."
        else:
            try:
                # 1. Create User Authentication Account
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=name,
                    is_active=False,
                )

                # 2. Link or Create Customer Profile in Retail Workspace
                retail_ws = Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first() or Workspace.objects.first()
                existing_customer = Customer.objects.filter(user=user, workspace=retail_ws).first()
                customer_record = existing_customer

                if existing_customer:
                    if not existing_customer.phone and phone:
                        existing_customer.phone = phone
                    if not existing_customer.address and address:
                        existing_customer.address = address
                    if not existing_customer.name and name:
                        existing_customer.name = name
                    existing_customer.save()
                elif retail_ws:
                    cust_code = f"CUST-ONL-{random.randint(10000, 99999)}"
                    customer_record = Customer.objects.create(
                        workspace=retail_ws,
                        user=user,
                        code=cust_code,
                        name=name,
                        email=email,
                        phone=phone,
                        address=address,
                    )

                if customer_record:
                    transaction.on_commit(lambda c=customer_record: dispatch_new_customer_notification(c))

                # Send ownership verification first. Welcome is sent only after activation.
                if user.email:
                    _send_registration_verification(user, defer_delivery=True)

                request.session["pending_verification_user_id"] = user.pk
                return redirect("/dang-ky/?verification_sent=1")
            except Exception:
                logger.exception("Unable to create pending public registration")
                error_message = "Đã xảy ra lỗi trong quá trình tạo tài khoản. Vui lòng thử lại sau."

    pending_user_id = request.session.get("pending_verification_user_id")
    pending_user = User.objects.filter(pk=pending_user_id, is_active=False).first() if pending_user_id else None
    verification_delivery_failed = False
    if pending_user:
        verification_delivery_failed = CustomerEmailDelivery.objects.filter(
            user=pending_user,
            event_type=CustomerEmailDelivery.EventType.EMAIL_VERIFICATION,
            status=CustomerEmailDelivery.Status.FAILED,
        ).exists()
    context = {
        "page_title": "Đăng ký tài khoản khách hàng | Nền tảng Doanh nghiệp AI",
        "error": error_message,
        "verification_sent": request.GET.get("verification_sent") == "1",
        "verification_error": request.GET.get("verification_error") == "invalid",
        "pending_verification": bool(pending_user),
        "verification_delivery_failed": verification_delivery_failed,
        "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
    }
    return render(request, "public/auth_register.html", context)


@require_POST
def public_resend_verification_view(request):
    """Enumeration-safe, session-throttled resend for inactive registrations."""
    now_ts = timezone.now().timestamp()
    last_sent = request.session.get("verification_resend_at", 0)
    try:
        throttled = now_ts - float(last_sent) < 60
    except (TypeError, ValueError):
        throttled = False
    email = request.POST.get("email", "").strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=False).first() if email else None
    if user:
        request.session["pending_verification_user_id"] = user.pk
        if not throttled:
            _send_registration_verification(user)
            request.session["verification_resend_at"] = now_ts
    return redirect("/dang-ky/?verification_sent=1")


def public_verify_email_view(request, token):
    """Activate exactly one pending User after proving mailbox ownership."""
    try:
        payload = signing.loads(token, salt=EMAIL_VERIFICATION_SALT, max_age=86400)
        user_id = payload.get("user_id")
        email = str(payload.get("email", "")).strip().lower()
    except (signing.BadSignature, signing.SignatureExpired, TypeError, AttributeError):
        return redirect("/dang-ky/?verification_error=invalid")

    with transaction.atomic():
        user = User.objects.select_for_update().filter(pk=user_id, email__iexact=email).first()
        if not user:
            return redirect("/dang-ky/?verification_error=invalid")
        if user.is_active:
            return redirect("/dang-nhap/?verified=already")

        user.is_active = True
        user.save(update_fields=("is_active", "updated_at"))
        retail_ws = Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first() or Workspace.objects.first()
        customer = Customer.objects.filter(user=user, workspace=retail_ws).first() if retail_ws else None
        if customer:
            transaction.on_commit(lambda c=customer: dispatch_new_customer_notification(c))
        send_customer_welcome_email(
            user_email=user.email,
            name=user.first_name or user.username,
            customer_code=getattr(customer, "code", "") if customer else "",
            phone=getattr(customer, "phone", "") if customer else "",
            user=user,
            deduplication_key=f"welcome:user:{user.pk}:{user.email.lower()}",
            defer_delivery=True,
        )

    request.session.pop("pending_verification_user_id", None)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return redirect("/tai-khoan/?registered=1&email_verified=1")


def public_logout_view(request):
    """
    Public Logout View (GET & POST /dang-xuat/).
    Terminates session and returns to public homepage.
    """
    if request.user.is_authenticated:
        logout(request)
    return redirect("/dang-nhap/?logged_out=1")


def public_forgot_password_view(request):
    """
    Public Forgot Password View (GET & POST /quen-mat-khau/).
    Generates secure Django reset token and returns enumeration-safe notice.
    """
    submitted = False

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if email:
            user = User.objects.filter(email__iexact=email, is_active=True).first()
            if user:
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = request.build_absolute_uri(f"/quen-mat-khau/xac-nhan/{uid}/{token}/")

                subject = "[Nền tảng Doanh nghiệp AI] Hướng dẫn đặt lại mật khẩu"
                message = (
                    f"Xin chào {user.first_name or user.username},\n\n"
                    f"Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản liên kết với email này.\n"
                    f"Vui lòng truy cập liên kết sau để thiết lập mật khẩu mới:\n\n"
                    f"{reset_url}\n\n"
                    f"Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng bỏ qua thư này.\n\n"
                    f"Trân trọng,\nĐội ngũ Nền tảng Doanh nghiệp AI"
                )
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@abctech.vn"),
                        recipient_list=[email],
                        fail_silently=True,
                    )
                except Exception:
                    pass

        # Generic safe response prevents account enumeration
        submitted = True

    context = {
        "page_title": "Quên mật khẩu | Nền tảng Doanh nghiệp AI",
        "submitted": submitted,
    }
    return render(request, "public/auth_forgot_password.html", context)


def public_password_reset_confirm_view(request, uidb64, token):
    """
    Public Password Reset Confirm (GET & POST /quen-mat-khau/xac-nhan/<uidb64>/<token>/).
    Validates token and allows setting a new password.
    """
    user = None
    token_valid = False

    try:
        uid_str = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.filter(pk=uid_str, is_active=True).first()
        if user and default_token_generator.check_token(user, token):
            token_valid = True
    except Exception:
        token_valid = False

    error_message = None

    if request.method == "POST" and token_valid and user:
        new_password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if len(new_password) < 8:
            error_message = "Mật khẩu mới phải có ít nhất 8 ký tự."
        elif new_password != confirm_password:
            error_message = "Mật khẩu xác nhận không khớp."
        else:
            user.set_password(new_password)
            user.save()
            return redirect("/quen-mat-khau/hoan-tat/")

    context = {
        "page_title": "Thiết lập mật khẩu mới | Nền tảng Doanh nghiệp AI",
        "token_valid": token_valid,
        "error": error_message,
        "uidb64": uidb64,
        "token": token,
    }
    return render(request, "public/auth_password_reset_confirm.html", context)


def public_password_reset_complete_view(request):
    """
    Public Password Reset Complete (GET /quen-mat-khau/hoan-tat/).
    """
    context = {
        "page_title": "Đặt lại mật khẩu thành công | Nền tảng Doanh nghiệp AI",
    }
    return render(request, "public/auth_password_reset_complete.html", context)


@login_required(login_url="/dang-nhap/")
def public_customer_account_view(request):
    """
    Public Customer Account Portal (GET /tai-khoan/) - Light Theme.
    Displays customer profile, submitted service inquiries, and linked retail orders.
    Zero leakage of internal business metrics or employee management.
    """
    customer_profile = Customer.objects.filter(
        user=request.user,
        workspace__workspace_type=WorkspaceType.RETAIL,
    ).first()

    # Service requests submitted by this customer
    service_requests = []
    service_requests = ServiceRequest.objects.filter(
        customer__user=request.user,
        customer__workspace_id=F("workspace_id"),
        workspace__workspace_type=WorkspaceType.SERVICE,
    ).select_related("service").order_by("-created_at")[:10]

    # Retail orders linked to this customer
    from .customer_identity import customer_orders
    orders = customer_orders(request.user).select_related("branch").order_by("-order_date")[:10]

    registered_notice = request.GET.get("registered") == "1"
    customer_only_notice = request.GET.get("notice") == "customer_only"

    is_email_configured = bool(getattr(settings, "EMAIL_HOST_USER", "").strip())
    failed_deliveries = CustomerEmailDelivery.objects.filter(
        user=request.user,
        status=CustomerEmailDelivery.Status.FAILED,
    )[:10]

    context = {
        "page_title": "Tài khoản của tôi | Nền tảng Doanh nghiệp AI",
        "customer": customer_profile,
        "service_requests": service_requests,
        "orders": orders,
        "registered_notice": registered_notice,
        "customer_only_notice": customer_only_notice,
        "is_email_configured": is_email_configured,
        "settings_debug": getattr(settings, "DEBUG", False),
        "email_warning": request.session.pop("customer_email_warning", False) or failed_deliveries.exists(),
        "failed_email_deliveries": failed_deliveries,
        "active_nav": "account",
    }
    return render(request, "public/customer_account.html", context)


@login_required(login_url="/dang-nhap/")
@require_POST
def public_customer_email_resend_view(request, public_id):
    delivery = get_object_or_404(
        CustomerEmailDelivery,
        public_id=public_id,
        user=request.user,
        status__in=(CustomerEmailDelivery.Status.PENDING, CustomerEmailDelivery.Status.FAILED),
    )
    result = deliver_outbox_record(delivery)
    request.session["customer_email_warning"] = not bool(result)
    return redirect("/tai-khoan/")


def get_google_redirect_uri(request):
    """Return an explicitly configured callback, with a safe localhost fallback in DEBUG."""
    configured = getattr(settings, "GOOGLE_REDIRECT_URI", "").strip()
    if configured:
        if not settings.DEBUG and not configured.startswith("https://"):
            return ""
        return configured
    if settings.DEBUG and request.get_host().split(":", 1)[0] in {"localhost", "127.0.0.1"}:
        return request.build_absolute_uri("/accounts/google/callback/")
    return ""


def public_google_auth_view(request):
    """
    Public Google Sign-In Entrypoint (GET & POST /accounts/google/).
    When accessed with '?auth=1' or '?action=login', initiates Google OAuth 2.0 flow.
    When accessed directly, returns 200 with configuration status and direct sign-in button.
    """
    google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    google_client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")
    redirect_uri = get_google_redirect_uri(request)

    # If auth parameter is present, initiate OAuth 2.0 redirect
    if request.GET.get("auth") == "1" or request.GET.get("action") == "login":
        if not google_client_id or not google_client_secret or not redirect_uri:
            context = {
                "page_title": "Đăng nhập bằng Google | Nền tảng Doanh nghiệp AI",
                "status": "not_configured",
                "message": "Hệ thống chưa thiết lập thông số GOOGLE_CLIENT_ID hoặc GOOGLE_CLIENT_SECRET. Vui lòng cấu hình biến môi trường trước khi kết nối.",
            }
            return render(request, "public/auth_google_notice.html", context, status=200)

        # Generate cryptographic CSRF state token and save redirect_uri
        state = secrets.token_urlsafe(32)
        request.session["google_oauth_state"] = state
        request.session["google_oauth_state_issued_at"] = timezone.now().timestamp()
        request.session["google_oauth_redirect_uri"] = redirect_uri

        # Preserve next URL if provided
        next_url = request.GET.get("next", "").strip()
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            request.session["google_oauth_next"] = next_url

        params = {
            "client_id": google_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        oauth_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
        return redirect(oauth_auth_url)

    # Status / Info view (returns 200 OK)
    is_configured = bool(google_client_id and google_client_secret and redirect_uri)
    context = {
        "page_title": "Đăng nhập bằng Google | Nền tảng Doanh nghiệp AI",
        "status": "configured" if is_configured else "not_configured",
        "google_client_id": google_client_id,
        "redirect_uri": redirect_uri,
        "next": request.GET.get("next", ""),
        "message": (
            "Google OAuth 2.0 đã được cấu hình thành công với Client ID của doanh nghiệp. Quý khách có thể bắt đầu đăng nhập hoặc đăng ký an toàn bằng tài khoản Google."
            if is_configured
            else "Tính năng Đăng nhập bằng Google hiện đang ở chế độ Môi trường Phát triển (Dev Mode). Vui lòng cấu hình biến môi trường GOOGLE_CLIENT_ID và GOOGLE_CLIENT_SECRET."
        ),
    }
    return render(request, "public/auth_google_notice.html", context, status=200)


def public_google_callback_view(request):
    """
    Public Google OAuth 2.0 Callback Handler (GET /accounts/google/callback/).
    Exchanges code for access tokens, fetches Google profile, links/creates customer user,
    authenticates the customer, and dispatches security login & welcome emails.
    Strictly prevents internal staff role assignment.
    """
    error = request.GET.get("error")
    if error:
        logger.warning("Google OAuth authorization was not completed")
        return redirect("/dang-nhap/?error=google_denied" if error == "access_denied" else "/dang-nhap/?error=google_authorization_failed")

    code = request.GET.get("code")
    state = request.GET.get("state")
    expected_state = request.session.pop("google_oauth_state", None)
    issued_at = request.session.pop("google_oauth_state_issued_at", None)
    next_url = request.session.pop("google_oauth_next", None)
    redirect_uri = request.session.pop("google_oauth_redirect_uri", None) or get_google_redirect_uri(request)

    try:
        state_expired = not issued_at or timezone.now().timestamp() - float(issued_at) > 600
    except (TypeError, ValueError):
        state_expired = True
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state) or state_expired:
        logger.warning("Google OAuth callback rejected because state was missing, invalid, replayed, or expired")
        return redirect("/dang-nhap/?error=google_csrf_invalid")

    google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    google_client_secret = getattr(settings, "GOOGLE_CLIENT_SECRET", "")

    if not google_client_id or not google_client_secret or not redirect_uri:
        return redirect("/dang-nhap/?error=google_config_missing")

    # 1. Exchange authorization code for tokens
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = urllib.parse.urlencode({
        "code": code,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    try:
        token_req = urllib.request.Request(
            token_url,
            data=token_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "AIBusinessPlatform-OAuth/1.0"},
        )
        with _google_urlopen(token_req, timeout=12) as response:
            token_data = json.loads(response.read().decode("utf-8"))
        access_token = token_data.get("access_token")
        if not access_token:
            logger.warning("Google token endpoint returned no access token")
            return redirect("/dang-nhap/?error=google_token_failed")
    except urllib.error.HTTPError:
        logger.warning("Google token exchange was rejected")
        return redirect("/dang-nhap/?error=google_token_failed")
    except (urllib.error.URLError, TimeoutError):
        logger.warning("Google token exchange failed due to network timeout")
        return redirect("/dang-nhap/?error=google_token_network_error")
    except (ValueError, KeyError, TypeError):
        logger.warning("Google token endpoint returned an invalid response")
        return redirect("/dang-nhap/?error=google_token_failed")

    # 2. Fetch User Profile from Google UserInfo endpoint
    userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    try:
        userinfo_req = urllib.request.Request(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": "AIBusinessPlatform-OAuth/1.0"},
        )
        with _google_urlopen(userinfo_req, timeout=10) as response:
            userinfo = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        logger.warning("Google userinfo request failed")
        return redirect("/dang-nhap/?error=google_userinfo_error")
    except (ValueError, KeyError, TypeError):
        logger.warning("Google userinfo response was invalid")
        return redirect("/dang-nhap/?error=google_userinfo_error")

    email = userinfo.get("email", "").strip().lower()
    subject = str(userinfo.get("sub", "")).strip()
    name = userinfo.get("name") or userinfo.get("given_name") or email.split("@")[0]

    if not resolve_customer_recipients(None, email):
        return redirect("/dang-nhap/?error=google_no_email")
    if userinfo.get("email_verified") is not True:
        return redirect("/dang-nhap/?error=google_email_unverified")
    if not subject:
        return redirect("/dang-nhap/?error=google_identity_missing")

    # 3. Resolve the stable Google subject, linking by verified email only once.
    try:
        with transaction.atomic():
            identity = SocialIdentity.objects.select_related("user").filter(
                provider=SocialIdentity.Provider.GOOGLE,
                subject=subject,
            ).first()
            is_new_user = False
            activated_by_google = False
            if identity:
                user = identity.user
                email_owner = User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists()
                if email_owner:
                    return redirect("/dang-nhap/?error=google_identity_collision")
                if identity.provider_email != email:
                    identity.provider_email = email
                    identity.save(update_fields=("provider_email", "updated_at"))
            else:
                user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
                if user and SocialIdentity.objects.filter(
                    provider=SocialIdentity.Provider.GOOGLE, user=user
                ).exists():
                    return redirect("/dang-nhap/?error=google_identity_collision")
                if not user:
                    user = User.objects.create_user(username=email, email=email, first_name=name)
                    user.set_unusable_password()
                    user.save()
                    is_new_user = True
                SocialIdentity.objects.create(
                    provider=SocialIdentity.Provider.GOOGLE,
                    subject=subject,
                    user=user,
                    provider_email=email,
                )
            if not user.is_active:
                user.is_active = True
                activated_by_google = True
            first_name_changed = False
            if not user.first_name and name:
                user.first_name = name
                first_name_changed = True
            update_fields = []
            if activated_by_google:
                update_fields.append("is_active")
            if first_name_changed:
                update_fields.append("first_name")
            if update_fields:
                user.save(update_fields=tuple(set(update_fields + ["updated_at"])))
    except IntegrityError:
        logger.warning("Google identity linking rejected due to a uniqueness collision")
        return redirect("/dang-nhap/?error=google_identity_collision")

    # Invariant Rule 4: Public customer NEVER receives staff permissions or workspace membership
    # 4. Link or Create Customer Profile in Retail Workspace
    retail_ws = Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first() or Workspace.objects.first()
    customer_record = Customer.objects.filter(user=user, workspace=retail_ws).first() if retail_ws else None
    if not customer_record and retail_ws:
        cust_code = f"CUST-GG-{random.randint(10000, 99999)}"
        customer_record = Customer.objects.create(
            workspace=retail_ws,
            user=user,
            code=cust_code,
            name=name,
            email=email,
        )
        transaction.on_commit(lambda c=customer_record: dispatch_new_customer_notification(c))
    elif customer_record and not customer_record.name:
        customer_record.name = name
        customer_record.save(update_fields=["name"])
    if customer_record and activated_by_google:
        transaction.on_commit(lambda c=customer_record: dispatch_new_customer_notification(c))

    # 5. Log user in with standard ModelBackend
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    # 6. Dispatch Customer Emails
    # A. Welcome Email if newly registered via Google
    email_results = []
    if (is_new_user or activated_by_google) and user.email:
        email_results.append(
            send_customer_welcome_email(
                user_email=user.email,
                name=user.first_name or user.username,
                customer_code=getattr(customer_record, "code", "") if customer_record else "",
                user=user,
                deduplication_key=f"welcome:user:{user.pk}:{user.email.lower()}",
            )
        )

    # B. Security Login Alert for Google Sign-In
    if user.email:
        client_ip = get_client_ip(request)
        email_results.append(
            send_customer_login_alert_email(
                user_email=user.email,
                name=user.first_name or user.username,
                ip_address=client_ip,
                login_method="Google Sign-In (OAuth 2.0)",
                user=user,
                deduplication_key=f"login:google:{user.pk}:{uuid.uuid4().hex}",
            )
        )
    if any(not result for result in email_results):
        request.session["customer_email_warning"] = True

    # 7. Safe redirection
    if (
        next_url
        and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()})
        and not next_url.startswith("/dang-nhap")
        and not next_url.startswith("/dang-ky")
        and not next_url.startswith("/dang-xuat")
        and not next_url.startswith("/accounts/login")
        and not next_url.startswith("/accounts/google")
    ):
        if next_url.startswith("/noibo"):
            return redirect("/tai-khoan/?notice=customer_only")
        return redirect(next_url)

    return redirect("/tai-khoan/?login=google")


# =========================================================================
# 3. PUBLIC E-COMMERCE CART & CHECKOUT FLOW
# =========================================================================

def get_client_ip(request):
    """Retrieves client IP address safely for audit logging."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def serialize_cart_summary(cart, delivery_method="HOME_DELIVERY"):
    """Serializes ShoppingCart state to a clean JSON-friendly dictionary."""
    summary = cart.get_summary(delivery_method=delivery_method)
    items_data = []
    for item in summary["items"]:
        items_data.append({
            "product_id": item.product.id,
            "name": item.product.name,
            "sku": item.product.sku,
            "unit_price": int(item.unit_price),
            "formatted_unit_price": f"{int(item.unit_price):,}₫".replace(",", "."),
            "quantity": item.quantity,
            "line_total": int(item.line_total),
            "formatted_line_total": f"{int(item.line_total):,}₫".replace(",", "."),
            "image_url": item.image_url,
            "category_name": item.product.category.name if item.product.category else "",
            "detail_url": f"/san-pham/{item.product.id}/",
        })
    subtotal_int = int(summary["subtotal"])
    threshold_int = int(summary["free_shipping_threshold"])
    remaining_for_free = max(0, threshold_int - subtotal_int)
    progress_pct = min(100, int((subtotal_int / threshold_int) * 100)) if threshold_int > 0 else 100

    return {
        "items": items_data,
        "items_count": summary["items_count"],
        "total_quantity": summary["total_quantity"],
        "subtotal": subtotal_int,
        "formatted_subtotal": f"{subtotal_int:,}₫".replace(",", "."),
        "shipping_fee": int(summary["shipping_fee"]),
        "formatted_shipping_fee": f"{int(summary['shipping_fee']):,}₫".replace(",", ".") if summary['shipping_fee'] > 0 else "Miễn phí",
        "total_amount": int(summary["total_amount"]),
        "formatted_total_amount": f"{int(summary['total_amount']):,}₫".replace(",", "."),
        "is_free_shipping": summary["is_free_shipping"],
        "free_shipping_threshold": threshold_int,
        "remaining_for_free": remaining_for_free,
        "formatted_remaining": f"{remaining_for_free:,}₫".replace(",", "."),
        "progress_pct": progress_pct,
    }


def public_cart_json_view(request):
    """
    Returns live cart state as JSON for Slide-over Cyber Cart Drawer (GET /gio-hang/api/).
    """
    cart = get_cart(request)
    delivery_method = request.GET.get("delivery_method", "HOME_DELIVERY")
    data = serialize_cart_summary(cart, delivery_method=delivery_method)
    return JsonResponse(data)


def public_cart_view(request):
    """
    Public Shopping Cart View (GET /gio-hang/) - Light Theme.
    Re-calculates prices and totals from database Product records.
    """
    cart = get_cart(request)
    delivery_method = request.GET.get("delivery_method", "HOME_DELIVERY")
    summary = cart.get_summary(delivery_method=delivery_method)
    added_notice = request.GET.get("added") == "1"

    context = {
        "page_title": "Giỏ hàng của bạn | ABC Tech Store",
        "summary": summary,
        "items": summary["items"],
        "added_notice": added_notice,
        "active_nav": "cart",
    }
    return render(request, "public/cart.html", context)


def public_cart_add_view(request, pk):
    """
    Adds a product to shopping cart (POST /gio-hang/them/<pk>/).
    Supports 'buy_now' (redirects to /gio-hang/) and 'add_to_cart'.
    Also supports AJAX requests returning JSON.
    """
    if request.method not in ("POST", "GET"):
        return redirect("/san-pham/")

    raw_qty = request.POST.get("quantity") or request.GET.get("quantity") or 1
    action = request.POST.get("action") or request.GET.get("action") or "buy_now"

    try:
        quantity = max(1, int(raw_qty))
    except (ValueError, TypeError):
        quantity = 1

    cart = get_cart(request)
    success = cart.add(product_id=pk, quantity=quantity)

    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.GET.get("format") == "json"
        or request.POST.get("format") == "json"
        or "application/json" in request.headers.get("Accept", "")
    )

    if is_ajax:
        if not success:
            return JsonResponse({"success": False, "error": "Sản phẩm hiện không khả dụng."}, status=400)
        return JsonResponse({
            "success": True,
            "cart": serialize_cart_summary(cart),
            "total_items": cart.total_items_count,
        })

    if not success:
        return redirect(f"/san-pham/{pk}/?error=unavailable")

    if action == "buy_now":
        return redirect("/gio-hang/")
    return redirect(f"/gio-hang/?added=1")


def public_cart_update_view(request, pk):
    """
    Updates quantity of an item in shopping cart (POST /gio-hang/cap-nhat/<pk>/).
    Supports AJAX JSON responses.
    """
    if request.method == "POST":
        raw_qty = request.POST.get("quantity", "1")
        try:
            quantity = int(raw_qty)
        except (ValueError, TypeError):
            quantity = 1

        cart = get_cart(request)
        cart.set_quantity(product_id=pk, quantity=quantity)

        is_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.POST.get("format") == "json"
            or "application/json" in request.headers.get("Accept", "")
        )
        if is_ajax:
            return JsonResponse({
                "success": True,
                "cart": serialize_cart_summary(cart),
                "total_items": cart.total_items_count,
            })

    return redirect("/gio-hang/")


def public_cart_remove_view(request, pk):
    """
    Removes an item from shopping cart (POST /gio-hang/xoa/<pk>/).
    Supports AJAX JSON responses.
    """
    if request.method == "POST":
        cart = get_cart(request)
        cart.remove(product_id=pk)

        is_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.POST.get("format") == "json"
            or "application/json" in request.headers.get("Accept", "")
        )
        if is_ajax:
            return JsonResponse({
                "success": True,
                "cart": serialize_cart_summary(cart),
                "total_items": cart.total_items_count,
            })

    return redirect("/gio-hang/")


def public_cart_clear_view(request):
    """
    Clears all items from shopping cart (POST /gio-hang/xoa-tat-ca/).
    """
    if request.method == "POST":
        cart = get_cart(request)
        cart.clear()

        is_ajax = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or request.POST.get("format") == "json"
            or "application/json" in request.headers.get("Accept", "")
        )
        if is_ajax:
            return JsonResponse({
                "success": True,
                "cart": serialize_cart_summary(cart),
                "total_items": 0,
            })

    return redirect("/gio-hang/")


def public_copilot_api_view(request):
    """
    Public Customer AI Copilot API (POST /api/v1/public/copilot/).
    Safe customer-facing assistant providing:
    - Product specs, prices, and stock availability
    - IT service recommendations and SLA commitments (< 15 min response)
    - Branch locations, addresses, and hotlines
    - Order tracking by order number
    Zero leakage of internal business metrics (cost prices, labor rates, suppliers, workload).
    """
    if request.method != "POST":
        return JsonResponse({
            "status": "online",
            "assistant": "ABC Tech & XYZ IT Public Copilot",
            "capabilities": ["product_recommendation", "service_sla", "branch_locator", "order_tracking"]
        })

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

    if not isinstance(data, dict) or not isinstance(data.get("message", ""), str):
        return JsonResponse({"error": "Nội dung câu hỏi không hợp lệ."}, status=400)
    user_query = data.get("message", "").strip()
    if not user_query:
        user_query = request.POST.get("message", "").strip()

    if len(user_query) > 2000:
        return JsonResponse({"error": "Câu hỏi không được vượt quá 2000 ký tự."}, status=400)

    if not user_query:
        return JsonResponse({
            "reply": "Xin chào! Tôi là **AI Copilot** – Trợ lý điều phối công nghệ của ABC Tech Store & XYZ IT Services. Bạn có thể hỏi tôi về cấu hình máy tính, linh kiện, dịch vụ kỹ thuật, hoặc tra cứu chi nhánh gần nhất.",
            "suggestions": ["Tư vấn Laptop doanh nghiệp", "Chuột & phụ kiện cao cấp", "Dịch vụ IT khẩn cấp (SLA 15m)", "Hệ thống chi nhánh & Hotline"]
        })

    q_lower = user_query.lower()
    
    # 1. Order tracking intent
    import re
    order_match = re.search(r'(ORD-[A-Z0-9\-]+|[0-9]{5,})', user_query, re.IGNORECASE)
    if any(k in q_lower for k in ["đơn hàng", "tra cứu", "vận chuyển", "kiểm tra đơn", "order"]) and order_match:
        matched_code = order_match.group(1).upper()
        from .customer_identity import customer_orders
        if request.user.is_authenticated:
            orders = customer_orders(request.user)
        else:
            orders = Order.objects.filter(
                workspace__workspace_type=WorkspaceType.RETAIL,
                created_by__isnull=True,
                order_number__in=request.session.get("public_order_success_numbers", []),
            )
        order = orders.filter(order_number__iexact=matched_code).first()
        if order:
            items_count = order.items.count()
            status_display = order.get_status_display() if hasattr(order, "get_status_display") else order.status
            total_vnd = f"{int(order.total_amount):,}₫".replace(",", ".")
            created_date = order.created_at.strftime("%d/%m/%Y %H:%M")
            reply = (
                f"📦 **Thông tin đơn hàng {order.order_number}:**\n"
                f"- **Trạng thái:** `{status_display}`\n"
                f"- **Ngày đặt:** {created_date}\n"
                f"- **Số lượng sản phẩm:** {items_count} mặt hàng\n"
                f"- **Tổng giá trị:** {total_vnd}\n"
                f"Quý khách có thể xem chi tiết hành trình tại [Lịch sử đơn hàng](/tai-khoan/don-hang/{order.order_number}/)."
            )
            return JsonResponse({
                "reply": reply,
                "suggestions": ["Mua thêm phụ kiện", "Yêu cầu kỹ thuật cài đặt", "Hỗ trợ bảo hành"]
            })
        else:
            return JsonResponse({
                "reply": f"Không tìm thấy đơn hàng mã `{matched_code}`. Quý khách vui lòng kiểm tra lại mã đơn hàng hoặc đăng nhập tại [Tài khoản khách hàng](/tai-khoan/) để xem toàn bộ lịch sử.",
                "suggestions": ["Xem lịch sử đơn hàng", "Tư vấn sản phẩm mới", "Liên hệ hỗ trợ"]
            })

    # 2. Branch & Location intent
    if any(k in q_lower for k in ["chi nhánh", "địa chỉ", "ở đâu", "vị trí", "quận", "hà nội", "hồ chí minh", "đà nẵng", "hotline", "gần nhất", "bản đồ"]):
        branches = Branch.objects.filter(is_active=True, workspace__workspace_type=WorkspaceType.RETAIL).order_by("name")[:4]
        if branches:
            lines = ["🏢 **Hệ thống Chi nhánh & Trạm kỹ thuật ABC Tech - XYZ IT:**\n"]
            for b in branches:
                lines.append(f"📍 **{b.name}**\n   - Địa chỉ: {b.address or 'Trung tâm công nghệ'}\n   - Hotline: `{b.phone or '1900 6868'}` (08:00 - 21:30)")
            lines.append("\n👉 Quý khách có thể bật định vị GPS để xem trạm gần nhất tại [Bản đồ chiến thuật GIS](/chi-nhanh/).")
            return JsonResponse({
                "reply": "\n".join(lines),
                "suggestions": ["Xem bản đồ chi nhánh", "Đặt lịch hẹn tại trạm kỹ thuật", "Tư vấn sản phẩm"]
            })

    # 3. Technical Service & SLA intent
    if any(k in q_lower for k in ["dịch vụ", "kỹ thuật", "sửa", "cài đặt", "mạng", "bảo trì", "server", "sla", "khẩn cấp", "sự cố", "khắc phục", "it"]):
        services = Service.objects.filter(is_active=True, workspace__workspace_type=WorkspaceType.SERVICE)
        srv_matches = []
        for word in user_query.split():
            if len(word) >= 3:
                srv_matches.extend(services.filter(Q(name__icontains=word) | Q(description__icontains=word) | Q(category__icontains=word)))
        matched_services = list({s.id: s for s in srv_matches}.values()) if srv_matches else list(services[:3])
        
        lines = [
            "⚡ **Dịch vụ Kỹ thuật Doanh nghiệp & Xử lý Sự cố (XYZ IT Services):**\n",
            "🛡️ **Cam kết SLA:** Phản hồi xác nhận trong **< 15 phút** cho sự cố khẩn cấp (P1), kỹ sư có mặt tại hiện trường trong **30-45 phút**.\n"
        ]
        for s in matched_services[:3]:
            lines.append(f"🔹 **{s.name}** ({s.category})\n   - {s.description[:120]}...\n   - [Đặt yêu cầu dịch vụ này](/yeu-cau-dich-vu/?service_id={s.id})")
        
        lines.append("\nHoặc gửi yêu cầu trực tiếp qua [Form Điều phối Dịch vụ 3 bước](/yeu-cau-dich-vu/).")
        return JsonResponse({
            "reply": "\n".join(lines),
            "suggestions": ["Gửi yêu cầu dịch vụ", "Sự cố máy chủ/mạng", "Bảo trì định kỳ", "Hỏi mua thiết bị"]
        })

    # 4. Product Catalog intent (hardware, laptops, accessories, price)
    products = Product.objects.filter(
        is_active=True,
        deleted_at__isnull=True,
        workspace__workspace_type=WorkspaceType.RETAIL,
    ).select_related("category")
    
    prod_matches = []
    keywords = [w for w in user_query.split() if len(w) >= 2]
    q_filter = Q()
    for kw in keywords:
        q_filter |= Q(name__icontains=kw) | Q(description__icontains=kw) | Q(sku__icontains=kw) | Q(category__name__icontains=kw)
    
    if q_filter:
        prod_matches = list(products.filter(q_filter)[:4])
        
    if not prod_matches and any(k in q_lower for k in ["sản phẩm", "laptop", "máy tính", "chuột", "phím", "thiết bị", "mua", "giá", "hardware"]):
        prod_matches = list(products[:4])

    if prod_matches:
        lines = ["💻 **Sản phẩm công nghệ chính hãng tại ABC Tech Store:**\n"]
        for p in prod_matches:
            price_str = f"{int(p.unit_price):,}₫".replace(",", ".")
            lines.append(f"✨ **{p.name}**\n   - Mã SKU: `{p.sku}` | Danh mục: {p.category.name if p.category else 'Thiết bị'}\n   - Giá niêm yết: **{price_str}**\n   - [Xem chi tiết & Mua hàng](/san-pham/{p.id}/)")
        lines.append("\n🚚 *Miễn phí vận chuyển toàn quốc cho đơn hàng từ 5.000.000₫. Cam kết 100% hàng chính hãng CO/CQ.*")
        return JsonResponse({
            "reply": "\n".join(lines),
            "suggestions": ["Xem toàn bộ sản phẩm", "Chính sách bảo hành", "Tìm chi nhánh mua trực tiếp", "Dịch vụ kỹ thuật đi kèm"]
        })

    # 5. Default smart guidance
    return JsonResponse({
        "reply": (
            "Xin chào! Tôi là **AI Copilot** – Trợ lý điều phối công nghệ của ABC Tech Store & XYZ IT Services. "
            "Tôi có thể hỗ trợ bạn tìm kiếm bất kỳ thông tin nào trên hệ thống:\n\n"
            "1. 🖥️ **Sản phẩm & Cấu hình:** Tìm kiếm laptop, máy trạm, linh kiện chính hãng và giá ưu đãi.\n"
            "2. 🛠️ **Hỗ trợ Kỹ thuật:** Tiếp nhận sự cố IT, điều phối kỹ sư lưu động với cam kết SLA < 15 phút.\n"
            "3. 📍 **Trạm kỹ thuật & Chi nhánh:** Vị trí 3 showroom & trạm dịch vụ trung tâm.\n"
            "4. 📦 **Tra cứu đơn hàng:** Kiểm tra tiến độ xử lý và hành trình giao nhận.\n\n"
            "Bạn có thể chọn một trong các gợi ý bên dưới hoặc nhập câu hỏi cụ thể!"
        ),
        "suggestions": ["Tư vấn Laptop doanh nghiệp", "Dịch vụ IT khẩn cấp", "Tìm chi nhánh gần tôi", "Chính sách bảo hành"]
    })


def public_checkout_view(request):
    """
    Public Checkout Page (GET /thanh-toan/) - Light Theme.
    Step 2: Customer details, shipping address, delivery method, and COD payment review.
    """
    cart = get_cart(request)
    items = cart.get_items()
    if not items:
        return redirect("/gio-hang/")

    delivery_method = request.GET.get("delivery_method", "HOME_DELIVERY")
    summary = cart.get_summary(delivery_method=delivery_method)

    branches = Branch.objects.filter(is_active=True, workspace__workspace_type=WorkspaceType.RETAIL).order_by("name")

    # Pre-fill customer info if logged in
    customer_name = ""
    customer_phone = ""
    customer_email = ""
    customer_address = ""

    if request.user.is_authenticated:
        customer_name = request.user.first_name or request.user.username
        customer_email = request.user.email
        customer_profile = Customer.objects.filter(user=request.user, workspace__workspace_type=WorkspaceType.RETAIL).first()
        if customer_profile:
            customer_name = customer_profile.name or customer_name
            customer_phone = customer_profile.phone or ""
            customer_address = customer_profile.address or ""

    error_message = request.session.pop("checkout_error", None)

    context = {
        "page_title": "Thanh toán đơn hàng | ABC Tech Store",
        "summary": summary,
        "items": items,
        "branches": branches,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "customer_email": customer_email,
        "customer_address": customer_address,
        "delivery_method": delivery_method,
        "error_message": error_message,
        "active_nav": "cart",
    }
    return render(request, "public/checkout.html", context)


@transaction.atomic
def public_checkout_place_order_view(request):
    """
    Atomic Order Placement (POST /thanh-toan/dat-hang/ or POST /thanh-toan/).
    Validates products, recalculates totals server-side, snapshots prices in OrderItem,
    checks/decrements branch stock if applicable, creates Order, logs AuditLog, and clears cart.
    """
    if request.method != "POST":
        return redirect("/thanh-toan/")

    cart = get_cart(request)
    cart_items = cart.get_items()
    if not cart_items:
        request.session["checkout_error"] = "Giỏ hàng của bạn đang trống."
        return redirect("/gio-hang/")

    name = request.POST.get("name", "").strip()
    phone = request.POST.get("phone", "").strip()
    email = request.POST.get("email", "").strip().lower()
    address = request.POST.get("address", "").strip()
    city = request.POST.get("city", "").strip()
    district = request.POST.get("district", "").strip()
    notes = request.POST.get("notes", "").strip()
    delivery_method = request.POST.get("delivery_method", "HOME_DELIVERY").strip()
    branch_id = request.POST.get("branch_id", "").strip()

    # Form Validation
    if not name or not phone or not email:
        request.session["checkout_error"] = "Vui lòng điền đầy đủ Họ tên, Số điện thoại và Email."
        return redirect("/thanh-toan/")

    if delivery_method == "HOME_DELIVERY" and not address:
        request.session["checkout_error"] = "Vui lòng nhập địa chỉ nhận hàng chi tiết."
        return redirect("/thanh-toan/")

    retail_ws = Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first() or Workspace.objects.first()
    if not retail_ws:
        request.session["checkout_error"] = "Không gian làm việc bán lẻ chưa sẵn sàng."
        return redirect("/thanh-toan/")

    # Validate Branch if Store Pickup
    branch = None
    if delivery_method == "STORE_PICKUP":
        if not branch_id:
            request.session["checkout_error"] = "Vui lòng chọn chi nhánh cửa hàng để nhận hàng."
            return redirect("/thanh-toan/")
        branch = Branch.objects.filter(id=branch_id, is_active=True, workspace=retail_ws).first()
        if not branch:
            request.session["checkout_error"] = "Chi nhánh được chọn không tồn tại hoặc đã ngừng hoạt động."
            return redirect("/thanh-toan/")

    # Re-validate live product state & lock rows to prevent concurrency race conditions
    product_ids = [item.product.id for item in cart_items]
    locked_products = Product.objects.select_for_update().filter(
        id__in=product_ids,
        workspace=retail_ws,
    )
    product_map = {p.id: p for p in locked_products}

    # Verify all products are active and not deleted
    for item in cart_items:
        prod = product_map.get(item.product.id)
        if not prod or not prod.is_active or prod.is_deleted:
            request.session["checkout_error"] = f"Sản phẩm '{item.product.name}' hiện không còn kinh doanh. Vui lòng cập nhật giỏ hàng."
            return redirect("/gio-hang/")

    # Optional Stock Balance validation & safe deduction if branch stock balance exists
    if branch:
        for item in cart_items:
            stock = StockBalance.objects.select_for_update().filter(
                workspace=retail_ws,
                branch=branch,
                product_id=item.product.id,
            ).first()
            if stock:
                if stock.quantity_on_hand < item.quantity:
                    request.session["checkout_error"] = f"Sản phẩm '{item.product.name}' tại chi nhánh '{branch.name}' chỉ còn {stock.quantity_on_hand} sản phẩm (yêu cầu: {item.quantity})."
                    return redirect("/gio-hang/")
                stock.quantity_on_hand -= item.quantity
                stock.save(update_fields=["quantity_on_hand", "updated_at"])

    from .customer_identity import customer_for_submission
    customer = customer_for_submission(
        workspace=retail_ws, user=request.user, name=name,
        email=email, phone=phone, address=address,
    )

    # Server-Side Computations
    subtotal = sum(product_map[item.product.id].unit_price * Decimal(item.quantity) for item in cart_items)
    shipping_fee = cart.calculate_shipping_fee(delivery_method)
    total_amount = subtotal + shipping_fee

    today = timezone.now().date()
    rand_suffix = uuid.uuid4().hex[:6].upper()
    order_number = f"ORD-{today.strftime('%Y%m%d')}-{rand_suffix}"

    # Build comprehensive delivery notes
    full_address_parts = [p for p in [address, district, city] if p]
    full_address = ", ".join(full_address_parts)
    delivery_label = "Nhận tại chi nhánh" if delivery_method == "STORE_PICKUP" else "Giao hàng tận nơi"
    order_notes = f"[{delivery_label}] Người nhận: {name} ({phone}). Địa chỉ: {full_address or 'Nhận tại cửa hàng'}"
    if notes:
        order_notes += f". Ghi chú: {notes}"
    if shipping_fee > Decimal("0.00"):
        order_notes += f". Phí vận chuyển: {shipping_fee:,.0f} VNĐ"

    # Create Order Header
    order = Order.objects.create(
        workspace=retail_ws,
        order_number=order_number,
        customer=customer,
        branch=branch,
        order_date=today,
        order_timestamp=timezone.now(),
        status=OrderStatus.PENDING,
        subtotal_amount=subtotal,
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        total_amount=total_amount,
        payment_method=PaymentMethod.CASH,
        created_by=request.user if request.user.is_authenticated else None,
        notes=order_notes,
    )

    from .models import OrderDeliveryAddress
    OrderDeliveryAddress.objects.create(
        order=order, recipient_name=name, email=email, phone=phone,
        address_line=address, district=district, city=city, delivery_method=delivery_method,
    )

    # Create Line Items with HISTORICAL PRICE SNAPSHOT
    for item in cart_items:
        prod = product_map[item.product.id]
        OrderItem.objects.create(
            order=order,
            product=prod,
            quantity=item.quantity,
            unit_price=prod.unit_price,  # Critical: Historical Snapshot
            discount=Decimal("0.00"),
            subtotal=prod.unit_price * Decimal(item.quantity),
        )

    # Log AuditLog
    log_action(
        workspace=retail_ws,
        actor_user=request.user if request.user.is_authenticated else None,
        action="ORDER_CREATED",
        entity_type="Order",
        entity_id=order.id,
        changes={
            "order_number": order.order_number,
            "total_amount": str(order.total_amount),
            "customer": customer.name,
            "items_count": len(cart_items),
            "delivery_method": delivery_method,
        },
        ip_address=get_client_ip(request),
    )

    # Dispatch New Order Notification safely on commit
    transaction.on_commit(lambda o=order: dispatch_new_order_notification(o))

    # Dispatch Customer Order Confirmation Email
    order_recipients = resolve_customer_recipients(
        request.user if request.user.is_authenticated else None, email
    )
    delivery_user = request.user if request.user.is_authenticated else None
    for recipient in order_recipients:
        send_order_confirmation_email(
            order=order,
            recipient_email=recipient,
            user=delivery_user,
            deduplication_key=f"order:{order.pk}:{recipient}",
            defer_delivery=True,
        )

    # Clean Shopping Cart
    cart.clear()

    # Guest success pages are visible only in the browser session that created them.
    session_orders = request.session.get("public_order_success_numbers", [])
    request.session["public_order_success_numbers"] = ([*session_orders, order.order_number])[-10:]

    return redirect(f"/dat-hang-thanh-cong/{order.order_number}/")


def public_order_success_view(request, order_number):
    """
    Public Order Success Confirmation View (GET /dat-hang-thanh-cong/<order_number>/) - Light Theme.
    Displays order confirmation summary, line items snapshot, and next steps.
    """
    orders = Order.objects.select_related("customer", "branch").prefetch_related("items__product").filter(
        workspace__workspace_type=WorkspaceType.RETAIL,
    )
    if request.user.is_authenticated:
        orders = orders.filter(
            created_by=request.user
        )
    elif order_number not in request.session.get("public_order_success_numbers", []):
        orders = orders.none()

    order = get_object_or_404(orders, order_number=order_number)

    deliveries = CustomerEmailDelivery.objects.filter(entity_type="Order", entity_id=str(order.pk))
    resendable_deliveries = deliveries.none()
    if request.user.is_authenticated:
        resendable_deliveries = deliveries.filter(
            user=request.user,
            status__in=(CustomerEmailDelivery.Status.PENDING, CustomerEmailDelivery.Status.FAILED),
        )
    context = {
        "page_title": f"Đặt hàng thành công #{order.order_number} | ABC Tech Store",
        "order": order,
        "items": order.items.all(),
        "email_delivery_failed": deliveries.filter(status=CustomerEmailDelivery.Status.FAILED).exists(),
        "resendable_email_deliveries": resendable_deliveries,
        "active_nav": "cart",
    }
    return render(request, "public/order_success.html", context)


@login_required(login_url="/dang-nhap/")
def public_customer_orders_view(request):
    """
    Public Customer Order History List (GET /tai-khoan/don-hang/) - Light Theme.
    Displays only the authenticated customer's own commercial orders.
    """
    customer_profile = Customer.objects.filter(
        user=request.user,
        workspace__workspace_type=WorkspaceType.RETAIL,
    ).first()
    from .customer_identity import customer_orders
    orders = customer_orders(request.user).select_related("branch").order_by("-order_timestamp")

    context = {
        "page_title": "Đơn hàng của tôi | Nền tảng Doanh nghiệp AI",
        "orders": orders,
        "customer": customer_profile,
        "active_nav": "account",
    }
    return render(request, "public/customer_orders.html", context)


@login_required(login_url="/dang-nhap/")
def public_customer_order_detail_view(request, order_number):
    """
    Public Customer Order Detail (GET /tai-khoan/don-hang/<order_number>/) - Light Theme.
    Strict IDOR Protection: Verifies order strictly belongs to authenticated customer.
    """
    customer_profile = Customer.objects.filter(
        user=request.user,
        workspace__workspace_type=WorkspaceType.RETAIL,
    ).first()

    # Strict IDOR Enforcement
    order = get_object_or_404(
        Order.objects.select_related("customer", "branch").prefetch_related("items__product"),
        order_number=order_number,
        created_by=request.user,
        workspace__workspace_type=WorkspaceType.RETAIL,
    )

    context = {
        "page_title": f"Chi tiết đơn hàng #{order.order_number} | Nền tảng Doanh nghiệp AI",
        "order": order,
        "items": order.items.all(),
        "customer": customer_profile,
        "active_nav": "account",
    }
    return render(request, "public/customer_order_detail.html", context)
