from django.urls import path

from apps.integration import ui_views

urlpatterns = [
    path("integration/", ui_views.integration_dashboard_view, name="noibo_integration_dashboard"),
    path("integration/sources/", ui_views.data_sources_list_view, name="noibo_integration_sources"),
    path("integration/import/", ui_views.import_wizard_view, name="noibo_integration_import"),
    path("integration/jobs/", ui_views.import_jobs_list_view, name="noibo_integration_jobs"),
    path("integration/jobs/<uuid:pk>/", ui_views.import_job_detail_view, name="noibo_integration_job_detail"),
]
