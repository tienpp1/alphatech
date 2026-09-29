import os
import django
from django.core.mail import send_mail
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

try:
    print("Triggering real email via SMTP...")
    send_mail(
        subject="[AlphaTech] Nghiem thu Email That - Cong 91",
        message=f"He thong da gui thu thanh cong tu moi truong Test.\nThoi gian: {timezone.now()}",
        from_email="minhtien147896325@gmail.com",
        recipient_list=["minhtien147896325@gmail.com"],
        fail_silently=False,
    )
    print("SUCCESS: Email sent!")
except Exception as e:
    print(f"FAILED: {e}")
