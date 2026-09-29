# Đợt cập nhật bản tin và grounding — 24/09/2026

## Đã triển khai

1. Form sửa bản tin tiếng Việt, liên kết từ bảng tin chỉ hiện với người có quyền.
2. GET/POST `/noibo/bang-tin/<id>/sua/` và POST `/api/v1/notifications/bulletins/<id>/update/`.
3. Dùng model InternalBulletin hiện có; không thêm migration, role hoặc hệ thống bản tin song song.
4. Workspace phải được chọn rõ và có quyền ADMIN/MANAGER (hoặc superuser); không fallback khi thiếu/sai workspace.
5. Lookup bản tin trong workspace đã được cấp quyền, ID chéo workspace trả 404; public customer, EMPLOYEE/VIEWER, membership inactive bị chặn.
6. Service cũng kiểm tra quyền; transaction và row lock; chỉ lưu title/content/priority/updated_at. Tác giả, workspace, publication và pin expiry không nhận từ client.
7. CSRF giữ nguyên; GET API không sửa dữ liệu; title quá dài, priority sai, nội dung rỗng, JSON sai được từ chối. Form lỗi giữ nội dung nhập và hiển thị lỗi theo trường + summary.
8. Root-cause tồn kho bỏ con số forecast/lead-time/ngưỡng hard-code, yêu cầu quyền retail.view_product, tra sản phẩm chính xác trong workspace.
9. Không tự chọn sản phẩm đầu tiên, không chọn tùy ý tên trùng, không báo tồn bằng 0 khi thiếu balance. Chỉ trình bày tồn quan sát được, không suy ra nguyên nhân từ riêng con số tồn.
10. Nhánh SLA/phân công bỏ kết luận giả về thời gian/trọng số. Chưa tích hợp bằng chứng cụ thể thì yêu cầu mã phiếu/khuyến nghị và nói rõ chưa đủ căn cứ.

## Kiểm thử thực chạy

- `python manage.py test tests.test_bulletin_update tests.test_bulletin_and_team_chat tests.test_branch_warning_evidence_route tests.test_phase10_demonstration_scenarios --settings=config.settings_evidence_test --noinput -v 1`
  - **29 tests OK, 241.546s**. Chạy trước khi bổ sung 2 test bulletin và các regression tồn kho cuối.
- `python manage.py test tests.test_root_cause_grounding --settings=config.settings_evidence_test --noinput -v 1`
  - **4 tests OK, 0.136s**, bản đầu trước khi bổ sung 2 trường hợp.
- Nhóm cuối `python manage.py test tests.test_bulletin_update tests.test_root_cause_grounding --settings=config.settings_evidence_test --noinput -v 1`
  - Lần đầu: **16 tests, 1 error, 1.605s** do fixture tài khoản thứ hai dùng email rỗng trùng unique constraint. Sửa email fixture, không sửa model hay assertion.
  - Chạy lại: **16 tests OK, 5.088s** (10 bulletin + 6 grounding).
- `python manage.py check`: no issues.
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `git diff --check` trên file tracked vừa sửa: không có lỗi whitespace.

Các lần chạy có trùng test; không cộng thành số test độc lập. Không có live API model, không gửi email, không thay dữ liệu nghiệp vụ. Full suite chưa rerun sau đợt này.

## Giao diện và giới hạn

Skill ui-ux-pro-max được dùng cho nhãn form, giữ input, lỗi theo trường và summary. Browser thử mở tab local nhưng công cụ báo `failed to write kernel assets ... path specified`; chưa có visual QA desktop/mobile. Server-rendered UI và POST được test, không thay cho kiểm chứng browser.

Không push/deploy. Chưa có conflict detection cho hai người cùng sửa nội dung cũ: row lock bảo vệ ghi trong transaction nhưng hiện vẫn last-write-wins. Không tự thêm schema/version ngoài phạm vi đợt này.

## Liên hệ checklist

- Mục 81: đã lấp khoảng trống chức năng cập nhật bản tin và cập nhật ma trận; còn cần rà toàn bộ use case/ảnh browser trước khi đóng cả mục ma trận 12 nhóm.
- Mục 11/39/80: giảm thêm tuyên bố AI thiếu căn cứ, nhưng chưa thay thế chấm semantic độc lập hay đồng bộ tất cả tài liệu.
- Giữ **72/97 đóng tạm thời**, không tự tăng % vì hoàn tất vài phần của mục rộng.
- CI/Sentry/live email/restore và policy được duyệt vẫn giữ điều kiện trước; không yêu cầu user cung cấp lại thông tin đã xác nhận.
