# Tiếp tục nghiệm thu — 01/10/2026

Phiên được mở lại theo yêu cầu tiếp tục của chủ dự án. Không thay ID hoặc tiêu chí của 97 mục; không thực hiện restore đã hoãn.

## Kiểm chứng local

- Nhóm HTTPS/email/deployment 77/77 OK, 249.440s, settings test cô lập PostgreSQL loopback và email bộ nhớ. Đồng thời bỏ Google/SMTP credentials trong override để kiểm tra điều kiện tương tự CI. Không chứng minh email inbox hoặc CI runner.
- CSP/readiness/deployment/health: 15/15 OK, 5.702s. Mỗi script HTTPS trong template được đối chiếu origin allowlist; kiểm tra header enforcement thật.
- `python manage.py check`: exit 0, không có lỗi.
- `python manage.py makemigrations --check --dry-run`: exit 0, No changes detected.
- Lệnh check dùng settings_evidence_test ban đầu bị chặn đúng thiết kế vì settings này chỉ dành cho test; không sửa guard. Hai lệnh validation sau dùng settings thông thường, chỉ đọc.
- Quét source: 780 files, 0 findings; quét 33 commit reachable: 0 findings theo mẫu giới hạn. Không chứng nhận mọi loại secret hoặc provider rotation. Chủ dự án đã xác nhận rotation trước đây.

## Release đang triển khai

- Commit `f2a831c2dd36369797b06889c0fc184a59b8d3fd`, đã push main. Chỉ commit CSP middleware, test, bước CI và changelog; giữ nguyên các tài liệu dirty/untracked khác.
- Render deploy `dep-dav1j7e0tbcc73d6ddlg`, ban đầu build_in_progress. Chưa tính là live cho đến khi kiểm tra trạng thái và HTTP/browser.
- Cập nhật từng biến riêng qua Render API: CSP_ENFORCE=True, CSP_REPORT_ONLY=False, SECURE_HSTS_SECONDS=3600, FORECAST_ASYNC_ENABLED=False. Không thay toàn bộ env hoặc in secret.
- HSTS khởi đầu một giờ; CSP còn inline/eval theo giao diện legacy. Không gọi đây là strict nonce CSP. Giữ Render Free và không khẳng định có worker production.

## Cổng CI còn cần bằng chứng đúng nguồn

- Run 36833413144 failure tại HTTPS email and deployment regressions, không có raw artifact truy cập được bằng credential hiện có.
- File integrations-tests.log chủ dự án cung cấp ghi test_service_email_commit/Python 3.11/pytest; workflow run này dùng Python 3.12/Django test và nhóm lỗi không chứa test_service_email_commit. Assertion trích trong log cũng khác source hiện tại. Chưa xác minh được liên hệ file với run/SHA; không kết luận SMTP là nguyên nhân và không patch giả thuyết.
- Run mới 36836448440 cho f2a831c đang chạy tại lần kiểm tra đầu. Không thay kết quả runner bằng local PASS.

## Restore

Mục 96 tiếp tục hoãn vô thời hạn. Không thao tác database sandbox hoặc dữ liệu đang chạy.

## Kết quả cuối phiên

- Render deploy trên đã `live`; SHA đúng f2a831c, trùng mã CI. Mục 90 đóng cho release này, không bao gồm tài liệu dirty chưa commit.
- Run https://github.com/tienpp1/alphatech/actions/runs/36836448440 completed/success; job 110284905126 không có bước failure. Provider, Command Center, CSP, worker, RAG, Django check/migration, pip-audit, Bandit, hai nhóm coverage, coverage gate và artifact upload đều success. Mục 93 đóng cho run này. Chưa tải artifact nên không công bố tỷ lệ coverage hoặc tổng test runner chính xác. Không suy đoán nguyên nhân run cũ failure.
- HTTP `/dang-nhap/` thật 200: Strict-Transport-Security=max-age=3600; CSP enforcement có, report-only không có; nosniff; csrftoken Secure. HttpOnly của session được khóa True trong source; không đăng nhập để đọc session production. CSRF cookie không HttpOnly để tương thích JS. Env DEBUG=False/SSL redirect/Secure cookies/CSP flags được đối chiếu qua API, không in secret.
- Browser production: chi nhánh khởi tạo Leaflet/3 marker, tile OSM hiển thị; homepage video readyState=4, paused=False, error=None; quantum core/intro còn hoạt động. Console chỉ cảnh báo Tailwind CDN không phù hợp production; chưa chuyển asset build trong đợt này. Không chứng nhận lại mọi thao tác đăng nhập hoặc nội bộ. Mục 95 đóng trong phạm vi baseline tương thích này; inline/eval vẫn là hạn chế.
- Mục 92 đóng có điều kiện: chủ dự án không sử dụng async production trên Render Free và env FORECAST_ASYNC_ENABLED=False được xác minh. Local và CI worker tests success; không có bằng chứng worker production, không khẳng định restart production PASS. Nếu bật async, phải mở lại gate và có worker thật.
- Mục 97 đóng trong phạm vi quản lý secret release: .env bị Git ignore; scanner release 781 files/34 reachable commits không có mẫu secret đã biết; CI secret scan success. Rotation chỉ theo xác nhận chủ dự án, không phải truy cập kiểm chứng provider; không bảo đảm scan mọi dạng secret.
- Test service email được nêu trong log cung cấp: 1/1 OK, 8.925s cục bộ; không cần patch SMTP hoặc sửa test để gọi xanh.

Tổng: **96/97 mục tạm đóng theo phạm vi và bằng chứng phân loại**, chỉ 96 hoãn. Không đồng nghĩa 97/97, không chứng nhận disaster recovery hoặc mọi năng lực production. Các mục kế thừa không được chạy lại toàn bộ trong phiên này.
