"""
URL patterns for Workspace endpoints.
"""

from django.urls import path
from apps.workspaces.views import (
    WorkspaceListAPIView,
    WorkspaceSwitchAPIView,
    CurrentWorkspaceAPIView,
)

urlpatterns = [
    path("", WorkspaceListAPIView.as_view(), name="workspace_list"),
    path("switch/", WorkspaceSwitchAPIView.as_view(), name="workspace_switch"),
    path("current/", CurrentWorkspaceAPIView.as_view(), name="workspace_current"),
]
