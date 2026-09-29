"""
API URL Configuration for Internal Notifications.
"""

from django.urls import path
from apps.notifications.bulletin_edit_views import bulletin_update_api
from apps.notifications.views import (
    notification_unread_count_api,
    notification_latest_api,
    notification_mark_read_api,
    notification_mark_all_read_api,
    bulletin_list_api,
    bulletin_create_api,
    team_chat_messages_api,
    team_chat_send_api,
)

urlpatterns = [
    path("bulletins/<int:pk>/update/", bulletin_update_api, name="api_bulletin_update"),
    path("unread-count/", notification_unread_count_api, name="api_notification_unread_count"),
    path("latest/", notification_latest_api, name="api_notification_latest"),
    path("<int:pk>/read/", notification_mark_read_api, name="api_notification_mark_read"),
    path("read-all/", notification_mark_all_read_api, name="api_notification_mark_all_read"),
    path("bulletins/", bulletin_list_api, name="api_bulletin_list"),
    path("bulletins/create/", bulletin_create_api, name="api_bulletin_create"),
    path("chat/messages/", team_chat_messages_api, name="api_team_chat_messages"),
    path("chat/send/", team_chat_send_api, name="api_team_chat_send"),
]
