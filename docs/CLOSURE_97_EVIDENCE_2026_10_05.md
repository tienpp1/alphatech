# Phụ lục đối chiếu 97 tiêu chí — 05/10/2026

Không sửa ID, tiêu chí, cấu trúc hoặc tiến độ CHECKLIST_97_PROGRESS.md. Đây là
chỉ mục bằng chứng và giới hạn, không phải biên bản 97/97 PASS. Không quy đổi số
file/test xanh thành phần trăm hoàn thành. Các dòng kế thừa cần đọc nguồn tương
ứng trước khi ký nghiệm thu; việc lập bảng không tự chứng nhận lại nội dung.

## Cách đọc

- D: bằng chứng tài liệu; không thay kiểm thử runtime.
- T: có kết quả test local được ghi nhận; không thay UAT/provider thật.
- H: xác nhận của chủ dự án, không phải quan sát độc lập của agent.
- P: bằng chứng trực tiếp trên deployment có ngày/SHA riêng.
- C: phạm vi điều chỉnh đã được chủ dự án chọn, không phải PASS production.
- M: còn cần đối chiếu/chấm hoặc bằng chứng rộng hơn; không tự đóng.

Nguồn viết tắt (đường dẫn từ repository):

| Mã | Nguồn |
|---|---|
| S | docs/ACADEMIC_ACCEPTANCE_SCOPE.md; docs/ACADEMIC_SCOPE_ALIGNMENT.md |
| W | docs/IEEE_AND_SUBMISSION_AUDIT_2026_09_26.md; bản Word teacher_review_v2 |
| F | docs/FORECAST_INTEGRITY_2026_10_05.md; docs/FORECAST_EXPERIMENT_PROTOCOL.md |
| R | apps/knowledge/evaluation_scoring.py; apps/knowledge/evidence_metrics.py; docs/RAG_HUMAN_EVALUATION_EVIDENCE.md |
| A | docs/HO_SO_KIEM_TOAN_AUDIT_TRAIL.md; tests/test_approval_concurrency_evidence.py; tests/test_audit_database_evidence.py |
| G | docs/GIS_REFERENCE_EVIDENCE.md; docs/PRODUCTION_OSM_EVIDENCE_2026_09_26.md |
| B | docs/HO_SO_DOI_CHIEU_TAC_VU_EMPLOYEE_VA_RBAC.md; docs/ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md |
| L | docs/CLOSURE_RELEASE_2026_10_05.md; docs/RELEASE_ACCEPTANCE_2026_10_04.md; docs/FORECAST_INTEGRITY_2026_10_05.md |
| Q | docs/ACCEPTANCE_BATCH_2026_09_25_CLAIMS.md; tests/test_public_policy_copy.py; tests/test_customer_email_policy_boundary.py |
| X | docs/HO_SO_THUC_NGHIEM_DU_BAO_VA_DATA_CATALOG.md; docs/FORECAST_REPRODUCIBLE_BUNDLE_2026_09_24.md |

## Đối chiếu từng ID

| ID | Tiêu chí kiểm tra / nguồn | Loại và ranh giới nghiệm thu |
|---|---|---|
| 1 | Tên đề tài — S/W | D; tên chuẩn trong bản duyệt, tên cũ ở nhật ký không là tên bản nộp. |
| 2 | Bắt buộc/mở rộng — S/B; docs/COLLABORATION_UAT_2026_10_05.md | D/C/P; chat và bản tin bắt buộc, MANAGER/EMPLOYEE UAT theo thứ tự; same-session polling không là hai user đồng thời, roadmap không tự thành yêu cầu. |
| 3 | Phụ lục — W | H/D; chủ dự án xác nhận bản duyệt giữ hướng tương lai. |
| 4 | ERP/WMS — S/Q | D; không chứng nhận ERP/WMS đầy đủ. |
| 5 | Ví dụ LST/deep learning — S | D; không tự bổ sung model theo hình minh họa. |
| 6 | Lịch khoa — docs/ACCEPTANCE_REAUDIT_2026_09_23.md | D; hạn hành chính tách lịch phát triển, chưa chứng nhận đã nộp. |
| 7 | Tuyên bố 100% — Q/L | D; rút tuyên bố cũ, phụ lục này không khôi phục nó. |
| 8 | Tỷ trọng 15/85 — S | D kế thừa; không có phép đo tỷ trọng. |
| 9 | Air-gap — S | D; chỉ cách ly logic/RBAC. |
| 10 | Workspace bảng con — docs/PROJECT_CONTEXT.md | D/T; phạm vi kế thừa qua cha, không tự động lọc mọi query. |
| 11 | Tuyệt đối/không ảo giác — Q | D/T; guard nội dung không chứng minh an toàn tuyệt đối. |
| 12 | Ingestion/handler/training — docs/AI_METHOD_BOUNDARIES.md | D; không fine-tune Gemini. |
| 13 | Đồng bộ trạng thái — L/phụ lục này | D; trạng thái hiện hành ghi ea18f14/1201; nhật ký cũ giữ riêng, không dùng header lịch sử làm release mới. |
| 14 | Không cộng test trùng — L | T; dùng một log full riêng và các focused run riêng. |
| 15 | Nhận xét metric — F/X | T/D; XGBoost kém lag7 về MAE/RMSE vẫn được ghi nhận. |
| 16 | R² âm — F | T/D; không diễn giải là giải thích phần lớn phương sai. |
| 17 | Giữ kết quả kém — F/X | D; kết quả cũ và recursive mới đều không bị xóa. |
| 18 | One-step/recursive — F | T; 14 ngày một origin synthetic, không suy rộng nhiều origin. |
| 19 | Chọn run/workspace — tests/test_academic_report_command.py | T; selection tường minh, không gộp mọi run theo target. |
| 20 | Metric thiếu — F; tests/test_academic_reporting.py | T; unmeasured/null, RMSE zero khác RMSE thiếu. |
| 21 | Độ chính xác hiển thị — tests/test_academic_reporting.py | T; xem renderer, không làm tròn để che chênh lệch. |
| 22 | Train/calibration/test — F/X | T/D; snapshot mới có split, run lịch sử thiếu không hồi điền. |
| 23 | Tham số/phiên bản — F/X | T; provenance và manifest, không là backup dữ liệu sản xuất. |
| 24 | Baseline cùng horizon — F | T; recursive baseline tự roll-forward, không đọc actual tương lai. |
| 25 | MAPE gần zero — tests/test_forecasting_training.py | T/D; điều kiện mẫu số phải đi cùng số liệu. |
| 26 | Dải tham khảo — F | T; không calibrated; coverage one-step không dùng cho recursive. |
| 27 | Seed/hiệu quả thật — F/S | D; synthetic không chứng minh hiệu quả thương mại. |
| 28 | Bài toán chính — F | D/C; doanh thu ngày, chưa nghiên cứu đa origin/dữ liệu doanh nghiệp thật. |
| 29 | Keyword không là semantic — R | T; required groups/numeric chỉ proxy. |
| 30 | Chunk retrieval — R; tests/test_rag_chunk_metrics.py | T; gold IDs khác nguồn do chính answer trả về. |
| 31 | Hybrid cả hai nguồn — tests/test_rag_evaluation_scoring.py | T/H; user đã chấm IND-HYB ngày05/10 trên output offline thật; không đánh giá mọi câu hybrid. |
| 32 | Citation rate — R | T; source presence không tự chứng minh entailment. |
| 33 | Fallback precision — R | T; TP/(TP+FP), không dùng recall thay precision. |
| 34 | Từ chối nhầm — R | T; false positive có mẫu số riêng. |
| 35 | API/fallback — tests/test_generation_provenance.py | T; simulated provider không gọi live API. |
| 36 | Embedding thực dùng — tests/test_embedding_provenance.py | T; legacy UNKNOWN giữ UNKNOWN. |
| 37 | Bộ độc lập — apps/knowledge/independent_benchmark.py | H/C; user chốt chỉ nghiệm thu5 IND đã chấm, không holdout mù; không tính đã chứng minh bộ mù độc lập. |
| 38 | Output/time/error — tests/test_rag_evaluation_runner.py | T; mới bổ sung IND execution, không chỉ mock runner. |
| 39 | Đúng/đủ/số liệu — docs/RAG_REVIEW_FORM_2026_09_30.md; docs/RAG_INDEPENDENT_EXECUTION_2026_10_05.md | H; user đã đọc/chấm5 IND mới ĐẠT lúc09:40 ngày05/10; không semantic quality tổng quát. |
| 40 | Đối kháng — tests/test_adversarial_rag_execution.py | T/H; bốn answer/two denials, không quality tổng quát. |
| 41 | Workspace/role RAG — tests/test_rag_security_rbac.py | T; actor không superuser ở bộ IND mới. |
| 42 | Router không là LLM — R/S | D/T; mode phải đi cùng kết quả. |
| 43 | Cam kết thương mại — Q | T/P; không công bố cam kết từ SOP demo. |
| 44 | ISO/mã hóa — Q/S | D/C; không có chứng nhận ISO doanh nghiệp, không tuyên bố có. |
| 45 | Chính sách/demo — Q | D; synthetic policy không là văn bản doanh nghiệp ký duyệt. |
| 46 | Đồng nhất các kênh — Q/L | T/P/C; đóng bằng ranh giới không công bố điều kiện chưa duyệt. |
| 47 | Trọng tâm — S | D/C; nhân sự/pháp lý chuyên sâu ngoài phạm vi. |
| 48 | Tư vấn/triển khai — Q | D; trả góp không được coi đã triển khai chỉ từ lời chatbot. |
| 49 | What-if/giả định — tests/test_simulation_evidence.py | T; cần nhãn giả định, không là quan sát thật. |
| 50 | Nguồn khoảng cách — G | D/T; kiểm selected reference cases. |
| 51 | PostGIS không 100% — G | D; kiểm reference không chứng nhận mọi operation. |
| 52 | Biên radius — tests/test_gis_reference_distances.py | T; phân biệt spheroid nội bộ/Haversine public. |
| 53 | Invalid/foreign coordinates — tests/test_gis_security.py | T; không cho client chọn workspace ngoài quyền. |
| 54 | Chim bay/đường bộ — G | D/T; hai loại khoảng cách khác nhau. |
| 55 | Không shortest tuyệt đối — G/S | D; lựa chọn trong tuyến provider, không live traffic. |
| 56 | Nominatim — G | P ngày 26/09; không uptime SLA. |
| 57 | GPS thiết bị — L | H; user xác nhận deny/unavailable/low accuracy. |
| 58 | Provider timeout — tests/test_public_branch_finder.py | T/D; best-effort, rate/cache theo contract. |
| 59 | Approval không gán điểm — A; tests/test_academic_reporting.py | T; không suy compliance từ count. |
| 60 | Count không là workflow — A | D; kiểm tác động thực cần chuỗi execution. |
| 61 | Proposal→audit — tests/test_approvals.py | T; action hỗ trợ, không mọi tư vấn. |
| 62 | Reject/self/role/params — tests/test_approvals.py | T; separation of duties không bỏ để demo. |
| 63 | Replay/concurrency — tests/test_approval_concurrency_evidence.py | T; DB unique/locks, không exactly-once mọi ngoại dịch vụ. |
| 64 | Rollback/compensation — tests/test_approval_state_integrity.py | T; giới hạn hành động hỗ trợ. |
| 65 | Advisory/action — apps/approvals/registry.py | D/T; chỉ action contract đã đăng ký. |
| 66 | Reorder/workload — S/A | C; cố ý không map, không tính triển khai execution. |
| 67 | Audit thực — tests/test_audit_trail_evidence.py | T; actor/time/changes từ sự kiện, không gán sẵn. |
| 68 | Trigger DB — tests/test_audit_database_evidence.py; restore | T; DB owner vẫn có quyền, không bất khả sửa tuyệt đối. |
| 69 | Role matrix — B; tests/test_internal_authorization_regressions.py | T/P; Google identity chỉ public, password nội bộ theo role. |
| 70 | EMPLOYEE — B | D/T; không nâng quyền mutation ngoài seeded capabilities. |
| 71 | Order/service lifecycle — B | T; chuyển trạng thái sai có regression. |
| 72 | Customer/ownership — tests/test_public_ecommerce_cart_and_checkout.py | T/P; khác tài khoản không xem được TEST 162. |
| 73 | Fulfillment/inventory — tests/test_fulfillment_inventory_consistency.py | T; strict policy opt-in, không giả định bật production. |
| 74 | Email failure/retry — tests/test_brevo_email_backend.py | T; provider acceptance khác receipt, timeout có trạng thái bất định. |
| 75 | Celebration — L | P/H; đúng owner, người khác không thấy, ack/reload; TEST đã hủy. |
| 76 | Registration/replay — tests/test_registration_codes.py; L | T/H; cross-device user UAT riêng. |
| 77 | Import→mapping — tests/test_import_mapping_acceptance.py | T; scoped invalid/duplicate, không replay-idempotency mọi child entity. |
| 78 | Không yếu assertion — L | T/D; cleanup connection sửa teardown, không skip/keepdb để che lỗi. |
| 79 | Nghiên cứu so sánh — docs/RESEARCH_SOURCE_CHECK_2026_09_25.md; docs/DRAFT_SOURCE_AND_DIAGRAM_AUDIT_2026_10_05.md | D/M; sửa nguồn3/4, thêm so sánh5nguồn và giới hạn GIS; chưa fullpaper-review mọinguồn hoặc khảo sát trongnước. |
| 80 | Gap ứng dụng — S/W | D; tích hợp không tự là tính mới thuật toán. |
| 81 | Requirement→evidence — B | T/D; 35 UC matched log, không chứng nhận adequacy/visual tự động. |
| 82 | Sơ đồ/code — B; tests/test_academic_diagram_contract.py | D/T/M; sửa22 FK và4 sequence draft, snapshot48model mới; chưa có bản nộp cuối để kiểm mọi hình. |
| 83 | Data catalog — X | D/T; synthetic nguồn/seed/hash; dữ liệu production không đưa vào gói công khai. |
| 84 | Replay experiment — F/X | T; CSV/model/manifest replay, không multi-origin generalization. |
| 85 | Cùng source/run — F/L | T; full1201 tree c800480 khớp source release ea18f14; CI exactea18f14, không nhập các run thành một. Sửa tài liệu tiếp theo có focused run riêng. |
| 86 | Fail/skip — F/L | D/T; lỗi CI teardown trước giữ lại, full log0skip không chứng minh provider thật. |
| 87 | README/demo/migrations — docs/DEMO_IDENTITY_RUNBOOK.md; B | D/T; seed chỉ DB local trống, không reseed/reset hệ thống hiện hành. |
| 88 | Demo mạng lỗi — docs/DEMO_FALLBACK_RUNBOOK.md | D/T; phải ghi offline/deterministic, không giả live API. |
| 89 | IEEE/tên/claims — W/Q; docs/DRAFT_SOURCE_AND_DIAGRAM_AUDIT_2026_10_05.md | D/M; sửa claims/citation draft, Word duyệt giữ hash; không áp bibliography khác lên Word, chưa nghiệm thu bản nộp cuối. |
| 90 | Deploy SHA — L | P; Render dep-db1h2hegekts73dptdbg exactea18f14. Sửa draft local sau đó không gọi đã deploy. |
| 91 | Inbox bốn event — L | H; không Message ID độc lập cho release cuối. |
| 92 | Worker production — F | C/T; tắt async Render Free, local lifecycle không production certification. |
| 93 | CI/security — L | P; run37256797585 success exactea18f14, coverage58%, không100%. |
| 94 | Sentry — L | H; user thấy events, chưa có Event ID độc lập cho release cuối. |
| 95 | HTTPS/cookie/CSP — L/F | P; baseline enforcement, còn inline/eval, không strict nonce CSP. |
| 96 | pg_dump→pg_restore — docs/PRODUCTION_RESTORE_DRILL_2026_10_02.md | T;60 bảng/10576 dòng cùng snapshot; offsite/media/grants không bao gồm. |
| 97 | Secrets — F/L | T/H; known-pattern source/history scan, rotation user xác nhận, không quét mọi dạng secret. |

## Gói bằng chứng hiện hành và những gì không được gọi PASS

`output/use_case_closure_release_20261005.json`: 35 UC, không missing file hoặc
unobserved test file khi nối với full log1201. Đây là reference/execution check,
không là chứng chỉ nghiệp vụ. Full log: output/policy_release_jx0ekuc9/tests.log,
tree c80048022ab604cb3a807dee49b5f77a0fecb532; source khớp release ea18f14.
Các run1197/04406c8 là lịch sử, không cộng với run này. Thay đổi draft sau release
có kết quả focused riêng, không hồi gán full1201 cho source chưa chạy lại.

Giữ Word duyệt SHA256 9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816.
Không ghi đè Word, upload dump production, sửa mật khẩu demo hoặc mở async/S3.
Không tái tạo đơn TEST production. Backup ổ D cùng máy không bảo vệ mất máy;
offsite hoãn theo chủ dự án. Local Storage không là phục hồi file Render Free.

Chủ dự án đã chấm bộ IND mới và xác nhận chưa có báo cáo/slide cuối khác ngoài
Word duyệt: gói hiện có **chưa nghiệm thu bản nộp cuối**. Muốn gọi holdout mù
cần câu hỏi mới do reviewer giữ riêng, chưa dùng để sửa router/prompt.
Xác nhận cũ về email/Sentry/GPS giữ loại H, không giả Message/Event ID.
Nếu chỉ nghiệm thu phạm vi đồ án đã điều chỉnh, có thể ghi xử lý có giới hạn;
không được đổi thành mọi tiêu chí production gốc đều PASS.
