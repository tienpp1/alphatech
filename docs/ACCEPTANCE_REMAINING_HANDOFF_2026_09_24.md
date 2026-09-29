# 21 mục còn mở sau gói dự báo 24/09/2026

Nguồn trạng thái duy nhất: CHECKLIST_97_PROGRESS.md, 76/97 tạm ghi nhận,
không phải chứng nhận độc lập. Đợt này đóng thêm 26; không đóng 83/84 toàn bộ
chỉ nhờ một bộ dữ liệu tổng hợp. Các tiến bộ một phần được giữ riêng.

## Ưu tiên tiếp theo không cần thông tin bí mật

1. **7, 11, 13, 82, 89:** đối chiếu toàn bộ tài liệu nộp/slide/Word và sơ đồ
   với code; tiếp tục loại bỏ lời khẳng định tuyệt đối và xác minh nguồn IEEE.
   Đã sửa runtime RAG vs offline scoring, ERD role-permission nhiều-nhiều,
   membership.role nullable, dải RMSE và phạm vi tái lập ở hồ sơ chính.
2. **81:** khép ma trận yêu cầu → route → quyền → test → artifact; cập nhật
   bản tin đã có code/test nhưng còn đối chiếu toàn bộ use case và visual QA.
3. **39, 83, 84:** bổ sung bộ RAG/approval cố định và kết quả theo từng ca,
   đánh giá đủ ý/ngữ nghĩa độc lập. Gói doanh thu mới đã có snapshot/model/CSV
   prediction/bounds và replay; không dùng nó thay evidence của RAG/approval.
4. **85:** chạy lại các nhóm còn lỗi trên fingerprint thống nhất rồi full suite;
   giữ log lần 1.067 test FAILED. Không cộng các rerun để giả lập full suite xanh.
5. **97:** kiểm toán secret trong diff/release, báo vị trí đã che giá trị;
   xác nhận rotate cũ không chứng minh mọi file mới đều an toàn.

## Cần dữ liệu hoặc bằng chứng bên ngoài

- **46:** văn bản chính sách được người có thẩm quyền duyệt; bản Gemini tổng
  hợp source không thay được văn bản. Chưa công bố cam kết đổi trả/SLA/ISO mới.
- **56:** browser tìm địa chỉ công khai qua ứng dụng và nhận kết quả thật.
  Lần thử này: local 8018 không chạy, Render vẫn application-loading; chưa
  tiếp cận được form tìm kiếm, chưa gửi truy vấn địa chỉ.
- **57:** chủ thiết bị kiểm tra GPS thật, quyền vị trí và sai số; không giả lập
  tọa độ rồi coi đó là vị trí thật. Chưa bấm cấp quyền vị trí trong đợt này.
- **90, 91, 92, 93, 94, 95:** release SHA/deploy, từng email nghiệp vụ, worker
  restart/recovery, CI run, Sentry event và HTTPS/cookie/CSP trên đúng bản chạy.
  CI đã có source nhưng chưa run hiện tại; Sentry chưa có live DSN theo user.
- **96:** giữ hoãn pg_dump → pg_restore theo yêu cầu; không đụng database chạy.

Không yêu cầu gửi password, API key hoặc DSN vào chat. Các mục local ở trên
vẫn còn công việc thực hiện, không được diễn giải rằng cả 21 mục đều chỉ bị
chặn bởi hạ tầng hoặc người dùng.
