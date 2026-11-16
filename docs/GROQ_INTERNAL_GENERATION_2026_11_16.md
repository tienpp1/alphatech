# Groq cho AI nội bộ — 16/11/2026

## Phạm vi

Groq chỉ tổng hợp câu trả lời cuối từ nguồn RAG và số liệu công cụ đã được
cho phép. Không thay thuật toán dự báo, embedding, quyền, workspace, database,
phê duyệt, audit hay97mục. Chatbot khách hàng vẫn dùng hệ thống công khai cũ.
Đây không phải sử dụng quota ChatGPT Plus hoặc fine-tuning/training model.

## Cấu hình

```dotenv
LLM_GENERATION_PROVIDER=groq
GROQ_MODEL=openai/gpt-oss-120b
GROQ_API_KEY=<lưu riêng, không commit hoặc gửi chat>
```

Không thay LLM_API_KEY/LLM_PROVIDER/EMBEDDING_MODEL để bật chat Groq; những biến
đó vẫn quyết định không gian embedding/retrieval cũ. Mặc định selector là
gemini để tương thích hệ thống cũ. Đổi selector cần restart tiến trình server.
Để tắt Groq, bỏ selector hoặc đặt lại gemini; giữ nguyên key embedding cũ.
Không có migration, re-index hoặc import dữ liệu phải chạy cho thay đổi này.

Chủ dự án xác nhận đã bật ZDR cho chat inference trong phiên16/11. Đây là
xác nhận của người vận hành, không phải agent đã tự kiểm tra dashboard Groq.
ZDR không có nghĩa dữ liệu không được xử lý bởi nhà cung cấp, hoặc mọi nội dung
đều phù hợp để gửi. Chỉ dùng ngữ cảnh đã rà soát, không bí mật/không chứa PII.

## Hành vi

- Không có ngữ cảnh: không gọi model, giữ NO_CONTEXT/NO_EVIDENCE.
- What-if/simulation: deterministic, không dùng model viết lại giả định.
- Câu có nguồn và ngữ cảnh phù hợp: một HTTPS call tới api.groq.com, timeout12s.
- Model cố định openai/gpt-oss-120b, max_completion_tokens1024, reasoning thấp;
  không hiển thị reasoning hoặc chạy tool do model tự yêu cầu.
- Prompt quá8000ký tự, credential/field cá nhân nhận diện được: deterministic.
-429, timeout, lỗi, dữ liệu phản hồi quá64KiB/không hoàn chỉnh: deterministic.
- Không retry ngầm, không gửi sang provider thứ hai, không tự nâng gói trả phí.
- Không ghi key, body provider, prompt hoặc exception có thể chứa secret vào log.

Các nhãn email/điện thoại/personnel/credential được kiểm ở cấu trúc và prompt
hoàn chỉnh; có test cho DB_PASSWORD, GROQ_API_KEY, AWS_SECRET_ACCESS_KEY.
Đây là heuristic bổ sung, không phát hiện được mọi tên người/địa chỉ trong văn
xuôi. Không được tuyên bố100%khôngPII hoặc câu trả lời luôn đúng.

## Bằng chứng và giới hạn

Log ở output/groq_generation_20261116/ trên máy triển khai thử nghiệm:

- Baseline17tests; RED feature12tests/10fail, rồi focused36/36 đạt.
- Focused sau rà soát55/55 đạt6,077s; workspace chính49/49 đạt3,723s.
- Full đầu1613/500,344s đạt, thu thập trước regression credential cuối.
- Full cuối1614/432,310s OK trên worktree phát hành sau regression sửa cuối;
  TEST DB riêng tự hủy. Không gọi đây là full trên workspace chính bẩn.
- Live3attempts:1fallback403 trước khi thêm User-Agent;2LLM_RESPONSE sau sửa.
  Synthetic doanh thu1.230.000VND/3đơn/2hoàn tất được trả đúng số; synthetic
  bảo hành12/24tháng được nêu mâu thuẫn và dẫn cả2nguồn.
- Không gửi dữ liệu nghiệp vụ thật.2câu thành công không phải benchmark tổng
  quát hay nghiệm thu mọi câu hỏi. Không xác nhận bằng chứng Inbox/GPS/Sentry mới.
- Module Groq Bandit0findings, scan888files0known-secret findings. Không
  xóa/làm yếu assertion, skip hoặc thay ledger97.
- Selector local đã bật và xác minh settings; server đang chạy cần restart
  để nạp cấu hình. Chưa push/deploy hoặc thay Render Environment.

## Render và bước tiếp theo

Code và selector local không tự đồng bộ lên Render. Triển khai sau cần push
đúng commit đã kiểm, lưu GROQ_API_KEY riêng trong Render Environment cùng
hai biến không bí mật ở trên, deploy/restart rồi UAT bằng câu khôngPII.
Không sao chép .env lên GitHub. Giữ gói Free, không tự bật billing/nâng cấp.
Không coi khóa model cố định là cam kết miễn phí nếu người vận hành đổi gói.

Nguồn vận hành: https://console.groq.com/docs/rate-limits,
https://console.groq.com/docs/your-data,
https://console.groq.com/docs/api-reference.
