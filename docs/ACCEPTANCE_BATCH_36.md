# Đợt 36 — ba nhóm thay đổi và một kiểm chứng live bị chặn

Ngày 18/09/2026. Giữ nguyên dirty worktree; không commit/push/deploy, không sửa
database nghiệp vụ hoặc cấp thêm quyền kỹ thuật viên.

## 1. Checkout và tồn kho đồng thời

- Product locks trong checkout sắp theo PK để nhất quán thứ tự khi giỏ đảo dòng.
- Sáu test mới chạy trên PostgreSQL với các connection riêng, xác nhận backend PID
  khác nhau, barrier khởi chạy và timeout khóa/query có giới hạn.
- Hai giao tận nhà, hai nhận tại cửa hàng, hoặc hai hình thức cùng tranh sản phẩm
  cuối: đúng một order/ORDER_CREATED, một người bị từ chối, tồn còn 0.
- Hai giỏ hai sản phẩm theo thứ tự ngược nhau: một order đủ hai dòng, tồn cả hai
  về 0, không deadlock trong ca kiểm thử.
- Hai hủy cùng lúc: một chuyển trạng thái, một bị từ chối, hoàn tồn đúng một lần.
- Tiêm lỗi tạo OrderItem sau giữ hàng: lỗi được nhận diện, order và giữ hàng rollback.
  Log `RuntimeError: fixture failure` là lỗi tiêm có chủ đích, không test failure.

Đây không phải stress test mọi mức tải. Legacy delivery không được bật strict
tự động; cấu hình/migration production chưa kiểm chứng. Mục 73 vẫn một phần.

## 2. RAG: không so sánh vector thuộc không gian khác nhau

- Chặn mode/provider/model/dimension đã biết không khớp; cả khi số chiều giống nhau.
- Chặn khác độ dài trước tính cosine, tránh ngưỡng 0 nhận một vector không hợp lệ.
- Metadata ghi số vector bị loại và số vector legacy chưa rõ nguồn được xét.
- Dữ liệu cũ giữ UNKNOWN và hành vi tìm kiếm tương thích; không tự re-embed.
- Sáu test mới gồm cùng model, khác model/provider, provider-vs-hash hai chiều,
  khác dimension và legacy. Không phải đánh giá độ đúng ngữ nghĩa.

Giới hạn: legacy chưa biết model vẫn có thể thuộc không gian không tương thích;
cần kế hoạch re-index riêng. Ca nội dung tài liệu mâu thuẫn vẫn chưa được sửa.

## 3. Tài liệu học thuật

- Bỏ claim XGBoost vượt trội; ghi đúng revenue/ticket kém baseline và R² âm.
- Bỏ bảo đảm LLM an toàn 100% và claim GIS sai số thực địa dưới 1% chưa có phép đo.
- Đồng bộ tên đề tài trong ba tài liệu, làm rõ không phải ERP/WMS đầy đủ.
- Làm rõ ví dụ LST/LSTM/GRU/Transformer của thầy không bắt buộc thêm model.
- Bản nháp chương 1/2 yêu cầu IEEE; đánh dấu bảng đối thủ chưa kiểm chứng, không
  biến bảng đó thành nghiên cứu liên quan đã được xác nhận. Không sửa file Word.

## Validation chính xác

```text
python manage.py test tests.test_checkout_concurrency tests.test_home_delivery_fulfillment tests.test_public_ecommerce_cart_and_checkout --settings=config.settings_evidence_test --noinput -v 1
39 tests, 138.155s, OK

python manage.py test tests.test_embedding_space_isolation tests.test_embedding_provenance tests.test_adversarial_rag_execution tests.test_rag_retrieval tests.test_rag_grounding_assistant --settings=config.settings_evidence_test --noinput -v 1
22 tests, 15.692s, OK
```

61 test riêng biệt trong hai nhóm cuối. Lượt đầu 17 checkout tests OK (10.301s)
trùng ca với nhóm cuối nên không cộng. Các database test mới được hủy sau chạy.
`manage.py check`: no issues; `makemigrations --check --dry-run`: no changes.
Không chạy full suite; email test dùng locmem, không phải inbox thật.

## Kiểm chứng live chưa đạt

- Đã đọc skill computer-use; công cụ browser không khởi tạo được do thiếu đường
  dẫn kernel assets (`os error 3`), chưa có ảnh kiểm chứng.
- HTTP thử trong sandbox bị proxy chặn. Sau escalation, GET trang `/chi-nhanh/`
  production timeout sau 45 giây; chưa tới bước POST tìm địa điểm.
- Không kết luận Nominatim hỏng từ timeout trang; không đánh dấu mục 56 hoàn tất.

## Tiến độ

48/97 đóng (49,5%), 28 một phần, 21 chưa xác nhận. Đợt này thu hẹp phần còn thiếu
và sửa lỗi thật, không chứng nhận trọn các mục còn phụ thuộc deployment/Word.
Đang chờ user chốt quyền kỹ thuật viên và quyền xem chi phí trước nhóm nghiệp vụ đó.
