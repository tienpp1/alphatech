# RAG IND — thực thi và repair ngày 05/10

Nguồn câu hỏi có sẵn: apps/knowledge/independent_benchmark.py, năm ID khác tập
router chính. Không có bằng chứng ai soạn độc lập; sau khi dùng để repair đây
không còn là holdout mù. Không gọi kết quả này chất lượng Gemini thật.

Test tạo hai workspace, actor không superuser có đúng permissions, một đơn
completed 15 triệu và một phiếu OPEN quá hạn. Policy synthetic: bảo hành24 tháng,
đổi1đổi1 trong30 ngày lỗi kỹ thuật. Provider network bị chặn; business DB không
đụng tới. Không nâng role/quyền để che chọn sai tool.

## Failure được giữ

- Lần tạo fixture đầu lỗi NOT NULL order_timestamp; thêm đúng trường theo model.
  Nhóm11 tests:1 error, không coi pass; test DB riêng đã được hủy.
- Output trước repair: output/evidence_tests/d8cefa934632407b/independent_rag/report.json.
  IND-OOD-01 gọi forecast sai domain rồi trả warranty SOP; IND-DATA-01 chọn stock
  tool bị thiếu permission và fallback sai. Proxy3/5 không phải semantic3/5.

## Repair và quan sát sau sửa

External market không retrieval/tool workspace; technical-request phrasing dùng
get_service_ticket_summary. Permission/domain models không thay đổi. Không sửa
expected question để biến kết quả cũ thành đúng.

Output sau sửa: output/evidence_tests/3e84be9a084e47f9/independent_rag/report.json.
Đủ5 output, doc24mo/30day; hybrid15m+policy có tool/citation; service1phiếu/
1overdue; hai unsupported từ chối. Các quan sát này không tự là điểm người chấm.
Nhóm83 tests/109.188s OK trước bổ sung assertion/variant cuối; full release
tiếp theo ghi log riêng, không cộng83 vào số full-suite.

Phiếu: output/rag_review_independent_20261005/review.md và review.json. Gồm đủ
output/nguồn/tool/reference và report fingerprint; reviewed0, unreviewed5,
pass rate null. Chỉ người dùng/reviewer điền true/false và lý do/thời điểm.
Sửa nội dung report sau khi chấm sẽ làm fingerprint không khớp.

## Human Evaluation được nhận sau đó

Chủ dự án đã sửa trực tiếp review.md và xác nhận qua chat: cả5 ID ĐẠT bốn tiêu
chí được hỏi. Mỗi dòng có lý do và thời điểm2026-10-05 09:40 (Asia/Bangkok).
Agent chuyển nguyên nhận xét và đánh giá được xác nhận sang review.json,
không tự chấm; bản blank giữ ở review.initial.json. human_summary.json được
tính bằng công cụ fingerprint hiện có; đây là kết quả người dùng báo cáo,
không xác thực danh tính reviewer bên ngoài hoặc chất lượng provider live.
User ghi tool/API trong phiếu; harness thực tế gọi service/ORM offline, không
thực hiện live HTTP/API. Không suy rộng kết luận không ảo giác ngoài5 mẫu này.

Full staged tree c80048022ab604cb3a807dee49b5f77a0fecb532:
1201 tests/414.870s OK, không failure/error/skip. Log
output/policy_release_jx0ekuc9/tests.log. Đây là full tree trước bổ sung hồ sơ
Human Evaluation và workflow mới; không đổi source ứng dụng/test sau run.
check0issues, migration drift No changes detected. Known-pattern scan806files/
0findings, không chứng nhận rotation hoặc mọi loại secret.

human_summary_verified.json xác nhận5reviewed/5PASS/0unreviewed, fingerprint
4719c5f77e99b54a95ac8d20e31da755434bf575aba8f2941ca78383b6641939.
Lệnh CLI đầu ghi summary xong nhưng stdout Windows cp1252 lỗi UnicodeEncodeError;
giữ file đầu và chạy lại -Xutf8 với exporter telemetry tắt, đích mới exit0.

Quyền denied trong bộ adversarial là kiểm security, không đưa vào mẫu số semantic.
Mẫu conflict12/24 được user chấm trước vẫn giữ nguồn Human Evaluation riêng;
không chuyển điểm đó sang bất kỳ answer mới chỉ vì tên case giống nhau.
