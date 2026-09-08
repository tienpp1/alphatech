from django.urls import path

from apps.forecasting.ui_views import forecasting_dashboard_view

urlpatterns = [path("forecasting/", forecasting_dashboard_view, name="noibo_forecasting_dashboard")]
