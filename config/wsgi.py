"""
WSGI config for AI Business Operations Platform project.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

def _bootstrap_production():
    """
    Self-healing production bootstrap:
    Ensures static files are collected for WhiteNoise and database
    has initial migrations and seeds applied if running on Render cloud.
    """
    try:
        from django.conf import settings
        from django.core.management import call_command
        import logging

        logger = logging.getLogger("config.wsgi")

        # 1. Collect static files if not already collected
        static_root = Path(settings.STATIC_ROOT)
        css_file = static_root / "css" / "public_pages.css"
        if not css_file.exists():
            logger.info("Collecting static files for WhiteNoise...")
            call_command("collectstatic", interactive=False, verbosity=0)

        # 2. Database migrations & seed if on Render or production environment
        is_cloud_prod = bool(
            os.getenv("RENDER")
            or os.getenv("RENDER_EXTERNAL_HOSTNAME")
            or os.getenv("DATABASE_URL")
            or not settings.DEBUG
        )
        if is_cloud_prod:
            try:
                print("==> [WSGI BOOTSTRAP] Running database migrations...", flush=True)
                call_command("migrate", interactive=False)
            except Exception as mig_err:
                print(f"==> [WSGI BOOTSTRAP] Migrate warning: {mig_err}", flush=True)

            # Check if products exist; if less than 10, run seed_demo
            try:
                from apps.retail.models import Product
                prod_count = Product.objects.count()
                print(f"==> [WSGI BOOTSTRAP] Current Product count in database: {prod_count}", flush=True)
                if prod_count < 10:
                    print("==> [WSGI BOOTSTRAP] Seeding demo dataset (ABC Tech & XYZ IT)...", flush=True)
                    call_command("seed_demo")
                    print("==> [WSGI BOOTSTRAP] Demo dataset successfully seeded!", flush=True)
            except Exception as seed_err:
                import traceback
                print(f"==> [WSGI BOOTSTRAP ERROR] seed_demo failed: {seed_err}", flush=True)
                traceback.print_exc()

            # Ensure student admin accounts exist
            try:
                call_command("seed_student_admin")
            except Exception as stu_err:
                print(f"==> [WSGI BOOTSTRAP] seed_student_admin note: {stu_err}", flush=True)

    except Exception as exc:
        import traceback
        print(f"==> [WSGI BOOTSTRAP CRITICAL] Exception: {exc}", flush=True)
        traceback.print_exc()

_bootstrap_production()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
