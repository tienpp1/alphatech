# Đợt 28 — seed an toàn, quyền demo và diễn giải học thuật

Ngày: 16/09/2026. Không thao tác dữ liệu nghiệp vụ, không push/deploy.

## Thay đổi và nguyên nhân

- seed_demo trước đây ghi đè mật khẩu, in token/password và xóa dữ liệu seed cũ.
  Nay chỉ chạy trên database local DEBUG mới và có xác nhận rõ ràng. Từ chối nếu
  có User/Workspace/Role; thêm identity-only để kiểm chứng quyền không cần domain seed.
- Test role cũ tự tạo permission matrix rồi kiểm tra chính matrix ấy; VIEWER còn
  được gán approval.view khác seed. Test mới dùng seed thật, kiểm tra retail/service,
  public user và membership inactive. Không sửa role grant để khớp tài liệu.
- README/runbook/demo guide phản ánh employee là VIEWER tại service; không được
  cập nhật task. Không coi khuyến nghị nhập hàng là giao dịch approval đã thực thi.
- Sửa scope/defense: không có phép đo tỷ trọng public/internal; không phải air-gap;
  bảng con lấy scope qua cha; ORM không tự lọc mọi truy vấn. Phân biệt ingestion,
  handler, inference và model.fit trong AI_METHOD_BOUNDARIES.md.
- Sửa các diễn giải liên quan R², leakage tuyệt đối và công thức GIS cũ ở tài liệu phạm vi.

## Kiểm chứng

```powershell
python manage.py test tests.test_seed_demo_safety tests.test_role_acceptance_matrix --settings=config.settings_evidence_test --keepdb --noinput -v 1
# 10 tests, 24.886s, OK
python manage.py test tests.test_service_rbac --settings=config.settings_evidence_test --keepdb --noinput -v 1
# 2 tests, 9.062s, OK
python manage.py check
# System check identified no issues (0 silenced).
python manage.py makemigrations --check --dry-run
# No changes detected
```

Test chạy trên PostgreSQL test database riêng do evidence settings tạo. Không chạy
seed trên database đang sử dụng. Có 12 test khác nhau, không cộng lại các lần chạy cũ.
Đối chiếu source: workspaces/models.py, accounts/services.py, retail/models.py,
service_ops/models.py, knowledge/services.py + embedding.py và forecasting/training.py.

## Checklist và giới hạn

Đóng 8, 9, 10, 12 trong tài liệu Markdown hiện hành đã rà: 44/97 =45,4%.
Mục 70 và 87 chuyển một phần. Nhật ký tỷ trọng cũ được đánh dấu superseded;
không tự sửa Word hoặc kết luận mọi tài liệu cũ đã đồng bộ.

Chưa kiểm tra full domain seed, chưa browser walkthrough toàn bộ vai trò, chưa
chốt quyền kỹ thuật viên với đề cương. Không chứng nhận production/LLM thật.
Không mở browser cho thay đổi CLI/tài liệu vì không có UI mới cần kiểm chứng.
Không áp dụng skill UI/docx vào sửa backend/Markdown để tránh mở rộng phạm vi.

Bước tiếp theo: đối chiếu đề cương hiện hành với tác vụ kỹ thuật viên (70),
chuẩn bị dữ liệu demo độc lập và walkthrough theo role (87), rồi hoàn thiện hồ sơ
dataset/run và chấm RAG độc lập. Không nâng quyền hoặc bịa số liệu để đóng mục.
