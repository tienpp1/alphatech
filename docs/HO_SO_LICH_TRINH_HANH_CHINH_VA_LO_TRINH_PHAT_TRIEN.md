> **ĐỐI CHIẾU 24/09/2026:** Dùng bản đề cương user xác nhận đã duyệt và PDF khoa gốc. Mục 3/6 đóng về đối chiếu phạm vi/lịch, không chứng nhận đã nghiệm thu sản phẩm hoặc đã nộp/bảo vệ.

# HỒ SƠ ĐỐI CHIẾU LỊCH TRÌNH HÀNH CHÍNH VÀ LỘ TRÌNH PHÁT TRIỂN MỞ RỘNG (GATES 3 & 6)

**Mã cổng nghiệm thu:** Gate 3 & Gate 6 (`docs/CHECKLIST_97_PROGRESS.md`)  
**Trạng thái:** Đã đối chiếu nguồn cho mục 3 và 6  
**Phạm vi:**  
- **Cổng 3:** Xác nhận phạm vi phụ lục lộ trình mở rộng (Future Roadmap); phân định rạch ròi giữa các chức năng đã triển khai và các hướng phát triển tương lai trong bản thuyết minh tốt nghiệp.  
- **Cổng 6:** Phân biệt rạch ròi giữa lịch trình phát triển kỹ thuật nội bộ của nhóm tác giả với khung mốc hành chính đào tạo chính thức của Khoa/Trường (Hạn nộp bản thảo, Duyệt của GVHD, Lễ bảo vệ Hội đồng).

---

## 1. Cơ sở pháp lý & Nguyên tắc học thuật

Trong quá trình bảo vệ đồ án / khóa luận tốt nghiệp:
1. **Nguyên tắc ranh giới nghiệm thu (Scope Boundary Principle):**  
   Hội đồng chấm khóa luận đánh giá dựa trên những gì sinh viên **đã thực sự xây dựng, thử nghiệm và chứng minh được bằng dữ liệu thực tế**. Bất kỳ nội dung nào thuộc về ý tưởng mở rộng nhưng chưa triển khai bắt buộc phải được xếp vào mục *"Hướng phát triển tương lai"* (Future Work / Extension Roadmap) để không gây hiểu lầm là chức năng đã hoàn thành.
2. **Nguyên tắc phân định tiến độ (Timeline Separation Principle):**  
   Tiến độ phát triển kỹ thuật (Development Sprints / Batches) phản ánh quá trình kỹ thuật của nhóm lập trình. Khung mốc hành chính (Academic Milestones) tuân thủ quy chế đào tạo đại học của Khoa/Trường. Hai trục thời gian này có ý nghĩa khác nhau và phải được trình bày tách biệt.

---

## 2. Giải quyết Cổng 3 — Phụ lục Lộ trình Mở rộng (Future Development Roadmap)

### 2.1. Quyết định định hướng đã thống nhất
Theo phản hồi xác nhận của sinh viên/người dùng:  
*Phụ lục về lộ trình mở rộng được giữ lại trong cấu trúc bản thuyết minh Word và tài liệu kỹ thuật, nhưng gắn nhãn minh bạch là "Hướng phát triển tương lai", tuyệt đối không dùng làm căn cứ đánh giá nghiệm thu hiện tại.*

### 2.2. Ma trận phạm vi triển khai vs Hướng phát triển tương lai

Ma trận là phân loại phạm vi, không thay thế nghiệm thu từng chức năng; trạng thái thực theo CHECKLIST_97_PROGRESS.md.

| Phân hệ / Nghiệp vụ | Phạm vi triển khai (kiểm chứng riêng từng mục) | HƯỚNG PHÁT TRIỂN TƯƠNG LAI (Future Work — Post-Graduation) |
|---|---|---|
| **1. Bán lẻ (Retail Commerce)** | Quản lý sản phẩm, danh mục, nhà cung cấp, nhập kho, kiểm kê, đơn hàng đa kênh, trừ/hoàn tồn kho an toàn (Store Pickup & Home Delivery). | Tích hợp máy quét mã vạch POS cầm tay phần cứng, hóa đơn điện tử e-VAT kết nối trực tiếp Tổng cục Thuế, tự động định giá động theo AI (Dynamic Pricing Engine). |
| **2. Dịch vụ Kỹ thuật (Service Ops)** | Vòng đời phiếu sự cố, phân công kỹ thuật viên, tính giờ công lao động, lập lịch dispatch, cam kết SLA giờ hành chính. | Ứng dụng di động (Mobile App) cho kỹ thuật viên ngoài hiện trường (React Native / Flutter) hỗ trợ GPS tracking thời gian thực trên bản đồ vệ tinh. |
| **3. Không gian Địa lý (GIS)** | Tìm kiếm chi nhánh gần nhất theo Geodesic WGS84, khóa advisory lock Nominatim với cache 24h, phân cấp sai số GPS. | Tích hợp thuật toán định tuyến giao thông thời gian thực (Traffic-aware routing OSRM / Google Maps Directions API) tránh kẹt xe theo giờ cao điểm. |
| **4. Trợ lý AI & RAG** | RAG trên 24 tài liệu SOP nội bộ, trích xuất đại lượng số học regex, đo chunk precision/recall, phân lập tenant. | Triển khai mô hình cục bộ On-Premise LLM (Llama 3 8B / Qwen 2.5 7B quantized) chạy trên máy chủ GPU doanh nghiệp độc lập hoàn toàn với internet. |
| **5. Dự báo Doanh thu (ML)** | Mô hình XGBoost dự báo doanh thu bán lẻ ngày, phân tích lỗi/horizon, Data Catalog chuẩn hóa. | Nâng cấp mô hình Deep Learning chuỗi thời gian (PatchTST, Temporal Fusion Transformer - TFT) khi tích lũy đủ dữ liệu lịch sử trên 3 năm. |
| **6. Kiến trúc Hệ thống** | Modular Monolith trên Django 5.x + PostgreSQL 18 + PostGIS + pgvector (Tối ưu cho doanh nghiệp vừa và nhỏ). | Phân rã Microservices hoàn chỉnh với Kubernetes (K8s) và Kafka Event Bus khi quy mô giao dịch vượt 100.000 đơn/ngày. |

---

## 3. Giải quyết Cổng 6 — Phân biệt Lịch Kỹ thuật với Mốc Hành chính của Khoa

### 3.1. Phân biệt Bản chất Hai Trục Thời gian
1. **Trục Tiến độ Kỹ thuật (Engineering Delivery Chronicle):**
   - Phản ánh chuỗi 50 đợt kiểm thử và hoàn thiện (Batches 01–50) được ghi nhận chi tiết trong `docs/CHANGELOG_AI.md` và `docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md`.
   - Kết thúc khi 100% mã nguồn, bài kiểm thử tự động (1.056+ tests) và hồ sơ nghiệm thu kỹ thuật đạt chuẩn.
2. **Trục Mốc Hành chính Đào tạo (Faculty Administrative Milestones):**
   - Tuân thủ lịch trình chính thức của Ban Chủ nhiệm Khoa Công nghệ Thông tin và Phòng Đào tạo trường Đại học.
   - Gồm các mốc hành chính: nộp bản thảo duyệt, nhận xét của GVHD, nộp quyển chính thức cho Hội đồng, và Lễ bảo vệ khóa luận.

### 3.2. Mốc chính thức theo thông báo khoa

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
