"""Correct unsupported visible claims without changing slide layout or CSS."""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "docs/SLIDES_BAO_VE_KHOA_LUAN.html"
text = path.read_text(encoding="utf-8")
replacements = {
    "Trợ lý RAG FactGuard": "Trợ lý RAG và đánh giá ngoại tuyến",
    "Grounded RAG (pgvector Cosine Sim + FactGuard Regex)": "RAG runtime; numeric scoring ngoại tuyến",
    "Hiện thực hóa 100% trong `apps/`": "Phạm vi triển khai • kiểm chứng theo từng mục",
    "Tri thức & FactGuard": "Tri thức & đánh giá RAG",
    "Vector `pgvector`, Gold Chunks, đối chiếu regex số học triệt tiêu 100% ảo giác.": "Truy xuất pgvector; đánh giá chunk và số liệu ngoại tuyến, chưa bảo đảm đúng ngữ nghĩa.",
    "Trợ Lý AI RAG & Rào Chắn Số Liệu FactGuard": "Trợ Lý RAG & Đánh Giá Ngoại Tuyến",
    "Cổng 47 • Triệt tiêu 100% Ảo giác Số": "Cần kiểm chứng đúng, đủ và nguồn",
    "Nguyên lý Hoạt động Grounded RAG + FactGuard": "Runtime và bộ chấm là hai luồng riêng",
    ">94.6%</div>": ">Chưa đo</div>",
    ">100%</div>": ">Có giới hạn</div>",
    "Triệt tiêu Ảo giác Số liệu": "Không bảo đảm hết ảo giác",
    "Truy xuất Top-3 đoạn trích vàng (Gold Chunks) từ tài liệu quy chế chuẩn (SOP).": "Truy xuất đoạn phù hợp trong workspace; gold chunk chỉ là nhãn đánh giá, không mặc định là kết quả runtime.",
    "và đối chiếu với Gold Chunks.": "và đối chiếu rubric có nhãn khi đánh giá ngoại tuyến.",
    "Tập trung duy nhất vào Bán lẻ thiết bị công nghệ & Dịch vụ kỹ thuật IT (Quy chế đổi trả 7 ngày, quy trình bảo hành, cam kết SLA 30 phút / 2 giờ).": "Ngữ liệu demo bán lẻ và dịch vụ IT; không thay thế chính sách thương mại được duyệt.",
    "Đóng góp cơ chế rào chắn số liệu FactGuard bảo vệ doanh nghiệp khỏi các rủi ro pháp lý và cam kết sai lệch của trí tuệ nhân tạo.": "Tách nguồn, tool và bộ chấm ngoại tuyến; vẫn cần người đánh giá ngữ nghĩa, không bảo đảm loại bỏ mọi phản hồi sai.",
}
for old, new in replacements.items():
    text = text.replace(old, new)
lines = []
for line in text.splitlines():
    if "Đo lường Độ bao phủ Thực nghiệm (Coverage):" in line:
        line = '                                <li><strong>Coverage chưa xác minh:</strong> Thiếu actual/prediction/bounds để tái tính; không coi dải hiển thị là khoảng tin cậy đã hiệu chỉnh.</li>'
    if "Độ Bao phủ 100% SKU:" in line:
        line = '                                <li><strong>Kiểm tra tồn kho:</strong> Chạy <code>check_fulfillment_stock</code> trên dữ liệu demo hiện tại; không dùng số SKU cố định thay kết quả kiểm tra.</li>'
    lines.append(line)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
