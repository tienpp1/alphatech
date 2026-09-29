# Phân loại baseline Bandit 68 findings — 25/09/2026

Nguồn SHA256: `b0113caa3756dd95d03239c26b58120b13d37336f6ab40cd94f5e0dc8a80d50c`. Dòng bên dưới là vị trí baseline, không phải vị trí sau sửa.

Phân loại không đồng nghĩa đóng CI; không thêm suppression hoặc đổi threshold. Không chứa raw code/credential.

| Vị trí baseline | Rule | Phân loại | Căn cứ / giới hạn |
|---|---|---|---|
| apps/accounts/management/commands/seed_demo.py:254 | B105 | Fixture có điều kiện | Credential demo công khai; CLI chặn production/remote/nonempty DB. Hàm seed_demo_identities vẫn là helper đặc quyền, không được gọi trên DB nghiệp vụ. |
| apps/accounts/management/commands/seed_demo.py:267 | B105 | Fixture có điều kiện | Credential demo công khai; CLI chặn production/remote/nonempty DB. Hàm seed_demo_identities vẫn là helper đặc quyền, không được gọi trên DB nghiệp vụ. |
| apps/accounts/management/commands/seed_demo.py:280 | B105 | Fixture có điều kiện | Credential demo công khai; CLI chặn production/remote/nonempty DB. Hàm seed_demo_identities vẫn là helper đặc quyền, không được gọi trên DB nghiệp vụ. |
| apps/accounts/management/commands/seed_demo.py:293 | B105 | Fixture có điều kiện | Credential demo công khai; CLI chặn production/remote/nonempty DB. Hàm seed_demo_identities vẫn là helper đặc quyền, không được gọi trên DB nghiệp vụ. |
| apps/accounts/management/commands/seed_demo.py:544 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:544 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:544 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:545 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:547 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:551 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:552 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:561 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:561 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:586 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:588 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:589 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:590 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:602 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:603 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:604 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:607 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:613 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:614 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:620 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:622 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:623 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:733 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:735 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:737 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:739 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:741 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:784 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:784 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:787 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/accounts/management/commands/seed_demo.py:1006 | B311 | Ngẫu nhiên mô phỏng | Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập. |
| apps/forecasting/management/commands/forecast_worker.py:2 | B404 | Subprocess có ranh giới | Worker gọi sys.executable/manage.py bằng argv list, PK/UUID, không shell; đòi hỏi code/runtime/DB quản trị đáng tin. Chưa có live restart proof. |
| apps/forecasting/management/commands/forecast_worker.py:44 | B603 | Subprocess có ranh giới | Worker gọi sys.executable/manage.py bằng argv list, PK/UUID, không shell; đòi hỏi code/runtime/DB quản trị đáng tin. Chưa có live restart proof. |
| apps/integration/parsers/api_parser.py:37 | B104 | False positive có căn cứ | 0.0.0.0 nằm trong denylist SSRF, không là bind address; test_integration_ssrf kiểm từ chối. Chưa suppression. |
| apps/knowledge/adversarial_cases.py:14 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/knowledge/adversarial_cases.py:22 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/knowledge/adversarial_cases.py:33 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/knowledge/adversarial_cases.py:41 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/knowledge/adversarial_cases.py:49 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/knowledge/embedding.py:83 | B110 | Đã sửa, cần scan đối chiếu | Fallback giữ nguyên, log mã cố định không exception/key; test_ai_error_boundary và provenance. |
| apps/knowledge/embedding.py:108 | B110 | Đã sửa, cần scan đối chiếu | Fallback giữ nguyên, log mã cố định không exception/key; test_ai_error_boundary và provenance. |
| apps/knowledge/fields.py:42 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/knowledge/fields.py:64 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/knowledge/services.py:172 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/knowledge/services.py:243 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/knowledge/services.py:324 | B110 | Đã sửa, cần scan đối chiếu | Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định. |
| apps/knowledge/services.py:382 | B110 | Đã sửa, cần scan đối chiếu | Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định. |
| apps/knowledge/services.py:416 | B110 | Đã sửa, cần scan đối chiếu | Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định. |
| apps/knowledge/services.py:441 | B110 | Đã sửa, cần scan đối chiếu | Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định. |
| apps/knowledge/services.py:461 | B110 | Đã sửa, cần scan đối chiếu | Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định. |
| apps/knowledge/services.py:478 | B110 | Đã sửa, cần scan đối chiếu | Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định. |
| apps/knowledge/services.py:508 | B110 | Đã sửa, cần scan đối chiếu | Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định. |
| apps/knowledge/services.py:1424 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/notifications/management/commands/seed_bulletin_and_chat_demo.py:30 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/public_web/views.py:384 | B311 | ID hiển thị, không là secret | Mã phiếu/khách hàng không cấp quyền truy cập. Rủi ro va chạm mã vẫn cần xử lý riêng; không tuyên bố unique từ random. |
| apps/public_web/views.py:587 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/public_web/views.py:588 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/public_web/views.py:936 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/public_web/views.py:1169 | B105 | False positive có căn cứ | Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection. |
| apps/public_web/views.py:1287 | B311 | ID hiển thị, không là secret | Mã phiếu/khách hàng không cấp quyền truy cập. Rủi ro va chạm mã vẫn cần xử lý riêng; không tuyên bố unique từ random. |
| apps/retail/image_services.py:136 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/retail/management/commands/purge_deleted_products.py:108 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| apps/retail/services.py:379 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
| config/views.py:564 | B110 | Cần xử lý tiếp | Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner. |
