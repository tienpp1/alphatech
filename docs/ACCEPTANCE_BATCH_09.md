# Đợt 9 — Nghiệm thu theo kết quả, không theo số lần sửa

Ngày: 15/09/2026. Phạm vi: checklist gốc 97 mục; môi trường PostgreSQL/PostGIS local cô lập, không nghiệm thu production.

## Bằng chứng và tiêu chí đóng

| Mục | Tiêu chí | Bằng chứng |
|---|---|---|
| 61 | Khuyến nghị → chấp thuận → người khác duyệt → thực thi → dữ liệu → audit | `test_actionable_recommendation_acceptance_creates_one_approval`: API thật trong Django test client, hai user không phải superuser, membership và quyền tùy chỉnh; chấp thuận chưa đổi ticket; tự duyệt bị từ chối; người khác duyệt đổi trạng thái/người nhận; audit đúng actor/workspace/entity; replay chỉ một execution. |
| 65 | Phân biệt tư vấn với thực thi | Khuyến nghị không có `proposed_action` chỉ chuyển ACCEPTED, không tạo ApprovalRequest; khuyến nghị có action đi qua registry/schema/permission và hàng đợi duyệt, không tự thực thi. Trường action/parameters/approval chỉ đọc trong serializer. |
| 66 | Không tự động map reorder/workload | Rà `recommendations/rules.py`: chỉ rule gần kỹ thuật viên gán dispatch. Test riêng sinh cảnh báo quá tải từ 3 Task thật và cảnh báo hết hàng từ đầu ra predictor kiểm soát: không gán action/không tạo approval. Test stockout là kiểm chứng mapping, không phải độ chính xác mô hình. |
| 75 | Thông báo đúng người/thời điểm, không phát vô hạn | 6 test `test_customer_approval_notices`: chưa duyệt không phát, lưu lặp chỉ một, service ASSIGNED→IN_PROGRESS không lặp, rollback không lưu thông báo, hủy đơn không trả thông báo, người khác/anonymous/CSRF bị chặn, ack xong feed rỗng. Rà JS có tập shown theo phiên trang và ack server; chưa kiểm tra hình ảnh animation trên production. |
| 76 | Đăng ký trùng, hết hạn, replay, khác thiết bị | 14 test registration hiện có, nhóm OAuth/email mô phỏng, thêm regression gửi lại mã giữa bước lookup/consume; link được kiểm tra lại dưới khóa User. Test client riêng mô phỏng máy tính/điện thoại, không phải xác nhận trên hai thiết bị thật. |

## Sửa lỗi thực tế

Trước đây view xác minh link kiểm tra chữ ký/phiên mã trước khi khóa user; gửi lại mã xen giữa lookup và consume có thể khiến link cũ tiêu thụ challenge mới. `consume_registration_link(user, token)` kiểm tra lại token dưới cùng khóa User mà resend sử dụng. Không thay route, schema, thời hạn hay quyền khách hàng. Test mô phỏng chính xác thứ tự xen kẽ; không gọi đó là kiểm thử tải đồng thời.

## Kiểm thử

1. `python manage.py test tests.test_recommendations tests.test_customer_approval_notices tests.test_registration_codes tests.test_customer_email_outbox_and_oauth_security --settings=config.settings_evidence_test --keepdb --noinput` — **48 passed, 225.698s**.
2. `python manage.py test tests.test_registration_codes.RegistrationCodeTests.test_resend_between_link_lookup_and_consume_rejects_stale_link tests.test_registration_codes.RegistrationCodeTests.test_email_link_activates_on_phone_and_original_session_can_poll --settings=config.settings_evidence_test --keepdb --noinput` — **2 passed, 19.447s**, sau bản vá.
3. Hai ca overload/stockout được chạy riêng sau khi bổ sung; kết quả ghi trong CURRENT_STATUS.
4. Django check: 0 issues; migration drift: no changes. Log RuntimeError/CSRF/OAuth denial trong bộ test là ca lỗi cố ý, không bị ẩn hoặc bỏ assertion.

Không cộng 48+2 thành số ca độc lập vì có chạy lại ca khác thiết bị. SMTP dùng outbox/mocks; Google HTTP mock. Không dùng log “accepted” để chứng minh inbox thật.

## Ranh giới và việc tiếp theo

- Mục 74 chỉ một phần: đã kiểm tra email thất bại/retry/ownership và đăng ký còn tồn tại, chưa chứng minh đầy đủ checkout/service failure và chống gửi trùng khi server chết sau SMTP accept.
- Mục 67 vẫn một phần; tạm ngừng mở rộng audit để ưu tiên các mục kiểm chứng được thành nhóm.
- Ưu tiên tiếp: 72–74 (ownership/stock/email nghiệp vụ), 50–55/58 (GIS định lượng), 22–28/35–41 (bằng chứng AI); cuối cùng tài liệu Word/IEEE cần nguồn và bản nộp hiện hành.
- 56–57/90–97 cần môi trường/provider/thiết bị hoặc xác nhận thật; giữ riêng. Restore vẫn hoãn. Không truy cập/đổi secrets, reset dữ liệu, push hoặc deploy trong đợt này.
