from django.urls import path

from apps.recommendations.ui_views import recommendations_dashboard_view

urlpatterns = [path("recommendations/", recommendations_dashboard_view, name="noibo_recommendations_dashboard")]
