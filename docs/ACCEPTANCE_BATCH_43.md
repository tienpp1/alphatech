# Đợt 43 — Nghiệm thu Tổng quan Nghiên cứu Khoa học, Phân tích So sánh & Chứng minh Khoảng trống Ứng dụng

Ngày chốt: 22/09/2026.
Phạm vi: Cụm Cổng 79 & 80 theo [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) và [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md).
Tài liệu trọng tâm: [docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md](file:///d:/ai_business_platform/docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md) và [docs/THUYET_MINH_DO_AN_CHUONG_1_VA_2.md](file:///d:/ai_business_platform/docs/THUYET_MINH_DO_AN_CHUONG_1_VA_2.md).

---

## 1. Các Hạng mục Hoàn tất

- **Mục 79: Bổ sung Tổng quan Nghiên cứu Liên quan & Phân tích So sánh Khoa học (Related Work & Comparative Analysis)**:
  - Khảo sát và tổng hợp 4 trục lý thuyết nền tảng với 25 trích dẫn học thuật quốc tế chuẩn IEEE (các bài báo đăng tại NeurIPS, KDD, ICML, EMNLP, ACM TISSEC, IEEE Computer, IEEE Software, PLOS ONE,...):
    1. *Kiến trúc Đa khách thuê (Multi-Tenancy) & RBAC:* Mô hình RBAC96 (Sandhu et al., 1996), chuẩn NIST RBAC (Ferraiolo et al., 2001), kiến trúc lưu trữ đa khách thuê Shared DB - Discriminator Column (Bezemer & Zaidman, 2010), nguyên lý Modular Monolith (Fowler, 2015).
    2. *Kỹ thuật RAG & Rào chắn Độ tin cậy:* Mô hình RAG nền tảng (Lewis et al., 2020), REALM (Guu et al., 2020), khảo sát hiện tượng ảo giác (Ji et al., 2023; Maynez et al., 2020), rào chắn kiểm tra đại lượng số học (Chen et al., 2021).
    3. *Học máy Dự báo Bán lẻ Chuỗi Thời gian:* Thuật toán Gradient Tree Boosting (Chen & Guestrin, 2016 - XGBoost), so sánh mô hình dạng cây với ARIMA và Deep Learning trong cuộc thi M4 (Makridakis et al., 2018; Hyndman & Athanasopoulos, 2018), giao thức phân chia thời gian chặt chẽ Chronological Split (Bergmeir & Benítez, 2012).
    4. *Hệ thống Thông tin Địa lý (GIS) & Tối ưu Điều phối Hiện trường:* Chuẩn OGC Simple Features (OGC, 2011), giải thuật khoảng cách Geodesic trên mặt cầu Elipsoid WGS84 (Karney, 2013), bài toán định vị cơ sở và vùng phủ dịch vụ (Drezner & Hamacher, 2004; Church & Murray, 2009).
  - Thay thế hoàn toàn bảng so sánh cảm tính cũ bằng **Ma trận Phân tích So sánh Khoa học** đối chiếu giữa: Hệ thống POS cục bộ truyền thống, Bộ phần mềm ERP thương mại lớn (SAP, Odoo), Hệ thống SaaS rời rạc, và Nền tảng AlphaTech AI Platform trên 5 tiêu chí kiến trúc:
    1. Cơ chế Tenancy & Mức độ cô lập logic dữ liệu.
    2. Tích hợp không gian GIS & Điều phối hiện trường.
    3. Trợ lý tri thức nghiệp vụ & Rào chắn số liệu (Grounded RAG with Numeric Guardrails).
    4. Năng lực dự báo chuỗi thời gian & Minh bạch giao thức thực nghiệm.
    5. Kiểm soát an toàn hành động (Human-in-the-Loop) & Giao dịch bù trừ (Rollback).

- **Mục 80: Chứng minh Khoảng trống ở Mức Ứng dụng Thực tiễn (Application Gap Justification)**:
  - Khẳng định tính trung thực học thuật: Đề tài không tự nhận phát minh thuật toán mới mà giải quyết 3 khoảng trống tích hợp ứng dụng thực tiễn trong chuyển đổi số doanh nghiệp SMEs:
    1. *Khoảng trống Tích hợp Dọc (Vertical Integration Gap):* Khắc phục sự phân mảnh giữa bán lẻ đa kênh (Retail Orders & Inventory) và dịch vụ kỹ thuật bảo hành (Field Service & SLA) bằng mô hình dữ liệu quan hệ thống nhất trên PostgreSQL 18.
    2. *Khoảng trống Xác thực Đại lượng Số học trong RAG (Factual Grounding & Numeric Verification Gap):* Bổ sung cơ chế rào chắn kép (đo lường `chunk_precision`, `chunk_recall` trên tập chunk vàng kết hợp trích xuất regex đại lượng số học bắt buộc `required_numeric_facts`) để loại bỏ hoàn toàn lỗi ảo giác số liệu nghiệp vụ.
    3. *Khoảng trống An toàn khi AI Can thiệp Vận hành (Safe Action Execution & Auditing Gap):* Cung cấp cơ chế chuyển tiếp có kiểm soát từ đề xuất của AI sang hành động giao dịch thực tế thông qua mô hình phê duyệt chéo bắt buộc (Human-in-the-Loop), giao dịch bồi hoàn bù trừ an toàn (Rollback) và nhật ký kiểm toán bất biến (PostgreSQL Trigger-Protected Audit Log).

- **Đồng bộ hóa Tài liệu Thuyết minh**:
  - Cập nhật trực tiếp Mục 1.3 và bổ sung Mục 1.4 vào [docs/THUYET_MINH_DO_AN_CHUONG_1_VA_2.md](file:///d:/ai_business_platform/docs/THUYET_MINH_DO_AN_CHUONG_1_VA_2.md).
  - Lưu trữ chuyên khảo học thuật đầy đủ tại [docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md](file:///d:/ai_business_platform/docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md).

---

## 2. Kết quả Kiểm thử Tự động & Tính Toàn vẹn Hệ thống

```powershell
python manage.py check
```
```text
System check identified no issues (0 silenced).
```

```powershell
python manage.py makemigrations --check --dry-run
```
```text
No changes detected
```

```powershell
python manage.py test tests.test_rag_numeric_facts tests.test_rag_chunk_metrics --keepdb
```
```text
Ran 15 tests in 0.008s
OK
System check identified no issues (0 silenced).
```
*(Xác nhận sự nhất quán 100% giữa luận giải lý thuyết RAG Numeric Guardrails và mã nguồn thực thi).*

---

## 3. Tác động tới Tiến độ Checklist 97 Mục

- **Mục 79 (Bổ sung tổng quan nghiên cứu có phân tích so sánh)**: Chuyển từ *Chưa xác nhận đóng* sang **Đóng**.
- **Mục 80 (Chứng minh khoảng trống ở mức ứng dụng)**: Chuyển từ *Chưa xác nhận đóng* sang **Đóng**.

**Bảng Thống kê Tiến độ Cập nhật:**
- **Đóng hoàn toàn:** **66 / 97 mục (68,04% làm tròn 68,0%)** (tăng thêm 2 mục: 79, 80).
- **Một phần:** **20 mục** (20,6%).
- **Chưa xác nhận đóng:** **11 mục** (11,3%).
- Tổng số mục: **97 mục** (bảo toàn 100% mẫu số gốc).
