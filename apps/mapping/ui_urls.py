from django.urls import path

from apps.mapping.ui_views import mapping_dashboard_view, mapping_profile_create_view, mapping_studio_view

urlpatterns = [
    path("mapping/", mapping_dashboard_view, name="noibo_mapping_dashboard"),
    path("mapping/profiles/new/", mapping_profile_create_view, name="noibo_mapping_profile_create"),
    path("mapping/profiles/<uuid:pk>/", mapping_studio_view, name="noibo_mapping_studio"),
]
