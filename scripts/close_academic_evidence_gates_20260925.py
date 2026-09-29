"""Apply the reviewed 25 September evidence decision to the existing 97 IDs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'docs/CHECKLIST_97_PROGRESS.md'
text = path.read_text(encoding='utf-8')
updates = {
    81: '25/09: 35 use cases đối chiếu Word được duyệt, source/test/giới hạn; audit v3 xác nhận mọi file có tồn tại và test ID trong full run. Xem ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md. Đóng hồ sơ truy vết, không suy ra visual/live hay độ đầy đủ mọi test.',
    82: '25/09: xuất 48 model ORM, FK/M2M/constraints và URL/view; thay ERD viết tay, sửa kiến trúc và 4 sequence theo source. Xem model_contract_20260925_v2 và ACCEPTANCE_BATCH_2026_09_25.md. Không chứng nhận schema production hoặc render Word.',
    83: '25/09: catalog forecast 180 dòng + RAG 5 fixture/6 câu + approval fixture builders, nguồn/config/version/hash/giới hạn; xem ACADEMIC_REPLAY_CATALOG_2026_09_25.md. Run cũ Batch 44 thiếu provenance vẫn không được hồi điền.',
    84: '25/09: forecast snapshot/model/results đã replay; RAG/approval replay từ source snapshot độc lập 17 tests OK, 6 phản hồi/trạng thái RAG khớp. Giới hạn offline, semantic_pass null, không chứng nhận mọi run cũ hoặc LLM API thật.',
    85: '25/09: full suite 1095 tests OK, 3037.883s, 0 failure/error/skipped, fingerprint apps/config/tests không đổi; log/source snapshot lưu đủ. Dirty worktree dùng snapshot SHA256, không phải commit đã deploy. Bản vá cộng tác sau full run có 52 focused tests OK riêng; không cộng chồng hay gọi full suite sau vá xanh.',
}
lines = text.splitlines()
seen = set()
for i, line in enumerate(lines):
    if not line.startswith('| '):
        continue
    cells = [c.strip() for c in line.split('|')[1:-1]]
    if len(cells) == 4 and cells[0].isdigit() and int(cells[0]) in updates:
        item = int(cells[0])
        cells[2:] = ['Đóng — đối chiếu bằng chứng 25/09', updates[item]]
        lines[i] = '| ' + ' | '.join(cells) + ' |'
        seen.add(item)
if seen != set(updates):
    raise ValueError('Missing or malformed gate rows; do not change denominator')
text = '\n'.join(lines) + '\n'
text = text.replace('**76/97 mục (78.4%) đang ghi nhận đóng: 70 kế thừa và 6 đối chiếu lại; 21 mục mở lại/chờ bằng chứng.**',
                    '**81/97 mục (83.5%) đang ghi nhận đóng: 70 kế thừa và 11 đối chiếu lại; 16 mục mở lại/chờ bằng chứng.**')
path.write_text(text, encoding='utf-8')
print('Updated exactly five evidence decisions; preserved all 97 IDs.')
