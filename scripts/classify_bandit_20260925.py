"""Redacted inventory of the 68-finding baseline; never suppresses a finding."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = root / 'output/bandit_provider_admin_final_20260925.json'
raw = source.read_bytes()
report = json.loads(raw)
rows = []
for finding in report['results']:
    path = finding['filename'].replace('\\', '/')
    rule, line = finding['test_id'], finding['line_number']
    decision = 'Cần xử lý tiếp'
    rationale = 'Exception bị bỏ qua; cần bảo toàn lỗi/quyền và quan sát được failure, không chỉ thay pass để né scanner.'
    if rule == 'B104':
        decision, rationale = 'False positive có căn cứ', '0.0.0.0 nằm trong denylist SSRF, không là bind address; test_integration_ssrf kiểm từ chối. Chưa suppression.'
    elif rule == 'B105':
        if 'seed_demo.py' in path:
            decision, rationale = 'Fixture có điều kiện', 'Credential demo công khai; CLI chặn production/remote/nonempty DB. Hàm seed_demo_identities vẫn là helper đặc quyền, không được gọi trên DB nghiệp vụ.'
        else:
            decision, rationale = 'False positive có căn cứ', 'Nội dung rubric kỳ vọng hoặc thông báo/token endpoint, không phải giá trị xác thực. Giữ scanner, không đổi chuỗi để né detection.'
    elif rule == 'B311':
        if 'seed_demo.py' in path:
            decision, rationale = 'Ngẫu nhiên mô phỏng', 'Sinh dữ liệu demo, không dùng cho token/mật khẩu; đổi sang secrets sẽ làm mất mục đích tái lập.'
        else:
            decision, rationale = 'ID hiển thị, không là secret', 'Mã phiếu/khách hàng không cấp quyền truy cập. Rủi ro va chạm mã vẫn cần xử lý riêng; không tuyên bố unique từ random.'
    elif rule in ('B404', 'B603'):
        decision, rationale = 'Subprocess có ranh giới', 'Worker gọi sys.executable/manage.py bằng argv list, PK/UUID, không shell; đòi hỏi code/runtime/DB quản trị đáng tin. Chưa có live restart proof.'
    elif rule == 'B110' and path == 'apps/knowledge/embedding.py':
        decision, rationale = 'Đã sửa, cần scan đối chiếu', 'Fallback giữ nguyên, log mã cố định không exception/key; test_ai_error_boundary và provenance.'
    elif rule == 'B110' and path == 'apps/knowledge/services.py' and line in (324,382,416,441,461,478,508):
        decision, rationale = 'Đã sửa, cần scan đối chiếu', 'Sáu nhánh mutation truyền failure lên handler có redaction; generation fallback có log cố định.'
    rows.append(f'| {path}:{line} | {rule} | {decision} | {rationale} |')
text = '# Phân loại baseline Bandit 68 findings — 25/09/2026\n\n'
text += f'Nguồn SHA256: `{hashlib.sha256(raw).hexdigest()}`. Dòng bên dưới là vị trí baseline, không phải vị trí sau sửa.\n\n'
text += 'Phân loại không đồng nghĩa đóng CI; không thêm suppression hoặc đổi threshold. Không chứa raw code/credential.\n\n'
text += '| Vị trí baseline | Rule | Phân loại | Căn cứ / giới hạn |\n|---|---|---|---|\n'
text += '\n'.join(rows) + '\n'
(root / 'docs/BANDIT_FINDING_TRIAGE_2026_09_25.md').write_text(text, encoding='utf-8')
print(f'Classified {len(rows)} baseline records; no suppressions generated.')
