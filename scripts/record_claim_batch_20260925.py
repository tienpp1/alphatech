"""Record bounded document-gate closures without changing original criteria."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
p = root / 'docs/CHECKLIST_97_PROGRESS.md'
text = p.read_text(encoding='utf-8')
text = text.replace('**81/97 mục (83.5%) đang ghi nhận đóng: 70 kế thừa và 11 đối chiếu lại; 16 mục mở lại/chờ bằng chứng.**', '**84/97 mục (86.6%) đang ghi nhận đóng: 70 kế thừa và 14 đối chiếu lại; 13 mục mở lại/chờ bằng chứng.**')
evidence = {
 7: 'Đối chiếu các bản nháp nộp/slide, hướng dẫn demo, runbook và Word duyệt không đổi; thu hồi kết luận 97/97 trong nội dung, không chỉ thêm banner. Xem ACCEPTANCE_BATCH_2026_09_25_CLAIMS.md; không chứng nhận production.',
 11: 'Bỏ các tuyên bố GIS chính xác tuyệt đối, bất khả xâm phạm, chống replay triệt để; giới hạn audit/RAG/phân quyền theo ca kiểm thử. Có regression chống tái xuất hiện; không coi lexical guard là bằng chứng an toàn toàn hệ thống.',
 13: 'Ledger là nguồn trạng thái; đồng bộ CURRENT_STATUS, slide, hồ sơ nghiệm thu, cổng đóng, ContactSubmission/RBAC trong PROJECT_CONTEXT. Lịch sử được đánh dấu thu hồi, không xóa failure. Word duyệt giữ nguyên. IEEE còn mở ở 89.',
}
lines = text.splitlines()
for i, line in enumerate(lines):
    for key, note in evidence.items():
        if line.startswith(f'| {key} |'):
            parts = line.split(' | ')
            parts[2] = 'Đóng — đối chiếu tài liệu 25/09'
            parts[3] = note + ' |'
            lines[i] = ' | '.join(parts[:4])
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')
p = root / 'docs/SLIDES_BAO_VE_KHOA_LUAN.html'
text = p.read_text(encoding='utf-8').replace('81/97 mục tạm đóng · 16 mục còn thiếu bằng chứng', '84/97 mục tạm đóng · 13 mục còn thiếu bằng chứng')
p.write_text(text, encoding='utf-8')
p = root / 'docs/CURRENT_STATUS.md'
text = p.read_text(encoding='utf-8')
heading = '> **HIỆN HÀNH 25/09/2026 — đợt claims:** **84/97 (86,6%) tạm đóng**, 70 kế thừa + 14 đối chiếu lại; 13 mở. Đóng thêm 7/11/13 trong phạm vi tài liệu. Xem ACCEPTANCE_BATCH_2026_09_25_CLAIMS.md. Không chứng nhận production hoặc toàn bộ các mục kế thừa.\n\n'
if not text.startswith(heading):
    text = heading + '## Bản ghi trước đợt claims (lịch sử)\n\n' + text
p.write_text(text, encoding='utf-8')
print('Recorded 3 documentary closures: provisional 84/97; 13 open.')
