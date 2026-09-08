"""
API URL Configuration for Internal Notifications.
"""

from django.urls import path
from apps.notifications.views import (
    notification_unread_count_api,
    notification_latest_api,
    notification_mark_read_api,
    notification_mark_all_read_api,
)

urlpatterns = [
    path("unread-count/", notification_unread_count_api, name="api_notification_unread_count"),
    path("latest/", notification_latest_api, name="api_notification_latest"),
    path("<int:pk>/read/", notification_mark_read_api, name="api_notification_mark_read"),
    path("read-all/", notification_mark_all_read_api, name="api_notification_mark_all_read"),
]
