"""
Customer Email Service Module.
Handles formatted transactional and notification emails sent directly to customers:
- Registration & Welcome notifications
- Login security alert notifications (Google OAuth & standard credentials)
- E-Commerce order confirmation with itemized breakdown
- Technical service inquiry acknowledgment & SLA commitment
- Contact message confirmation
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional, Any
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.public_web.models import CustomerEmailDelivery

logger = logging.getLogger(__name__)

PLATFORM_BRAND_NAME = "Nền tảng Doanh nghiệp AI (ABC Tech Store & XYZ IT Services)"
SUPPORT_HOTLINE = "1900 6868"
SUPPORT_EMAIL = "contact@abctech.vn"
OFFICE_ADDRESS = "Tầng 12, Tòa nhà Công nghệ, Quận 1, TP. Hồ Chí Minh"


@dataclass(frozen=True)
class DeliveryResult:
    recipient: str
    status: str
    accepted_count: int
    error_code: str = ""
    public_id: str = ""

    def __bool__(self):
        return self.status == CustomerEmailDelivery.Status.SENT


def normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def resolve_customer_recipients(user=None, form_email: str = "") -> list[str]:
    """Return validated, case-insensitively deduplicated private recipients."""
    candidates = []
    if user is not None and getattr(user, "is_authenticated", False):
        candidates.append(getattr(user, "email", ""))
    candidates.append(form_email)
    recipients, seen = [], set()
    for candidate in candidates:
        email = normalize_email(candidate)
        if not email or email in seen:
            continue
        try:
            validate_email(email)
        except ValidationError:
            continue
        seen.add(email)
        recipients.append(email)
    return recipients


def public_url(path: str = "") -> str:
    base = getattr(settings, "PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base}/{path.lstrip('/')}" if base else ""


def _delivery_configuration_error() -> str:
    backend = settings.EMAIL_BACKEND
    if backend == "django.core.mail.backends.locmem.EmailBackend":
        return ""
    if backend == "django.core.mail.backends.smtp.EmailBackend":
        return "" if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD else "SMTP_CONFIG_MISSING"
    if backend in {"django.core.mail.backends.console.EmailBackend", "django.core.mail.backends.dummy.EmailBackend"}:
        return "NON_DELIVERING_BACKEND"
    return ""


def deliver_outbox_record(delivery: CustomerEmailDelivery) -> DeliveryResult:
    """Attempt one delivery and persist a truthful, sanitized outcome."""
    if delivery.status == CustomerEmailDelivery.Status.SENT:
        return DeliveryResult(delivery.recipient, delivery.status, 1, public_id=str(delivery.public_id))
    delivery.attempt_count += 1
    delivery.attempted_at = timezone.now()
    config_error = _delivery_configuration_error()
    if config_error:
        delivery.status = CustomerEmailDelivery.Status.FAILED
        delivery.last_error_code = config_error
        delivery.save(update_fields=("attempt_count", "attempted_at", "status", "last_error_code", "updated_at"))
        return DeliveryResult(delivery.recipient, delivery.status, 0, config_error, str(delivery.public_id))
    try:
        accepted = send_mail(
            subject=delivery.subject,
            message=delivery.plain_body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@abctech.vn"),
            recipient_list=[delivery.recipient],
            html_message=delivery.html_body or None,
            fail_silently=False,
        )
        if accepted != 1:
            raise RuntimeError("Email backend did not accept exactly one message")
        delivery.status = CustomerEmailDelivery.Status.SENT
        delivery.last_error_code = ""
        delivery.sent_at = timezone.now()
        delivery.save(update_fields=("attempt_count", "attempted_at", "status", "last_error_code", "sent_at", "updated_at"))
        logger.info("Customer email accepted event=%s delivery=%s", delivery.event_type, delivery.public_id)
        return DeliveryResult(delivery.recipient, delivery.status, 1, public_id=str(delivery.public_id))
    except Exception as exc:
        error_code = f"BACKEND_{exc.__class__.__name__.upper()}"[:80]
        delivery.status = CustomerEmailDelivery.Status.FAILED
        delivery.last_error_code = error_code
        delivery.save(update_fields=("attempt_count", "attempted_at", "status", "last_error_code", "updated_at"))
        logger.warning("Customer email failed event=%s delivery=%s error=%s", delivery.event_type, delivery.public_id, error_code)
        return DeliveryResult(delivery.recipient, delivery.status, 0, error_code, str(delivery.public_id))


def queue_and_deliver_email(*, event_type: str, recipient: str, subject: str, plain_body: str,
                            html_body: str = "", user=None, entity_type: str = "", entity_id: str = "",
                            deduplication_key: str = "", defer_delivery: bool = False) -> DeliveryResult:
    recipient = normalize_email(recipient)
    try:
        validate_email(recipient)
    except ValidationError:
        return DeliveryResult(recipient, CustomerEmailDelivery.Status.FAILED, 0, "INVALID_RECIPIENT")
    if not deduplication_key:
        material = "|".join((event_type, entity_type, str(entity_id), recipient, subject, plain_body))
        deduplication_key = hashlib.sha256(material.encode("utf-8")).hexdigest()
    delivery, _ = CustomerEmailDelivery.objects.get_or_create(
        deduplication_key=deduplication_key,
        defaults={
            "user": user if getattr(user, "is_authenticated", False) else None,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": str(entity_id or ""),
            "recipient": recipient,
            "subject": subject,
            "plain_body": plain_body,
            "html_body": html_body,
        },
    )
    if defer_delivery and delivery.status != CustomerEmailDelivery.Status.SENT:
        transaction.on_commit(
            lambda delivery_pk=delivery.pk: deliver_outbox_record(
                CustomerEmailDelivery.objects.get(pk=delivery_pk)
            )
        )
        return DeliveryResult(
            delivery.recipient, delivery.status, 0,
            delivery.last_error_code, str(delivery.public_id),
        )
    return deliver_outbox_record(delivery)


def _build_html_email_template(title: str, preheader: str, body_html: str, action_url: Optional[str] = None, action_text: Optional[str] = None) -> str:
    """
    Constructs a responsive, modern HTML email template matching the platform design tokens.
    """
    action_button_html = ""
    if action_url and action_text:
        action_button_html = f"""
        <div style="text-align: center; margin: 28px 0 10px;">
            <a href="{action_url}" style="background: #2563EB; color: #FFFFFF; text-decoration: none; padding: 13px 28px; border-radius: 8px; font-weight: 700; font-size: 15px; display: inline-block; letter-spacing: 0.02em;">
                {action_text} &rarr;
            </a>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F8FAFC; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #334155; line-height: 1.6;">
    <div style="display: none; max-height: 0px; overflow: hidden; mso-hide: all;">
        {preheader}
    </div>
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #F8FAFC; padding: 30px 15px;">
        <tr>
            <td align="center">
                <table width="600" border="0" cellspacing="0" cellpadding="0" style="max-width: 600px; width: 100%; background: #FFFFFF; border-radius: 14px; border: 1px solid #E2E8F0; overflow: hidden; box-shadow: 0 4px 14px rgba(0,0,0,0.04);">
                    <!-- Brand Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); padding: 26px 32px; text-align: left; border-bottom: 3px solid #2563EB;">
                            <table width="100%" border="0" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td>
                                        <div style="font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.12em; color: #38BDF8; margin-bottom: 4px;">
                                            Hệ Thống Doanh Nghiệp Hợp Nhất
                                        </div>
                                        <div style="font-size: 19px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.01em;">
                                            ABC Tech Store <span style="color: #64748B;">&</span> XYZ IT Services
                                        </div>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Main Body -->
                    <tr>
                        <td style="padding: 32px;">
                            <h2 style="font-size: 20px; font-weight: 800; color: #0F172A; margin: 0 0 16px; letter-spacing: -0.02em;">
                                {title}
                            </h2>
                            <div style="font-size: 14px; color: #334155; line-height: 1.65;">
                                {body_html}
                            </div>
                            {action_button_html}
                        </td>
                    </tr>
                    <!-- Support Notice Card -->
                    <tr>
                        <td style="padding: 0 32px 28px;">
                            <div style="background: #F1F5F9; border-radius: 10px; padding: 14px 18px; font-size: 13px; color: #475569; border-left: 4px solid #2563EB;">
                                <strong>Cần hỗ trợ khẩn cấp?</strong> Tổng đài kỹ sư trực tuyến: <span style="color: #2563EB; font-weight: 700;">{SUPPORT_HOTLINE}</span> (08:00 - 21:30 hàng ngày) hoặc hòm thư <span style="color: #2563EB; font-weight: 600;">{SUPPORT_EMAIL}</span>.
                            </div>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background: #F8FAFC; padding: 20px 32px; border-top: 1px solid #E2E8F0; text-align: center; font-size: 12px; color: #94A3B8; line-height: 1.5;">
                            <div>{PLATFORM_BRAND_NAME}</div>
                            <div>{OFFICE_ADDRESS}</div>
                            <div style="margin-top: 8px;">Đây là email tự động gửi từ hệ thống. Quý khách vui lòng không phản hồi trực tiếp vào hòm thư này.</div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def send_email_verification_email(user, verification_url: str, deduplication_key: str = "",
                                  defer_delivery: bool = False) -> DeliveryResult:
    """Send the ownership-verification link for a password registration."""
    email = normalize_email(getattr(user, "email", ""))
    if not email or not verification_url:
        return DeliveryResult(email, CustomerEmailDelivery.Status.FAILED, 0, "INVALID_VERIFICATION_REQUEST")
    display_name = user.first_name or user.username or email.split("@", 1)[0]
    subject = "[AlphaTech] Xác minh email để hoàn tất đăng ký"
    plain_text = f"""Xin chào {display_name},

Chúng tôi đã nhận được yêu cầu tạo tài khoản AlphaTech bằng địa chỉ email này.
Vui lòng mở liên kết dưới đây trong vòng 24 giờ để xác minh email và kích hoạt tài khoản:

{verification_url}

Nếu bạn không thực hiện đăng ký, hãy bỏ qua email này. Tài khoản chưa xác minh sẽ không thể đăng nhập.

Trân trọng,
Đội ngũ AlphaTech
"""
    body_html = f"""
    <p>Xin chào <strong>{display_name}</strong>,</p>
    <p>Chúng tôi đã nhận được yêu cầu tạo tài khoản AlphaTech bằng địa chỉ email này.</p>
    <p>Hãy xác minh quyền sở hữu email trong vòng <strong>24 giờ</strong>. Sau khi xác minh, tài khoản mới được kích hoạt và bạn sẽ nhận thư chào mừng với thông tin tài khoản.</p>
    <p style="font-size:13px;color:#64748B;">Nếu bạn không thực hiện đăng ký, hãy bỏ qua email này.</p>
    """
    html_content = _build_html_email_template(
        title="Xác Minh Email Đăng Ký",
        preheader="Xác minh email để kích hoạt tài khoản AlphaTech.",
        body_html=body_html,
        action_url=verification_url,
        action_text="Xác minh email",
    )
    return queue_and_deliver_email(
        event_type=CustomerEmailDelivery.EventType.EMAIL_VERIFICATION,
        recipient=email,
        subject=subject,
        plain_body=plain_text,
        html_body=html_content,
        user=user,
        entity_type="User",
        entity_id=user.pk,
        deduplication_key=deduplication_key,
        defer_delivery=defer_delivery,
    )


def send_customer_welcome_email(user_email: str, name: str, customer_code: Optional[str] = None,
                                phone: Optional[str] = None, user=None,
                                deduplication_key: str = "", defer_delivery: bool = False) -> DeliveryResult:
    """
    Sends a warm welcome email upon account registration or first-time Google sign-in.
    """
    if not user_email:
        return DeliveryResult("", CustomerEmailDelivery.Status.FAILED, 0, "INVALID_RECIPIENT")

    display_name = name or user_email.split("@")[0]
    subject = f"[ABC Tech & XYZ IT] Chào mừng {display_name} gia nhập Nền tảng Doanh nghiệp AI"
    preheader = "Tài khoản khách hàng của bạn đã được kích hoạt thành công."

    code_html = f"<li><strong>Mã khách hàng:</strong> <code style='background: #EFF6FF; color: #2563EB; padding: 2px 6px; border-radius: 4px; font-family: monospace;'>{customer_code}</code></li>" if customer_code else ""
    phone_html = f"<li><strong>Số điện thoại:</strong> {phone}</li>" if phone else ""

    body_html = f"""
    <p>Xin chào <strong>{display_name}</strong>,</p>
    <p>Chào mừng bạn đã đăng ký thành công tài khoản tại <strong>Nền tảng Doanh nghiệp AI</strong> — Hệ sinh thái tích hợp giữa bán lẻ thiết bị công nghệ chính hãng (ABC Tech Store) và dịch vụ kỹ thuật hạ tầng CNTT chuyên nghiệp (XYZ IT Technical Services).</p>
    
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px 20px; margin: 20px 0;">
        <h4 style="margin: 0 0 10px; font-size: 15px; color: #0F172A;">Thông tin tài khoản thành viên:</h4>
        <ul style="margin: 0; padding-left: 20px; font-size: 13.5px; color: #475569; line-height: 1.7;">
            <li><strong>Email đăng ký:</strong> {user_email}</li>
            {code_html}
            {phone_html}
            <li><strong>Trạng thái:</strong> <span style="color: #10B981; font-weight: 700;">Đã kích hoạt</span></li>
        </ul>
    </div>

    <p>Với tài khoản này, bạn có thể:</p>
    <ul style="margin: 0 0 16px; padding-left: 20px; font-size: 13.5px; color: #475569; line-height: 1.7;">
        <li>Mua sắm máy tính, thiết bị mạng, linh kiện cao cấp chính hãng 100% với chính sách bảo hành 1-đổi-1 trong 30 ngày.</li>
        <li>Gửi và theo dõi phiếu yêu cầu dịch vụ kỹ thuật, nhận hỗ trợ xử lý sự cố CNTT theo chuẩn cam kết SLA khắt khe.</li>
        <li>Quản lý lịch sử giao dịch và biên nhận điện tử minh bạch tại Cổng thông tin khách hàng.</li>
    </ul>
    """

    account_url = public_url("tai-khoan/")
    plain_text = f"""Xin chào {display_name},

Chào mừng bạn đã đăng ký tài khoản thành công tại Nền tảng Doanh nghiệp AI (ABC Tech Store & XYZ IT Services)!

Thông tin tài khoản:
- Email: {user_email}
{f'- Mã khách hàng: {customer_code}' if customer_code else ''}
{f'- Số điện thoại: {phone}' if phone else ''}
- Trạng thái: Đã kích hoạt

Bạn có thể truy cập {account_url} để quản lý đơn hàng và yêu cầu dịch vụ.

Tổng đài hỗ trợ: {SUPPORT_HOTLINE}
Trân trọng,
Đội ngũ Nền tảng Doanh nghiệp AI
"""

    html_content = _build_html_email_template(
        title="Chào Mừng Thành Viên Mới!",
        preheader=preheader,
        body_html=body_html,
        action_url=account_url,
        action_text="Truy cập Cổng Khách Hàng",
    )

    return queue_and_deliver_email(
        event_type=CustomerEmailDelivery.EventType.WELCOME,
        recipient=user_email, subject=subject, plain_body=plain_text, html_body=html_content,
        user=user, entity_type="User" if user else "", entity_id=getattr(user, "pk", ""),
        deduplication_key=deduplication_key,
        defer_delivery=defer_delivery,
    )


def send_customer_login_alert_email(user_email: str, name: str, ip_address: str = "",
                                    login_method: str = "Tài khoản mật khẩu", user=None,
                                    deduplication_key: str = "", defer_delivery: bool = False) -> DeliveryResult:
    """
    Sends a security notification email when a customer logs in (Google OAuth or password).
    """
    if not user_email:
        return DeliveryResult("", CustomerEmailDelivery.Status.FAILED, 0, "INVALID_RECIPIENT")

    display_name = name or user_email.split("@")[0]
    now_str = timezone.localtime(timezone.now()).strftime("%H:%M:%S, %d/%m/%Y")
    ip_display = ip_address or "Không xác định"

    subject = f"[AlphaTech] Bạn đã đăng nhập thành công bằng {login_method}"
    preheader = f"Tài khoản của bạn vừa đăng nhập thành công lúc {now_str}."

    body_html = f"""
    <p>Xin chào <strong>{display_name}</strong>,</p>
    <p>Bạn vừa đăng nhập thành công vào <strong>AlphaTech — Nền tảng Doanh nghiệp AI</strong>. Tài khoản của bạn đã sẵn sàng để mua sắm, theo dõi đơn hàng và gửi yêu cầu dịch vụ.</p>
    
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px 20px; margin: 20px 0;">
        <h4 style="margin: 0 0 10px; font-size: 15px; color: #0F172A;">Chi tiết phiên đăng nhập:</h4>
        <ul style="margin: 0; padding-left: 20px; font-size: 13.5px; color: #475569; line-height: 1.7;">
            <li><strong>Thời gian:</strong> {now_str}</li>
            <li><strong>Hình thức đăng nhập:</strong> <span style="color: #2563EB; font-weight: 700;">{login_method}</span></li>
            <li><strong>Địa chỉ IP:</strong> <code style="font-family: monospace; background: #E2E8F0; padding: 2px 6px; border-radius: 4px;">{ip_display}</code></li>
            <li><strong>Email tài khoản:</strong> {user_email}</li>
        </ul>
    </div>

    <p style="color: #64748B; font-size: 13px;">
        Nếu chính bạn vừa thực hiện thao tác này, bạn có thể an tâm bỏ qua thông báo. Trong trường hợp bạn không nhận ra phiên đăng nhập trên, vui lòng liên hệ tổng đài <strong>{SUPPORT_HOTLINE}</strong> hoặc đổi mật khẩu tài khoản ngay lập tức để bảo vệ an toàn dữ liệu.
    </p>
    """

    password_reset_url = public_url("quen-mat-khau/")
    plain_text = f"""Xin chào {display_name},

Hệ thống ghi nhận tài khoản của bạn vừa đăng nhập thành công:
- Thời gian: {now_str}
- Hình thức: {login_method}
- Địa chỉ IP: {ip_display}
- Email: {user_email}

Nếu không phải bạn thực hiện, vui lòng đổi mật khẩu ngay tại {password_reset_url} hoặc gọi {SUPPORT_HOTLINE}.

Trân trọng,
Đội ngũ Nền tảng Doanh nghiệp AI
"""

    html_content = _build_html_email_template(
        title="Đăng Nhập Thành Công",
        preheader=preheader,
        body_html=body_html,
        action_url=public_url("tai-khoan/"),
        action_text="Kiểm tra Tài Khoản",
    )

    return queue_and_deliver_email(
        event_type=CustomerEmailDelivery.EventType.LOGIN_ALERT,
        recipient=user_email, subject=subject, plain_body=plain_text, html_body=html_content,
        user=user, entity_type="User" if user else "", entity_id=getattr(user, "pk", ""),
        deduplication_key=deduplication_key,
        defer_delivery=defer_delivery,
    )


def send_order_confirmation_email(order: Any, recipient_email: Optional[str] = None, user=None,
                                  deduplication_key: str = "", defer_delivery: bool = False) -> DeliveryResult:
    """
    Sends an itemized order confirmation email to the purchasing customer.
    """
    email = recipient_email or (order.customer.email if order.customer else None)
    if not email:
        return DeliveryResult("", CustomerEmailDelivery.Status.FAILED, 0, "INVALID_RECIPIENT")

    customer_name = order.customer.name if order.customer else "Quý khách"
    order_number = order.order_number
    ts = getattr(order, "order_timestamp", None) or timezone.now()
    if timezone.is_aware(ts):
        time_str = timezone.localtime(ts).strftime("%H:%M, %d/%m/%Y")
    else:
        time_str = ts.strftime("%H:%M, %d/%m/%Y")
    
    # Items table build
    items = order.items.select_related("product").all()
    rows_html = ""
    rows_plain = ""
    for item in items:
        p_name = item.product.name if item.product else "Thiết bị"
        p_sku = item.product.sku if item.product else "-"
        qty = item.quantity
        price_formatted = f"{item.unit_price:,.0f}".replace(",", ".")
        sub_formatted = f"{item.subtotal:,.0f}".replace(",", ".")

        rows_html += f"""
        <tr>
            <td style="padding: 10px 12px; border-bottom: 1px solid #E2E8F0; font-size: 13.5px; color: #0F172A;">
                <strong>{p_name}</strong><br>
                <span style="font-size: 12px; color: #64748B; font-family: monospace;">SKU: {p_sku}</span>
            </td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #E2E8F0; font-size: 13.5px; text-align: center; color: #475569;">
                {qty}
            </td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #E2E8F0; font-size: 13.5px; text-align: right; color: #475569; font-family: monospace;">
                {price_formatted} đ
            </td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #E2E8F0; font-size: 13.5px; text-align: right; font-weight: 700; color: #0F172A; font-family: monospace;">
                {sub_formatted} đ
            </td>
        </tr>
        """
        rows_plain += f"- {p_name} (SKU: {p_sku}) x {qty} = {sub_formatted} VNĐ\n"

    subtotal_str = f"{order.subtotal_amount:,.0f}".replace(",", ".")
    total_str = f"{order.total_amount:,.0f}".replace(",", ".")
    shipping_fee = order.total_amount - order.subtotal_amount
    shipping_str = "Miễn phí" if shipping_fee <= 0 else f"{shipping_fee:,.0f}".replace(",", ".") + " đ"

    delivery_dest = order.branch.name if order.branch else (order.notes or "Giao tận nơi theo địa chỉ đăng ký")

    subject = f"[ABC Tech Store] Xác nhận đơn hàng #{order_number} thành công"
    preheader = f"Cảm ơn bạn đã mua sắm tại ABC Tech Store. Đơn hàng #{order_number} trị giá {total_str} đ đang được xử lý."

    body_html = f"""
    <p>Kính gửi <strong>{customer_name}</strong>,</p>
    <p>Cảm ơn quý khách đã đặt mua thiết bị công nghệ chính hãng tại <strong>ABC Tech Store</strong>. Đơn hàng của quý khách đã được tiếp nhận và nhân viên chăm sóc khách hàng sẽ liên hệ xác nhận trong thời gian sớm nhất.</p>

    <!-- Order Meta -->
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px 18px; margin: 16px 0; font-size: 13.5px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span>Mã đơn hàng:</span>
            <strong style="color: #2563EB; font-family: monospace; font-size: 14px;">#{order_number}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span>Thời gian đặt hàng:</span>
            <span>{time_str}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
            <span>Phương thức nhận hàng:</span>
            <strong>{delivery_dest}</strong>
        </div>
        <div style="display: flex; justify-content: space-between;">
            <span>Hình thức thanh toán:</span>
            <span style="color: #059669; font-weight: 700;">Tiền mặt khi nhận hàng (COD)</span>
        </div>
    </div>

    <!-- Items Table -->
    <h4 style="font-size: 15px; color: #0F172A; margin: 20px 0 10px;">Chi tiết sản phẩm trong đơn:</h4>
    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="border: 1px solid #E2E8F0; border-radius: 8px; overflow: hidden; margin-bottom: 16px;">
        <thead>
            <tr style="background: #F1F5F9;">
                <th style="padding: 10px 12px; font-size: 12px; text-align: left; color: #475569; font-weight: 700;">SẢN PHẨM</th>
                <th style="padding: 10px 12px; font-size: 12px; text-align: center; color: #475569; font-weight: 700;">SL</th>
                <th style="padding: 10px 12px; font-size: 12px; text-align: right; color: #475569; font-weight: 700;">ĐƠN GIÁ</th>
                <th style="padding: 10px 12px; font-size: 12px; text-align: right; color: #475569; font-weight: 700;">THÀNH TIỀN</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <!-- Totals Summary -->
    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 14px 18px; font-size: 14px; margin-bottom: 18px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px; color: #64748B;">
            <span>Tạm tính tiền hàng:</span>
            <span style="font-family: monospace; color: #0F172A;">{subtotal_str} đ</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px; color: #64748B;">
            <span>Phí vận chuyển:</span>
            <span style="font-family: monospace; color: #10B981; font-weight: 700;">{shipping_str}</span>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px; color: #64748B;">
            <span>Thuế VAT:</span>
            <span style="color: #10B981; font-size: 12px;">Đã bao gồm trong giá</span>
        </div>
        <div style="display: flex; justify-content: space-between; border-top: 1px solid #E2E8F0; padding-top: 10px; margin-top: 6px; font-size: 16px; font-weight: 800; color: #2563EB;">
            <span>TỔNG THANH TOÁN:</span>
            <span style="font-family: monospace;">{total_str} VNĐ</span>
        </div>
    </div>
    """

    # Grounded Policy Snippet (RAG-Enriched Customer Communication)
    policy_html = ""
    policy_plain = ""
    try:
        from apps.workspaces.models import Workspace
        from apps.knowledge.services import get_grounded_policy_snippet
        retail_ws = Workspace.objects.filter(workspace_type="RETAIL").first()
        if retail_ws:
            snippet = get_grounded_policy_snippet(retail_ws, "quy định đổi trả hàng 7 ngày")
            if snippet:
                doc_title = snippet["document_title"]
                text = snippet["content_snippet"]
                policy_html = f"""
    <div style="background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px; font-size: 12.5px; color: #475569;">
        <strong style="color: #0F172A;">Chính sách bảo hành & Đổi trả ({doc_title}):</strong>
        <p style="margin: 4px 0 0; line-height: 1.5;">{text}</p>
    </div>
                """
                policy_plain = f"\nChính sách bảo hành & Đổi trả ({doc_title}):\n{text}\n"
    except Exception:
        pass

    order_url = public_url(f"tai-khoan/don-hang/{order_number}/")
    plain_text = f"""Kính gửi {customer_name},

Cảm ơn quý khách đã đặt mua hàng tại ABC Tech Store!
Mã đơn hàng: #{order_number}
Thời gian đặt: {time_str}
Điểm giao/Chi nhánh: {delivery_dest}
Phương thức thanh toán: Tiền mặt khi nhận hàng (COD)

Danh sách sản phẩm:
{rows_plain}
Tạm tính: {subtotal_str} VNĐ
Phí vận chuyển: {shipping_str}
Tổng thanh toán: {total_str} VNĐ (Đã bao gồm VAT)
{policy_plain}
Xem chi tiết đơn hàng tại: {order_url}
Tổng đài tư vấn: {SUPPORT_HOTLINE}

Trân trọng,
ABC Tech Store
"""

    html_content = _build_html_email_template(
        title="Xác Nhận Đơn Hàng Thành Công",
        preheader=preheader,
        body_html=body_html + policy_html,
        action_url=order_url,
        action_text="Xem Chi Tiết Đơn Hàng",
    )

    return queue_and_deliver_email(
        event_type=CustomerEmailDelivery.EventType.ORDER,
        recipient=email, subject=subject, plain_body=plain_text, html_body=html_content,
        user=user, entity_type="Order", entity_id=order.pk,
        deduplication_key=deduplication_key or f"order:{order.pk}:{normalize_email(email)}",
        defer_delivery=defer_delivery,
    )


def send_service_request_confirmation_email(service_request: Any, recipient_email: Optional[str] = None,
                                            user=None, deduplication_key: str = "",
                                            defer_delivery: bool = False) -> DeliveryResult:
    """
    Sends an SLA & technical acknowledgment email when a customer submits a service request.
    Enriched with RAG policy commitments from enterprise SOP documents.
    """
    email = recipient_email or (service_request.customer.email if service_request.customer else None)
    if not email:
        return DeliveryResult("", CustomerEmailDelivery.Status.FAILED, 0, "INVALID_RECIPIENT")

    customer_name = service_request.customer.name if service_request.customer else "Quý khách"
    req_number = service_request.request_number
    service_name = service_request.service.name if service_request.service else "Dịch vụ kỹ thuật CNTT"
    time_str = timezone.localtime(service_request.created_at).strftime("%H:%M, %d/%m/%Y")
    priority_label = "Khẩn cấp (SLA tiếp ứng < 30 phút)" if service_request.priority == "URGENT" else "Tiêu chuẩn (Phản hồi trong ngày)"

    # Grounded SLA Snippet from Knowledge Base (RAG-Enriched)
    sla_desc = "Kỹ sư chuyên trách sẽ liên hệ trực tiếp qua số điện thoại để trao đổi chi tiết về phương án xử lý (online hoặc khảo sát tại chỗ). Mọi dữ liệu kỹ thuật và thiết bị của quý khách được bảo mật tuyệt đối theo tiêu chuẩn ISO 27001 và điều khoản NDA."
    sla_source = "Quy chuẩn SLA kỹ thuật 2026"
    try:
        from apps.workspaces.models import Workspace
        from apps.knowledge.services import get_grounded_policy_snippet
        svc_ws = Workspace.objects.filter(workspace_type="SERVICE").first()
        if svc_ws:
            snippet = get_grounded_policy_snippet(svc_ws, f"SLA cam kết xử lý sự cố {service_request.priority}")
            if snippet:
                sla_desc = snippet["content_snippet"]
                sla_source = snippet["document_title"]
    except Exception:
        pass

    subject = f"[XYZ IT Services] Tiếp nhận yêu cầu kỹ thuật #{req_number}"
    preheader = f"Yêu cầu dịch vụ '{service_name}' đã được chuyển đến bộ phận kỹ sư trực ban."

    body_html = f"""
    <p>Kính gửi <strong>{customer_name}</strong>,</p>
    <p>Đội ngũ kỹ thuật <strong>XYZ IT Technical Services</strong> đã tiếp nhận thành công phiếu yêu cầu hỗ trợ kỹ thuật của quý khách.</p>
    
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px 20px; margin: 20px 0;">
        <h4 style="margin: 0 0 10px; font-size: 15px; color: #0F172A;">Chi tiết phiếu yêu cầu kỹ thuật:</h4>
        <ul style="margin: 0; padding-left: 20px; font-size: 13.5px; color: #475569; line-height: 1.7;">
            <li><strong>Mã phiếu:</strong> <strong style="color: #0D9488; font-family: monospace;">#{req_number}</strong></li>
            <li><strong>Gói dịch vụ:</strong> {service_name}</li>
            <li><strong>Thời gian ghi nhận:</strong> {time_str}</li>
            <li><strong>Mức độ ưu tiên:</strong> <span style="color: #2563EB; font-weight: 700;">{priority_label}</span></li>
            <li><strong>Trạng thái ban đầu:</strong> <span style="background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 9999px; font-weight: 700; font-size: 12px;">Đang phân bổ kỹ sư</span></li>
        </ul>
    </div>

    <div style="background: #F0FDFA; border: 1px solid #99F6E4; border-radius: 10px; padding: 14px 18px; margin-bottom: 20px;">
        <h5 style="margin: 0 0 6px; color: #0F766E; font-size: 14px;">Cam kết chất lượng SLA (Theo {sla_source}):</h5>
        <p style="margin: 0; font-size: 13px; color: #115E59; line-height: 1.55;">
            {sla_desc}
        </p>
    </div>
    """

    account_url = public_url("tai-khoan/")
    plain_text = f"""Kính gửi {customer_name},

XYZ IT Technical Services đã tiếp nhận thành công yêu cầu hỗ trợ kỹ thuật:
- Mã phiếu: #{req_number}
- Dịch vụ: {service_name}
- Mức độ ưu tiên: {priority_label}
- Thời gian ghi nhận: {time_str}

Cam kết chất lượng SLA ({sla_source}):
{sla_desc}

Kỹ sư trưởng sẽ liên hệ với quý khách trong thời gian sớm nhất.
Theo dõi tiến độ tại: {account_url}
Hotline khẩn cấp 24/7: {SUPPORT_HOTLINE}

Trân trọng,
XYZ IT Technical Services
"""
    html_content = _build_html_email_template(
        title="Tiếp Nhận Yêu Cầu Dịch Vụ IT",
        preheader=preheader,
        body_html=body_html,
        action_url=account_url,
        action_text="Theo Dõi Phiếu Hỗ Trợ",
    )

    return queue_and_deliver_email(
        event_type=CustomerEmailDelivery.EventType.SERVICE_REQUEST,
        recipient=email, subject=subject, plain_body=plain_text, html_body=html_content,
        user=user, entity_type="ServiceRequest", entity_id=service_request.pk,
        deduplication_key=deduplication_key or f"service:{service_request.pk}:{normalize_email(email)}",
        defer_delivery=defer_delivery,
    )


def send_contact_confirmation_email(name: str, email: str, phone: str = "", message_body: str = "",
                                    user=None, deduplication_key: str = "",
                                    defer_delivery: bool = False) -> DeliveryResult:
    """
    Sends an acknowledgment email when a customer submits a general contact or feedback form.
    """
    if not email:
        return DeliveryResult("", CustomerEmailDelivery.Status.FAILED, 0, "INVALID_RECIPIENT")

    display_name = name or "Quý khách"
    now_str = timezone.localtime(timezone.now()).strftime("%H:%M, %d/%m/%Y")
    
    subject = "[Nền tảng Doanh nghiệp AI] Xác nhận tiếp nhận tin nhắn liên hệ"
    preheader = f"Cảm ơn bạn đã liên hệ. Bộ phận hỗ trợ sẽ phản hồi trong 24 giờ làm việc."

    body_html = f"""
    <p>Kính gửi <strong>{display_name}</strong>,</p>
    <p>Cảm ơn quý khách đã gửi tin nhắn kết nối với <strong>Nền tảng Doanh nghiệp AI</strong> (ABC Tech Store & XYZ IT Services).</p>
    
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 16px 20px; margin: 20px 0;">
        <h4 style="margin: 0 0 10px; font-size: 15px; color: #0F172A;">Nội dung tin nhắn đã tiếp nhận:</h4>
        <div style="font-size: 13.5px; color: #475569; line-height: 1.6; font-style: italic; background: #FFFFFF; padding: 12px; border-radius: 6px; border: 1px dashed #CBD5E1; margin-bottom: 10px;">
            "{message_body}"
        </div>
        <div style="font-size: 13px; color: #64748B;">
            Thời gian gửi: <strong>{now_str}</strong> • Số điện thoại liên hệ: <strong>{phone or 'Chưa cung cấp'}</strong>
        </div>
    </div>

    <p style="font-size: 13.5px; color: #334155;">
        Chuyên viên phụ trách sẽ kiểm tra thông tin và chủ động liên hệ lại qua số điện thoại hoặc email của quý khách trong vòng <strong>24 giờ làm việc</strong>.
    </p>
    """

    plain_text = f"""Kính gửi {display_name},

Cảm ơn bạn đã liên hệ với Nền tảng Doanh nghiệp AI!
Chúng tôi đã nhận được nội dung tin nhắn của bạn gửi lúc {now_str}:
"{message_body}"

Chuyên viên chăm sóc khách hàng sẽ liên hệ lại qua số {phone or 'email'} trong vòng 24 giờ làm việc.
Tổng đài tư vấn trực tiếp: {SUPPORT_HOTLINE}

Trân trọng,
Nền tảng Doanh nghiệp AI
"""

    html_content = _build_html_email_template(
        title="Tiếp Nhận Tin Nhắn Liên Hệ",
        preheader=preheader,
        body_html=body_html,
        action_url=public_url(),
        action_text="Về Trang Chủ Nền Tảng",
    )

    return queue_and_deliver_email(
        event_type=CustomerEmailDelivery.EventType.CONTACT,
        recipient=email, subject=subject, plain_body=plain_text, html_body=html_content,
        user=user, deduplication_key=deduplication_key,
        defer_delivery=defer_delivery,
    )
