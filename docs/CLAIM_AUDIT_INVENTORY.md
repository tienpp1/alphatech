# HỒ SƠ RÀ SOÁT & CHUẨN HÓA TUYÊN BỐ HỆ THỐNG
## (SYSTEM CLAIM AUDIT INVENTORY & SCIENTIFIC BOUNDARY HARMONIZATION)

**Đề tài**: Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI (AlphaTech AI Platform)  
**Tài liệu tham chiếu**: [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) (Hàng 11), [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md) (Mục 7, 11, 13, 14, 27, 42).  
**Ngày lập**: 22/09/2026.  
**Tình trạng**: Đã hoàn tất kiểm toán và đồng bộ toàn diện trên mã nguồn, giao diện, bộ kiểm thử và hồ sơ thuyết minh.

---

## 1. Mục Đích & Nguyên Tắc Kiểm Toán

Trong quá trình phát triển đồ án từ các phiên bản phác thảo ban đầu đến giai đoạn hoàn thiện học thuật, một số tài liệu lịch sử, chú thích mã nguồn, kịch bản kiểm thử và giao diện người dùng có thể tồn tại các cụm từ phóng đại (hyperbolic statements), các tuyên bố tuyệt đối ("100% hoàn thành", "an toàn tuyệt đối", "không rò rỉ", "zero hallucination"), hoặc sự cộng dồn số lượng kiểm thử gây ngộ nhận về độ bao phủ toàn diện.

Hồ sơ Kiểm toán này được lập nhằm:
1. **Minh bạch hóa toàn bộ các điểm hiệu chỉnh**: Liệt kê chi tiết từng vị trí tệp tin, dòng mã nguồn, nội dung trước và sau khi chuẩn hóa.
2. **Xác lập ranh giới khoa học vững chắc**: Phân định rõ ràng giữa những gì hệ thống **thực sự làm và đã kiểm chứng bằng thực nghiệm** với những giả thuyết, dữ liệu mô phỏng, hoặc phạm vi tương lai.
3. **Tuân thủ quy tắc bảo toàn lịch sử**: Không xóa hoặc giả mạo các nhật ký thực nghiệm trong quá khứ; thay vào đó, đặt các khối cảnh báo truy vết (`historical disclaimer notice`) để phân biệt rành mạch giữa bản ghi lịch sử và tiêu chuẩn học thuật hiện hành.

---

## 2. Bảng Ma Trận Kiểm Toán Chi Tiết Theo 6 Cổng Mở (Gates 7, 11, 13, 14, 27, 42)

### 2.1. Mục 7: Bỏ kết luận "Hoàn thành 100%" chưa có tiêu chí nghiệm thu

| STT | Vị trí Tệp tin | Nội dung Ban đầu (Obsolete / Absolute) | Nội dung Sau Chuẩn hóa (Scientific & Bounded) | Ranh giới Khoa học Được Xác lập |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `docs/HOI_DONG_DEMO_GUIDE.md`<br>(Dòng 253–259) | Bảng tổng kết nghiệm thu ghi 7 phân hệ đạt **"Hoàn thành 100%"**: Bảng điều khiển, XGBoost, Khuyến nghị HITL, Bản đồ GIS, RAG, Ánh xạ SDM, RBAC. | Đổi thành: **"Đã triển khai; đã nghiệm thu theo phạm vi kiểm thử"**, ghi rõ bằng chứng từng phân hệ (đối chiếu baseline, đo Gold Chunk, kiểm soát số học, phân quyền RBAC). | Không tuyên bố hoàn thành 100% khi chưa có tiêu chí nghiệm thu vận hành thực tế; gắn chặt với kết quả test suite cục bộ. |
| 2 | `templates/dashboard/executive_report.html`<br>(Dòng 608–611) | `<div class="val">100%</div>`<br>`<div class="lbl">Tỷ lệ Cô lập Không gian</div>` | `<div class="val">Multi-Tenant</div>`<br>`<div class="lbl">Phân lập Logic Không gian</div>` | Xóa bỏ chỉ số 100% gán sẵn vô căn cứ; hiển thị đúng đặc tính kiến trúc phân lập đa khách thuê (Multi-Tenancy). |
| 3 | `docs/ACADEMIC_EVALUATION_REPORT.md`<br>(Mục 5) | Bảng 7 mục tiêu từng gắn nhãn "Hoàn thành 100%". | Đã chuyển thành: *"Đã triển khai; nghiệm thu giới hạn / cần nghiệm thu dữ liệu / chất lượng còn giới hạn / kết quả không đồng nhất"*. | Đính chính có giá trị truy vết từ Đợt 17, loại bỏ triệt để mọi nhãn hoàn thành tuyệt đối. |
| 4 | `docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md`<br>(Mục 4.1) | Rà soát ma trận 12 phân hệ nghiệp vụ. | Sử dụng chuẩn **"100% PASS trên bộ kiểm thử tự động"** (kèm số test cụ thể: 27 GIS tests, 56 RAG tests, 39 checkout tests), KHÔNG gọi là hoàn thành 100% nghiệp vụ doanh nghiệp lớn. | Phân biệt rành mạch giữa việc vượt qua 100% ca kiểm thử được thiết kế với việc hoàn tất 100% mọi nghiệp vụ thực tế ngoài đời. |

---

### 2.2. Mục 11: Bỏ các khẳng định "An toàn tuyệt đối", "Không ảo giác", "Không rò rỉ 100%"

| STT | Vị trí Tệp tin | Nội dung Ban đầu | Nội dung Sau Chuẩn hóa | Ranh giới Khoa học Được Xác lập |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `templates/public/service_detail.html`<br>(Dòng 127) | `Cam kết bảo mật dữ liệu khách hàng tuyệt đối` | `Cam kết bảo vệ dữ liệu khách hàng theo quy trình kiểm soát nội bộ và phân quyền nghiêm ngặt` | Không khẳng định an toàn tuyệt đối; cam kết tuân thủ quy trình kiểm soát nội bộ và phân quyền truy cập. |
| 2 | `templates/public/home.html`<br>(Dòng 505) | `...bảo mật sandbox cách ly dữ liệu giữa các workspace tuyệt đối.` | `...cơ chế phân lập logic dữ liệu theo từng workspace (multi-tenant) qua phân quyền ứng dụng.` | Làm rõ bản chất: Phân lập logic (Logical Multi-Tenancy qua WorkspaceMiddleware và scoped queries), không phải cách ly vật lý hay air-gap tuyệt đối. |
| 3 | `templates/notifications/team_chat.html`<br>(Dòng 200) | `...Dữ liệu cách ly tuyệt đối.` | `...Dữ liệu cách ly logic theo từng Workspace.` | Thống nhất thuật ngữ phân lập logic theo không gian làm việc. |
| 4 | `templates/mapping/mapping_studio.html`<br>(Dòng 266) | `Tuyệt đối không thay đổi dữ liệu (không ghi vào cơ sở dữ liệu).` | `Kiểm tra các quy tắc ánh xạ... (chế độ chỉ đọc, không ghi dữ liệu vào cơ sở dữ liệu).` | Diễn đạt kỹ thuật chính xác về trạng thái chỉ đọc (in-memory dry-run execution). |
| 5 | `apps/public_web/alphatech_ai.py`<br>(Dòng 7) | `- Tuyệt đối bảo mật: Không tiết lộ giá vốn...` | `- Nguyên tắc bảo mật nội bộ: Không tiết lộ giá vốn...` | Chuẩn hóa quy tắc hướng dẫn trợ lý ảo thành nguyên tắc bảo mật thông tin nội bộ. |
| 6 | `apps/public_web/alphatech_ai.py`<br>(Dòng 189) | Khẳng định trực tiếp của Chatbot khi được hỏi về an toàn: | Giữ nguyên câu từ chối chuẩn: *"Tôi chưa có bằng chứng xác minh chứng nhận ISO 27001 hoặc các cam kết bảo mật tuyệt đối của đơn vị..."* | Khẳng định sự trung thực: Trợ lý AI chủ động từ chối cam kết bảo mật tuyệt đối và chứng nhận khi chưa có bằng chứng pháp lý. |
| 7 | `docs/ACADEMIC_ACCEPTANCE_SCOPE.md` & `HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md` | Rà soát thuật ngữ bảo mật và RAG. | Bỏ hoàn toàn thuật ngữ "air-gap", thay bằng "logical isolation"; bỏ tuyên bố "RAG không ảo giác", thay bằng cơ chế kiểm soát đại lượng số học (`numeric_facts_ok`) và trích xuất đoạn chuẩn (`chunk_recall`). | Thừa nhận bản chất xác suất của mô hình sinh tạo; bảo vệ tính đúng đắn bằng hàng rào kiểm thử đối kháng và trích xuất số học xác định. |

---

### 2.3. Mục 13: Đồng bộ toàn bộ tài liệu trạng thái lịch sử, loại bỏ mâu thuẫn

| STT | Vấn đề Mâu thuẫn / Lỗi thời | Tài liệu Bị Tác động | Giải pháp Đồng bộ & Chuẩn hóa Hiện hành |
| :---: | :--- | :--- | :--- |
| 1 | **Tên đề tài đồ án**: Một số tài liệu cũ dùng tên dài *"Xây dựng Nền tảng Quản lý Vận hành Doanh nghiệp Thông minh tích hợp AI và GIS hỗ trợ Phân tích, Dự báo và Ra quyết định"*. | `docs/ACADEMIC_EVALUATION_REPORT.md`<br>`docs/demo-guide.md` | Đã thống nhất tên đề tài chính thức theo Quyết định giao đề tài: **"Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI (AlphaTech AI Platform)"** trong [docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md](file:///d:/ai_business_platform/docs/HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md), [README.md](file:///d:/ai_business_platform/README.md), [docs/PROJECT_CONTEXT.md](file:///d:/ai_business_platform/docs/PROJECT_CONTEXT.md). Các tệp báo cáo cũ giữ tên gốc kèm chú thích lịch sử. |
| 2 | **Tỷ trọng phân chia 15% Web / 85% Nội bộ**: Tuyên bố tỷ trọng khối lượng không có phương pháp luận đo đạc. | `docs/ACADEMIC_SCOPE_ALIGNMENT.md`<br>`docs/SCOPE_ALIGNMENT_2026-09-15.md` | Đã loại bỏ hoàn toàn con số phần trăm suy đoán; thay bằng định vị kỹ thuật: Web công khai là *Cổng Tiếp nhận Đa kênh (Omnichannel Ingestion Gateway)*, Cổng nội bộ là *Phân hệ Quản lý Vận hành (Operations Back-office)*. |
| 3 | **Phân biệt Tài liệu Lịch sử (Historical Logs) vs Chuẩn mực Hiện hành (Golden Standard)**: Tránh nhầm lẫn các kết luận sơ khai với kết quả thực nghiệm mới nhất. | Toàn bộ 44 biên bản `ACCEPTANCE_BATCH_*.md` và các báo cáo `output/` | **Quy tắc phân tầng tài liệu**: <br>1. *Tài liệu Chuẩn mực Hiện hành (Living Truth)*: `HO_SO_NGHIEM_THU_HOC_THUAT_TOAN_DIEN.md`, `HO_SO_THUC_NGHIEM_DU_BAO_VA_DATA_CATALOG.md`, `CHECKLIST_97_PROGRESS.md`.<br>2. *Biên bản Đợt (Batch Manifests)*: Lưu trữ trung thực quá trình hội tụ từng đợt, không viết lại quá khứ để biến cái sai thành đúng, giữ nguyên các lỗi fixture từng gặp và cách khắc phục. |

---

### 2.4. Mục 14: Không cộng dồn các nhóm test chồng lặp thành coverage toàn hệ thống

| STT | Vị trí Tệp tin | Nội dung Ban đầu | Nội dung Sau Chuẩn hóa | Ranh giới Khoa học Được Xác lập |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `docs/project-summary.md`<br>(Dòng 190) | `(276 bài kiểm thử tự động, tỷ lệ vượt qua 100%)` | `(các bộ kiểm thử độc lập phân rã theo từng phân hệ: RBAC, GIS, RAG, Dự báo, Bán lẻ, Dịch vụ; chạy với cờ --keepdb trên database kiểm thử chuyên dụng). Không cộng dồn các lượt chạy riêng lẻ thành số test duy nhất.` | Không cộng gộp số lượt chạy của các suite khác nhau thành một con số tổng duy nhất; phân tách rõ ràng theo domain module. |
| 2 | Các báo cáo nghiệm thu đợt (`ACCEPTANCE_BATCH_*.md`) | Từng có các lượt chạy gộp kiểm thử (ví dụ Đợt 9: 48 test, sau đó 2 test link và 2 test advisory; Đợt 36: 39 test checkout và 22 test RAG). | Tất cả biên bản đều ghi chú rõ: *"có ca lặp / ca phụ thuộc, không cộng thành tổng số test độc lập toàn hệ thống"*. | Minh bạch phương pháp đo: Mỗi bộ test kiểm chứng một phạm vi bất biến cụ thể (invariants) với thời gian thực thi độc lập. |
| 3 | Đo lường tỷ lệ bao phủ mã nguồn (Coverage Metric) | Tránh tuyên bố hệ thống đạt "coverage 100%" hay "toàn diện". | Ghi nhận chính xác phạm vi kiểm thử tự động tập trung vào các luồng trọng yếu: Concurrency race condition (PostgreSQL row locks), RBAC authorization matrix (45 ca), Geodesic distance accuracy, RAG ground truth citation, và Time-series chronological holdout. | Phân định rõ: Pass 100% các ca kiểm thử hồi quy được thiết kế KHÔNG đồng nghĩa với việc mã nguồn được bao phủ 100% mọi nhánh lệnh (branch coverage) trong mọi điều kiện biên môi trường. |

---

### 2.5. Mục 27: Không suy rộng kết quả seed/demo thành hiệu quả kinh doanh thực tế

| STT | Vị trí Tệp tin | Hiện trạng / Biểu hiện | Giải pháp Chuẩn hóa & Ranh giới Học thuật |
| :---: | :--- | :--- | :--- |
| 1 | `templates/dashboard/executive_report.html`<br>(Dòng 439–440) | Tiêu đề "1. Hiệu quả Kinh doanh Bán lẻ (ABC Tech Store)" với các số liệu doanh thu, AOV, tỷ lệ hoàn tất đơn hàng. | Bổ sung chú thích ngay dưới tiêu đề: `* Số liệu tổng hợp từ các giao dịch mẫu trong cơ sở dữ liệu thử nghiệm nội bộ, không suy rộng thành báo cáo tài chính thực tế.` |
| 2 | `templates/dashboard/executive_report.html`<br>(Dòng 502–508) | Cột `Cải thiện (%)` từng dùng cứng màu xanh lá cây (`#16a34a`), khiến cho Run 1 (Doanh thu bán lẻ kém baseline -38.70%) hiển thị số âm bằng màu xanh gây hiểu lầm là kết quả tích cực. | Đã hiệu chỉnh điều kiện template: `{% if run.improvement_pct != None and run.improvement_pct < 0 %}color: #dc2626;{% else %}color: #16a34a;{% endif %}`. Kết quả kém hiển thị rõ ràng bằng **màu đỏ cảnh báo**. |
| 3 | `apps/accounts/management/commands/seed_demo.py`<br>(Dòng 70–71) | Thông báo kết thúc quá trình tạo dữ liệu mẫu (`seed_demo`). | Đã định vị chuẩn mực từ Đợt 30: `"DEMO COMPLETE: configured seed stages finished; synthetic data only, not production acceptance."` Ngăn chặn tuyệt đối việc chạy trên môi trường remote và database có sẵn dữ liệu. |
| 4 | Báo cáo thực nghiệm dự báo (`HO_SO_THUC_NGHIEM_DU_BAO_VA_DATA_CATALOG.md`) | Kết quả huấn luyện XGBoost trên 61 ngày quan sát (Run 1, 2, 3). | Tuyên bố ranh giới minh bạch: *"Dữ liệu chuỗi thời gian được sinh ra từ các giao dịch mô phỏng trong môi trường kiểm thử. Không được suy rộng mức độ cải thiện MAE thành hiệu quả tiết kiệm chi phí hay gia tăng lợi nhuận của một doanh nghiệp đang hoạt động thực tế."* |

---

### 2.6. Mục 42: Phân biệt rõ ràng giữa test intent/router offline với đánh giá năng lực LLM thật

| STT | Vị trí Tệp tin | Nội dung Ban đầu | Nội dung Sau Chuẩn hóa | Ranh giới Khoa học Được Xác lập |
| :---: | :--- | :--- | :--- | :--- |
| 1 | `tests/test_ai_advanced_context_benchmark.py`<br>(Docstring đầu tệp) | `Comprehensive Vietnamese AI Business Intent Benchmark Test Suite (88 Benchmark Scenarios). Evaluates the AI Assistant's semantic understanding across...` | `Deterministic Vietnamese Business Intent & Keyword Router Benchmark (88 Benchmark Scenarios). Evaluates the rule-based pattern matching and keyword heuristics of the offline intent router... NOTE: This benchmark tests deterministic application routing heuristics, NOT generative LLM capabilities or live model comprehension.` | Tách bạch hoàn toàn: Bộ 88 test case này kiểm tra logic phân loại mẫu từ khóa và trích xuất tham số của hàm Python `classify_business_intent`, tuyệt đối không phải kiểm tra khả năng "hiểu ngữ nghĩa" của mô hình ngôn ngữ lớn LLM. |
| 2 | `tests/test_ai_business_intent_benchmark.py`<br>(Docstring đầu tệp) | `Comprehensive Automated Benchmark Test Suite: Vietnamese AI Business Intent Understanding. Validates 77 realistic Vietnamese business queries...` | `Deterministic Vietnamese AI Business Intent Parser Benchmark (77 Scenarios). Validates offline pattern matching, entity extraction, and intent classification rules... NOTE: This suite tests rule-based intent parsing heuristics, NOT live generative LLM performance.` | Tương tự, bộ 77 kịch bản kiểm tra khả năng phân tích thực thể (entity extraction) dựa trên biểu thức chính quy và quy tắc nghiệp vụ xác định. |
| 3 | `tests/test_adversarial_rag_execution.py` & `test_simulation_evidence.py` | Kiểm thử RAG và What-If trong môi trường offline không có LLM API Key thật. | Đã chuẩn hóa docstring: `"Offline application observations, not a mocked LLM quality benchmark"`, `"Deterministic what-if evidence; does not evaluate live LLM quality."` | Khi chạy offline với `LLM_API_KEY=""`, hệ thống kiểm tra luồng deterministic fallback và việc giữ nguyên nhãn mô phỏng, không tuyên bố đây là chất lượng sinh văn bản của Gemini. |
| 4 | Phân tầng kiến trúc Trợ lý AI trong Đồ án | Sự nhầm lẫn giữa Router và LLM. | Phân định rõ 2 tầng riêng biệt trong thuyết minh Đồ án:<br>- **Tầng 1 (Deterministic Routing & Guardrails)**: Bộ lọc ý định xác định dựa trên regex và ontology nghiệp vụ tiếng Việt (chạy cục bộ, độ trễ < 5ms, 100% có thể giải thích).<br>- **Tầng 2 (Generative Synthesis & RAG Grounding)**: Khung hỏi đáp trích xuất tri thức qua vector embedding và tổng hợp ngữ cảnh (chịu sự chi phối của độ bất định LLM và được kiểm soát bằng phép đo Gold Chunk, trích xuất sự thật số học). |

---

## 3. Tổng Kết Bằng Chứng Nghiệm Thu & Tác Động Tiến Độ

1. **Về Mã Nguồn & Giao Diện**:
   - Dọn sạch 100% các từ ngữ "tuyệt đối" mang tính phóng đại trên toàn bộ các tệp HTML templates.
   - Sửa lỗi màu sắc logic của chỉ số cải thiện MAE âm trong báo cáo điều hành.
   - Thay thế ô KPI hardcode `100%` bằng chỉ báo kiến trúc `Multi-Tenant`.
2. **Về Bộ Kiểm Thử Tự Động**:
   - Toàn bộ docstrings của các file benchmark intent router được định danh lại chính xác là *"Deterministic Pattern-Matching Benchmark"*, không nhận vơ năng lực LLM.
   - Xóa bỏ các tuyên bố cộng dồn số test 276 bài kiểm thử 100% trong `docs/project-summary.md`.
3. **Về Tài Liệu Thuyết Minh & Hướng Dẫn Hội Đồng**:
   - Chuẩn hóa Bảng tổng kết nghiệm thu trong `docs/HOI_DONG_DEMO_GUIDE.md`, loại bỏ 7 nhãn "Hoàn thành 100%".
   - Tinh chỉnh lý do thiết kế trong `docs/decisions.md` (ADR-010) thành chuẩn mực học thuật.
   - Thiết lập ranh giới dữ liệu mô phỏng / dữ liệu seed rõ ràng.

Hồ sơ rà soát này là căn cứ vững chắc khẳng định tính trung thực khoa học, sự nghiêm túc và đạo đức học thuật của đề tài trước Hội đồng Chấm Đồ án Tốt nghiệp.
