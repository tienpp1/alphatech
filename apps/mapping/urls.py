"""
Data Mapping & Standard Data Model URL Configuration.
"""

from django.urls import path
from apps.mapping.views import (
    MappingProfileListCreateAPIView,
    MappingProfileDetailAPIView,
    MappingProfileFieldsAPIView,
    MappingProfileRulesAPIView,
    MappingRuleDetailAPIView,
    MappingPreviewAPIView,
    MappingApplyAPIView,
    MappingAISuggestAPIView,
)
from apps.mapping.ui_views import (
    mapping_dashboard_view,
    mapping_profile_create_view,
    mapping_studio_view,
)

urlpatterns = [
    # Web UI Routes
    path("mapping/", mapping_dashboard_view, name="mapping_dashboard"),
    path("mapping/profiles/new/", mapping_profile_create_view, name="mapping_profile_create"),
    path("mapping/profiles/<uuid:pk>/", mapping_studio_view, name="mapping_studio"),

    # REST API Routes
    path("api/v1/mapping/profiles/", MappingProfileListCreateAPIView.as_view(), name="api-mapping-profiles"),
    path("api/v1/mapping/profiles/<uuid:pk>/", MappingProfileDetailAPIView.as_view(), name="api-mapping-profile-detail"),
    path("api/v1/mapping/profiles/<uuid:pk>/fields/", MappingProfileFieldsAPIView.as_view(), name="api-mapping-profile-fields"),
    path("api/v1/mapping/profiles/<uuid:pk>/rules/", MappingProfileRulesAPIView.as_view(), name="api-mapping-profile-rules"),
    path("api/v1/mapping/profiles/<uuid:pk>/rules/<int:rule_id>/", MappingRuleDetailAPIView.as_view(), name="api-mapping-rule-detail"),
    path("api/v1/mapping/preview/", MappingPreviewAPIView.as_view(), name="api-mapping-preview"),
    path("api/v1/mapping/apply/", MappingApplyAPIView.as_view(), name="api-mapping-apply"),
    path("api/v1/mapping/ai-suggest/", MappingAISuggestAPIView.as_view(), name="api-mapping-ai-suggest"),
]
