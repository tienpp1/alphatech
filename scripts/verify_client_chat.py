import os
import sys
import json
import django

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from apps.accounts.models import User

client = Client(SERVER_NAME="127.0.0.1")
user = User.objects.filter(is_superuser=True).first()
client.force_login(user)

# Test Core Handbook Question 1
resp = client.post(
    "/api/v1/ai/chat/",
    data=json.dumps({"message": "Nội quy thời giờ làm việc, quy định đi muộn và số ngày phép năm của nhân viên?"}),
    content_type="application/json"
)
print("HTTP STATUS:", resp.status_code)
body = resp.json()
data = body.get("data", {})
print("INTENT:", data.get("intent"))
print("\n--- GROUNDED ANSWER ---")
print(data.get("answer"))
print("\n--- CITATIONS ---")
for c in data.get("sources", []):
    heading = c.get("heading") or "N/A"
    sim = c.get("similarity", 0.0)
    print(f"- {c['document_title']} | Section: {heading} | Similarity: {sim:.3f}")

# Test Core Handbook Question 2
print("\n" + "=" * 80)
resp2 = client.post(
    "/api/v1/ai/chat/",
    data=json.dumps({"message": "Quy chế thanh toán công tác phí, hạn mức tiền ăn và thời hạn nộp hóa đơn hoàn ứng?"}),
    content_type="application/json"
)
body2 = resp2.json()
data2 = body2.get("data", {})
print("INTENT 2:", data2.get("intent"))
print("\n--- GROUNDED ANSWER 2 ---")
print(data2.get("answer"))
print("\n--- CITATIONS 2 ---")
for c in data2.get("sources", []):
    heading = c.get("heading") or "N/A"
    sim = c.get("similarity", 0.0)
    print(f"- {c['document_title']} | Section: {heading} | Similarity: {sim:.3f}")
