"""
UI URL Configuration for Internal Notification Center (/noibo/thong-bao/).
"""

from django.urls import path
from apps.notifications.ui_views import (
    notification_center_ui_view,
    notification_redirect_detail_view,
)

urlpatterns = [
    path("", notification_center_ui_view, name="notification_center"),
    path("<int:pk>/", notification_redirect_detail_view, name="notification_redirect_detail"),
]
