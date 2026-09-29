# Đợt 39 — Nội dung công khai và đối chiếu nguồn chính sách

Ngày chốt: 19/09/2026. Thực thi/kiểm thử bắt đầu 18/09/2026.

## Kết quả

- Sửa nội dung mặc định trên home/about/products/product_detail/contact:
  bỏ ISO 27001, NDA tuyệt đối, CO/CQ toàn bộ, bảo hành 12–24 tháng mặc định,
  đổi trả 30 ngày mặc định, VAT tức thì/đã gồm, SLA 15–30 phút và số marketing
  không có nguồn đo. Khối số liệu chuyển thành thông tin sử dụng nền tảng.
- Email liên hệ xác nhận tiếp nhận và yêu cầu xác nhận thời gian xử lý;
  không hứa 24 giờ. Không đổi hạn 24 giờ xác minh tài khoản.
- Giữ markup/style/animation, nội dung sản phẩm nhập trong DB, giá/tổng tiền,
  người nhận, outbox/dedup/retry và các snapshot cũ.
- File Gemini là bản dò nguồn, không phải chính sách được duyệt. SOP tài chính
  ghi ký quỹ 10%, không chứng minh VAT 10%; SOP change management không chứng
  minh ISO. Xem POLICY_PUBLICATION_REVIEW.md.

## Kiểm chứng

```powershell
python manage.py test tests.test_public_policy_copy tests.test_customer_email_policy_boundary --settings=config.settings_evidence_test --noinput -v 1
python manage.py test tests.test_google_oauth_and_email_notifications --settings=config.settings_evidence_test --noinput -v 1
python manage.py check
python manage.py makemigrations --check --dry-run
```

- 5 tests / 0.516s OK trên nội dung cuối (lần trước 1.306s, không cộng lặp).
- 14 tests / 101.907s OK. Tổng 19 test khác nhau; thêm 3 test mới trong
  test_public_policy_copy.py; cập nhật assertion contact cho hành vi mới.
- Django check không lỗi; migration: No changes detected.
- Diff check các file sửa qua. Diff check toàn cây còn whitespace của thay đổi
  sẵn có tại static/css/public_pages.css:1168,1222; không sửa ngoài phạm vi.
- Browser local /gioi-thieu/ HTTP 200, thấy các điều kiện mới và khối giới thiệu
  thay số liệu. Sau restart đã xác nhận câu chữ cuối trong accessibility tree
  và chụp màn hình. Preview hẹp có tràn ngang; chưa sửa CSS của agent khác,
  không chứng nhận responsive, mọi trang hay production từ kiểm tra này.
- OAuth HTTP mock và email test backend: không là bằng chứng OAuth/inbox thật.

## Còn lại và thông tin cần cung cấp

- Bản chính sách được chủ sở hữu duyệt, phạm vi và ngày hiệu lực nếu muốn công bố
  bảo hành/đổi trả/SLA/VAT cụ thể. Bản tóm tắt AI và template không thay thế được.
- Xác nhận ABC/XYZ và các SOP là mô hình đồ án hay chính sách doanh nghiệp thực;
  trong lúc chờ chỉ sử dụng như nguồn nội bộ chưa xác minh, không công bố cam kết.
- Quyền kỹ thuật viên: có được xem giá/chi phí không? Chưa thay quyền khi chưa chốt.
- Các mô tả trong catalog, thông tin liên hệ mẫu, nội dung ở các trang khác và
  toàn bộ seed/SOP vẫn cần rà; không báo mục 43–46 hoàn tất toàn hệ thống.
- Không migration dữ liệu, gửi mail thật, push, deploy hoặc backup/restore.

Tiến độ giữ 51/97 = 52,6%; không tăng bằng cách đếm test hoặc số file.
