"""Targeted corrections to working manuscripts, never the approved syllabus."""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]


def replace(path, pairs):
    text = path.read_text(encoding="utf-8")
    for old, new in pairs:
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")


def main():
    path = ROOT / "docs/THUYET_MINH_DO_AN_CHUONG_1_VA_2.md"
    text = path.read_text(encoding="utf-8")
    start, end = text.index("Thay vì đưa ra"), text.index("## 1.4.")
    text = text[:start] + '''Bảng sau đối chiếu nhu cầu của kịch bản đồ án với cách triển khai và giới hạn.
Không dùng nhận xét chưa kiểm chứng về SAP, Odoo hoặc các sản phẩm thương mại
để chứng minh đề tài tốt hơn thị trường.

| Nhu cầu | Triển khai | Giới hạn kiểm chứng |
|---|---|---|
| Phân quyền và phân lập | Workspace, membership và permission tại view/service | Không suy ra an toàn tuyệt đối từ các test đã chạy |
| Bản đồ và tìm chi nhánh | PostGIS cho khoảng cách địa lý, Leaflet/OSM và OSRM cho bản đồ/tuyến đường | Không bảo đảm đường ngắn nhất tuyệt đối hoặc giao thông trực tiếp |
| Hỏi đáp có nguồn | Truy xuất tài liệu và công cụ đọc có quyền; chấm số/chunk ở pipeline offline | Không có Numeric FactGuard bắt buộc tại runtime; cần đánh giá ngữ nghĩa |
| Dự báo | XGBoost so với lag-7 và MA-7, giữ kết quả kém baseline | Dữ liệu tổng hợp không chứng minh hiệu quả kinh doanh |
| Hành động có kiểm soát | Registry, người duyệt khác người đề xuất, transaction và audit | Chỉ áp dụng action có contract; DB rollback không hoàn tác mọi side effect ngoài DB |

---

''' + text[end:]
    text = text.replace("Khắc phục triệt để hiện tượng ảo giác số liệu của các mô hình ngôn ngữ lớn bằng cơ chế rào chắn kép: đo lường truy xuất ở cấp độ chunk vàng (`chunk_recall`, `chunk_precision`) kết hợp trích xuất và đối chiếu bắt buộc biểu thức chính quy số học (`required_numeric_facts`).", "Bổ sung phép đo offline cho retrieval và đại lượng số dựa trên rubric. Regex không kiểm chứng đầy đủ ngữ nghĩa; không tuyên bố loại bỏ ảo giác hoặc dùng bộ chấm như rào chắn runtime.")
    text = text.replace("đảm bảo cô lập hoàn toàn", "kiểm soát truy cập và phân lập logic")
    text = text.replace("Xây dựng thuật toán định tuyến và định vị chi nhánh tối ưu dựa trên PostGIS.", "Tích hợp PostGIS để tính khoảng cách địa lý và nhà cung cấp định tuyến đường bộ; không phát minh thuật toán định tuyến.")
    path.write_text(text, encoding="utf-8")
    replace(ROOT / "docs/THUYET_MINH_DO_AN_CHUONG_3_4_5.md", [
        ("ranh giới an toàn tuyệt đối", "ranh giới phân quyền và sở hữu dữ liệu"),
        ("100% các câu truy vấn cơ sở dữ liệu đều đi qua Django ORM với tham số hóa (Parameterized Queries). Các câu truy vấn không gian phức tạp đều sử dụng biến an toàn `%s`, tuyệt đối không ghép chuỗi SQL trực tiếp.", "Django ORM và SQL tham số hóa được sử dụng trong các luồng đã rà soát. Mã nguồn còn có SQL trực tiếp (ví dụ advisory lock, migration trigger); cần kiểm tra từng vị trí, không suy ra toàn bộ SQL đều an toàn."),
        ("Quản lý kho tri thức SOP, vector hóa văn bản và trợ lý RAG FactGuard.", "Quản lý SOP, vector hóa, RAG runtime và bộ đánh giá số liệu offline riêng."),
        ("đảm bảo tính tuần tự hóa tuyệt đối", "kiểm soát tranh chấp trong giao dịch đã kiểm thử"),
        ("Cung cấp một nền tảng quản trị vận hành hoàn chỉnh, sẵn sàng triển khai cho các chuỗi doanh nghiệp bán lẻ thiết bị công nghệ và dịch vụ bảo hành - sửa chữa kỹ thuật vừa và nhỏ (SMEs) tại Việt Nam với chi phí phần mềm và hạ tầng tối thiểu.", "Cung cấp bản triển khai phục vụ kịch bản đồ án bán lẻ và dịch vụ. Chưa chứng nhận sẵn sàng production, chi phí tối thiểu hay hiệu quả tại doanh nghiệp thật."),
        ("đảm bảo bảo mật tuyệt đối dữ liệu nội bộ không đi qua Internet", "giảm phụ thuộc API ngoài; vẫn cần kiểm soát mạng, quyền truy cập và telemetry, không bảo đảm bảo mật tuyệt đối"),
        ("Khi quy mô doanh nghiệp vượt quá 100 chi nhánh", "Khi có số liệu tải và yêu cầu vận hành chứng minh cần tách dịch vụ"),
    ])
    path = ROOT / "docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'- \*\*Hiện tượng Ảo giác.*', '- **Giới hạn factuality:** Ji et al. [11] và Maynez et al. [12] nghiên cứu ảo giác và tính trung thực của văn bản sinh. Không quy đổi thành tỷ lệ 15–30% cho hệ thống này. FinQA [13] đánh giá suy luận số học trên dữ liệu tài chính, không chứng minh regex loại bỏ ảo giác trong SOP hoặc SLA.', text)
    text = text.replace("giảm thiểu 70% sai sót cấu hình so với mô hình danh sách kiểm soát truy cập (ACL) truyền thống", "không cung cấp bằng chứng cho tỷ lệ giảm lỗi cấu hình cụ thể của đồ án này")
    text = text.replace('10.1145/2939672.2945397', '10.1145/2939672.2939785')
    text = text.replace('[13] W. Chen et al., "Program Synthesis for Reading Comprehension on Financial Reports," in Proc. 2021 Conf. on Empirical Methods in Natural Language Processing (EMNLP \'21), pp. 3201-3213, 2021.', '[13] Z. Chen et al., "FinQA: A Dataset of Numerical Reasoning over Financial Data," in Proc. EMNLP, pp. 3697–3711, 2021, doi: 10.18653/v1/2021.emnlp-main.300.')
    # Remove the unused preprint entry and renumber later entries/citations together.
    if '[14] R. Thoppilan' in text:
        text = re.sub(r'^\[14\] R\. Thoppilan.*\n', '', text, flags=re.M)
        text = re.sub(r'\[(\d+)\]', lambda m: '[' + str(int(m[1])-1 if int(m[1]) > 14 else int(m[1])) + ']', text)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
