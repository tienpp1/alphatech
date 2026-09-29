# HỒ SƠ RÀ SOÁT TÀI LIỆU SOP VÀ PHÂN ĐỊNH TRỌNG TÂM NGHIỆP VỤ (GATE 47)

**Mã cổng nghiệm thu:** Gate 47 (`docs/CHECKLIST_97_PROGRESS.md`)  
**Trạng thái:** Đã phân loại ngữ liệu Gate 47; không phải chính sách doanh nghiệp được duyệt (Gate 46 vẫn mở).  
**Phạm vi:** Rà soát toàn bộ 24 tài liệu quy chuẩn vận hành (SOP) trong hệ thống; tập trung rạch ròi vào 2 nghiệp vụ trọng tâm cốt lõi của đề tài: **Bán lẻ Đa kênh (Retail Commerce)** và **Vận hành Dịch vụ Kỹ thuật IT (Service Operations)**; phân định rõ các tài liệu nhân sự, lương thưởng, datacenter làm ngữ liệu thử nghiệm kỹ thuật cho RAG, không làm loãng phạm vi nghiên cứu của đề tài.

---

## 1. Bối cảnh & Yêu cầu của Giảng viên Hướng dẫn

Trong quá trình hướng dẫn, Giảng viên Hướng dẫn (GVHD) và Hội đồng nhận xét:
> *"Đề tài có tên 'Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI', tập trung vào 2 phân hệ nghiệp vụ chính là Bán lẻ và Dịch vụ kỹ thuật. Việc đưa quá nhiều tài liệu chuyên sâu về Nhân sự, Lương thưởng, Pháp lý hợp đồng và Trung tâm dữ liệu (Datacenter) dễ gây hiểu lầm rằng sinh viên phải xây dựng cả phân hệ HRM và quản trị Datacenter hoàn chỉnh, làm loãng trọng tâm nghiên cứu và phản ánh không đúng bản chất sản phẩm."*

Để giải quyết triệt để vấn đề này, Đợt 50 tiến hành rà soát, phân loại và phân vùng khoa học toàn bộ 24 tài liệu SOP đang lưu trữ tại thư mục `data/knowledge/` và cấu hình tại `apps/knowledge/sop_catalog.py`.

---

## 2. Danh mục Phân vùng Tài liệu SOP Khoa học

Toàn bộ 24 tài liệu được phân định thành 2 nhóm với mục đích sử dụng hoàn toàn tách biệt:

### 2.1. Nhóm 1: Tài liệu Nghiệp vụ Trọng tâm Cốt lõi (`PRIMARY_SOPS` — 7 tài liệu)
Đây là các tài liệu mô tả chính xác quy trình vận hành của 2 phân hệ cốt lõi mà hệ thống đã triển khai đầy đủ cả CSDL, API, giao diện web và quyền RBAC:

| STT | Tên Tệp SOP | Phân hệ Nghiệp vụ | Nội dung Trọng tâm Quy chuẩn |
|:---:|---|:---:|---|
| 1 | `SOP_RETAIL_SUPPLY_CHAIN_2026.md` | Bán lẻ (Retail) | Quy trình nhập hàng từ nhà cung cấp, kiểm đếm chất lượng hàng hóa khi nhập kho. |
| 2 | `SOP_RETAIL_FINANCIAL_MARGIN_2026.md` | Bán lẻ (Retail) | Quản lý biên lợi nhuận, chi phí vốn hàng bán (COGS) và chính sách chiết khấu giá bán lẻ. |
| 3 | `SOP_INTER_BRANCH_TRANSFER_2026.md` | Bán lẻ (Retail) | Quy trình điều chuyển tồn kho giữa 3 chi nhánh (`BR-D1`, `BR-BT`, `BR-D7`) và bù trừ số dư. |
| 4 | `SOP_RETAIL_RMA_WARRANTY_2026.md` | Bán lẻ (Retail) | Quy chuẩn đổi trả hàng bảo hành (RMA), thời hạn đổi trả 7 ngày lỗi NSX. |
| 5 | `SOP_OMNICHANNEL_FULFILLMENT_2026.md` | Bán lẻ (Retail) | Quy trình xử lý đơn hàng đa kênh: Nhận tại cửa hàng (Pickup) và Giao hàng tận nơi (Home Delivery). |
| 6 | `SOP_RETAIL_INVENTORY_AUDIT_2026.md` | Bán lẻ (Retail) | Quy trình kiểm kê định kỳ, đối soát số lượng thực tế với phần mềm, xử lý lệch kho. |
| 7 | `SOP_SERVICE_OPS_INCIDENT_SLA_2026.md` | Dịch vụ (Service) | Phân loại mức độ ưu tiên sự cố (Critical/High/Medium/Low), cam kết thời gian phản hồi và xử lý SLA. |

---

### 2.2. Nhóm 2: Ngữ liệu Thử nghiệm Kỹ thuật RAG (`SUPPLEMENTARY_SOPS` — 17 tài liệu)
Toàn bộ 17 tài liệu còn lại (gồm 6 tài liệu nhân sự `SOP_CORE_*`, quy chuẩn Datacenter, an ninh mạng, thanh lý tài sản...) được xếp vào **Phụ lục Ngữ liệu Thử nghiệm Kỹ thuật RAG (RAG Benchmark Fixtures)** với các vai trò thực nghiệm sau:
1. **Kiểm thử đối kháng (Adversarial Testing):** Kiểm tra xem Trợ lý AI có bị dẫn dụ trả lời nhầm sang các chủ đề nhạy cảm về lương thưởng hay không.
2. **Kiểm tra ranh giới phân quyền Multi-Tenant:** Xác nhận rằng nhân viên ở tổ chức Bán lẻ không thể truy xuất được các tài liệu thuộc phòng ban hạ tầng nội bộ nếu không được phân quyền.
3. **Đo lường độ chính xác phân loại ý định (Intent Routing Precision):** Cung cấp các văn bản đa dạng ngữ nghĩa để đánh giá bộ phân loại câu hỏi (Router) có nhận diện chính xác câu hỏi nằm ngoài phạm vi nghiệp vụ (`OUT_OF_SCOPE`) hay không.

Danh mục 17 tài liệu ngữ liệu thử nghiệm:
- **Nhóm Nhân sự & Đời sống nội bộ (6 tài liệu):**  
  `SOP_CORE_WORKING_HOURS_LEAVE_2026.md`, `SOP_CORE_EXPENSE_TRAVEL_REIMBURSEMENT_2026.md`, `SOP_CORE_IT_SECURITY_DEVICE_USAGE_2026.md`, `SOP_CORE_ONBOARDING_PROBATION_2026.md`, `SOP_CORE_CODE_OF_CONDUCT_CULTURE_2026.md`, `SOP_CORE_PERFORMANCE_BENEFITS_BONUS_2026.md`.
- **Nhóm Hạ tầng Kỹ thuật Chuyên sâu & Hỗ trợ (11 tài liệu):**  
  `SOP_CUSTOMER_RETENTION_LOYALTY_2026.md`, `SOP_SUPPLIER_CONTRACT_PENALTIES_2026.md`, `SOP_RETAIL_PROMO_FRAUD_2026.md`, `SOP_RETAIL_TRADE_IN_2026.md`, `SOP_FIELD_ENGINEERING_SAFETY_2026.md`, `SOP_CYBERSECURITY_INCIDENT_DRP_2026.md`, `SOP_SLA_ESCALATION_DISPUTE_2026.md`, `SOP_DATACENTER_THERMAL_ENERGY_2026.md`, `SOP_SVC_CHANGE_MANAGEMENT_2026.md`, `SOP_SVC_ASSET_DECOMMISSION_2026.md`, `SOP_SVC_BACKUP_RETENTION_2026.md`.

---

## 3. Bằng chứng Kiểm thử Tự động (Automated Test Evidence)

Kiến trúc phân loại này được bảo vệ chặt chẽ bằng bài kiểm thử hồi quy tự động trong [tests/test_sop_catalog.py](file:///d:/ai_business_platform/tests/test_sop_catalog.py):

```python
def test_hr_datacenter_not_primary_academic_cases(self):
    """Xác nhận không tài liệu HR hay Datacenter nào bị lẫn vào danh mục Primary."""
    self.assertFalse(any('SOP_CORE_' in name or 'DATACENTER' in name for name in PRIMARY_SOPS))
    self.assertEqual(len(PRIMARY_SOPS) + len(SUPPLEMENTARY_SOPS), 24)
```

Kết quả thực thi kiểm thử:
```text
tests.test_sop_catalog (4 tests in 0.006s) — OK (PASS 100%)
```

---

## 4. Kết luận Nghiệm thu Gate 47

| Tiêu chuẩn Đánh giá | Trạng thái | Minh chứng Cụ thể |
|---|:---:|---|
| Không làm loãng 2 nghiệp vụ chính (Bán lẻ & Dịch vụ IT) | **ĐẠT** | 7 tài liệu `PRIMARY_SOPS` độc quyền bao phủ Bán lẻ & Dịch vụ IT |
| Phân loại rạch ròi tài liệu nhân sự, lương, Datacenter | **ĐẠT** | 17 tài liệu được định danh là Phụ lục Ngữ liệu Thử nghiệm RAG |
| Không ngụy tạo chức năng HRM hay quản lý Datacenter | **ĐẠT** | Khẳng định không cam kết phần mềm Nhân sự/Datacenter trong đề tài |
| Kiểm thử tự động bảo toàn cấu trúc phân loại | **ĐẠT** | `tests/test_sop_catalog.py` pass 4/4 ca kiểm thử |

**Quyết định:** Chuyển trạng thái Gate 47 từ **Chưa xác nhận đóng** sang **Đóng hoàn toàn (Closed)**.
