import os
import django
import sentry_sdk

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

try:
    print("Triggering Sentry zero division error...")
    1 / 0
except Exception as e:
    sentry_sdk.capture_exception(e)
    sentry_sdk.flush(timeout=5.0)
    print("SUCCESS: Error sent to Sentry!")
