"""
URL configuration for Business Recommendations (Phase 10).
"""

from django.urls import path
from apps.recommendations import views, ui_views

app_name = "recommendations"

urlpatterns = [
    # Web UI Dashboard
    path("recommendations/", ui_views.recommendations_dashboard_view, name="ui_dashboard"),

    # REST APIs
    path("api/v1/recommendations/", views.RecommendationListAPIView.as_view(), name="api_list"),
    path("api/v1/recommendations/evaluate/", views.RecommendationEvaluateAPIView.as_view(), name="api_evaluate"),
    path("api/v1/recommendations/<int:pk>/", views.RecommendationDetailAPIView.as_view(), name="api_detail"),
    path("api/v1/recommendations/<int:pk>/accept/", views.RecommendationAcceptAPIView.as_view(), name="api_accept"),
    path("api/v1/recommendations/<int:pk>/reject/", views.RecommendationRejectAPIView.as_view(), name="api_reject"),
]
