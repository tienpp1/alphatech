# Đợt 41 — Nghiệm thu Siết chặt Dẫn chứng Tri thức RAG, Đánh giá Ngữ nghĩa & Số liệu

Ngày chốt: 22/09/2026.
Phạm vi: Cụm Cổng 29, 30, 35, 36, 39 theo [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) và [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md).

---

## 1. Các Hạng mục Hoàn tất

- **Mục 29 & 39: Đánh giá đủ ý và đúng số liệu (Factual & Numerical Accuracy)**:
  - Loại bỏ hoàn toàn cơ chế chấm đạt bằng một từ khóa chung chung.
  - Áp dụng cấu trúc `required_numeric_facts` với regex trích xuất đại lượng số (thời hạn bảo hành, SLA, tỷ lệ) và đối chiếu chính xác giá trị kỳ vọng.
  - Áp dụng `required_keyword_groups` bắt buộc phải thỏa mãn tất cả các nhóm ngữ nghĩa cần thiết trước khi công nhận kết quả.
  - Phân tích rõ ràng giới hạn của câu phủ định (ví dụ: "Không bảo hành 24 tháng" chứa số 24 nhưng mang nghĩa phủ định sai) và ghi nhận rõ trong tài liệu học thuật.
- **Mục 30: Đo lường truy xuất ở cấp độ đoạn tri thức (Gold Chunk Recall & Precision)**:
  - Tính toán chính xác `chunk_recall` và `chunk_precision` trên danh sách định danh đoạn tri thức chuẩn (`expected_chunk_ids`).
  - Phạt nặng các đoạn trích dẫn không liên quan hoặc trùng lặp, bảo đảm chỉ những câu trích đúng đoạn tài liệu chứa căn cứ mới được tính điểm.
- **Mục 35 & 36: Ghi nhận minh bạch Embedding Provenance và Tách bạch Live vs Offline**:
  - Ghi nhận đầy đủ metadata `embedding_provenance` trên từng chunk: `mode` (DETERMINISTIC / LIVE), `provider`, `model`, `dimension`, và `fallback_reason`.
  - Phân biệt rõ ràng giữa mô hình ngoại tuyến thử nghiệm và dịch vụ live API; không lấy kết quả fallback làm bằng chứng đánh giá năng lực Gemini.
  - Vector kế thừa cũ không rõ nguồn gốc được gắn nhãn minh bạch `UNKNOWN`, không suy diễn tự động từ cấu hình hiện tại.
- **Kiểm chứng Bộ ca Đối kháng (Adversarial Robustness Testing)**:
  - `ADV-PARAPHRASE-01`: Diễn đạt khác nhau nhưng cùng quy về câu trả lời chuẩn xác có dẫn nguồn.
  - `ADV-MISSING-01`: Nhận diện sản phẩm/dữ liệu chưa từng xuất hiện và thông báo thiếu dữ liệu, không bịa đặt nguồn.
  - `ADV-CONFLICT-01`: Phát hiện mâu thuẫn giữa 2 văn bản nội bộ (12 tháng vs 24 tháng) và yêu cầu người dùng xác nhận, không tự chọn thiên lệch.
  - `ADV-PERMISSION-01` & `ADV-TENANT-01`: Ngăn chặn tuyệt đối truy vấn khi người dùng thiếu quyền `ai.chat` hoặc truy vấn chéo Workspace (Quy tắc 3 & 4 trong AGENTS.md).
- **Nghiệm thu Trực quan Trình duyệt (Live Browser Verification)**:
  - Trực tiếp kiểm thử giao diện Trợ lý AI tại `http://127.0.0.1:8000/noibo/ai/assistant/`.
  - Kiểm chứng câu trả lời trích dẫn chính xác nội quy nội bộ (*Nội Quy Lao Động, Thời Giờ Làm Việc, Chấm Công & Nghỉ Phép Năm 2026*) kèm thẻ trích dẫn đoạn (Đoạn trích #398, độ khớp 38%).

---

## 2. Kết quả Kiểm thử Tự động

```powershell
python manage.py test tests.test_rag_numeric_facts tests.test_rag_chunk_metrics tests.test_rag_evaluation_scoring tests.test_embedding_space_isolation tests.test_embedding_provenance tests.test_generation_provenance tests.test_adversarial_rag_execution tests.test_rag_security_rbac --keepdb
```

```text
Ran 56 tests in 119.335s
OK
System check identified no issues (0 silenced).
```

- **56/56 tests đạt PASS 100%**, bao gồm:
  - 8 ca kiểm thử số liệu và đại lượng số học (`test_rag_numeric_facts.py`).
  - 8 ca kiểm chứng chỉ số chunk recall / chunk precision (`test_rag_chunk_metrics.py`).
  - 9 ca kiểm thử scoring rubric và summarize (`test_rag_evaluation_scoring.py`).
  - 5 ca kiểm thử cô lập không gian vector đa Workspace (`test_embedding_space_isolation.py`).
  - 4 ca kiểm thử lưu vết nguồn gốc vector embedding (`test_embedding_provenance.py`).
  - 5 ca kiểm chứng metadata sinh câu trả lời (`test_generation_provenance.py`).
  - 6 ca kiểm thử toàn diện quy trình đối kháng offline (`test_adversarial_rag_execution.py`).
  - 11 ca kiểm thử phân quyền RBAC và chặn truy cập trái phép (`test_rag_security_rbac.py`).

---

## 3. Minh chứng Trực quan Trình duyệt (Browser Verification Artifacts)

- `ai_assistant_grounded_qa_1790068101670.png`: Ảnh chụp màn hình giao diện Trợ lý Tri thức AI, câu trả lời dẫn chứng và panel trích dẫn nguồn văn bản.
- `ai_assistant_flow_1790067784506.webp`: Video toàn bộ luồng tương tác thực tế của browser subagent.

---

## 4. Tác động tới Tiến độ Checklist 97 Mục

- **Mục 29 (Sửa cách chấm một keyword)**: Chuyển sang **Đóng**.
- **Mục 30 (Sửa cách đo retrieval, đo cấp độ chunk)**: Chuyển sang **Đóng**.
- **Mục 35 (Tách kết quả API thật và fallback)**: Chuyển sang **Đóng**.
- **Mục 36 (Ghi nhận model/embedding thực sự sử dụng)**: Chuyển sang **Đóng**.
- **Mục 39 (Đánh giá đủ ý và đúng số liệu)**: Chuyển sang **Đóng**.
- Tiến độ: Tăng thêm 5 mục hoàn thành từ 53/97 lên **58/97 (59,8%)**. Số mục một phần giảm từ 28 xuống **23 mục**.
