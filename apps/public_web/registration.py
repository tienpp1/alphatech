"""Database-serialized registration codes, independent of browser rate limits."""
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import make_password, check_password
from django.core import signing
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from .models import RegistrationCode, SocialIdentity
from .email_service import queue_and_deliver_email, CustomerEmailDelivery, public_url

REGISTRATION_LINK_SALT = "public_web.registration_code_link.v1"


@transaction.atomic
def issue_registration_code(user):
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.is_active or SocialIdentity.objects.filter(user=user).exists():
        return "unavailable"
    now = timezone.now()
    challenge = RegistrationCode.objects.filter(user=user).first()
    if challenge:
        if (now - challenge.sent_at).total_seconds() < 60:
            return "cooldown"
        if now - challenge.window_started_at >= timedelta(hours=1):
            challenge.sends = 0
            challenge.failures = 0
            challenge.window_started_at = now
        if challenge.sends >= 5 or challenge.failures >= 5:
            return "limited"
    else:
        challenge = RegistrationCode(user=user, window_started_at=now, sends=0)
    code = f"{secrets.randbelow(1000000):06d}"
    challenge.code_hash = make_password(code)
    challenge.expires_at = now + timedelta(minutes=10)
    challenge.sent_at = now
    challenge.consumed_at = None
    challenge.sends += 1
    challenge.save()
    confirmation_token = signing.dumps(
        {"user_id": user.pk, "challenge_id": challenge.pk, "sent_at": int(now.timestamp())},
        salt=REGISTRATION_LINK_SALT, compress=True,
    )
    confirmation_url = public_url(f"xac-minh-dang-ky/{confirmation_token}/")
    queue_and_deliver_email(
        event_type=CustomerEmailDelivery.EventType.EMAIL_VERIFICATION,
        user=user, recipient=user.email, entity_type="User", entity_id=user.pk,
        subject="[AlphaTech] Mã xác minh đăng ký tài khoản",
        plain_body=(f"Xin chào,\n\nMã đăng ký AlphaTech của bạn: {code}\n\n"
                    "Nhập mã trên trang đăng ký trong vòng 10 phút để hoàn tất. "
                    "Mã chỉ dùng một lần. Không chia sẻ mã này với người khác.\n"
                    f"Bạn cũng có thể xác minh trực tiếp trên thiết bị bất kỳ:\n{confirmation_url}\n"
                    "Nếu bạn không yêu cầu đăng ký, hãy bỏ qua thư này.\n\nĐội ngũ AlphaTech"),
        deduplication_key=f"registration-code:{user.pk}:{now.isoformat()}",
        defer_delivery=True,
    )
    return "sent"


def registration_link_user(token):
    """Resolve a one-use link for the latest challenge without changing state."""
    try:
        payload = signing.loads(token, salt=REGISTRATION_LINK_SALT, max_age=600)
    except (signing.BadSignature, signing.SignatureExpired, TypeError, AttributeError):
        return None
    challenge = RegistrationCode.objects.select_related("user").filter(
        pk=payload.get("challenge_id"), user_id=payload.get("user_id"), consumed_at__isnull=True,
    ).first()
    if not challenge or int(challenge.sent_at.timestamp()) != int(payload.get("sent_at", -1)):
        return None
    return challenge.user


def consume_registration_code(user, code):
    """Caller holds the User row lock and activates in the same transaction."""
    challenge = RegistrationCode.objects.filter(user=user).first()
    now = timezone.now()
    if not challenge or challenge.consumed_at or challenge.expires_at <= now:
        return False
    if challenge.failures >= 5:
        return False
    if len(code) != 6 or not code.isascii() or not code.isdigit() or not check_password(code, challenge.code_hash):
        challenge.failures += 1
        challenge.save(update_fields=("failures",))
        return False
    challenge.consumed_at = now
    challenge.code_hash = ""
    challenge.save(update_fields=("consumed_at", "code_hash"))
    return True


@transaction.atomic
def consume_registration_link(user):
    """Consume the latest signed email link under the User lock."""
    user = User.objects.select_for_update().get(pk=user.pk)
    challenge = RegistrationCode.objects.select_for_update().filter(user=user).first()
    if not challenge or challenge.consumed_at or challenge.expires_at <= timezone.now():
        return False
    challenge.consumed_at = timezone.now()
    challenge.code_hash = ""
    challenge.save(update_fields=("consumed_at", "code_hash"))
    return True
