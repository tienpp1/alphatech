# Phạm vi nghiệm thu đồ án

**Tên đề tài:** Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI

Ngày chốt làm việc: 18/09/2026. Căn cứ: yêu cầu người dùng, góp ý thầy được người
dùng chuyển trong task và mã nguồn hiện tại. Đây là phạm vi thực hiện/đối chiếu,
không phải xác nhận thay mặt giảng viên hoặc bản Word đã được duyệt.

## Chức năng bắt buộc trong phạm vi làm việc

| Mã | Yêu cầu | Điều kiện nghiệm thu |
|---|---|---|
| AUTH | Tài khoản khách hàng, đăng nhập/đăng ký/xác minh; tách cổng nội bộ | Chặn trùng email/replay/IDOR, không tự cấp membership; email thật nghiệm thu riêng |
| TENANCY | Workspace và RBAC nội bộ | Kiểm chứng tài khoản thường, sai workspace/sai quyền và mutation, không chỉ superuser |
| RETAIL | Danh mục, khách hàng, đơn hàng, tồn kho hỗ trợ bán lẻ | Luồng đặt–duyệt–hoàn tất/hủy, reservation/rollback và ownership rõ |
| SERVICE | Tiếp nhận yêu cầu, task, phân công, thời gian và SLA | Luồng trạng thái hợp lệ, quyền nhân viên đúng phạm vi, dữ liệu SLA thiếu không ghi thành đạt |
| GIS | Chi nhánh, tìm vị trí/địa điểm, bán kính, gợi ý dẫn đường | Phân biệt khoảng cách địa lý với đường giao thông; công bố provider/timeout; GPS thật còn nghiệm thu |
| DATA | Import, mapping và dữ liệu chuẩn | Dữ liệu hợp lệ/sai/trùng/sai workspace; chỉ gọi hỗ trợ entity đã kiểm thử |
| RAG | Trợ lý truy xuất tài liệu và số liệu nghiệp vụ có nguồn | Lưu câu trả lời/nguồn/mode, chấm đủ ý/số liệu; sai quyền bị từ chối; không dùng keyword làm semantic accuracy |
| FORECAST | Một bài toán dự báo chính: doanh thu bán lẻ theo ngày | Dataset/split/run có hồ sơ, so hai baseline cùng thông tin; giữ kết quả kém và phân biệt one-step/recursive |
| APPROVAL | Khuyến nghị, phê duyệt và thực thi action được hỗ trợ | Không tự duyệt, không thực thi trùng, rollback và audit; advisory không biến thành action |
| NOTIFY | Thông báo nghiệp vụ và email khách hàng | Đúng người/sự kiện; lỗi email không mất nghiệp vụ; không coi locmem là inbox thật |
| TEAM_CHAT | Chat realtime giữa nhân viên theo workspace (thầy bổ sung) | Đã hoàn thành: Trao đổi hai chiều, polling since_id, cô lập workspace, chặn tài khoản khách hàng |
| BULLETIN | Bản tin nội bộ (thầy bổ sung) | Đã hoàn thành: Đăng/xem theo quyền (Admin/Manager), ghim tin, phân phối đúng workspace |

TEAM_CHAT và BULLETIN đã được triển khai đầy đủ tại apps/notifications/ (InternalBulletin,
TeamChatMessage, bulletin_service, chat_service, UI views, APIs) và kiểm thử tự động tại
tests/test_bulletin_and_team_chat.py, đáp ứng đầy đủ yêu cầu bổ sung của giảng viên hướng dẫn.

## Mở rộng, không phải điều kiện hoàn tất đồ án hiện tại

- Thêm LSTM/GRU/Transformer, bài toán nhiệt độ bề mặt đất LST: chỉ là ví dụ
  phương pháp lập luận thầy gửi chung, không phải công nghệ bắt buộc của đề tài.
- ERP/WMS đầy đủ, kế toán tổng hợp, bảng lương, sản xuất, sơ đồ kệ/picking/packing,
  phát hiện gian lận, tối ưu lịch Hungarian, tích hợp SAP/Odoo: không đưa vào cam kết.
- Stock reorder/workload auto-execution chưa có contract/rollback an toàn: giữ
  advisory, không mở mapping chỉ để trông đủ chức năng.
- Dự báo nhiều SKU/chi nhánh/mô hình là mở rộng nghiên cứu sau bài toán chính;
  những đường code đã có vẫn giữ, không suy ra đã nghiệm thu chất lượng tất cả.
- Production observability, worker vận hành, HTTPS/inbox/backup/CI: theo dõi cổng
  production riêng. Không xóa khỏi checklist 97, không coi local là production.

## Phụ lục và tài liệu nộp

Không dùng lộ trình V2–V5 để chứng minh hoàn thành. Không đưa tính năng chưa làm
vào mục kết quả đạt được. Việc giữ/bỏ phụ lục trong file Word cụ thể vẫn cần đối
chiếu bản Word mới nhất và comment của thầy (mục 3 chưa đóng).
Mốc nộp/bảo vệ theo thông báo khoa, không suy ra từ lịch phát triển (mục 6 mở).

## Điều không được tuyên bố

Đây không phải ERP/WMS hoàn chỉnh, không có chứng nhận an toàn tuyệt đối hoặc
RAG không ảo giác. Không coi ghép nhiều công nghệ là bằng chứng tính mới học thuật.
Không nhận khả năng tư vấn của chatbot là chức năng giao dịch đã triển khai.
Không cộng các test chạy lặp thành coverage toàn hệ thống.

Xem `ACADEMIC_REQUIREMENTS_MATRIX.md` để biết bằng chứng và phần thiếu từng yêu cầu.
Các tài liệu thuyết minh/demo cũ phải đọc dưới giới hạn của tài liệu này;
Word, nguồn IEEE, khảo sát đối thủ và semantic review vẫn phải nghiệm thu riêng.
