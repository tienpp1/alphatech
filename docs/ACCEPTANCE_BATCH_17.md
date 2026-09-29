# Đợt 17 — Hiệu chỉnh kết luận trong báo cáo học thuật

Ngày đối chiếu: 15/09/2026.

## Mục tiêu

Loại bỏ các kết luận tuyệt đối còn xuất hiện trong báo cáo đánh giá học thuật
hiện hành khi bảng số liệu và bằng chứng chưa hỗ trợ chúng. Giữ nguyên số liệu
lịch sử để truy vết, nhưng tách rõ số liệu, diễn giải và giới hạn nghiệm thu.

## Đã hiệu chỉnh

- XGBoost: nhận xét nay phản ánh kết quả không đồng nhất; revenue/ticket từng
  kém baseline và R² âm, không còn câu “vượt trội” hay “giải thích phần lớn”.
- RAG: đổi “Zero Hallucination”, “luôn”, “tuyệt đối” thành mô tả theo ca đã
  kiểm thử; ghi rõ heuristic không chứng minh semantic correctness.
- GIS: giữ sai số của hai cặp minh họa nhưng không gọi là PostGIS đúng 100% hay
  chứng minh SLA thực địa.
- Approval/audit: bỏ 100% và “Xuất sắc”; thay bằng phạm vi action đã đo và
  trạng thái chưa kết luận tỷ lệ toàn hệ thống.
- Bảng tổng hợp bảy mục đổi từ “Hoàn thành 100%” sang trạng thái triển khai,
  nghiệm thu giới hạn và các phần còn thiếu.

## Kiểm tra

```powershell
rg -n "100%|Hoàn thành|hoàn thành|vượt trội|đúng 100|an toàn tuyệt đối|không ảo giác|không rò rỉ" docs/ACADEMIC_EVALUATION_REPORT.md
git diff --check
```

Các cụm còn lại trong file báo cáo chỉ nằm trong phần đính chính lịch sử hoặc
giải thích metric (ví dụ 100% là giá trị MAPE/fallback cũ), không còn được dùng
làm kết luận nghiệm thu hiện hành. `git diff --check` không có lỗi whitespace.

## Tác động checklist

Mục 7 và 11 được củng cố nhưng vẫn **Một phần** vì các tài liệu cũ, marketing
và dữ liệu mẫu chưa được rà toàn bộ. Không tăng số mục đóng; tổng conservative
giữ **35 đóng / 29 một phần / 33 chưa xác nhận** (35/97 = 36,1%).

Không có thay đổi code runtime, migration, database, secret, push hoặc deploy.
