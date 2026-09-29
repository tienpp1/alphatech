# Transport provider và CI thực tế — 25/09/2026

## Bằng chứng CI

GitHub API công khai trả HTTP 200 cho run
https://github.com/tienpp1/alphatech/actions/runs/34746264651
ở commit `a92b31750210c5d68c12faef6989ba9a1673053c` (trùng HEAD local,
không bao gồm dirty worktree). Kết quả **failure**:

- Cài dependency, Django check, migration drift, migrate, pip-audit: success.
- Bandit, Focused regressions, HTTPS email/deployment regressions: failure.
- Coverage gate và xuất artifact: success; không làm toàn pipeline thành PASS.
- Tải log job qua public API: 403. Annotation chỉ có exit code 1, không có
  traceback test. Cần log/artifact hoặc quyền đọc Actions để phân tích đúng run.

## Thay đổi mã nguồn

`config/provider_http.py` chỉ cho HTTPS, hostname trong allowlist của từng
caller, port chuẩn, không userinfo/fragment. Redirect bị từ chối trước khi gửi
request tiếp theo. OAuth giữ tùy chọn proxy và URL UserInfo đang dùng;
embedding/chat giữ timeout và fallback hiện có. Không đổi route, schema hoặc DB.

Các caller đã chuyển: Google token/UserInfo, Gemini embedding/generation,
OpenAI embedding. Test mô phỏng provider được retarget; guard offline chặn
cả urlopen cũ lẫn opener mới. Không dùng test mô phỏng làm bằng chứng live.
Workflow thêm nhóm regression transport và secret guard; chưa push/deploy.

## Bandit local

Cài Bandit 1.9.4 vào `output/security_tools`, không sửa package runtime.
Chạy cùng phạm vi `apps config`, không hạ severity, không thêm global skip:

```powershell
$env:PYTHONPATH='D:\ai_business_platform\output\security_tools'
python -m bandit -q -r apps config -x "*/migrations/*" -f json -o output/bandit_provider_fix_20260925.json
```

- Trước: **74 findings = 69 LOW + 5 MEDIUM**.
- Sau sửa transport: **70 findings = 69 LOW + 1 MEDIUM**; exit 1 vẫn giữ.
- Medium còn lại B104 ở `FORBIDDEN_HOSTNAMES` trong api_parser.py: địa chỉ
  0.0.0.0 dùng để CHẶN SSRF, không phải socket bind. Có ca kiểm tương ứng trong
  test_integration_ssrf.py; chưa thêm suppression hoặc gọi toàn scan là sạch.
- LOW còn 14 B105, 20 B110, 33 B311, 1 B404, 1 B603: phải phân loại từng vị trí,
  không xóa findings hàng loạt. Không in raw code/secret trong báo cáo này.
- JSON gốc giữ trong output (Git ignored), không phải artifact đã public/upload.

## Kiểm chứng và giới hạn

Provider/provenance/manifest: 23 tests OK, 17.398s; đây là lượt trước điều chỉnh
allowlist theo chính xác URL UserInfo hiện có. Lượt OAuth/email sau điều chỉnh
được lưu riêng tại output/provider_security_tests_20260925.log.
Kết quả lượt sau điều chỉnh: **51 tests OK, 157.630s**, database test riêng được
dọn sau chạy. Các event email trong log là backend test, không phải inbox thật.
Django check: 0 issues.

Probe HTTPS lúc 2026-09-25T13:07:36Z vẫn ReadTimeout; không chạy geocoding,
không xác nhận cookie/CSP. Xem output/public_probe_provider_batch_20260925.json.

Mục 93 và 97 còn mở, không tăng phần trăm chỉ vì sửa 4 findings.
Các cổng người duyệt/GPS/production/restore không thể thay bằng unit test.

## Rủi ro bổ sung đã sửa: legacy admin bootstrap

`seed_student_admin` trước đây đặt mật khẩu cố định và cấp superuser/staff cùng
ADMIN ở mọi workspace cho hai danh tính viết sẵn, kể cả tài khoản đã tồn tại.
Startup hiện không gọi lệnh này, nhưng chạy thủ công vẫn có nguy cơ chiếm quyền.
Lệnh đã được vô hiệu hóa: CommandError trước truy cập DB trong cả DEBUG=True/False.
Không chạy seed trên database nghiệp vụ; không đổi quyền hoặc mật khẩu người dùng.
Test SimpleTestCase không cho phép DB access chứng minh đường từ chối này.
Không thay bằng cơ chế quản trị song song: dùng createsuperuser tương tác khi
thực sự cần tạo tài khoản mới, cấp quyền workspace qua quản trị hiện có.

Guard/manifest sau thay đổi cuối: **11 tests OK, 2.027s**. Không cộng lượt này
với 51 để gọi là 62 test duy nhất (có test transport chạy lặp).

Bandit cuối sau vô hiệu hóa bootstrap: **68 findings (67 LOW + 1 MEDIUM)**,
vẫn exit 1; file output/bandit_provider_admin_final_20260925.json.
Known-secret scanner: 752 source files, 0 mẫu phát hiện; không phải chứng nhận
mọi secret/rotation. File output/release_secret_scan_provider_admin_20260925.json.
Các lệnh kiểm thử chính:

```powershell
python manage.py test tests.test_provider_http_boundary tests.test_generation_provenance tests.test_embedding_provenance tests.test_google_oauth_and_email_notifications tests.test_customer_email_outbox_and_oauth_security --settings=config.settings_evidence_test --noinput -v 1
python manage.py test tests.test_provider_http_boundary tests.test_legacy_admin_seed_disabled tests.test_academic_test_manifest_audit --settings=config.settings_evidence_test --noinput -v 1
```
