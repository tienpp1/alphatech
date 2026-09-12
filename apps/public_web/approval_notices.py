"""Customer approval acknowledgments reuse the persistent notification store.

Model save signals cover internal UI/API services and Django admin edits.
Bulk SQL/update() intentionally does not emit customer events.
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_protect
from apps.notifications.models import Notification, NotificationEventType
from apps.retail.models import Order
from apps.service_ops.models import ServiceRequest

EVENTS = [NotificationEventType.CUSTOMER_ORDER_APPROVED, NotificationEventType.CUSTOMER_SERVICE_APPROVED]


@receiver(pre_save, sender=Order)
@receiver(pre_save, sender=ServiceRequest)
def remember_status(sender, instance, raw=False, update_fields=None, using="default", **kwargs):
    instance._customer_previous_status = None
    if raw or not instance.pk or (update_fields is not None and "status" not in update_fields):
        return
    instance._customer_previous_status = sender.objects.using(using).filter(pk=instance.pk).values_list("status", flat=True).first()


@receiver(post_save, sender=Order)
@receiver(post_save, sender=ServiceRequest)
def approval_notice(sender, instance, created, raw=False, using="default", **kwargs):
    previous = getattr(instance, "_customer_previous_status", None)
    if created or raw or not previous or previous == instance.status:
        return
    is_order = sender is Order
    accepted = previous == "PENDING" and instance.status == "CONFIRMED" if is_order else previous == "OPEN" and instance.status in ("ASSIGNED", "IN_PROGRESS")
    if not accepted:
        return
    customer = instance.customer
    if customer.workspace_id != instance.workspace_id:
        return
    recipient_id = instance.created_by_id if is_order else customer.user_id
    if not recipient_id:
        return
    number = instance.order_number if is_order else instance.request_number
    title = "Đơn hàng của bạn đã được duyệt!" if is_order else "Yêu cầu dịch vụ đã được tiếp nhận!"
    message = (
        f"Cảm ơn bạn đã mua sắm cùng chúng tôi! Đơn hàng {number} đã được xác nhận. Chúng tôi sẽ cập nhật tiến độ xử lý trong tài khoản của bạn."
        if is_order else
        f"Cảm ơn bạn đã tin tưởng sử dụng dịch vụ của chúng tôi! Yêu cầu {number} đã được tiếp nhận. Đội ngũ kỹ thuật sẽ đồng hành và hỗ trợ bạn."
    )
    Notification.objects.using(using).get_or_create(
        workspace_id=instance.workspace_id, recipient_id=recipient_id,
        event_type=EVENTS[0] if is_order else EVENTS[1],
        entity_type="Order" if is_order else "ServiceRequest", entity_id=str(instance.pk),
        defaults={"title": title, "message": message},
    )


def own_notices(request):
    return Notification.objects.filter(recipient=request.user, event_type__in=EVENTS)


def still_owned(notice, user):
    if notice.entity_type == "Order":
        return Order.objects.filter(pk=notice.entity_id, workspace_id=notice.workspace_id, created_by=user, status__in=["CONFIRMED", "COMPLETED"]).exists()
    if notice.entity_type == "ServiceRequest":
        return ServiceRequest.objects.filter(pk=notice.entity_id, workspace_id=notice.workspace_id, customer__user=user, customer__workspace_id=notice.workspace_id, status__in=["ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]).exists()
    return False


@require_GET
def pending_approval_notices(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Vui lòng đăng nhập."}, status=401)
    notices = []
    for item in own_notices(request).filter(is_read=False).order_by("created_at").iterator(chunk_size=50):
        if still_owned(item, request.user):
            notices.append({"id": item.pk, "title": item.title, "message": item.message})
            if len(notices) == 10:
                break
    response = JsonResponse({"notifications": notices})
    response["Cache-Control"] = "no-store"
    return response


@require_POST
@csrf_protect
def acknowledge_approval_notice(request, notice_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Vui lòng đăng nhập."}, status=401)
    item = get_object_or_404(own_notices(request), pk=notice_id)
    own_notices(request).filter(pk=item.pk, is_read=False).update(is_read=True, read_at=timezone.now())
    return JsonResponse({"ok": True})
