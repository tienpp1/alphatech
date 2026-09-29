"""Explicit, bounded corrections to active academic drafts; never edits Word."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
replacements = {
 'docs/academic-defense-notes.md': {
  'Độ chính xác truy xuất (85.7%), Độ đúng đắn có căn cứ (100%), Trích dẫn nguồn (100%), Độ chính xác câu dự phòng chống ảo giác (100%).': 'Đối chiếu chunk IDs, nội dung, số liệu và nguồn theo từng ca. Các tỷ lệ cũ 85.7/100 chưa có bộ bằng chứng tương ứng nên không dùng để bảo vệ. Bộ replay 25/09 là offline; điểm ngữ nghĩa chưa được người chấm xác nhận.',
  'Tính minh bạch và xác định tuyệt đối.': 'Luật được định nghĩa và có thể truy vết trong mã nguồn.',
  'sự phân tách tuyệt đối giữa người yêu cầu và người phê duyệt': 'quy tắc người yêu cầu không tự phê duyệt, được kiểm trên các luồng đã nêu',
  'Bản ghi kiểm toán bất biến.': 'Bản ghi kiểm toán có model guard và PostgreSQL trigger chống UPDATE/DELETE; không chống quyền chủ database hoặc outer transaction rollback.',
  'bảng đệm staging bất biến': 'bảng đệm staging',
 },
 'docs/ai-defense-guide.md': {
  'hình học trắc địa chính xác tuyệt đối': 'hình học trắc địa theo mô hình khoảng cách đã chọn',
  'trên hình cầu WGS 84': 'với tọa độ WGS 84',
  'cấu trúc giải trình bất biến': 'cấu trúc giải trình',
 },
 'docs/HOI_DONG_DEMO_GUIDE.md': {
  'Chứng minh tính bất khả xâm phạm của mô hình phân quyền: Khách hàng công khai tuyệt đối không có quyền truy cập vào Cổng Quản trị Doanh nghiệp `/noibo/`.': 'Trình diễn ca tài khoản khách hàng bị từ chối truy cập `/noibo/`; đây là bằng chứng cho ca đã chạy, không chứng minh hệ thống bất khả xâm phạm.',
 },
 'docs/project-summary.md': {'giải quyết triệt để các thách thức này': 'hỗ trợ xử lý các nhu cầu này trong phạm vi đồ án'},
 'docs/THUYET_MINH_DO_AN_CHUONG_3_4_5.md': {
  '- **Số mục tạm giữ đóng theo bằng chứng kế thừa:** 71/97 (73,2%), chưa phải chứng nhận độc lập toàn bộ.': '- **Trạng thái hiện hành:** đọc CHECKLIST_97_PROGRESS.md; số mục kế thừa không phải chứng nhận độc lập.',
  '- **Số mục mở lại / thiếu bằng chứng:** 26 mục, xem CHECKLIST_97_PROGRESS.md.': '- **Mục thiếu bằng chứng:** giữ nguyên từng ID và điều kiện trong ledger; không suy ra đã đóng từ việc có tài liệu.',
 },
 'docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md': {
  'phân lập tuyệt đối giữa khách hàng và nhân sự nội bộ': 'phân tách quyền khách hàng và nhân sự nội bộ',
  'ngăn chặn triệt để lặp mã, brute-force và IDOR': 'kiểm thử replay mã, giới hạn thử mã và ownership trên các ca đã chạy',
  'phân tách tuyệt đối khách hàng và nội bộ': 'kiểm phân tách khách hàng và nội bộ',
  'áp dụng giải pháp kiến trúc khắc phục triệt để': 'áp dụng giải pháp với giới hạn và phạm vi kiểm thử được ghi riêng',
  'phân quyền RBAC phân cấp': 'phân quyền RBAC theo workspace',
 },
 'docs/PROJECT_CONTEXT.md': {
  'contacts create notifications but there is no Contact model.': 'contacts persist ContactSubmission and create notifications.',
  'Contact has no persistent entity.': 'ContactSubmission is the persistent public contact event.',
  'Actual enforcement remains inconsistent outside the hardened Service/GIS paths: several list/detail APIs check membership only; knowledge UI calls built-in `user.has_perm()` instead of custom workspace RBAC; assistant tools contain stale permission names.': 'The reviewed internal modules use custom workspace RBAC. This does not certify every future endpoint; explicit exceptions and gaps belong in the current checklist rather than stale pre-convergence descriptions.',
 },
}

for name, changes in replacements.items():
    path = ROOT / name
    content = path.read_text(encoding='utf-8')
    for old, new in changes.items():
        if old not in content and new not in content:
            raise ValueError('Expected passage missing: ' + name)
        content = content.replace(old, new)
    path.write_text(content, encoding='utf-8')

path = ROOT / 'docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md'
content = path.read_text(encoding='utf-8')
start = content.index('### 4.1 ')
end = content.index('### 4.2 ', start)
content = content[:start] + '''### 4.1 Trạng thái nghiệm thu hiện hành

Nguồn trạng thái duy nhất là CHECKLIST_97_PROGRESS.md; không dùng kết luận
97/97 của Batch 50 đã bị thu hồi. Ledger phân biệt mục kế thừa, mục được đối
chiếu lại và mục còn thiếu bằng chứng. Không chia số test cho 97 để tính tiến độ.

Full suite 25/09 trước bản vá cộng tác: 1.095 tests OK, log và fingerprint tại
ACCEPTANCE_BATCH_2026_09_25.md. Rerun focused, replay và UI/live là các phạm vi
riêng. Runbook production không thay thế deploy/CI/inbox/Sentry/restore thật.

Các dòng biên niên ở mục 4.2 là phát biểu lịch sử theo từng đợt, không phải
quyết định đóng mục hiện hành; quyết định đã bị thu hồi không được tái sử dụng.

''' + content[end:]
path.write_text(content, encoding='utf-8')
print('Corrected active drafts and status references; approved DOCX untouched.')
