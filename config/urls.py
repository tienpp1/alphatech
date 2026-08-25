"""
URL configuration for AI Business Operations Platform project.
"""

from django.contrib import admin
from django.urls import path
from config.views import health_check_api_view, health_check_ui_view

urlpatterns = [
    path("", health_check_ui_view, name="health_check_ui"),
    path("health/", health_check_api_view, name="health_check"),
    path("api/health/", health_check_api_view, name="api_health_check"),
    path("admin/", admin.site.urls),
]
