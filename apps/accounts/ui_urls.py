"""
URL configuration for Web UI Authentication (Login & Logout).
"""

from django.urls import path
from apps.accounts.ui_views import login_ui_view, logout_ui_view

urlpatterns = [
    path("login/", login_ui_view, name="login"),
    path("logout/", logout_ui_view, name="logout"),
]
