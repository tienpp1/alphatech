"""
UI URL Configuration for Internal Notification Center (/noibo/thong-bao/).
"""

from django.urls import path
from apps.notifications.ui_views import (
    notification_center_ui_view,
    notification_redirect_detail_view,
    bulletin_board_ui_view,
    bulletin_create_ui_view,
    team_chat_ui_view,
)

urlpatterns = [
    path("", notification_center_ui_view, name="notification_center"),
    path("<int:pk>/", notification_redirect_detail_view, name="notification_redirect_detail"),
    path("bang-tin/", bulletin_board_ui_view, name="bulletin_board"),
    path("bang-tin/create/", bulletin_create_ui_view, name="bulletin_create"),
    path("bang-tin/tao/", bulletin_create_ui_view, name="bulletin_create_alt"),
    path("trao-doi/", team_chat_ui_view, name="team_chat"),
]
