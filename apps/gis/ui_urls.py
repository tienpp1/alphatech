from django.urls import path

from apps.gis.ui_views import retail_gis_view, service_gis_view

urlpatterns = [
    path("retail/gis/", retail_gis_view, name="noibo_retail_gis"),
    path("services/gis/", service_gis_view, name="noibo_service_gis"),
]
