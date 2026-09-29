"""One-off bibliography/scope corrections to working Markdown, not approved Word."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
p = ROOT / 'docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md'
t = p.read_text(encoding='utf-8')
start, end = t.index('Thay vì đưa ra'), t.index('## 3.')
t = t[:start] + '''Đề tài chưa có khảo sát thực nghiệm các sản phẩm thương mại. Không dùng
nhận xét về SAP, Odoo hoặc SaaS nói chung làm bằng chứng ưu thế.
Ma trận triển khai/giới hạn theo code được ghi ở mục 1.3 của
THUYET_MINH_DO_AN_CHUONG_1_VA_2.md và ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md.

''' + t[end:]
t = re.sub(r'^\[5\] M\. Fowler, "MonolithFirst.*$', '[5] D. L. Parnas, "On the criteria to be used in decomposing systems into modules," Communications of the ACM, vol. 15, no. 12, pp. 1053–1058, 1972, doi: 10.1145/361598.361623.', t, flags=re.M)
t = re.sub(r'^- \*\*Phong cách Kiến trúc Modular Monolith.*$', '- **Phân chia module:** Parnas [5] nghiên cứu tiêu chí phân rã module. Nguồn này hỗ trợ thảo luận về modularity, không chứng minh Modular Monolith luôn nhanh/rẻ hơn microservices. Chọn monolith trong đồ án là quyết định thiết kế để dùng chung transaction và giảm thành phần vận hành; cần đo nếu muốn so sánh hiệu năng.', t, flags=re.M)
t = t.replace('"The M4 Competition: Results, findings, conclusion and way forward," PLOS ONE, vol. 13, no. 6, p. e0197722, Jun. 2018, doi: 10.1371/journal.pone.0197722.', '"The M4 Competition: Results, findings, conclusion and way forward," International Journal of Forecasting, vol. 34, no. 4, pp. 802–808, 2018, doi: 10.1016/j.ijforecast.2018.06.001.')
p.write_text(t, encoding='utf-8')
p = ROOT / 'docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md'
t = p.read_text(encoding='utf-8')
t = re.sub(r'^\[6\] M\. Fowler, "MonolithFirst.*$', '[6] D. L. Parnas, "On the criteria to be used in decomposing systems into modules," Communications of the ACM, vol. 15, no. 12, pp. 1053–1058, 1972, doi: 10.1145/361598.361623.', t, flags=re.M)
t = t.replace('*(Đóng Cổng Nghiệm thu Học thuật 1 & 89)*', '*(Phần làm việc; trạng thái mục 89 theo CHECKLIST_97_PROGRESS.md.)*')
t = t.replace('*(Đóng Cổng Nghiệm thu Học thuật 81 & 82)*', '*(Đối chiếu bổ sung: ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md và output/model_contract_20260925_v2/. Không chứng nhận mọi sơ đồ cũ đã đúng.)*')
p.write_text(t, encoding='utf-8')
p = ROOT / 'docs/THUYET_MINH_DO_AN_CHUONG_1_VA_2.md'
t = p.read_text(encoding='utf-8')
t = re.sub(r'Câu truy vấn này thực thi trong thời gian dưới.*?\n', 'Chưa có benchmark thời gian cho câu truy vấn này trong hồ sơ; không công bố mốc 5 ms hoặc kết luận tối ưu toàn cục.\n', t)
p.write_text(t, encoding='utf-8')
