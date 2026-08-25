"""
Core System Views for Health Check and Platform Status (Phase 0).
"""

from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.utils import timezone
import sys
import django
import os


def get_health_status():
    """Evaluate system dependencies and connectivity status."""
    db_status = "unknown"
    db_error = None
    postgis_status = "not_checked"

    # Test Database Connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            db_status = "connected"

            # Check PostGIS extension
            try:
                cursor.execute("SELECT PostGIS_Version();")
                postgis_version = cursor.fetchone()
                if postgis_version:
                    postgis_status = f"available ({postgis_version[0]})"
            except Exception:
                postgis_status = "extension_not_installed_or_disabled"
    except Exception as e:
        db_status = "disconnected"
        db_error = str(e)

    status_data = {
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": timezone.now().isoformat(),
        "platform": "Intelligent Business Operations Platform",
        "version": "1.0.0-phase0",
        "environment": {
            "python_version": sys.version.split()[0],
            "django_version": django.get_version(),
            "debug_mode": os.getenv("DEBUG", "True").lower() in ("true", "1"),
        },
        "database": {
            "engine": connection.settings_dict.get("ENGINE", ""),
            "name": connection.settings_dict.get("NAME", ""),
            "host": connection.settings_dict.get("HOST", ""),
            "port": connection.settings_dict.get("PORT", ""),
            "status": db_status,
            "error": db_error,
            "postgis": postgis_status,
        },
        "phase": {
            "current": "Phase 0 - Bootstrap & Environment Inspection",
            "next": "Phase 1 - Architecture & ERD Specification",
        },
    }
    return status_data


def health_check_api_view(request):
    """API endpoint returning health status JSON."""
    status_data = get_health_status()
    http_status = 200 if status_data["status"] == "healthy" else 503
    return JsonResponse(status_data, status=http_status)


def health_check_ui_view(request):
    """HTML status dashboard page for Phase 0."""
    status_data = get_health_status()
    return render(request, "health.html", {"health": status_data})
