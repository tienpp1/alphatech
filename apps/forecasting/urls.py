"""
URL Configuration for Predictive Analytics & Forecasting.
"""

from django.urls import path
from apps.forecasting.views import (
    ForecastModelConfigListCreateAPIView,
    ForecastModelConfigDetailAPIView,
    ForecastRunListAPIView,
    ForecastRunDetailAPIView,
    TrainForecastAPIView,
    ForecastResultListAPIView,
    ForecastChartDataAPIView,
    ForecastRunCancelAPIView,
)
from apps.forecasting.ui_views import forecasting_dashboard_view

urlpatterns = [
    # Web UI Dashboard
    path("forecasting/", forecasting_dashboard_view, name="forecasting_dashboard"),

    # REST APIs
    path("api/v1/forecasting/models/", ForecastModelConfigListCreateAPIView.as_view(), name="forecasting_model_list_create"),
    path("api/v1/forecasting/models/<int:pk>/", ForecastModelConfigDetailAPIView.as_view(), name="forecasting_model_detail"),
    path("api/v1/forecasting/runs/", ForecastRunListAPIView.as_view(), name="forecasting_run_list"),
    path("api/v1/forecasting/runs/<int:pk>/", ForecastRunDetailAPIView.as_view(), name="forecasting_run_detail"),
    path("api/v1/forecasting/runs/<int:pk>/cancel/", ForecastRunCancelAPIView.as_view(), name="forecasting_run_cancel"),
    path("api/v1/forecasting/train/", TrainForecastAPIView.as_view(), name="forecasting_train"),
    path("api/v1/forecasting/results/", ForecastResultListAPIView.as_view(), name="forecasting_result_list"),
    path("api/v1/forecasting/chart-data/", ForecastChartDataAPIView.as_view(), name="forecasting_chart_data"),
]
