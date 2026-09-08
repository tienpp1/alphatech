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
                call_command("migrate", interactive=False, verbosity=0)
            except Exception as mig_err:
                logger.warning(f"Production migrate warning: {mig_err}")

            # Check if products exist; if not, run seed_demo
            try:
                from apps.retail.models import Product
                if Product.objects.count() == 0:
                    logger.info("Seeding initial demo dataset (ABC Tech & XYZ IT)...")
                    call_command("seed_demo", verbosity=0)
            except Exception as seed_err:
                logger.warning(f"Production seed_demo warning: {seed_err}")

            # Ensure student admin accounts exist
            try:
                call_command("seed_student_admin", verbosity=0)
            except Exception as stu_err:
                logger.warning(f"Production seed_student_admin warning: {stu_err}")

    except Exception as exc:
        import logging
        logging.getLogger("config.wsgi").error(f"Production bootstrap exception: {exc}")

_bootstrap_production()

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
