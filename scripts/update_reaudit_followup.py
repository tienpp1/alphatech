"""Mechanical, repeat-safe corrections to the acceptance audit documents."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ledger = ROOT / "docs/CHECKLIST_97_PROGRESS.md"
text = ledger.read_text(encoding="utf-8")
updates = {
    3: ("Đóng — đối chiếu bản duyệt", "User xác nhận bản Word teacher_review_v2 là bản được duyệt; trang 16 giữ phụ lục định hướng tương lai. Hash và đường dẫn trong ACCEPTANCE_REAUDIT_2026_09_23.md. Không tính roadmap là chức năng đã làm."),
    6: ("Đóng — đối chiếu nguồn khoa", "PDF khoa 24/08/2026 trang 2, 5: nộp cuốn 16–20/11; báo cáo dự kiến 23–28/11; nộp file 30/11–06/12. Hồ sơ lịch đã bỏ khung 18 tuần tự suy ra; phân biệt với lịch kỹ thuật. Không chứng nhận đã nộp/bảo vệ."),
    81: ("Mở lại / chưa đủ bằng chứng", "Đề cương duyệt yêu cầu đăng/cập nhật/đọc bản tin. Source đã có list/create nhưng chưa thấy endpoint cập nhật; ma trận cần phản ánh thiếu chức năng thay vì đánh dấu toàn bộ hoàn tất."),
}
lines = []
for line in text.splitlines():
    match = re.match(r"\| (\d+) \|", line)
    if match and int(match[1]) in updates:
        cells = line.split("|")
        state, evidence = updates[int(match[1])]
        line = f"| {match[1]} | {cells[2].strip()} | {state} | {evidence} |"
    lines.append(line)
text = "\n".join(lines) + "\n"
text = text.replace("**71/97 mục (73.2%) tạm giữ trạng thái đóng theo bằng chứng lịch sử; 26 mục mở lại/chờ bằng chứng.**", "**72/97 mục (74.2%) đang ghi nhận đóng: 70 kế thừa và 2 đối chiếu lại nguồn; 25 mục mở lại/chờ bằng chứng.**")
ledger.write_text(text, encoding="utf-8")

path = ROOT / "docs/HO_SO_LICH_TRINH_HANH_CHINH_VA_LO_TRINH_PHAT_TRIEN.md"
text = path.read_text(encoding="utf-8")
text = re.sub(r"^> .*\n", "> **ĐỐI CHIẾU 24/09/2026:** Dùng bản đề cương user xác nhận đã duyệt và PDF khoa gốc. Mục 3/6 đóng về đối chiếu phạm vi/lịch, không chứng nhận đã nghiệm thu sản phẩm hoặc đã nộp/bảo vệ.\n", text, count=1)
text = text.replace("**Trạng thái phê duyệt:** ĐÓNG HOÀN TOÀN (CLOSED)", "**Trạng thái:** Đã đối chiếu nguồn cho mục 3 và 6")
text = text.replace("### 2.2. Ma trận phân định Phạm vi Đã nghiệm thu vs Hướng phát triển tương lai", "### 2.2. Ma trận phạm vi triển khai vs Hướng phát triển tương lai\n\nMa trận là phân loại phạm vi, không thay thế nghiệm thu từng chức năng; trạng thái thực theo CHECKLIST_97_PROGRESS.md.")
text = text.replace("Phạm vi ĐÃ XÂY DỰNG & NGHIỆM THU (Scope Acceptance)", "Phạm vi triển khai (kiểm chứng riêng từng mục)")
start = text.index("### 3.2.")
text = text[:start] + '''### 3.2. Mốc chính thức theo thông báo khoa

Nguồn: `C:/Users/anhbe/Downloads/Kế hoạch thực hiện đồ án môn học kỳ 1 năm học 2026-2027.pdf`, thông báo ngày 24/08/2026, trang 2 và mục 6 trang 5 (đã trích xuất và kiểm tra ảnh render).
Đây là **Đồ án chuyên ngành**, không tự đổi thành quy trình khóa luận tốt nghiệp.

| Mốc | Ngày năm 2026 | Căn cứ / ý nghĩa |
|---|---|---|
| Đăng ký GVHD/đề tài | 24/08–04/09 | Tuần 1–2; hạn đăng ký 15 giờ 04/09 tại trang 4 |
| Nộp quyển đề cương | 10–11/09 | Tuần 3, trang 2 |
| Phân tích, thiết kế | 14–20/09 | Tuần 4 |
| Cài đặt thực nghiệm | 21/09–18/10 | Tuần 5–8 |
| Kiểm thử và đánh giá | 19/10–01/11 | Tuần 9–10 |
| Viết báo cáo | 02–15/11 | Tuần 11–12 |
| Nộp 02 cuốn báo cáo | 16–20/11 | Mục 6 trang 5; không phải tuần 17 |
| Báo cáo trước hội đồng | 23–28/11, dự kiến | Tuần 14, theo lịch cụ thể của khoa |
| Sửa theo hội đồng và nộp file | 30/11–06/12 | Tuần 15; mục 6 trang 5 |

Trang 1 ghi thời gian thực hiện chung đến **04/12**, trong khi bảng tuần 15 và mục 6 ghi hạn nộp file đến **06/12**. Giữ nguyên hai thông tin của nguồn và hỏi khoa nếu cần chốt hạn thực tế; không tự sửa nguồn.

### 3.3. Đối chiếu với lịch kỹ thuật trong đề cương

Bản duyệt `output/docx_review/teacher_review_v2/De_cuong_Ha_Minh_Tien_sua_gop_y_lan_2.docx` có kế hoạch 15 tuần, khung 24/08–04/12. Tuần 12 làm chat/bản tin, tuần 14 kiểm thử tổng hợp và tuần 15 hoàn thiện báo cáo là kế hoạch công việc, **không thay thế** hạn nộp cuốn tuần 13 và báo cáo tuần 14 của khoa.

Do đó bản demo, kết quả thực nghiệm và cuốn báo cáo phải được chuẩn bị trước **16–20/11**; tuần 14 chỉ dùng cho kiểm tra cuối/báo cáo, tuần 15 sửa theo hội đồng. Không tự chỉnh bản Word đã duyệt; ghi nhận điều chỉnh thứ tự thực hiện trong hồ sơ kỹ thuật này.

## 4. Quyết định đối chiếu

- **Mục 3:** giữ phụ lục tương lai theo bản duyệt user xác nhận; trang 16. Không cam kết triển khai mọi mục V2–V5 trong đồ án.
- **Mục 6:** đã đối chiếu lịch khoa với lịch kỹ thuật, chỉ rõ khác biệt cần quản lý. Thu hồi toàn bộ khung tuần 16–18 do agent suy ra trước đây.
- Đóng hai tiêu chí đối chiếu; không có tuyên bố khoa đã ký nghiệm thu, đã nộp cuốn hoặc đã bảo vệ.
'''
path.write_text(text, encoding="utf-8")
