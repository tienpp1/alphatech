# Backup mã hóa và kiểm tra lại 97 mục — 02/10/2026

## Kết luận

Không đủ cơ sở gọi toàn bộ 97 mục “hoàn thành thực sự 100%”. Checklist đủ 97 ID, không trùng/thiếu; 70 mục đang “Giữ đóng (kế thừa)”, không phải 70 mục được chạy lại trong phiên này. CI success là release f2a831c; full run 1095 ngày 25/09 không thay thế full test suite của các bản vá sau đó. Không thay số tiến độ/cấu trúc checklist theo AGENTS.md.

Mục restore 96 đã có bằng chứng thực thi độc lập PASS ngày 02/10, thay trạng thái hoãn cũ cho lần diễn tập được cho phép. Ledger/NEXT_CLOSURE_GATES và header cũ vẫn cần được đồng bộ khi chủ dự án cho cập nhật tiến độ; bản này ghi rõ chênh lệch, không gọi 97/97 từ một thay đổi nhãn.

## Backup đã thực hiện theo lựa chọn lưu ổ D

- File: `D:/AlphaTech_Backups/alphatech_20261002_a3abbcd933/backup.fernet`, 5000716 bytes.
- SHA-256: `437b4ec7d01892320d4e4a3d4de23b173b2b66236067ab7c00fdeea77f5a7e4d`.
- Gói 868 files: production dump/evidence/TOC đã kiểm chứng, 740 local media files, 124 local forecast files. Không đóng gói .env hoặc secret key files.
- Fernet authenticated encryption; random key được Windows DPAPI bảo vệ tại thư mục riêng `D:/AlphaTech_Backup_Keys/alphatech_20261002_a3abbcd933/recovery.key.dpapi`. ACL hai thư mục chỉ cấp tài khoản Windows hiện tại và SYSTEM. Không in khóa hoặc viết plaintext archive lên disk.
- Đã đọc lại ciphertext/key từ disk, giải mã trong RAM, đối chiếu hash và file set toàn gói PASS. Sửa ciphertext bị từ chối. Không restore lại DB hoặc ghi đè file hiện có để kiểm tra.
- 7/7 unit tests guard/backup PASS (0.047s). 14/14 policy/CSP regressions PASS (0.318s); không cộng hai nhóm thành tỷ lệ toàn hệ thống.
- Browser local `127.0.0.1:8022` đã hiển thị nhãn minh họa và disclaimer; chọn ưu tiên khẩn cấp vẫn cập nhật thời gian/nhân sự/phí. Không có console error trong mẫu kiểm tra, còn cảnh báo Tailwind CDN production. Đây không phải kiểm chứng bản deploy; server dùng database restore ở chế độ read-only.

**Giới hạn quan trọng:** ổ D trên cùng máy không phải off-site; key DPAPI thường cần cùng Windows account/machine. Chưa có khóa phục hồi portable được giữ ở password manager/thiết bị khác. Dump có thể chứa password hashes/session/token, dù không có .env. Không upload dump hay khóa lên GitHub/chat.

## File production chưa đủ bằng chứng sao lưu

Nguồn Django đang dùng FileSystemStorage/MEDIA_ROOT local. Render API xác nhận plan free/disk null. Vì vậy chưa có bằng chứng persistence cho uploaded media/model files qua redeploy hoặc mất instance; không thể coi backup file local là backup production đầy đủ.

Đối chiếu DB production snapshot đã restore: 9 document file references có đường dẫn tồn tại trong local media (chưa chứng minh nội dung bằng file production remote); 0 product image file references. 3 COMPLETED forecast runs có artifact basename không tồn tại trong local model tree. Chưa đọc filesystem Render nên không khẳng định file production đã mất, nhưng **chưa có bản backup artifact tương ứng**. Không tự train lại và gọi đó là phục hồi model cũ.

## Các điểm cần khắc phục/kiểm chứng theo ưu tiên

| Ưu tiên | Liên hệ 97 mục | Phát hiện và bước tiếp theo |
|---|---|---|
| P1 | 96, vận hành mở rộng | Chọn USB/cloud ngoài máy; có khóa portable giữ riêng; copy ciphertext và kiểm tra lại từ đích. Chưa có lịch backup tự động/retention/PITR. |
| P1 | 23, 84, 88, 96 | Thu hồi/đối chiếu 3 model artifacts production và các file tài liệu/media remote; chọn object storage hoặc persistent storage phù hợp. Không tự mua dịch vụ trả phí. |
| P1 | 43, 46, 49 | Homepage còn CO-CQ 100%, uptime 99.98%, latency 1.2ms và SLA như cam kết trong khi chatbot chưa xác minh. Đã chuẩn bị patch local: bỏ số liệu không đo, giữ animations/counters nhưng ghi minh họa; mô phỏng SLA/phí/nhân sự không phải báo giá. Chưa push/deploy patch này. |
| P2 | 13 | Tài liệu nguồn trạng thái còn ghi restore hoãn/thiếu mặc dù đã có PASS. Báo cáo này ghi bổ sung; giữ nguyên ID/progress theo chỉ dẫn. |
| P2 | 85, 90, 93 | Chạy nghiệm thu cùng release cuối: local patch/scripts chưa commit; CI f2a831c không chứng nhận dirty source. Không suy ra full suite mới PASS từ focused regressions. |
| P2 | 75, 76 | Animation approval và xác minh khác thiết bị production chưa được agent kiểm chứng end-to-end. Test mô phỏng/đọc JS không thay thế inbox/thiết bị thực tế. |
| P2 | 39, 57, 91, 94 | Human Evaluation có giá trị trong mẫu đã xác nhận; RAG/GPS không bao phủ mọi trường hợp. Email/Sentry chưa có message/event ID đối chiếu độc lập với release cuối. |
| P3 | 92, 95, 97 | Async production tắt theo lựa chọn Free; không gọi worker production PASS. CSP còn inline/eval, Tailwind CDN. Secret scan chỉ known patterns; rotation theo xác nhận user. Giữ giới hạn này, không biến thành lỗi bắt buộc mở rộng đồ án. |

## Đối chiếu toàn bộ danh sách

`python scripts/audit_acceptance_evidence.py` chỉ đọc ledger và tạo `output/acceptance_audit_20261002.json`: mỗi ID có yêu cầu gốc, trạng thái hiện hành, bằng chứng cũ và ghi chú review. Kiểm tra file tham chiếu chỉ chứng minh tồn tại, không chứng minh nội dung đúng hoặc mọi test PASS. Không xóa failure lịch sử, không nâng quyền/đổi schema để làm đẹp tiến độ.

## Việc cần chủ dự án quyết định

**Cập nhật yêu cầu 02/10:** chủ dự án chưa có USB/ổ cứng rời/cloud và chọn làm off-site sau. Giữ backup local trên D; off-site và phục hồi khi mất máy **HOÃN / CHƯA KIỂM CHỨNG**, không tự đóng hoặc tính PASS. Điều này không phủ nhận lần pg_dump → pg_restore local đã PASS.

1. Nơi giữ ciphertext ngoài máy và cách giữ khóa phục hồi riêng. Nếu tiếp tục chỉ dùng D, chấp nhận đây là backup local, không bảo vệ mất máy/ổ đĩa.
2. Nơi lưu production media/model bền vững và quyền truy cập filesystem/object storage để đối chiếu file thật. Chưa cần gửi secrets qua chat.
3. Có cho phép push/deploy bản vá nội dung homepage và đồng bộ ledger với bằng chứng restore mới hay không. Không sửa bản Word thầy duyệt hoặc cấu trúc 97 ID.
