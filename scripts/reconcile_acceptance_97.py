"""One-off mechanical reconciliation of existing ledger; preserve original criteria."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
REOPEN = {
    3: "Cần xác nhận của GVHD về giữ/bỏ phụ lục; tài liệu do agent viết không phải phê duyệt.",
    6: "Khung tuần 15–18 chưa có đối chiếu trang/ngày trong thông báo khoa gốc.",
    7: "Các báo cáo/slides mới tái xuất hiện kết luận 97/97; cần rà toàn bộ bản nộp.",
    11: "Đã đính chính FactGuard ở thuyết minh nhưng các tài liệu/slide khác còn cần đồng bộ.",
    13: "Đang đính chính canonical status; bản Word/slide và lịch sử còn chưa đồng bộ đầy đủ.",
    14: "Đếm discovery không chứng minh pass; tổng theo module chưa truy nguyên tới test ID.",
    26: "Thiếu actual/prediction/bounds để chứng minh coverage 10/15; đã rút lại tỷ lệ.",
    39: "Numeric regex có test giới hạn phủ định; thiếu phiếu chấm đúng/đủ ngữ nghĩa trên dataset độc lập.",
    46: "Hồ sơ mới khẳng định 7 ngày/12 tháng/24 giờ, trái ranh giới POLICY_PUBLICATION_REVIEW; cần đối chiếu nguồn được duyệt.",
    56: "Báo cáo có tên ảnh/browser nhưng chưa xác minh artifact live Nominatim tương ứng trong đợt này.",
    57: "Test pure function và browser mô phỏng chưa chứng minh GPS/accuracy trên thiết bị thật.",
    80: "Khoảng trống mô tả FactGuard runtime chưa khớp code bộ chấm ngoại tuyến.",
    82: "Sequence RAG mô tả guard runtime chưa tồn tại; cần sửa sơ đồ theo source.",
    83: "Run dùng trong Batch 44 ghi thiếu provenance; catalog chưa thay thế snapshot dataset phiên bản hóa.",
    84: "Chưa có gói dataset/config/model/results đầy đủ để tái chạy đúng các số đã báo cáo.",
    85: "Đang chạy full suite trên fingerprint; nhiều batch trước không cùng commit.",
    86: "Đang thu log failures/errors/skips thực tế; manifest trước chỉ kiểm tra chuỗi trong tài liệu.",
    89: "Các bản thuyết minh/slide/Word còn cần rà đồng bộ và kiểm chứng từng nguồn IEEE.",
    90: "Cần SHA deploy trùng mã nghiệm thu; dirty worktree chưa phải release đã deploy.",
    91: "Đã có xác nhận nhận hai thư trước đây; còn thiếu bằng chứng từng sự kiện nghiệp vụ trên phiên bản hiện tại.",
    92: "Cần log worker claim/heartbeat/restart/recovery trên deployment thật.",
    93: "Cần CI run URL và artifact security/coverage ứng với SHA nghiệm thu hiện tại.",
    94: "Cần event ID/timestamp Sentry đã nhận thật; cấu hình DSN không đủ.",
    95: "Cần kiểm tra HTTPS/cookie/CSP trên bản deployment nghiệm thu.",
    96: "HOÃN theo yêu cầu trước: chưa thực hiện pg_dump → pg_restore; không thay bằng TEMPLATE/runbook.",
    97: "Ghi nhận user đã xác nhận rotate; chưa kiểm chứng bảo vệ secret trên toàn bộ diff/release hiện tại.",
}


def main():
    path = ROOT / "docs/CHECKLIST_97_PROGRESS.md"
    source = path.read_text(encoding="utf-8")
    rows = []
    for line in source.splitlines():
        match = re.match(r"^\| (\d+) \| (.*?) \| (.*?) \| (.*) \|$", line)
        if match:
            rows.append((int(match[1]), match[2], match[4]))
    assert [r[0] for r in rows] == list(range(1, 98)), "Do not change a ledger with unexpected IDs"
    retained = 97 - len(REOPEN)
    introduction = (
        "# Đối chiếu lại 97 mục — 23/09/2026\n\n"
        f"**{retained}/97 mục ({retained / 97:.1%}) tạm giữ trạng thái đóng theo bằng chứng lịch sử; "
        f"{len(REOPEN)} mục mở lại/chờ bằng chứng.** Đây là số dư kiểm toán tạm thời, "
        "KHÔNG phải chứng nhận độc lập toàn bộ mục đã hoàn thành. Không có kết luận 97/97.\n\n"
        "Giữ nguyên ID, nội dung gốc và mẫu số. `Giữ đóng (kế thừa)` nghĩa là chưa phát hiện "
        "mâu thuẫn đủ để mở lại trong đợt này, không đồng nghĩa đã chạy lại tất cả bằng chứng. "
        "Test local, kiểm thử mô phỏng, tài liệu hướng dẫn và bằng chứng production phải tách riêng. "
        "Các kết luận đợt 40–50 bên dưới là lịch sử, bị thay thế ở những dòng có đính chính.\n\n"
        "## Bảng đối chiếu đủ 97 mục\n\n"
        "| Mục | Nội dung gốc | Trạng thái hiện tại | Bằng chứng / điều kiện còn thiếu |\n"
        "|---|---|---|---|\n"
    )
    for number, criterion, evidence in rows:
        state = "Mở lại / chưa đủ bằng chứng" if number in REOPEN else "Giữ đóng (kế thừa)"
        detail = REOPEN.get(number, "Đối chiếu bằng chứng lịch sử dưới đây; chưa chứng nhận lại toàn bộ trong đợt này.")
        introduction += f"| {number} | {criterion} | {state} | {detail} Bằng chứng trước: {evidence} |\n"
    introduction += "\n## Kết quả chạy mới\n\nXem `ACCEPTANCE_REAUDIT_2026_09_23.md` và `output/acceptance_verification/`. Không cộng test lặp giữa các lượt.\n"
    path.write_text(introduction, encoding="utf-8")
    notices = {
        "CURRENT_STATUS.md": "Kết luận 97/97 và full-suite 100% trong các mục lịch sử dưới đây bị thu hồi. Xem CHECKLIST_97_PROGRESS.md và ACCEPTANCE_REAUDIT_2026_09_23.md. Quyền bảng tin đã bỏ bypass is_staff; 11 test local qua. Full suite đang được đo bằng log, không bằng discovery.",
        "NEXT_CLOSURE_GATES.md": "Các quyết định đóng trước đây phải đọc cùng CHECKLIST_97_PROGRESS.md phiên bản đính chính 23/09. Cổng production 90–97 chưa được đóng bằng bằng chứng live.",
        "HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md": "Các tổng 1055/1056/1065, 100% pass và zero skips bên dưới là tuyên bố chưa có log toàn bộ tương ứng. Không dùng để nghiệm thu. Dùng kết quả thực thi mới tại output/acceptance_verification; discovery và test kiểm tra tài liệu không chứng minh thực thi.",
        "THUYET_MINH_DO_AN_CHUONG_3_4_5.md": "Bản thảo CHƯA ĐỦ ĐIỀU KIỆN NỘP: bảng phân bổ test và kết luận hoàn tất ở các chương chưa được nghiệm thu. Đính chính RAG/coverage ở mục 4; không công bố 97/97. Xem ACCEPTANCE_REAUDIT_2026_09_23.md.",
        "HOI_DONG_DEMO_GUIDE.md": "Không sử dụng số 97/97 trong bản này để trình bày nghiệm thu. Dùng CHECKLIST_97_PROGRESS.md đính chính; các cổng production còn thiếu bằng chứng.",
        "HO_SO_LICH_TRINH_HANH_CHINH_VA_LO_TRINH_PHAT_TRIEN.md": "Khung tuần bên dưới chỉ là đề xuất chưa đối chiếu thông báo khoa. Chưa có phê duyệt giữ phụ lục từ GVHD. Thu hồi kết luận đóng mục 3 và 6.",
        "HO_SO_VAN_HANH_HA_TANG_PRODUCTION_VA_DEPLOYMENT_RUNBOOK.md": "Đây là RUNBOOK, không là log thực thi. Các cổng 90–97 chưa được chứng nhận. Theo checklist gốc: 95=HTTPS/cookie/CSP, 97=secret. Email Render Free dùng Brevo HTTPS API khi cấu hình backend tương ứng; không yêu cầu chuyển sang SMTP cổng 587.",
        "HO_SO_DOI_CHIEU_CHINH_SACH_VA_RANH_GIOI_CONG_BO.md": "Các mốc bảo hành/đổi trả/SLA trong bản này chưa có nguồn phê duyệt công khai. Không dùng chúng làm cam kết khách hàng. POLICY_PUBLICATION_REVIEW.md vẫn là ranh giới công bố; mục 46 mở lại.",
    }
    for name, notice in notices.items():
        target = ROOT / "docs" / name
        existing = target.read_text(encoding="utf-8")
        target.write_text("> **ĐÍNH CHÍNH 23/09/2026:** " + notice + "\n\n" + existing, encoding="utf-8")
    print(f"Reconciled 97 original IDs: {retained} inherited closures, {len(REOPEN)} reopened.")


if __name__ == "__main__":
    main()
