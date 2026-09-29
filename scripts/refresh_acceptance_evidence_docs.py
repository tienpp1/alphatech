"""Repeat-safe mechanical updates of test evidence; no fabricated execution."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
run = ROOT / "output/acceptance_verification/20260923T072453Z"
data = json.loads((run / "test_summary.json").read_text(encoding="utf-8"))
lines = ["# Bằng chứng full suite thực chạy — 23/09/2026", "",
    "Nguồn duy nhất: `output/acceptance_verification/20260923T072453Z/django.log`.",
    f"SHA256: `{data['log_sha256']}`.", "",
    f"Runner báo **{data['tests_run']} tests**, **{data['seconds']}s**, **{data['outcome']}**; "
    f"{data['failures']} failures, {data['errors']} errors, {data['skipped']} skipped.",
    "Không cộng các rerun vào tổng này. Không suy ra số pass bằng cách trừ error entries.",
    f"Trích xuất được {data['observed_unique_ids']} ID duy nhất từ dòng verbose; không coi danh sách này là toàn bộ {data['tests_run']} ca do định dạng/log xen kẽ.",
    "Mỗi incident dưới đây được giữ nguyên; lỗi cleanup lặp không bị giấu.", "",
    "| Loại | Test ID |", "|---|---|"]
lines += [f"| {row['status']} | `{row['test_id']}` |" for row in data['incidents']]
lines += ["", "## Skipped, phần chưa chạy và rerun", "",
    "Lần chạy này báo 0 bài kiểm thử bị bỏ qua (0 skipped tests); không phải lời bảo đảm cho môi trường khác.",
    "Node/browser, OAuth thật, inbox, CI runner, Sentry và restore không nằm trong lệnh Django này.",
    "Sau sửa đã có rerun có phạm vi tại ACCEPTANCE_REAUDIT_2026_09_23.md và ACCEPTANCE_BATCH_BULLETIN_GROUNDING_2026_09_24.md; chưa full-suite rerun.",
    "Test kiểm tra chuỗi trong tài liệu chỉ kiểm tra tài liệu, không chứng minh nghiệp vụ hoặc production.", "",
    "## Danh mục file hiện tại (inventory, không phải pass)", "",
    "Danh mục file phục vụ đối chiếu source; không quy đổi số file thành số test hoặc coverage.", ""]
lines += [f"- `{p.name}`" for p in sorted((ROOT / "tests").glob("test_*.py"))]
report = "\n".join(lines) + "\n"
(ROOT / "docs/TEST_EXECUTION_EVIDENCE.md").write_text(report, encoding="utf-8")

path = ROOT / "docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md"
text = path.read_text(encoding="utf-8")
start = text.index("#### 4.3.1")
end = text.index("#### 4.3.2", start)
section = text[start:end]
table = []
for line in section.splitlines():
    if line.startswith("|") and "TỔNG CỘNG" not in line:
        parts = line.split("|")
        if len(parts) >= 6 and re.fullmatch(r"\s*\d+\s*", parts[3]):
            parts[3] = " Không quy đổi thành pass "
            line = "|".join(parts)
        table.append(line)
replacement = """#### 4.3.1 Phân nhóm source và bằng chứng thực thi

Các nhóm sau là phân loại chức năng, có file dùng chung, **không cộng** các dòng
thành tổng test độc lập. Số test/nhóm cũ không có log tương ứng đã được rút lại.
Kết quả full suite thực: **1.067 test; 8 failures, 8 errors; 0 skipped**, 2.032,520s.
Xem TEST_EXECUTION_EVIDENCE.md cho log hash, incident test ID và phạm vi chưa chạy.
Không phải full-suite pass; các rerun sửa lỗi không được ghép thành một lần chạy xanh.

""" + "\n".join(table) + "\n\n"
text = text[:start] + replacement + text[end:]
text = re.sub(r"> \*\*Kết luận Kiểm kê Skips:.*", "> **Kết luận Kiểm kê Skips:** Lần chạy 23/09 có 0 bài kiểm thử bị bỏ qua (0 skipped tests), nhưng FAILED (8 failures, 8 errors). Không chứng minh mọi test đều pass. Xem TEST_EXECUTION_EVIDENCE.md.", text)
text = text.replace("**ĐƯỢC THỰC THI ĐẦY ĐỦ (PASS)** do dự án vận hành 100% trên PostgreSQL 18 chuẩn.", "Điều kiện chạy phụ thuộc backend; kết quả theo log từng lần, không suy ra PASS từ việc dùng PostgreSQL.")
marker = "## Inventory source hiện tại (không phải kết quả test)"
text = text.split(marker)[0].rstrip() + "\n\n" + marker + "\n\n" + "\n".join(lines[lines.index("## Danh mục file hiện tại (inventory, không phải pass)")+4:]) + "\n"
path.write_text(text, encoding="utf-8")
