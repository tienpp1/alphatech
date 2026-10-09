# THUYẾT MINH ĐỒ ÁN TỐT NGHIỆP: CHƯƠNG 1 VÀ CHƯƠNG 2
**Đề tài:** Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI (*AlphaTech AI Platform*)  
**Chuyên ngành:** Kỹ thuật Phần mềm / Hệ thống Thông tin  
**Chuẩn trích dẫn yêu cầu:** IEEE. Danh mục được xếp theo lần trích dẫn đầu trong bản nháp ngày 09/10/2026; không thay bibliography của Word đã được duyệt.

---

# CHƯƠNG 1: TỔNG QUAN VÀ KHẢO SÁT BÀI TOÁN

## 1.1. Đặt vấn đề và Tính cấp thiết của Đề tài
Chuyển đổi số có thể hỗ trợ doanh nghiệp nhỏ và vừa tổ chức thông tin và vận hành, nhưng việc áp dụng còn phụ thuộc nguồn lực, kỹ năng và khả năng đầu tư. Báo cáo OECD về chuyển đổi số SMEs phân tích các rào cản này [1]. Đây là bối cảnh lựa chọn đề tài, không phải bằng chứng khảo sát doanh nghiệp AlphaTech hoặc kết quả đo lợi ích tài chính của hệ thống.

Trong kịch bản đồ án bán lẻ thiết bị và dịch vụ kỹ thuật, bài toán cần giải quyết là theo dõi đơn hàng, tồn kho và phiếu dịch vụ trên một nền tảng có phân quyền; cung cấp cổng riêng để khách hàng tra cứu giao dịch và tìm chi nhánh. Nhân viên còn cần hỏi đáp tài liệu có nguồn và tham khảo dự báo, nhưng không được xem dữ liệu ngoài workspace hoặc biến lời tư vấn của AI thành giao dịch tự động.

RAG cung cấp một hướng kết hợp mô hình sinh với tài liệu truy xuất [2], song kết quả nghiên cứu không tự chứng minh câu trả lời tiếng Việt của đồ án đúng và đủ. Nghiên cứu UIT-ViQuAD của nhóm tác giả tại Việt Nam xây dựng bộ đọc hiểu tiếng Việt với câu hỏi và đáp án do con người tạo từ Wikipedia [3]. Bài toán đó khác hỏi đáp SOP kết hợp số liệu có phân quyền, vì vậy đồ án cần kiểm riêng truy xuất, nguồn, số liệu và đánh giá của người đọc thay vì chuyển điểm benchmark sang hệ thống này.

Từ nhu cầu trên, đề tài **"Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI"** xây dựng một modular monolith Django, kết hợp quản lý nghiệp vụ, GIS, dự báo và trợ lý có nguồn. Đóng góp được giới hạn ở triển khai tích hợp và kiểm chứng trên kịch bản đã xác định; không tuyên bố giải quyết toàn diện vận hành doanh nghiệp hoặc phát minh thuật toán mới.

---

## 1.2. Mục tiêu nghiên cứu và Phạm vi đề tài

### 1.2.1. Mục tiêu chung
Xây dựng nền tảng web quản lý vận hành với cách ly logic theo workspace, phục vụ hai đối tượng. Đây không phải ERP hoặc WMS hoàn chỉnh:
- **Khối quản trị nội bộ:** Quản lý đơn hàng và tồn kho hỗ trợ bán lẻ, theo dõi vòng đời phiếu dịch vụ, dự báo và đề xuất hỗ trợ quản lý. Các action được hỗ trợ phải đi qua kiểm tra quyền và quy trình phê duyệt; không có phê duyệt tự động mọi giao dịch.
- **Khối khách hàng công khai (Public Portal):** Trải nghiệm xem sản phẩm, tìm chi nhánh gần nhất bằng bản đồ GIS, đặt hàng nhận tại shop/giao tận nơi, tra cứu tiến độ dịch vụ và tương tác với Trợ lý AI AlphaTech.

### 1.2.2. Mục tiêu cụ thể
- Thiết kế mô hình kiểm soát truy cập dựa trên vai trò (RBAC) nghiêm ngặt, kiểm soát truy cập và phân lập logic giữa người dùng công khai và nhân sự nội bộ.
- Tích hợp PostGIS để tính khoảng cách địa lý và nhà cung cấp định tuyến đường bộ; không phát minh thuật toán định tuyến.
- Đánh giá XGBoost so với lag-7 và trung bình trượt 7 ngày trên cùng horizon; bài toán thực nghiệm chính là doanh thu ngày. Baseline là đối chứng, không phải mô hình ensemble với XGBoost [4].
- Xây dựng trợ lý nội bộ truy xuất SOP trong workspace được cấp quyền, ghi nguồn và đánh giá câu trả lời. Trợ lý công khai chỉ dùng phạm vi thông tin công khai, không mở SOP nội bộ cho khách hàng.

### 1.2.3. Đối tượng và Phạm vi áp dụng
- **Đối tượng nghiên cứu:** Doanh nghiệp bán lẻ thiết bị công nghệ và dịch vụ kỹ thuật điện tử - tin học (mô hình chuỗi cửa hàng).
- **Phạm vi kỹ thuật:** 
  - Backend: Django REST Framework, PostgreSQL với PostGIS mở rộng.
  - Phân tích & AI: Scikit-learn, XGBoost, RAG Vector Search & Embeddings.
  - Frontend: Kiến trúc giao diện Responsive (Desktop/Mobile), Canvas/Three.js, bản đồ Leaflet/OpenStreetMap.

---

## 1.3. Khảo sát Hiện trạng và Phân tích So sánh Giải pháp Khoa học
*(Tham khảo chuyên khảo chi tiết tại docs/TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md)*

Bảng sau đối chiếu nhu cầu của kịch bản đồ án với cách triển khai và giới hạn.
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

## 1.4. Khoảng trống Nghiên cứu & Đóng góp Ứng dụng Thực tiễn của Đề tài

Đề tài không tuyên bố tính mới về mặt phát minh thuật toán toán học cơ bản mà tập trung giải quyết **ba khoảng trống tích hợp ứng dụng thực tiễn** trong chuyển đổi số doanh nghiệp SMEs:
1. **Nhu cầu tích hợp cổng vận hành:** Đơn hàng, tồn kho và phiếu dịch vụ dùng chung nền tảng và quy tắc phân quyền; workspace bán lẻ và dịch vụ có thể tách biệt. Không tuyên bố có liên kết tự động từ mọi đơn hàng sang bảo hành hoặc đã triển khai toàn bộ chuỗi cung ứng.
2. **Khoảng trống Kiểm soát Đại lượng Số học trong RAG (Factual Grounding & Numeric Verification Gap):** Bổ sung phép đo offline cho retrieval và đại lượng số dựa trên rubric. Regex không kiểm chứng đầy đủ ngữ nghĩa; không tuyên bố loại bỏ ảo giác hoặc dùng bộ chấm như rào chắn runtime.
3. **Nhu cầu thực thi có kiểm soát và truy vết:** action có contract đi qua phê duyệt với con người giám sát, transaction và audit append-only. DB rollback không tự bồi hoàn side effect ngoài database; trigger không bảo vệ trước chủ DB vô hiệu hóa nó. Stock reorder và workload balancing vẫn advisory, không tuyên bố saga tổng quát đã triển khai.

# CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ NỀN TẢNG KỸ THUẬT

## 2.1. Mô hình Kiểm soát Truy cập Dựa trên Vai trò (RBAC) và Kiến trúc Đa khách thuê (Multi-Tenancy)

### 2.1.1. Lý thuyết Mô hình RBAC96
Theo nghiên cứu kinh điển của Sandhu et al. (1996) [5], mô hình kiểm soát truy cập dựa trên vai trò (Role-Based Access Control - RBAC) tổ chức quyền hạn thông qua các tập hợp hình thức:
- Tập hợp người dùng: $U = \{u_1, u_2, \dots, u_m\}$
- Tập hợp vai trò: $R = \{r_1, r_2, \dots, r_n\}$
- Tập hợp quyền hạn: $P = \{p_1, p_2, \dots, p_k\}$
- Quan hệ gán người dùng - vai trò: $UA \subseteq U \times R$
- Quan hệ gán quyền - vai trò: $PA \subseteq P \times R$

Quyền hạn của người dùng $u \in U$ được xác định bởi:
$$\text{AuthorizedPermissions}(u) = \bigcup_{r \in \{r \mid (u, r) \in UA\}} \{p \mid (p, r) \in PA\}$$

Trong đề tài AlphaTech, quyền nội bộ được gán qua membership trong workspace với các vai trò seed `ADMIN`, `MANAGER`, `EMPLOYEE`, `VIEWER`. Không mô tả cơ chế này là kế thừa vai trò nếu chưa có mô hình kế thừa trong mã nguồn. Superuser là ngoại lệ kiểm soát riêng; kỹ thuật viên là hồ sơ nghiệp vụ, không phải một vai trò RBAC mới. Khách hàng công khai chỉ sử dụng chức năng công khai và dữ liệu thuộc quyền sở hữu; đăng ký không tự tạo membership nội bộ.

### 2.1.2. Kiến trúc Cô lập Dữ liệu Đa khách thuê (Shared Database, Workspace-scoped Rows)
Đề tài dùng cơ sở dữ liệu chung và phạm vi workspace; đây là lựa chọn triển khai, không phải kết luận tối ưu chi phí đã đo. Nghiên cứu đa khách thuê [6] cung cấp bối cảnh về bảo trì và phát triển hệ thống.
- Các thực thể gốc được gắn workspace; thực thể con có thể được giới hạn qua quan hệ cha thay vì có khóa workspace trực tiếp. Workspace không đồng nghĩa với chi nhánh.
- Truy vấn dữ liệu bảo vệ phải áp dụng phạm vi được cấp quyền, trực tiếp hoặc qua quan hệ cha:
  $$\mathcal{Q}_{\text{scoped}} = \sigma_{\text{workspace\_id} = \text{current\_workspace}}(\mathcal{Q})$$
- Đây là yêu cầu an toàn cần kiểm thử trên từng đường đọc/ghi; các ca kiểm thử đã chạy không chứng minh mọi đường truy cập đều không thể có lỗi.

---

## 2.2. Kỹ thuật Tăng cường Tạo văn bản bằng Truy xuất (Retrieval-Augmented Generation - RAG)

### 2.2.1. Nguyên lý hoạt động của RAG
Mô hình ngôn ngữ lớn (LLM) tuy có khả năng suy luận mạnh mẽ nhưng bị giới hạn bởi:
1. Tri thức tĩnh bị đóng băng tại thời điểm huấn luyện.
2. Xu hướng tạo ra thông tin giả mạo nhưng nghe có vẻ thuyết phục (Hallucination).

Nghiên cứu của Lewis et al. (2020) [2] kết hợp tri thức tham số của mô hình với bộ nhớ truy xuất phi tham số. RAG hỗ trợ đưa nguồn vào quá trình tạo câu trả lời, nhưng không loại bỏ hoàn toàn hallucination. Quy trình khái quát gồm:
1. **Giai đoạn Ingestion (Chỉ mục hóa):**
   Tài liệu quy trình chuẩn (SOP), chính sách bảo hành được phân mảnh thành các đoạn văn (chunks) $D = \{d_1, d_2, \dots, d_N\}$. Mỗi chunk $d_i$ được chuyển đổi thành một vector nhúng:
   $$v_i = \text{Embed}(d_i) \in \mathbb{R}^d$$
2. **Giai đoạn Retrieval (Truy xuất):**
   Khi người dùng gửi câu hỏi $q$, hệ thống tạo vector câu hỏi $v_q = \text{Embed}(q)$ và tính toán độ tương đồng Cosine:
   $$\text{Sim}(v_q, v_i) = \frac{v_q \cdot v_i}{\|v_q\| \|v_i\|}$$
   Hệ thống chọn ra Top-$K$ đoạn tài liệu có điểm tương đồng cao nhất: $\mathcal{D}_{\text{top}} = \{d_{(1)}, d_{(2)}, \dots, d_{(K)}\}$.
3. **Giai đoạn Generation (Tạo sinh):**
   Prompt gửi tới LLM được cấu trúc:
   $$\mathcal{P} = \text{SystemPrompt} \oplus \text{Context}(\mathcal{D}_{\text{top}}) \oplus \text{History} \oplus q$$
   Prompt yêu cầu trả lời dựa trên nguồn truy xuất và nêu nguồn. Việc mô hình tuân thủ, trích dẫn đúng và trả lời đủ cần đánh giá riêng; yêu cầu trong prompt không phải bằng chứng chất lượng đầu ra.

---

## 2.3. Phương pháp Dự báo Chuỗi Thời gian trong Bán lẻ (Time-Series Demand Forecasting)

### 2.3.1. Đường cơ sở: Trung bình trượt (Moving Average)
Mô hình đường cơ sở dự báo giá trị tại thời điểm $t$ dựa trên trung bình cộng của $k$ chu kỳ trước đó:
$$\hat{y}_t = \frac{1}{k} \sum_{i=1}^{k} y_{t-i}$$
Mô hình này có ưu điểm đơn giản, phản ánh nhanh xu hướng ngắn hạn, đóng vai trò chuẩn so sánh (Baseline) để đánh giá các mô hình phức tạp hơn.

### 2.3.2. Cây Quyết định Tăng cường (Gradient Tree Boosting - XGBoost)
Theo Chen & Guestrin (2016) [7], XGBoost là một hệ thống học máy mở rộng dựa trên thuật toán tăng cường độ dốc (Gradient Boosting). Mô hình dự đoán $\hat{y}_i$ được biểu diễn dưới dạng tổng của $K$ cây quyết định hồi quy (regression trees):
$$\hat{y}_i = \sum_{k=1}^{K} f_k(x_i), \quad f_k \in \mathcal{F}$$

Hàm mục tiêu cần tối thiểu hóa tại bước lặp $t$:
$$\mathcal{L}^{(t)} = \sum_{i=1}^{n} l\left(y_i, \hat{y}_i^{(t-1)} + f_t(x_i)\right) + \Omega(f_t)$$
Trong đó hàm phạt điều chuẩn $\Omega(f)$ giúp kiểm soát độ phức tạp của cây và tránh hiện tượng quá khớp (overfitting):
$$\Omega(f) = \gamma T + \frac{1}{2} \lambda \sum_{j=1}^{T} w_j^2$$
Áp dụng khai triển Taylor bậc 2 quanh điểm $\hat{y}_i^{(t-1)}$:
$$\tilde{\mathcal{L}}^{(t)} \approx \sum_{i=1}^{n} \left[ l\left(y_i, \hat{y}_i^{(t-1)}\right) + g_i f_t(x_i) + \frac{1}{2} h_i f_t^2(x_i) \right] + \Omega(f_t)$$
với $g_i = \partial_{\hat{y}^{(t-1)}} l(y_i, \hat{y}^{(t-1)})$ và $h_i = \partial^2_{\hat{y}^{(t-1)}} l(y_i, \hat{y}^{(t-1)})$.

Trong đề tài AlphaTech, cấu hình mặc định tại `apps/forecasting/features.py` dùng lag 1/7/14 ngày, cửa sổ rolling 7/14 ngày và đặc trưng lịch. Không có đặc trưng ngày lễ trong cấu hình mặc định. Chất lượng từng target phải đối chiếu baseline trên cùng tập đánh giá; không mặc định XGBoost luôn tốt hơn.

### 2.3.3. Các độ đo đánh giá mô hình (Evaluation Metrics)
Để đối chiếu độ chính xác giữa các thuật toán, hệ thống sử dụng các độ đo chuẩn:
- **Mean Absolute Error (MAE):**
  $$\text{MAE} = \frac{1}{n} \sum_{i=1}^{n} |y_i - \hat{y}_i|$$
- **Root Mean Squared Error (RMSE):**
  $$\text{RMSE} = \sqrt{\frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2}$$
- **Mean Absolute Percentage Error (MAPE):**
  $$\text{MAPE} = \frac{100\%}{n} \sum_{i=1}^{n} \left| \frac{y_i - \hat{y}_i}{y_i} \right|$$

  Trong triển khai `compute_mape`, chỉ tính trên mẫu có `abs(actual) > 1e-3`; mẫu số là số mẫu còn lại. Hàm hiện trả 0 nếu không còn mẫu, nhưng giá trị đó không chứng minh sai số bằng 0 hoặc dự báo hoàn hảo. Khi trình bày kết quả phải ghi số mẫu hợp lệ và trường hợp không đánh giá được.

---

## 2.4. Hệ thống Thông tin Địa lý (GIS) và Bài toán Định tuyến Đơn hàng

### 2.4.1. Cơ sở dữ liệu Không gian và Tiện ích mở rộng PostGIS
Theo Güting (1994) [8], hệ thống cơ sở dữ liệu không gian mở rộng các kiểu dữ liệu quan hệ truyền thống bằng các kiểu hình học không gian (Points, LineStrings, Polygons) và các hàm quan hệ không gian (Spatial Predicates).
- PostGIS bổ sung kiểu dữ liệu `GEOMETRY(Point, 4326)` (Hệ quy chiếu WGS 84).
- Tọa độ chi nhánh được biểu diễn bằng điểm không gian. Không suy ra mọi địa chỉ giao hàng dạng chữ đã được geocode hoặc lưu thành Point; vị trí người dùng trên bản đồ có thể chỉ tồn tại trong phiên browser. Biểu thức tạo điểm là:
  $$\text{Location} = \text{ST\_SetSRID}(\text{ST\_MakePoint}(\text{Longitude}, \text{Latitude}), 4326)$$

### 2.4.2. Công thức Khoảng cách Cầu (Haversine Formula) và Định vị Tối ưu
Để hỗ trợ tìm chi nhánh gần vị trí đã chọn, giao diện công khai sử dụng khoảng cách cung tròn lớn trên mặt cầu (Great-Circle Distance). Kết quả không tự điều phối kỹ thuật viên hoặc cam kết giao hàng hỏa tốc:
$$d = 2 R \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1) \cos(\phi_2) \sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$
Trong đó:
- $R \approx 6,371,000 \text{ m}$ (Bán kính trung bình Trái đất).
- $\phi_1, \phi_2$ là vĩ độ (radians) của hai điểm.
- $\Delta \phi = \phi_2 - \phi_1$; $\Delta \lambda = \lambda_2 - \lambda_1$ là độ lệch vĩ độ và kinh độ.

Trong `apps/gis/services.py`, truy vấn nội bộ dùng `Distance(..., spheroid=True)` trên queryset đã được giới hạn phạm vi. Haversine trong luồng bản đồ công khai là phép tính khoảng cách mặt cầu, không đồng nhất với khoảng cách theo đường giao thông. Việc sắp xếp khoảng cách không tự chứng minh sử dụng chỉ mục hoặc hiệu năng truy vấn. Chưa có benchmark thời gian trong hồ sơ; không công bố mốc 5 ms hay tuyến đường ngắn nhất tuyệt đối.

---

## 2.5. Tài liệu tham khảo Chương 1 & Chương 2 (Chuẩn IEEE)

[1] OECD, *The Digital Transformation of SMEs*. Paris, France: OECD Publishing, 2021, doi: 10.1787/bdb9256a-en.

[2] P. Lewis *et al.*, "Retrieval-augmented generation for knowledge-intensive NLP tasks," in *Advances in Neural Information Processing Systems (NeurIPS 2020)*, vol. 33, Curran Associates, Inc., 2020, pp. 9459–9474.

[3] K. V. Nguyen, D.-V. Nguyen, A. G.-T. Nguyen, and N. L.-T. Nguyen, "A Vietnamese dataset for evaluating machine reading comprehension," in *Proc. 28th International Conference on Computational Linguistics*, 2020, pp. 2595–2605, doi: 10.18653/v1/2020.coling-main.233.

[4] R. J. Hyndman and G. Athanasopoulos, *Forecasting: Principles and Practice*, 3rd ed. Melbourne, Australia: OTexts, 2021. [Online]. Available: https://otexts.com/fpp3/ [Accessed: Oct. 9, 2026].

[5] R. S. Sandhu, E. J. Coyne, H. L. Feinstein, and C. E. Youman, "Role-based access control models," *IEEE Computer*, vol. 29, no. 2, pp. 38–47, Feb. 1996, doi: 10.1109/2.485845.

[6] C.-P. Bezemer and A. Zaidman, "Multi-tenant SaaS applications: Maintenance dream or nightmare?," in *Proc. 4th Int. Joint ERCIM/IWPSE Symp. Software Evolution (IWPSE-EVOL)*, Antwerp, Belgium, 2010, pp. 88–92. [Online]. Available: https://azaidman.github.io/publications/bezemerIWPSE2010.pdf [Accessed: Oct. 5, 2026].

[7] T. Chen and C. Guestrin, "XGBoost: A scalable tree boosting system," in *Proc. 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD '16)*, San Francisco, CA, USA, 2016, pp. 785–794, doi: 10.1145/2939672.2939785.

[8] R. H. Güting, "An introduction to spatial database systems," *The VLDB Journal*, vol. 3, no. 4, pp. 357–399, Oct. 1994, doi: 10.1007/BF01231602.
