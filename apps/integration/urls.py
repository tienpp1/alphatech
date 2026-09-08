"""
Data Integration & Ingestion URL Configuration.
"""

from django.urls import path
from apps.integration import views, mock_api_views, ui_views

urlpatterns = [
    # 1. REST API Endpoints
    path("api/v1/integration/data-sources/", views.DataSourceListCreateAPIView.as_view(), name="api_datasource_list_create"),
    path("api/v1/integration/data-sources/<uuid:pk>/", views.DataSourceDetailAPIView.as_view(), name="api_datasource_detail"),
    path("api/v1/integration/import-jobs/", views.ImportJobListCreateAPIView.as_view(), name="api_importjob_list_create"),
    path("api/v1/integration/import-jobs/<uuid:pk>/", views.ImportJobDetailAPIView.as_view(), name="api_importjob_detail"),
    path("api/v1/integration/import-jobs/<uuid:pk>/errors/", views.ImportJobErrorsAPIView.as_view(), name="api_importjob_errors"),
    path("api/v1/integration/import-jobs/<uuid:pk>/raw-records/", views.ImportJobRawRecordsAPIView.as_view(), name="api_importjob_raw_records"),
    path("api/v1/integration/imports/preview/", views.ImportPreviewAPIView.as_view(), name="api_import_preview"),

    # 2. Mock External Partner REST APIs
    path("api/v1/mock-external/retail/orders/", mock_api_views.MockRetailOrdersAPIView.as_view(), name="mock_retail_orders"),
    path("api/v1/mock-external/retail/customers/", mock_api_views.MockRetailCustomersAPIView.as_view(), name="mock_retail_customers"),
    path("api/v1/mock-external/retail/products/", mock_api_views.MockRetailProductsAPIView.as_view(), name="mock_retail_products"),
    path("api/v1/mock-external/service/tickets/", mock_api_views.MockServiceTicketsAPIView.as_view(), name="mock_service_tickets"),
    path("api/v1/mock-external/service/technicians/", mock_api_views.MockServiceTechniciansAPIView.as_view(), name="mock_service_technicians"),

    # 3. Web UI Server-Rendered Routes
    path("integration/", ui_views.integration_dashboard_view, name="integration_dashboard"),
    path("integration/sources/", ui_views.data_sources_list_view, name="integration_sources"),
    path("integration/import/", ui_views.import_wizard_view, name="integration_import"),
    path("integration/jobs/", ui_views.import_jobs_list_view, name="integration_jobs"),
    path("integration/jobs/<uuid:pk>/", ui_views.import_job_detail_view, name="integration_job_detail"),
]
