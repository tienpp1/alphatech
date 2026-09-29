# Kiểm toán lại 97 mục — cập nhật 24/09/2026

## Kết luận có căn cứ

Thu hồi kết luận 97/97 và 1.065 test pass từ các báo cáo trước.
Checklist hiện là đối chiếu tạm thời, không phải chứng nhận độc lập hoặc production.
Không cộng số test giữa các lần chạy thành tổng độc lập.

## Full suite thực chạy

- Lệnh: `python manage.py test tests --settings=config.settings_evidence_test --noinput -v 2`.
- Log: `output/acceptance_verification/20260923T072453Z/django.log`.
- Manifest: `output/acceptance_verification/20260923T072453Z/result.json`.
- Bắt đầu UTC 23/09/2026 07:24:56; kết thúc 07:59:11.
- Kết quả: **1.067 test, 2.032,520 giây; 8 failures và 8 errors; exit 1**.
- Fingerprint apps/config/tests không đổi trong lần chạy. Không bao gồm docs/scripts.
- Không có skipped được báo trong phần tổng kết; không suy ra mọi môi trường đều không skip.
- Database PostgreSQL/PostGIS test riêng, không phải dữ liệu nghiệp vụ hay production.
- Một số errors là cleanup trùng ca test; không lấy 1.067 trừ 16 để công bố số pass độc lập.

## Phân loại và xử lý

| Nhóm | Nguyên nhân | Xử lý / bằng chứng |
|---|---|---|
| Integration jobs/preview, Mapping AI/preview | Fixture tạo role ADMIN nhưng thiếu permission đã seed thực tế | Bổ sung đúng permission vào fixture, giữ nguyên assertion và quyền runtime |
| Đăng ký / thông báo nội bộ | Test cũ đòi thông báo trước xác minh email | Test đi qua OTP, chứng minh chưa thông báo khi inactive và thông báo sau xác minh |
| Xóa sản phẩm | Wrapper legacy bị thay đổi thành soft-delete dù có order items | Khôi phục ValidationError trong wrapper; API/UI thùng rác riêng không đổi. 19 test retail pass, 201,465 giây |
| Phase10 scenario A | Root-cause router mới che luồng lấy recommendations | Bổ sung đọc recommendations cho cảnh báo không xác định chi nhánh; không gán dữ liệu workspace cho chi nhánh cụ thể |
| Academic report / RAG human review | Windows sandbox PermissionError ở thư mục tạm | Chạy lại 2 module với quyền phù hợp: 11 test pass, 0,336 giây; không sửa assertion |
| Bulletin authorization | is_staff vượt quyền workspace | Bỏ bypass; test EMPLOYEE/VIEWER staff và inactive membership. 11 test pass, 127,577 giây |

Lần chạy nhóm 33 test sau sửa fixture đầu tiên: 227,185 giây, 1 failure Mapping AI
(fixture cấp manage nhưng endpoint read yêu cầu view). Đã đổi sang view.
Lần chạy tiếp theo: **143 test pass, 206,868 giây**:

`python manage.py test tests.test_mapping_ai tests.test_branch_warning_evidence_route tests.test_phase10_demonstration_scenarios tests.test_ai_advanced_context_benchmark.VietnameseAdvancedContextBenchmarkTestCase --settings=config.settings_evidence_test --noinput -v 1`

Giữ nguyên assertion Phase10; thêm 3 regression cho route cảnh báo chung, không
gán bằng chứng workspace cho chi nhánh có tên, và không bịa nguyên nhân khi thiếu dữ liệu.
Không mô tả lần chạy 33 test trước đó là 33/33 pass.
Full suite chưa chạy lại sau các sửa chữa; không có kết luận toàn bộ đã xanh.

Kiểm tra cuối 24/09: `python manage.py check` không có issues;
`python manage.py makemigrations --check --dry-run` trả `No changes detected`;
`git diff --check` trên các file code/status vừa sửa không báo lỗi whitespace.

## Nguồn học thuật và yêu cầu mới xác nhận

- Người dùng xác nhận bản duyệt là `output/docx_review/teacher_review_v2/De_cuong_Ha_Minh_Tien_sua_gop_y_lan_2.docx`.
- SHA256: `9DAEEFDB61D1F0241B601E71882D2BABB3ACE148173ACBBA57FA40D4B8FD1816`.
- Trang 16 giữ phụ lục định hướng phát triển; không tính nội dung tương lai là chức năng đã nghiệm thu.
- Bản duyệt yêu cầu chat, và bản tin có đăng/cập nhật/đọc. Chưa thấy endpoint cập nhật bản tin trong source đã rà; ma trận yêu cầu phải ghi khoảng trống này.
- PDF khoa ngày 24/08/2026: trang 2 và 5 quy định nộp cuốn 16–20/11, báo cáo dự kiến 23–28/11, nộp file 30/11–06/12. Khung 18 tuần cũ không có căn cứ.

## Chưa hoàn thành

- RAG: regex số không chứng minh đúng/đủ ngữ nghĩa; chưa có chấm độc lập đầy đủ.
- Một số nhánh explain_root_cause còn số/ngưỡng hard-code; phải thay bằng dữ liệu domain hoặc thông báo chưa đủ bằng chứng, không coi deterministic là grounded.
- Forecast: thiếu raw actual/prediction/bounds để xác minh coverage đã công bố; thiếu provenance đầy đủ cho run Batch 44. Không tái dựng giả bằng chứng cũ.
- Bản thuyết minh/slide mới còn nội dung cần đồng bộ theo đề cương và source.
- Chính sách kinh doanh chưa có văn bản được duyệt; bản dò source từ Gemini không thay thế văn bản đó.
- CI: user xác nhận chỉ có workflow, chưa có remote run của mã hiện tại.
- Sentry: user xác nhận chưa có DSN/live event; không coi cấu hình mã nguồn là đã vận hành.
- Restore: tiếp tục HOÃN theo user; không chạy pg_dump/pg_restore và không coi TEMPLATE clone/runbook là DR hoàn thành.
- Production OAuth/email từng được user xác nhận, nhưng chưa có bằng chứng mọi sự kiện của release hiện tại.

Không push/deploy toàn bộ dirty worktree chỉ để kích hoạt CI trước khi xác định gói thay đổi an toàn.

## Số dư checklist ngày 24/09

**72/97 (74,2%) ghi nhận đóng: 70 kế thừa, 2 đối chiếu nguồn; 25 còn mở.**
Mục 3 và 6 được đóng lại sau xác nhận bản duyệt và đọc PDF khoa gốc. Mục 81 mở
lại vì ma trận chưa phản ánh thiếu cập nhật bản tin. Đây không phải xác nhận độc
lập 72 mục đã được kiểm thử đầy đủ. Không dùng tiến độ này thay cho production gate.
