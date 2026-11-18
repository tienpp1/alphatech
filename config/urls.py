"""
URL configuration for AI Business Operations Platform project.
"""

from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from config.views import (
    health_check_api_view,
    root_dashboard_ui_view,
    executive_operational_report_ui_view,
    export_report_csv_view,
    ai_command_center_ui_view,
)
from apps.workspaces.ui_views import switch_workspace_ui_view
from apps.notifications.ui_views import bulletin_board_ui_view, bulletin_create_ui_view, team_chat_ui_view
from apps.notifications.bulletin_edit_views import bulletin_edit_ui
from apps.notifications.chat_member_views import chat_employee_create_view, chat_employee_add_view
from apps.forecasting.demo_views import DEMO_PAGE_NAME, DEMO_RUN_NAME, ai_demo_page, ai_demo_run
from apps.public_web.product_media import product_image

urlpatterns = [
    path("media/<path:image_path>", product_image, name="public_product_image"),
    # 1. Public Business Website Layer (Root / & Customer-facing pages)
    path("", include("apps.public_web.urls")),

    # 2. Internal Business Management Portal (/noibo/)
    path("noibo/", root_dashboard_ui_view, name="noibo_dashboard"),
    path("noibo/ai-command-center/", ai_command_center_ui_view, name="noibo_ai_command_center"),
    path("noibo/bao-cao-dieu-hanh/", executive_operational_report_ui_view, name="noibo_executive_report"),
    path("noibo/bao-cao-dieu-hanh/export-csv/", export_report_csv_view, name="noibo_executive_report_csv"),
    path("noibo/thong-bao/", include("apps.notifications.ui_urls")),
    path("noibo/bang-tin/", bulletin_board_ui_view, name="noibo_bulletin_board"),
    path("noibo/bang-tin/<int:pk>/sua/", bulletin_edit_ui, name="noibo_bulletin_edit"),
    path("noibo/bang-tin/create/", bulletin_create_ui_view, name="noibo_bulletin_create"),
    path("noibo/bang-tin/tao/", bulletin_create_ui_view, name="noibo_bulletin_create_alt"),
    path("noibo/trao-doi/", team_chat_ui_view, name="noibo_team_chat"),
    path("noibo/trao-doi/nhan-vien/tao/", chat_employee_create_view, name="noibo_chat_employee_create"),
    path("noibo/trao-doi/thanh-vien/them/", chat_employee_add_view, name="noibo_chat_employee_add"),
    path("noibo/retail/", include("apps.retail.ui_urls")),
    path("noibo/services/", include("apps.service_ops.ui_urls")),
    path("noibo/", include("apps.gis.ui_urls")),
    path("noibo/", include("apps.integration.ui_urls")),
    path("noibo/", include("apps.mapping.ui_urls")),
    path("noibo/", include("apps.knowledge.ui_urls")),
    path("noibo/", include("apps.forecasting.ui_urls")),
    path("noibo/mo-phong-ai/", ai_demo_page, name=DEMO_PAGE_NAME),
    path("noibo/mo-phong-ai/run/", ai_demo_run, name=DEMO_RUN_NAME),
    path("noibo/", include("apps.recommendations.ui_urls")),
    path("noibo/", include("apps.approvals.ui_urls")),

    # 3. Dedicated System Status & Health Endpoints
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

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

