# Demo khi mạng hoặc API bên ngoài lỗi

Phạm vi: phiên bản có generation_metadata trong AI chat. Dữ liệu demo phải nằm
trong database riêng đã chuẩn bị; không seed/reset database đang vận hành.

## Chuẩn bị

1. Dùng bản code đã nghiệm thu và database demo riêng. Chạy `python manage.py
   check` và `python manage.py showmigrations --plan` để xem trạng thái.
2. Đăng nhập sẵn bằng tài khoản local có membership/quyền phù hợp. Google OAuth
   cần Internet; không dùng nó làm cách đăng nhập duy nhất trong buổi demo.
3. Chuẩn bị một truy vấn có số liệu (ví dụ tổng doanh thu workspace) và một câu
   hỏi tài liệu đã được nạp/kiểm tra. Embedding có thể cần provider tùy cấu hình;
   nếu truy xuất lỗi thì chuyển sang câu hỏi số liệu, không gọi đó là RAG thành công.
4. Chỉ tại môi trường demo, đặt `LLM_API_KEY` rỗng và khởi động lại để diễn tập
   trả lời theo quy tắc. Giữ bản cấu hình ban đầu tại nơi bảo mật để phục hồi.

## Thao tác và lời trình bày

| Tình huống | Thực hiện | Bằng chứng và cách diễn giải |
|---|---|---|
| Chưa cấu hình LLM | Hỏi doanh thu/ticket từ dữ liệu demo | Nhãn “Chế độ trả lời theo quy tắc”; metadata DETERMINISTIC/NO_API_KEY. Đây là tổng hợp dữ liệu, không dùng để đo năng lực Gemini. |
| Provider timeout/JSON lỗi | Hệ thống tự dùng nhánh dự phòng sau lời gọi provider | DETERMINISTIC/PROVIDER_UNAVAILABLE. Hai test mô phỏng transport xác nhận nhánh này; chưa chứng minh outage trên production. |
| Không có ngữ cảnh | Hỏi nội dung không có căn cứ | NO_CONTEXT, không phát sinh câu trả lời LLM tự do. Một số nhánh router có phản hồi riêng chưa có metadata thì UI ghi chưa ghi nhận. |
| Mô phỏng what-if | Hỏi kịch bản giả định | DETERMINISTIC/SIMULATION, giữ nhãn giả định và công thức. |
| OSM/Nominatim/OSRM không truy cập được | Dùng danh sách chi nhánh, địa chỉ đã lưu; trình bày thông báo provider lỗi | Không dựng địa chỉ/tuyến đường giả, không gọi ảnh bản đồ lưu sẵn là tuyến trực tiếp. |
| Email không gửi được | Giữ nghiệp vụ, trình bày cảnh báo và trạng thái outbox | Backend kiểm thử hoặc email preview không chứng minh inbox thật. |
| Database demo không hoạt động | Dùng báo cáo/bằng chứng đã lưu có ngày và commit | Dừng thao tác nghiệp vụ; nói rõ đây là bản ghi của lần chạy trước. |

Sau demo, khôi phục cấu hình và kiểm tra chế độ của câu trả lời mới. Có key
không đảm bảo LLM đã phản hồi. Lịch sử cũ không được tự gán mode; metadata mới
được lưu trong audit của nhánh tổng hợp, không cần migration ChatMessage.

## Kiểm tra giao diện riêng, không cần dữ liệu nghiệp vụ

```powershell
python scripts/preview_assistant_modes.py
```

Mở `http://127.0.0.1:8012/`, nhập một câu hỏi và gửi. Đây là fixture UI được ghi
nhãn rõ, dùng template thật và trả lời mẫu 100 VND; không kết nối DB hoặc provider.
Dừng server bằng Ctrl+C. Không deploy script preview làm ứng dụng thật.

Skill ui-ux-pro-max được dùng để chọn thông báo bằng chữ và `role=status`,
để trạng thái không chỉ được thể hiện bằng màu sắc.
