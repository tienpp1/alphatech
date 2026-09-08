"""
URL configuration for AI Business Operations Platform project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from config.views import (
    health_check_api_view,
    health_check_ui_view,
    root_dashboard_ui_view,
    executive_operational_report_ui_view,
    export_report_csv_view,
    system_telemetry_ui_view,
)
from apps.workspaces.ui_views import switch_workspace_ui_view

urlpatterns = [
    # 1. Public Business Website Layer (Root / & Customer-facing pages)
    path("", include("apps.public_web.urls")),

    # 2. Internal Business Management Portal (/noibo/)
    path("noibo/", root_dashboard_ui_view, name="noibo_dashboard"),
    path("noibo/bao-cao-dieu-hanh/", executive_operational_report_ui_view, name="noibo_executive_report"),
    path("noibo/bao-cao-dieu-hanh/export-csv/", export_report_csv_view, name="noibo_executive_report_csv"),
    path("noibo/telemetry/", system_telemetry_ui_view, name="noibo_telemetry"),
    path("noibo/status/", health_check_ui_view, name="noibo_health_check_ui"),
    path("noibo/thong-bao/", include("apps.notifications.ui_urls")),
    path("noibo/retail/", include("apps.retail.ui_urls")),
    path("noibo/services/", include("apps.service_ops.ui_urls")),
    path("noibo/", include("apps.gis.ui_urls")),
    path("noibo/", include("apps.integration.ui_urls")),
    path("noibo/", include("apps.mapping.ui_urls")),
    path("noibo/", include("apps.knowledge.ui_urls")),
    path("noibo/", include("apps.forecasting.ui_urls")),
    path("noibo/", include("apps.recommendations.ui_urls")),
    path("noibo/", include("apps.approvals.ui_urls")),

    # 3. Dedicated System Status & Health Endpoints
    path("status/", health_check_ui_view, name="health_check_ui"),
    path("health/", health_check_api_view, name="health_check"),
    path("api/health/", health_check_api_view, name="api_health_check"),

    # 4. Core Platform APIs & Web UI Auth
    path("accounts/", include("apps.accounts.ui_urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/workspaces/", include("apps.workspaces.urls")),
    path("workspaces/switch-ui/<uuid:workspace_id>/", switch_workspace_ui_view, name="workspace_switch_ui"),

    # 5. Specialized Internal Web UI Routes (Direct & Backwards-Compatible)
    path("retail/", include("apps.retail.ui_urls")),
    path("services/", include("apps.service_ops.ui_urls")),
    path("notifications/", include("apps.notifications.ui_urls")),
    path("", include("apps.gis.urls")),
    path("", include("apps.integration.urls")),
    path("", include("apps.mapping.urls")),
    path("", include("apps.knowledge.urls")),
    path("", include("apps.forecasting.urls")),
    path("", include("apps.recommendations.urls")),
    path("", include("apps.approvals.urls")),

    # 6. REST APIs (/api/v1/...)
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/retail/", include("apps.retail.urls")),
    path("api/v1/service-ops/", include("apps.service_ops.urls")),

    # 7. Django Admin
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


