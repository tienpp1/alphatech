# Đợt 37 — khóa phạm vi và đối chiếu yêu cầu

## Kết quả

Đóng 2/4/5: 48 → 51/97 (52,6%); 28 một phần, 18 chưa xác nhận. Đây là ba
quyết định phạm vi/tài liệu, không phải ba tính năng mới hoặc chứng nhận Word.

- Scope 12 nhóm bắt buộc, mở rộng và giới hạn đã được ghi cụ thể.
- Ma trận nhóm yêu cầu → file code → test → batch/thiếu đã có và kiểm đường dẫn.
- Cổng đóng các cụm còn mở ghi điều kiện và phụ thuộc, không rà lại toàn hệ thống.
- Bỏ V1 “hoàn thành trọn vẹn”, kết luận bài đã hoàn chỉnh, so sánh deep learning
  thiếu chứng cứ và claim threshold/fallback cố định trong scope/defense.
- README dùng tên đề tài người dùng đã chốt; không suy ra tất cả Word đã đồng bộ.

## Phát hiện không được bỏ qua

Thầy yêu cầu chat realtime và bản tin nội bộ. Tìm kiếm models/routes/config/tests
không thấy entity/transport tương ứng. `apps/knowledge/models.py` chứa hội thoại
AI; `apps/notifications/models.py` chứa thông báo sự kiện cho từng recipient.
Hai thứ này không chứng minh chat nhân viên/bản tin. Không bỏ yêu cầu hoặc tự
thêm mục để thay đổi mẫu số 97. Cần thiết kế và triển khai trước nghiệm thu đồ án.

File Downloads trùng tên `1. Chốt phạm vi nghiệp vụ (Phân tíc.txt` nay là báo cáo
UI của agent khác ngày 17/09, khác nội dung đối chiếu ngày 15/09. Chỉ dùng làm
đầu vào cần tái hiện, không coi nhận định nguyên nhân lỗi 500 là chẩn đoán đã chứng minh.

## Bằng chứng và giới hạn

- Đã đối chiếu `config/urls.py`, workspace middleware, Knowledge và Notification
  models; rà các hướng dẫn phạm vi/bảo vệ và file source/test trong ma trận.
- `python -m unittest tests.test_academic_scope_contract -v`: 3 tests OK, 0.018s.
  Chỉ kiểm tài liệu đủ 12 mã, không mất TEAM_CHAT/BULLETIN, liên kết/paths tồn tại.
  Không đánh đồng đây là kiểm thử chức năng của 12 nhóm.
- Diff whitespace của README/scope qua. Không thay runtime, schema, database;
  không cần chạy lại 61 regression backend đợt trước cho thay đổi Markdown.
- Không sửa Word/PDF hoặc UI: không dùng documents/browser hình thức; chưa đóng
  1/3/6/81/89. Không push/deploy dirty worktree của các agent khác.

## Thứ tự tiếp

1. Đối chiếu bản Word/comment cuối để khóa use case chat/bản tin, phụ lục và lịch.
2. Rà chính sách và tài liệu seed/công khai; không biến SOP demo thành cam kết thật.
3. Triển khai thiếu sót bắt buộc theo scope, song song về kế hoạch với hồ sơ thực
   nghiệm; không tiếp tục thêm model/tính năng mở rộng ngoài đồ án.
4. Gom live gates khi website/browser/credentials khả dụng; backup vẫn hoãn.
