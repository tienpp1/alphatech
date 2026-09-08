"""
URL patterns for Authentication & Identity endpoints.
"""

from django.urls import path
from apps.accounts.views import LoginAPIView, LogoutAPIView, MeAPIView

urlpatterns = [
    path("login/", LoginAPIView.as_view(), name="auth_login"),
    path("logout/", LogoutAPIView.as_view(), name="auth_logout"),
    path("me/", MeAPIView.as_view(), name="auth_me"),
]
