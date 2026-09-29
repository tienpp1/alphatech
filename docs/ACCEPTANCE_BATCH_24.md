# Đợt 24 — Phân biệt mô phỏng với quan sát thực tế

## Kết quả

Đóng mục 49 trong phạm vi ba kịch bản what-if hiện có: doanh thu, số ticket,
và cạn tồn kho. Câu trả lời chứa tool mô phỏng dùng bộ tổng hợp xác định,
kể cả khi có LLM key hoặc kèm tool khác. Nhãn, giả định và công thức không
giao cho LLM viết lại. Các câu hỏi không có tool mô phỏng giữ luồng cũ.

Nhu cầu 2 sản phẩm/ngày được ghi rõ là giả định cố định, không phải lịch sử
bán hàng hoặc kết quả mô hình. Trường hợp không có kỹ thuật viên không còn
được thay bằng một người; tải mỗi người trả null và giải thích thiếu dữ liệu.

## Kiểm thử

```text
python manage.py test tests.test_simulation_evidence tests.test_rag_grounding_assistant --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

9/9 đạt trong 44.842 giây, gồm 4 test mới và 5 test grounding hiện có.
Test mới kiểm tra nhãn cả ba kịch bản, không gọi provider khi có key placeholder,
giả định tồn kho, số nhân sự bằng 0 và denial khi dùng workspace khác.
User test là member có permission, không dùng superuser để bỏ qua RBAC.

- `python manage.py check`: no issues (0 silenced).
- `python manage.py makemigrations --check --dry-run`: No changes detected.
- `git diff --check` hai file source: exit 0.

## Giới hạn

Không đánh giá LLM thật, không khẳng định dự báo chính xác, không sửa các failure
AI demonstration đã biết. Chưa kiểm thử trực quan browser hoặc production;
đây là thay đổi tầng tool/synthesis, không phải thiết kế giao diện.
Không push/deploy trong đợt này. Không thay đổi dữ liệu nghiệp vụ hay migration.
Các giả định toán học vẫn là kịch bản đơn giản, không thay thế mô hình nhu cầu.

Tiến độ: 37 đóng / 29 một phần / 31 chưa xác nhận, tương đương 38,1% mục đóng.
