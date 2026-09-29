"""Narrow, repeat-safe corrections; preserves bibliography and historical batches."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md"
text = path.read_text(encoding="utf-8")
start = text.index("## 3.")
end = text.index("## 4.", start)
text = text[:start] + '''## 3. KHOẢNG TRỐNG Ở MỨC ỨNG DỤNG VÀ PHẠM VI CHỨNG MINH

Đây là các nhu cầu của kịch bản đồ án bán lẻ thiết bị và dịch vụ kỹ thuật,
không phải kết quả khảo sát thị trường hay chứng minh tính mới của thuật toán.
Không suy ra "đa số doanh nghiệp" hoặc "đa số hệ thống RAG" thiếu chức năng
khi chưa có dữ liệu khảo sát. Việc ghép Django, RAG, PostGIS và XGBoost tự nó
không chứng minh đóng góp khoa học mới.

### 3.1. Nhu cầu vận hành bán lẻ và dịch vụ trong một cổng

- **Vấn đề của kịch bản:** nhân viên cần truy cập đơn hàng, tồn kho và phiếu dịch vụ trong phạm vi được phân quyền; khách hàng cần cổng riêng theo dõi giao dịch.
- **Cách triển khai:** các app retail/service_ops dùng kiến trúc chung và dữ liệu workspace-scoped. Workspace bán lẻ và dịch vụ vẫn có thể tách nhau; không tuyên bố mọi Order đã liên kết với ServiceRequest hoặc có tự động tra bảo hành từ đơn hàng nếu chưa có quan hệ/chức năng đó.
- **Nguồn kiểm tra:** `apps/public_web/fulfillment.py`, `apps/service_ops/services.py`, `apps/workspaces/authorization.py`; tests `test_checkout_concurrency.py`, `test_service_requests.py`, `test_internal_authorization_regressions.py`.
- **Giới hạn:** demo tích hợp cổng và quyền; chưa đo hiệu quả tài chính hay tiết kiệm thời gian tại doanh nghiệp thật.

### 3.2. Nhu cầu câu trả lời có nguồn và đo chất lượng tách bạch

- **Vấn đề của kịch bản:** trả lời nghiệp vụ cần phân biệt tài liệu, số liệu tool, fallback và câu chưa đủ bằng chứng.
- **Runtime:** `apps/knowledge/services.py` điều phối intent, retrieval, tool có kiểm tra quyền và sinh phản hồi; retrieval ghi provenance/không gian embedding. Nhánh root-cause thiếu dữ liệu yêu cầu bổ sung, không tự đặt giờ SLA hoặc trọng số.
- **Đánh giá ngoại tuyến:** `apps/knowledge/evaluation.py` gọi `evaluation_scoring.py` với rubric có nhãn, kiểm keyword groups, numeric facts và gold chunk IDs. Đây KHÔNG phải bộ chặn runtime tự động từ chối hoặc sửa mọi câu trả lời.
- **Nguồn kiểm tra:** `test_embedding_space_isolation.py`, `test_adversarial_rag_execution.py`, `test_rag_evaluation.py`, `test_root_cause_grounding.py`.
- **Giới hạn:** regex có thể khớp số trong câu phủ định; cần chấm đúng/đủ ngữ nghĩa độc lập. Không có cam kết loại bỏ toàn bộ ảo giác, không dùng test router làm điểm chất lượng LLM.

### 3.3. Nhu cầu kiểm soát hành động từ khuyến nghị

- **Vấn đề của kịch bản:** đề xuất không được mặc nhiên trở thành mutation có quyền quản trị.
- **Cách triển khai:** registry giới hạn action hỗ trợ; kiểm quyền workspace, cấm tự duyệt, quản lý trạng thái/idempotency, thực thi transaction đối với dữ liệu database và ghi audit.
- **Nguồn kiểm tra:** `apps/approvals/registry.py`, `apps/approvals/executor.py`; `test_approval_state_integrity.py`, `test_approval_concurrency_evidence.py`, `test_audit_database_evidence.py`.
- **Giới hạn:** DB rollback không tự hoàn tác side effect bên ngoài; trigger audit không bảo vệ trước mọi quyền quản trị database. Stock reorder/workload balancing chưa có contract đủ an toàn vẫn là advisory; không tuyên bố toàn bộ handler đã nghiệm thu production.

**Tiêu chí mục 80:** mô tả đúng vấn đề của kịch bản, cách triển khai và giới hạn,
không tuyên bố phát minh thuật toán hoặc tính mới chỉ nhờ tích hợp công nghệ.
Danh mục tham khảo mục 4 còn cần rà nguồn theo yêu cầu thầy (mục 89), không được
coi việc đóng ranh giới ứng dụng là đã duyệt tất cả tài liệu tham khảo.

---

''' + text[end:]
path.write_text(text, encoding="utf-8")

path = ROOT / "docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md"
text = path.read_text(encoding="utf-8")
start = text.index("#### Sơ đồ 3:")
end = text.index("#### Sơ đồ 4:", start)
text = text[:start] + '''#### Sơ đồ 3: RAG runtime và đánh giá ngoại tuyến tách riêng

Nguồn: `apps/knowledge/services.py`, `retrieval.py`, `tools.py`,
`evaluation.py` và `evaluation_scoring.py`. Không có Numeric FactGuard runtime
tự chặn mọi phản hồi. Provenance thuộc quá trình embedding/retrieval, không phải
kết quả kiểm chứng ngữ nghĩa. Gold chunk IDs chỉ có trong rubric đánh giá.

```mermaid
sequenceDiagram
    actor Employee as Nhân viên
    participant API as API / Workspace RBAC
    participant Service as Knowledge service
    participant Retrieve as Retrieval workspace-scoped
    participant Tools as Read tools + permission
    participant Generate as Generation / fallback
    participant Eval as Đánh giá ngoại tuyến
    Employee->>API: Câu hỏi
    API->>Service: Sau xác thực/quyền workspace
    Service->>Service: Phân loại intent và tham số
    opt Intent cần tri thức
        Service->>Retrieve: Truy vấn trong workspace, kiểm embedding compatibility
        Retrieve-->>Service: Chunks, similarity và provenance
    end
    opt Intent cần số liệu nghiệp vụ
        Service->>Tools: Tool cho phép và kiểm quyền riêng
        Tools-->>Service: Dữ liệu hoặc denial/error
    end
    Service->>Generate: Ngữ cảnh / tool results / trạng thái thiếu bằng chứng
    Generate-->>API: Phản hồi + citations + metadata
    API-->>Employee: Hiển thị kết quả
    Note over Eval: Chạy riêng khi đánh giá; không chặn phản hồi runtime
    Eval->>Eval: Rubric + output; keyword/numeric/chunk checks
    Note over Eval: Người chấm xác nhận đúng/đủ ngữ nghĩa
```

---

''' + text[end:]
text = text.replace("đã được kiểm chứng bằng mã nguồn, tệp migration, routes thực tế và các bộ kiểm thử tự động đạt tỷ lệ **100% PASS**", "được đối chiếu sơ bộ bằng mã nguồn/migration/routes; kết quả kiểm thử từng lần nằm tại TEST_EXECUTION_EVIDENCE.md và biên bản đợt, không phải toàn bộ 12 nhóm đã pass")
# Historical batch references remain, but remove aggregate pass labels in living tables.
text = text.replace("100% PASS", "kết quả theo log đợt tương ứng, chưa xác nhận lại toàn bộ")
path.write_text(text, encoding="utf-8")

path = ROOT / "docs/THUYET_MINH_DO_AN_CHUONG_3_4_5.md"
text = path.read_text(encoding="utf-8")
start = text.index("### 4.5.1.")
end = text.index("### 4.5.3.", start)
text = text[:start] + '''### 4.5.1. Kết quả thực thi có log

Full suite ngày 23/09/2026: **1.067 tests trong 2.032,520s; 8 failures,
8 errors, 0 skipped; FAILED**. Nguồn và hash tại TEST_EXECUTION_EVIDENCE.md.
Các nhóm sửa lỗi chạy lại được ghi riêng, chưa thay thế một full-suite rerun.

### 4.5.2. Phân biệt inventory và thực thi

Rút lại bảng số lượng test/file phân bổ 12 phân hệ vì chưa có chứng cứ đếm theo
test ID duy nhất. File chung cho chat/bulletin hoặc cross-cutting không được
cộng nhiều lần. Danh mục source ở TEST_EXECUTION_EVIDENCE.md chỉ là inventory.
Số discovery, số lần chạy và coverage là ba đại lượng khác nhau; chưa công bố
coverage toàn hệ thống. Phạm vi chức năng theo ACADEMIC_REQUIREMENTS_MATRIX.md.

''' + text[end:]
text = text.replace("[Knowledge Base RAG & FactGuard]", "[Knowledge Base RAG]            ")
text = text.replace("Vector Search Cosine Similarity + Regex FactGuard Checker", "Retrieval + generation; numeric scoring chạy ngoại tuyến")
path.write_text(text, encoding="utf-8")
