# Truy vết ca sử dụng theo đề cương được duyệt

Đối chiếu bản `output/docx_review/teacher_review_v2/De_cuong_Ha_Minh_Tien_sua_gop_y_lan_2.docx`,
không sửa bản đã duyệt. Ma trận tách **có triển khai**, **có kiểm thử** và **đã
nghiệm thu**; không biến sự tồn tại của file test thành bằng chứng pass.
Danh mục URL/view thực trích xuất: `output/model_contract_20260925_v2/routes.json`.
Danh mục field/quan hệ/constraint: `output/model_contract_20260925_v2/model_contract.json`.

## Yêu cầu và nơi kiểm chứng

Đường dẫn tương đối từ repo. Các file test bên dưới được đưa vào full-suite
`output/acceptance_verification/20260925T012747Z/`; chỉ đọc kết quả sau khi runner
kết thúc, không suy ra pass từ ma trận này. Cổng live được ghi riêng.

| ID | Ca sử dụng / tác nhân | Code xử lý | Kiểm thử | Điều kiện hoặc phần chưa xác nhận |
|---|---|---|---|---|
| UC01 | Khách đăng ký và xác minh email | apps/public_web/registration.py | tests/test_registration_codes.py | Code/link hết hạn, replay; inbox thật mục 91 |
| UC02 | Khách đăng nhập Google | apps/public_web/views.py | tests/test_google_oauth_and_email_notifications.py | Mô phỏng HTTP không chứng minh OAuth thật |
| UC03 | Quản trị tài khoản/vai trò | apps/accounts/services.py | tests/test_auth.py; tests/test_rbac.py | Quyền tùy workspace, không cấp membership cho khách |
| UC04 | Chọn workspace và cách ly | apps/workspaces/middleware.py | tests/test_workspaces.py; tests/test_internal_authorization_regressions.py | Header tường minh không được fallback |
| UC05 | Xem/đổi danh mục sản phẩm | apps/retail/services.py | tests/test_retail_products.py; tests/test_retail_product_management.py | view/manage tách biệt; xóa legacy có đơn phải từ chối |
| UC06 | Khách hàng và chi nhánh | apps/retail/models.py | tests/test_retail_customers.py; tests/test_retail_branches.py | Customer thuộc workspace, không gộp chỉ bằng email |
| UC07 | Mua hàng, nhận shop/giao hàng | apps/public_web/fulfillment.py | tests/test_home_delivery_fulfillment.py; tests/test_checkout_concurrency.py | Strict delivery opt-in, không mặc nhiên bật production |
| UC08 | Xem đơn đã mua | apps/public_web/views.py | tests/test_public_ecommerce_cart_and_checkout.py | Ownership tài khoản/guest session, không dùng ID đơn làm quyền |
| UC09 | Cập nhật trạng thái đơn | apps/retail/services.py | tests/test_retail_orders.py; tests/test_approval_state_integrity.py | Kiểm transition, tồn kho và replay |
| UC10 | Nhập hàng và số dư tồn kho | apps/retail/services.py | tests/test_retail_goods_receiving.py; tests/test_fulfillment_inventory_consistency.py | Không coi toàn bộ WMS đã hoàn thiện |
| UC11 | Danh mục dịch vụ/nhân viên | apps/service_ops/services.py | tests/test_service_catalog.py; tests/test_service_employees.py | Read/manage theo permission |
| UC12 | Khách gửi yêu cầu dịch vụ | apps/public_web/views.py | tests/test_public_auth_and_customer_experience.py | Customer–workspace và gửi thư sau commit |
| UC13 | Quản lý vòng đời phiếu | apps/service_ops/services.py | tests/test_service_requests.py; tests/test_service_rbac.py | Quyền chuyển trạng thái không suy ra từ quyền đọc |
| UC14 | Phân công và công việc | apps/service_ops/services.py | tests/test_service_tasks.py; tests/test_service_workload.py | Membership/permission, không mặc nhiên tự duyệt |
| UC15 | Lịch và thời gian lao động | apps/service_ops/services.py | tests/test_service_schedules.py; tests/test_service_labor.py | Chi phí và nhân sự theo quyền |
| UC16 | SLA và dashboard dịch vụ | apps/service_ops/sla_engine.py | tests/test_service_sla.py | Thiếu deadline = UNKNOWN, không coi đạt SLA |
| UC17 | Dashboard/doanh thu/báo cáo | config/views.py | tests/test_executive_reporting_and_telemetry.py; tests/test_retail_analytics.py | Aggregate chỉ workspace được phép; không dùng resolution làm SLA |
| UC18 | Nhập CSV/Excel/API giả lập | apps/integration/services.py | tests/test_integration_csv.py; tests/test_integration_excel.py; tests/test_integration_mock_api.py | SSRF/upload/rate limits có kiểm thử riêng |
| UC19 | Ánh xạ/preview/apply canonical | apps/mapping/services.py | tests/test_import_mapping_acceptance.py; tests/test_mapping_canonical_consistency.py | Preview không ghi; apply có validation/transaction |
| UC20 | Nạp tài liệu và embedding | apps/knowledge/services.py; apps/knowledge/embedding.py | tests/test_embedding_provenance.py; tests/test_embedding_space_isolation.py | Ghi API/hash-fallback/UNKNOWN thật, không suy từ config |
| UC21 | Truy xuất và trả lời có nguồn | apps/knowledge/retrieval.py; apps/knowledge/services.py | tests/test_adversarial_rag_execution.py; tests/test_generation_provenance.py | Đánh giá semantic/API thật còn thiếu; không có FactGuard runtime |
| UC22 | Kiểm đúng/đủ câu trả lời | apps/knowledge/evaluation.py; apps/knowledge/human_review.py | tests/test_rag_numeric_facts.py; tests/test_rag_human_review.py | Bộ chấm lexical/numeric không thay người chấm ngữ nghĩa |
| UC23 | Dự báo XGBoost/baseline | apps/forecasting/training.py | tests/test_forecasting_training.py; tests/test_forecast_experiment_bundle.py | Có snapshot tổng hợp replay; không chứng minh hiệu quả thật |
| UC24 | Worker dự báo và recovery | apps/forecasting/services.py | tests/test_forecasting_queue.py | Evidence production restart mục 92 vẫn thiếu |
| UC25 | Khuyến nghị có lý do | apps/recommendations/services.py | tests/test_recommendations.py | Luật xác định, không gọi là mô hình AI học độc lập |
| UC26 | Duyệt/từ chối hành động | apps/approvals/executor.py; apps/approvals/registry.py | tests/test_approvals.py; tests/test_approval_concurrency_evidence.py | Cấm tự duyệt, idempotency và contract theo action |
| UC27 | Nhật ký truy vết | apps/audit/services.py | tests/test_audit_database_evidence.py; tests/test_audit_trail_evidence.py | Trigger không bảo vệ khỏi chủ DB; outer transaction có giới hạn |
| UC28 | GIS chi nhánh/khách/phiếu/nhân viên | apps/gis/services.py | tests/test_gis_retail.py; tests/test_gis_service.py; tests/test_gis_security.py | Tọa độ/PII theo quyền, không công khai dữ liệu nội bộ |
| UC29 | Khoảng cách/bán kính | apps/gis/services.py | tests/test_gis_reference_distances.py | Spheroid khác road distance |
| UC30 | Bản đồ công khai/GPS/địa chỉ | apps/public_web/geocoding.py | tests/test_public_branch_finder.py | Live Nominatim và GPS thật mục 56/57 |
| UC31 | Thông báo nội bộ/đánh dấu đọc | apps/notifications/services.py | tests/test_internal_notifications.py | Đúng recipient, không chỉ đúng workspace |
| UC32 | Email/ăn mừng phê duyệt của khách | apps/public_web/email_service.py | tests/test_customer_approval_notices.py; tests/test_customer_email_outbox_and_oauth_security.py | SENT là provider acceptance, không phải inbox |
| UC33 | Chat gửi/nhận và lịch sử | apps/notifications/chat_service.py | tests/test_bulletin_and_team_chat.py | Polling 3 giây, không WebSocket; visual hai phiên còn thiếu |
| UC34 | Bản tin đọc/đăng | apps/notifications/bulletin_service.py | tests/test_bulletin_and_team_chat.py | Active ADMIN/MANAGER hoặc superuser đăng |
| UC35 | Bản tin cập nhật | apps/notifications/bulletin_edit_views.py | tests/test_bulletin_update.py | Scoped 404, field whitelist; last-write-wins |

## Sai khác mới cần xử lý, không giấu bằng ma trận

Rà `apps/notifications/ui_views.py` ngày 25/09 phát hiện màn hình chat/bản tin
còn fallback workspace khi query `workspace_id` tường minh không được phép;
UUID sai định dạng cũng chưa được xử lý thống nhất. Dữ liệu vẫn chọn từ workspace
được phép nhưng người dùng có thể xem/gửi nhầm workspace. Đây là lỗi contract
chọn workspace, không được mô tả là cross-workspace leak đã chứng minh.
Đã sửa sau khi full suite kết thúc; 12 regression mới nằm trong nhóm 52 tests OK.
Chi tiết bản vá và ranh giới hai phiên bản ở ACCEPTANCE_BATCH_2026_09_25.md.

## Đánh giá theo yêu cầu thầy

- Đã có nguồn đối chiếu cho nhóm quản lý, AI, GIS, cộng tác và kiểm soát hành động.
- Gemini 2.5 Flash/embedding API thật trong đề cương là đối tượng cần đánh giá;
  fallback và mocked tests không thay thế kết quả API thật.
- Chat/bản tin tách biệt ConversationSession của AI; polling được ghi rõ.
- Khả năng giảm thời gian/chi phí là mục tiêu cần đo, chưa là kết quả định lượng.
- Ma trận là tài liệu truy vết; các ô còn thiếu không được tính là đã nghiệm thu
  nghiệp vụ hoặc production. Visual QA không thể suy ra từ test API.
