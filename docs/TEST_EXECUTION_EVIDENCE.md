# Bằng chứng full suite thực chạy — 23/09/2026

> **Cập nhật 25/09:** Đã có full-suite mới 1.095 tests OK, 3037.883s, 0 failure/error/skipped, source fingerprint không đổi. Xem ACCEPTANCE_BATCH_2026_09_25.md và output/acceptance_verification/20260925T012747Z/. Bản vá collaboration sau đó có focused tests riêng. Phần dưới giữ nguyên các thất bại lịch sử ngày 23/09, không phải kết quả hiện tại và không bị xóa khi có lần chạy mới thành công.

Nguồn duy nhất: `output/acceptance_verification/20260923T072453Z/django.log`.
SHA256: `0b7e2ae84059dfc974794d4b649fead4126fd8c5c56372141d9123bde837c400`.

Runner báo **1067 tests**, **2032.52s**, **FAILED**; 8 failures, 8 errors, 0 skipped.
Không cộng các rerun vào tổng này. Không suy ra số pass bằng cách trừ error entries.
Trích xuất được 1066 ID duy nhất từ dòng verbose; không coi danh sách này là toàn bộ 1067 ca do định dạng/log xen kẽ.
Mỗi incident dưới đây được giữ nguyên; lỗi cleanup lặp không bị giấu.

| Loại | Test ID |
|---|---|
| ERROR | `tests.test_academic_report_command.AcademicReportCommandTests.test_all_collections_workspace_scoped` |
| ERROR | `tests.test_academic_report_command.AcademicReportCommandTests.test_all_collections_workspace_scoped` |
| ERROR | `tests.test_academic_report_command.AcademicReportCommandTests.test_existing_output_preserved` |
| ERROR | `tests.test_academic_report_command.AcademicReportCommandTests.test_existing_output_preserved` |
| ERROR | `tests.test_academic_report_command.AcademicReportCommandTests.test_requires_explicit_workspace` |
| ERROR | `tests.test_academic_report_command.AcademicReportCommandTests.test_unavailable_run_id_does_not_export` |
| ERROR | `tests.test_academic_report_command.AcademicReportCommandTests.test_unknown_workspace_denied_without_forecast_query` |
| ERROR | `tests.test_rag_human_review.HumanReviewTests.test_command_exports_and_preserves_existing_files` |
| FAIL | `tests.test_integration_jobs.ImportJobExecutionTests.test_import_job_rest_apis` |
| FAIL | `tests.test_integration_preview.ImportPreviewApiTests.test_preview_csv_upload_api` |
| FAIL | `tests.test_integration_preview.ImportPreviewApiTests.test_preview_mock_api_source` |
| FAIL | `tests.test_internal_notifications.InternalNotificationsTestCase.test_public_customer_registration_creates_new_customer_notification` |
| FAIL | `tests.test_mapping_ai.MappingAITestCase.test_ai_suggest_api_endpoint` |
| FAIL | `tests.test_mapping_preview.MappingPreviewTestCase.test_preview_api_endpoint` |
| FAIL | `tests.test_phase10_demonstration_scenarios.Phase10DemonstrationScenarioTests.test_scenario_a_retail_flagged_branch` |
| FAIL | `tests.test_retail_products.RetailProductTests.test_product_safe_delete_prevented_when_order_items_exist` |

## Skipped, phần chưa chạy và rerun

Lần chạy này báo 0 bài kiểm thử bị bỏ qua (0 skipped tests); không phải lời bảo đảm cho môi trường khác.
Node/browser, OAuth thật, inbox, CI runner, Sentry và restore không nằm trong lệnh Django này.
Sau sửa đã có rerun có phạm vi tại ACCEPTANCE_REAUDIT_2026_09_23.md và ACCEPTANCE_BATCH_BULLETIN_GROUNDING_2026_09_24.md; chưa full-suite rerun.
Test kiểm tra chuỗi trong tài liệu chỉ kiểm tra tài liệu, không chứng minh nghiệp vụ hoặc production.

## Danh mục file hiện tại (inventory, không phải pass)

Danh mục file phục vụ đối chiếu source; không quy đổi số file thành số test hoặc coverage.

- `test_academic_report_command.py`
- `test_academic_reporting.py`
- `test_academic_scope_contract.py`
- `test_academic_test_manifest_audit.py`
- `test_acceptance_log_summary.py`
- `test_adversarial_case_contract.py`
- `test_adversarial_rag_execution.py`
- `test_ai_advanced_context_benchmark.py`
- `test_ai_business_intent_benchmark.py`
- `test_ai_intent_router.py`
- `test_approval_concurrency_evidence.py`
- `test_approval_state_integrity.py`
- `test_approvals.py`
- `test_audit_database_evidence.py`
- `test_audit_trail_evidence.py`
- `test_auth.py`
- `test_authorization_convergence.py`
- `test_branch_warning_evidence_route.py`
- `test_brevo_email_backend.py`
- `test_bulletin_and_team_chat.py`
- `test_bulletin_update.py`
- `test_checkout_concurrency.py`
- `test_customer_account_identity.py`
- `test_customer_approval_notices.py`
- `test_customer_email_outbox_and_oauth_security.py`
- `test_customer_email_policy_boundary.py`
- `test_demo_document_routes.py`
- `test_deployment_boundaries.py`
- `test_embedding_provenance.py`
- `test_embedding_space_isolation.py`
- `test_enterprise_qna.py`
- `test_executive_reporting_and_telemetry.py`
- `test_forecasting_api.py`
- `test_forecasting_dataset.py`
- `test_forecasting_features.py`
- `test_forecasting_prediction.py`
- `test_forecasting_queue.py`
- `test_forecasting_security_rbac.py`
- `test_forecasting_training.py`
- `test_fulfillment_inventory_consistency.py`
- `test_full_demo_seed.py`
- `test_generation_provenance.py`
- `test_gis_reference_distances.py`
- `test_gis_retail.py`
- `test_gis_security.py`
- `test_gis_service.py`
- `test_gis_spatial.py`
- `test_google_oauth_and_email_notifications.py`
- `test_health.py`
- `test_home_delivery_fulfillment.py`
- `test_import_mapping_acceptance.py`
- `test_integration_csv.py`
- `test_integration_excel.py`
- `test_integration_jobs.py`
- `test_integration_mock_api.py`
- `test_integration_preview.py`
- `test_integration_security.py`
- `test_integration_ssrf.py`
- `test_internal_authorization_regressions.py`
- `test_internal_notifications.py`
- `test_isolation.py`
- `test_mapping_ai.py`
- `test_mapping_apply.py`
- `test_mapping_canonical_consistency.py`
- `test_mapping_preview.py`
- `test_mapping_profile.py`
- `test_mapping_rules.py`
- `test_mapping_security.py`
- `test_noibo_route_convergence.py`
- `test_phase10_demonstration_scenarios.py`
- `test_phase10_integration.py`
- `test_phase11_cross_domain_scenarios.py`
- `test_phase11_security_hardening.py`
- `test_policy_and_claim_consistency.py`
- `test_production_deployment_dossier.py`
- `test_production_readiness.py`
- `test_public_auth_and_customer_experience.py`
- `test_public_branch_finder.py`
- `test_public_consultation_evidence.py`
- `test_public_copilot_and_cart_api.py`
- `test_public_ecommerce_cart_and_checkout.py`
- `test_public_geocoding.py`
- `test_public_policy_copy.py`
- `test_public_website_and_portal_separation.py`
- `test_rag_chunk_metrics.py`
- `test_rag_chunking_embedding.py`
- `test_rag_documents.py`
- `test_rag_evaluation.py`
- `test_rag_evaluation_runner.py`
- `test_rag_evaluation_scoring.py`
- `test_rag_grounding_assistant.py`
- `test_rag_human_review.py`
- `test_rag_independent_dataset.py`
- `test_rag_numeric_facts.py`
- `test_rag_retrieval.py`
- `test_rag_security_rbac.py`
- `test_rbac.py`
- `test_recommendations.py`
- `test_registration_codes.py`
- `test_report_metric_truthfulness.py`
- `test_retail_analytics.py`
- `test_retail_branches.py`
- `test_retail_categories.py`
- `test_retail_customers.py`
- `test_retail_goods_receiving.py`
- `test_retail_isolation.py`
- `test_retail_orders.py`
- `test_retail_product_management.py`
- `test_retail_products.py`
- `test_retail_rbac.py`
- `test_retail_stockout_prediction.py`
- `test_role_acceptance_matrix.py`
- `test_root_cause_grounding.py`
- `test_scope_benchmark_inputs.py`
- `test_seed_demo_reporting.py`
- `test_seed_demo_safety.py`
- `test_service_catalog.py`
- `test_service_email_commit.py`
- `test_service_employees.py`
- `test_service_isolation.py`
- `test_service_labor.py`
- `test_service_rbac.py`
- `test_service_requests.py`
- `test_service_schedules.py`
- `test_service_sla.py`
- `test_service_tasks.py`
- `test_service_workload.py`
- `test_simulation_evidence.py`
- `test_smoke.py`
- `test_sop_catalog.py`
- `test_tool_registry.py`
- `test_web_auth_routing.py`
- `test_workspaces.py`
