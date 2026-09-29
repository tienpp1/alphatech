"""Record only gates supported by the 24 September evidence correction."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "docs/CHECKLIST_97_PROGRESS.md"
text = path.read_text(encoding="utf-8")
updates = {
    14: "Đóng — rút tổng cộng chồng lặp; hồ sơ/thuyết minh dùng log một run duy nhất, không cộng rerun hoặc file chung. TEST_EXECUTION_EVIDENCE.md ghi nguồn/hash, không suy ra pass từ discovery hay trừ lỗi cleanup. Bộ tổng hợp từ chối ghép nhiều run; 12 test parser/manifest qua.",
    80: "Đóng — mục 3 TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md đối chiếu nhu cầu kịch bản → source/test → giới hạn; bỏ Dual-Guard runtime giả, không tuyên bố mới thuật toán hay khảo sát đa số thị trường. Bibliography chưa duyệt, tiếp tục ở mục 89.",
    86: "Đóng — TEST_EXECUTION_EVIDENCE.md giữ đủ 8 failure/8 error entries, 0 skipped của run 23/09, các phần chưa chạy và rerun riêng. 14 ID lỗi duy nhất, không giấu cleanup trùng. Không đồng nghĩa full suite đã pass sau sửa hoặc production đã đạt.",
}
out = []
for line in text.splitlines():
    match = re.match(r"\| (\d+) \|", line)
    if match and int(match[1]) in updates:
        cells = line.split("|")
        line = f"| {match[1]} | {cells[2].strip()} | Đóng — kiểm chứng lại 24/09 | {updates[int(match[1])]} |"
    out.append(line)
text = "\n".join(out) + "\n"
text = text.replace("72/97 mục (74.2%) đang ghi nhận đóng: 70 kế thừa và 2 đối chiếu lại nguồn; 25 mục mở lại/chờ bằng chứng.", "75/97 mục (77.3%) đang ghi nhận đóng: 70 kế thừa và 5 đối chiếu lại; 22 mục mở lại/chờ bằng chứng.")
path.write_text(text, encoding="utf-8")

path = ROOT / "docs/SLIDES_BAO_VE_KHOA_LUAN.html"
text = path.read_text(encoding="utf-8").replace("71 / 97", "75 / 97").replace("data: [71, 26]", "data: [75, 22]")
text = text.replace("71 mục", "75 mục").replace("26 mục", "22 mục")
path.write_text(text, encoding="utf-8")

path = ROOT / "docs/HOI_DONG_DEMO_GUIDE.md"
text = path.read_text(encoding="utf-8").replace("**100% Đóng**", "**Theo bằng chứng từng mục**")
text = text.replace("Bộ kiểm thử tự động 1.065 tests", "Kết quả thực chạy: TEST_EXECUTION_EVIDENCE.md")
text = text.replace("FactGuard Regex kiểm số", "bộ chấm số liệu ngoại tuyến (không phải runtime guard)")
path.write_text(text, encoding="utf-8")
