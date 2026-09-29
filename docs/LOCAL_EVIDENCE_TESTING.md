# Đợt 4 — Kiểm chứng bằng PostgreSQL cô lập

## Cách chạy

Từ 17/09/2026: bỏ `--keepdb` cho lượt chạy thông thường để Django thu hồi database
mới của chính lượt test sau khi kết thúc. Chỉ thêm cờ này khi cần giữ DB điều tra;
tên ngẫu nhiên khiến mỗi lượt vẫn tạo DB khác. Không xóa DB cũ khi chưa được duyệt.

```powershell
python manage.py test tests.test_rag_evaluation tests.test_approvals tests.test_approval_state_integrity tests.test_public_copilot_and_cart_api --settings=config.settings_evidence_test --noinput -v 1
python manage.py test tests.test_rag_evaluation tests.test_audit_database_evidence --settings=config.settings_evidence_test --noinput -v 1
```

Cấu hình này chỉ dùng cho `test`, không dùng chạy web, shell hoặc migration thủ công. Nó bỏ qua `DATABASE_URL` và chỉ cho phép loopback PostgreSQL. Dùng các trường DB_HOST/PORT/USER/PASSWORD local trong `.env`; nếu cần tách riêng, cung cấp EVIDENCE_DB_HOST/PORT/USER/PASSWORD trong môi trường máy, không gửi password vào chat.

Mỗi tiến trình tạo database mới tên `test_alphatech_evidence_<random>`. `--keepdb` giữ database sau kiểm thử, **không có nghĩa lần sau sẽ dùng lại cùng DB**. Các database được giữ sẽ chiếm dung lượng; chỉ dọn sau khi xác minh đúng tên và không còn cần bằng chứng. Không có lệnh tự xóa database trong thay đổi này.

API AI tắt, email dùng memory backend, telemetry tắt trước khi base settings khởi tạo. Media và JSON benchmark lưu trong `output/evidence_tests/<run-id>/`. Test dùng dữ liệu dựng sẵn; không sao chép dữ liệu khách hàng. Quyền PostgreSQL local phải đủ để tạo test DB và cài extension mà migrations yêu cầu. Không tự cài package hoặc thay quyền DB toàn cục.

## Kết quả ngày 14/09/2026

| Nhóm | Kết quả | Phạm vi bằng chứng |
|---|---|---|
| RAG + approval workflow/state + public API/cart | 32/32 qua, 78.204 giây | DB test `06c5066e0b4148c1` |
| RAG + audit SQL | 3/3 qua, 6.466 giây | DB test `735e6c0bcea3412a` |
| Django check | 0 lỗi | Cấu hình/mã hiện tại |
| Migration drift | Không thay đổi | Không tạo migration mới |

Đây là 35 lượt chạy test, có **1 test RAG chạy lặp**, không phải 35 test riêng biệt.

Approval kiểm tra approved/rejected, replay, self-approval denial, unique key ở database, payload không được đổi với cùng key, từ chối truy cập kết quả không có quyền, tham số không hợp lệ, stock transfer thực thi/replay/compensation. Chưa đo cạnh tranh giữa nhiều tiến trình. Audit kiểm tra SQL UPDATE và DELETE bị trigger từ chối và bản ghi còn nguyên; chưa đo tính đầy đủ của mọi sự kiện hay khả năng chống tài khoản DB có quyền tắt trigger.

## RAG: kết quả có giới hạn

File: `output/evidence_tests/735e6c0bcea3412a/rag_benchmark.json`.

- 4 câu tài liệu, 2 câu dữ liệu, 1 hybrid, 3 ngoài phạm vi trên workspace Retail test.
- Lexical/evidence pass: 7/7; từ chối đúng: 3/3; từ chối sai: 0. Precision/recall từ chối: 100%.
- Tên nguồn/tool yêu cầu đều có; không đồng nghĩa mọi phát biểu được nguồn hỗ trợ.
- API key bị tắt trong test: chỉ chứng minh đường offline/deterministic trên fixture. Trường generation_mode của scorer vẫn UNKNOWN vì runtime chưa cung cấp provenance; metadata môi trường ghi rõ offline, không giả mạo LIVE.
- Semantic correctness vẫn null. Bộ câu hỏi nhỏ và fixture khớp rubric không phải tập đánh giá độc lập, không được ghi “AI chính xác 100%” trong báo cáo.

## Việc tiếp theo

1. Tạo tập đánh giá độc lập cho Retail và Service, gồm câu diễn đạt khác, phủ định, thiếu dữ liệu, dữ liệu mâu thuẫn và workspace isolation. Chốt đáp án/nguồn chuẩn trước khi chạy.
2. Thêm bằng chứng cạnh tranh/phê duyệt đồng thời và rollback lỗi thực thi; giữ mọi failure.
3. Ghi provenance embedding/synthesis và đánh giá ngữ nghĩa bởi người rà soát trước benchmark API thật.
4. Rà phần marketing/seed còn chưa xác minh. Full suite và production vẫn là đợt riêng; chưa push/deploy trong đợt này.
