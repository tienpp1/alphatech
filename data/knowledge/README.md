# Phạm vi sử dụng kho SOP trong đồ án

Các file SOP tại đây là nguồn trong repository, **chưa xác minh phê duyệt thương
mại hoặc quyền công bố**. Ngày hiệu lực, tên tiêu chuẩn, mức bồi hoàn hoặc chức
danh viết trong file không tự chứng minh các điều đó tồn tại ở doanh nghiệp thật.
Chờ chủ sở hữu xác nhận nguồn giả lập/thực tế; không tự coi tất cả là chính sách thật.

Danh mục máy đọc: `apps/knowledge/sop_catalog.py`, 24 file không trùng lặp.
7 nguồn trọng tâm: supply chain, financial margin, inter-branch transfer,
RMA warranty, omnichannel fulfillment, inventory audit và incident SLA.
17 nguồn còn lại là tham khảo bổ sung, không đưa thành năng lực đã triển khai
hay mục tiêu chính khi bảo vệ: đặc biệt nhân sự/lương thưởng, pháp lý hợp đồng,
datacenter, tiêu hủy dữ liệu và phục hồi thảm họa chuyên sâu.

Trong `scope_benchmark.py`, 3 câu RMA/BOPIS/SLA là nhóm trình bày chính;
7 câu còn lại giữ nguyên ở nhóm bổ sung. Giữ tất cả test cũ, không xóa câu thất
bại để nâng điểm. Không dùng tỷ lệ trên tập con để thay tỷ lệ toàn bộ benchmark.

Đây là phân loại phạm vi học thuật, không phải bộ lọc retrieval production.
Không tự xóa tài liệu DB, ingest lại hay chuyển tài liệu sang workspace khác.
Script `ingest_all_enterprise_sops.py` hiện có đường cập nhật tài liệu đã tồn tại;
không chạy chỉ để xem danh mục hoặc kiểm tra nguồn. README không cấp quyền ingest.
