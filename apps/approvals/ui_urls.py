from django.urls import path

from apps.approvals.ui_views import approvals_dashboard_view

urlpatterns = [path("approvals/", approvals_dashboard_view, name="noibo_approvals_dashboard")]
