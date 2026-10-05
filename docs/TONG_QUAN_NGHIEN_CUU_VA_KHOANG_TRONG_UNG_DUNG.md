# TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU, PHÂN TÍCH SO SÁNH & KHOẢNG TRỐNG ỨNG DỤNG
## Bản nháp tổng quan học thuật — không tự ký đóng cổng 79/80

---

- **Tên đề tài chuẩn:** **Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI (AlphaTech AI Platform)**
- **Tiêu đề tiếng Anh:** *Building an Intelligent Business Operations Platform Integrated with AI Assistant (AlphaTech AI Platform)*
- **Căn cứ thực hiện:** Mục 79 và 80 trong Danh mục 97 tiêu chí nghiệm thu ([docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md)) và [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md).
- **Chuẩn trích dẫn:** IEEE Citation Style.

---

## 1. TỔNG QUAN CÁC HƯỚNG NGHIÊN CỨU LIÊN QUAN (RELATED WORK)

Nghiên cứu và phát triển một nền tảng quản lý vận hành doanh nghiệp đa chi nhánh tích hợp trí tuệ nhân tạo đòi hỏi sự giao thoa giữa bốn trụ cột lý thuyết và công nghệ chính: (1) Kiến trúc đa khách thuê và kiểm soát truy cập dựa trên vai trò; (2) Kỹ thuật tạo văn bản tăng cường truy xuất (RAG) và rào chắn độ tin cậy thông tin; (3) Các phương pháp học máy dự báo chuỗi thời gian trong ngành bán lẻ; và (4) Hệ thống thông tin địa lý (GIS) phục vụ bài toán định vị và điều phối dịch vụ kỹ thuật.

### 1.1. Kiến trúc Đa khách thuê (Multi-Tenancy) và Kiểm soát Truy cập Dựa trên Vai trò (RBAC)

Trong phát triển phần mềm doanh nghiệp dạng dịch vụ (SaaS), bài toán cô lập dữ liệu và bảo mật phân quyền là nền tảng cốt lõi:
- **Mô hình Kiểm soát Truy cập Dựa trên Vai trò (RBAC):** Sandhu et al. [1] đã thiết lập mô hình hình thức chuẩn hóa RBAC96, phân tách rõ ràng giữa gán người dùng - vai trò ($UA$) và gán quyền hạn - vai trò ($PA$). Mô hình này sau đó được Viện Tiêu chuẩn và Công nghệ Quốc gia Hoa Kỳ (NIST) chuẩn hóa thông qua công trình của Ferraiolo et al. [2]. Nghiên cứu chỉ ra rằng RBAC phân cấp (Hierarchical RBAC) cho phép mô hình hóa trực quan cơ cấu tổ chức doanh nghiệp (Admin $\to$ Manager $\to$ Staff), không cung cấp bằng chứng cho tỷ lệ giảm lỗi cấu hình cụ thể của đồ án này.
- **Kiến trúc dữ liệu đa khách thuê:** [3] trình bày nhu cầu chia sẻ hạ tầng và khó khăn bảo trì/cấu hình; bản tác giả xác nhận IWPSE-EVOL2010, không phải tựaESEM trước đây. [4] thảo luận kiến trúc SaaS; metadata đối chiếu CLOSER2012. Shared-schema trong đồ án là quyết định thiết kế; membership, quyền và scope phải được kiểm tra, chưa đo chi phí giữa các kiến trúc nên không kết luận tối ưu mọiSME.
- **Phân chia module:** Parnas [5] nghiên cứu tiêu chí phân rã module. Nguồn này hỗ trợ thảo luận về modularity, không chứng minh Modular Monolith luôn nhanh/rẻ hơn microservices. Chọn monolith trong đồ án là quyết định thiết kế để dùng chung transaction và giảm thành phần vận hành; cần đo nếu muốn so sánh hiệu năng.

### 1.2. Kỹ thuật Tạo văn bản Tăng cường Truy xuất (RAG) và Kiểm soát Tính Xác thực

Sự bùng nổ của các mô hình ngôn ngữ lớn (LLMs) dựa trên kiến trúc Transformer [8] đã mở ra tiềm năng lớn cho trợ lý thông minh doanh nghiệp. Tuy nhiên, việc ứng dụng LLM trong môi trường doanh nghiệp gặp phải rào cản nghiêm trọng về hiện tượng "ảo giác" (hallucination) và thiếu cập nhật tri thức nội bộ:
- **RAG và REALM:** Lewis et al. [9] kết hợp bộ nhớ tham số của mô hình sinh với chỉ mục Wikipedia ngoài mô hình; nghiên cứu huấn luyện chung retriever và generator, dùng Maximum Inner Product Search, không mặc nhiên là cosine hoặc không cần fine-tuning. REALM [10] là hướng retrieval-augmented language-model pretraining, không đồng nhất với kiến trúc sinh của [9]. Đồ án chỉ vận dụng cách lấy tài liệu làm ngữ cảnh, dùng cosine/lexical ranking và provider đã có; không tái hiện phương pháp huấn luyện của hai bài.
- **Giới hạn factuality:** Ji et al. [11] và Maynez et al. [12] nghiên cứu ảo giác và tính trung thực của văn bản sinh. Không quy đổi thành tỷ lệ 15–30% cho hệ thống này. FinQA [13] đánh giá suy luận số học trên dữ liệu tài chính, không chứng minh regex loại bỏ ảo giác trong SOP hoặc SLA.

### 1.3. Mô hình Dự báo Chuỗi Thời gian trong Ngành Bán lẻ (Retail Time-Series Forecasting)

Dự báo nhu cầu hàng hóa và doanh thu bán lẻ là bài toán trung tâm của quản trị chuỗi cung ứng:
- **Thuật toán Gradient Tree Boosting (XGBoost):** Chen & Guestrin [14] trình bày hệ thống tree boosting. Nguồn [15] trình bày LightGBM với GOSS/EFB, không phải bằng chứng XGBoost vượt mạng học sâu trên doanh thu của đồ án. Đồ án chọn XGBoost để thử nghiệm trên đặc trưng trễ/lịch; hiệu quả phải đo so với baseline cùng điều kiện.
- **Đối chiếu các phương pháp dự báo:** M4 [16] ghi nhận kết quả tốt của phương pháp kết hợp và hybrid; không chứng minh XGBoost luôn tốt hơn LSTM trên chuỗi ngắn. Sách [17] và N-BEATS [18] là nguồn tham khảo phương pháp, không thay thế thực nghiệm đối chứng của đồ án. Chưa đo so sánh LSTM/N-BEATS hoặc chi phí GPU nên không công bố ưu thế tương ứng.
- **Giao thức đánh giá chuỗi thời gian:** Đồ án dùng chronological split và chỉ tạo đặc trưng từ quá khứ, theo giao thức thực nghiệm đã công bố. Nguồn [19] nghiên cứu cách đánh giá chuỗi thời gian; không diễn giải thành lệnh cấm mọi dạng cross-validation trong mọi điều kiện. Phạm vi và giả định của nguồn cần đối chiếu trước khi trích dẫn sâu.

### 1.4. Hệ thống Thông tin Địa lý (GIS) và Tối ưu hóa Điều phối Dịch vụ Hiện trường

Quản trị dịch vụ kỹ thuật bảo hành đòi hỏi sự hỗ trợ đắc lực của công nghệ không gian:
- **Chuẩn và khoảng cách không gian:** OGC [20] mô tả simple-feature geometry và hệ tham chiếu, không buộc mọi dữ liệu dùng WGS84. Karney [21] nghiên cứu geodesic trên ellipsoid; không dùng một tỷ lệ sai số cố định cho mọi cặp tọa độ. PostGIS [22] cung cấp toán tử geometry/geography; `ST_Distance` trên geography mặc định dùng spheroid, còn geometry có đơn vị theo SRID. GiST không tự bảo đảm mọi query distance đều dùng index. Đồ án chọn SRID 4326, phân biệt sphere/spheroid/road distance và kiểm reference cases.
- **Bài toán Định vị Chi nhánh và Vùng Phủ Dịch vụ:** Drezner & Hamacher [23] và Church & Murray [24] đã hệ thống hóa lý thuyết về bài toán định vị cơ sở (Facility Location Problem) và bài toán vùng phủ tối đa (Maximal Covering Location Problem - MCLP). Trong điều phối kỹ thuật viên hiện trường, việc xác định kỹ sư phù hợp dựa trên bán kính phục vụ tối đa ($R_{\text{service}}$) và khoảng cách thực tế đến vị trí khách hàng là bài toán tối ưu rời rạc có ràng buộc thực tiễn cao.

---

## 2. PHÂN TÍCH SO SÁNH GIẢI PHÁP KHOA HỌC (COMPARATIVE ANALYSIS)

Đề tài chưa có khảo sát thực nghiệm các sản phẩm thương mại. Không dùng
nhận xét về SAP, Odoo hoặc SaaS nói chung làm bằng chứng ưu thế.
Ma trận triển khai/giới hạn theo code được ghi ở mục 1.3 của
THUYET_MINH_DO_AN_CHUONG_1_VA_2.md và ACADEMIC_USE_CASE_TRACEABILITY_2026_09_25.md.

| Nguồn / bài toán | Cách tiếp cận được nguồn trình bày | Giới hạn khi áp dụng vào đồ án |
|---|---|---|
| Bezemer/Zaidman2010 [3] | Position paper về multi-tenancy, chia sẻ tài nguyên, cấu hình và bảo trì | Không benchmark code AlphaTech; lấy làm bối cảnh lựa chọn, không chứng nhận performance isolation |
| Krebs/Momm/Kounev2012 [4] | Phân tích các mối quan tâm kiến trúc multi-tenant | Không có kết quả định lượng giảm chi phí của đồ án |
| Lewis2020 [9] | Kết hợp mô hình sinh với bộ nhớ truy xuất trong bài toánNLP | Không tự đảm bảo câu tiếngViệt đúng/đủ hoặc tool số liệu có quyền; đo retrieval, provenance và chấm người riêng |
| Ji2023 [11] | Tổng quan hallucination trong natural-language generation | Không gán tỷ lệ hallucination của tổng quan cho5câu đồ án hoặc gọi regex là semantic guard |
| M42018 [16] | So sánh dự báo quy môcompetition, ghi nhận phương pháp hybrid/kết hợp | Không kết luận XGBoost thắnglag7 trên snapshot synthetic; giữ metric kém và horizon rõ |

Đây là đối chiếu cách áp dụng, không tái hiện thí nghiệm các bài báo hoặc chứng
minh đóng góp thuật toán mới. Bài2010/2012 là nền tảng lịch sử; các bài2018/2020/
2023 bổ sung hướng nghiên cứu trong khoảng5–10năm. Chưa khảo sát riêng nghiên
cứu trongnước, không tự gán nhãn đã đầy đủ theo yêu cầu thầy.

## 3. KHOẢNG TRỐNG Ở MỨC ỨNG DỤNG VÀ PHẠM VI CHỨNG MINH

Đây là các nhu cầu của kịch bản đồ án bán lẻ thiết bị và dịch vụ kỹ thuật,
không phải kết quả khảo sát thị trường hay chứng minh tính mới của thuật toán.
Không suy ra "đa số doanh nghiệp" hoặc "đa số hệ thống RAG" thiếu chức năng
khi chưa có dữ liệu khảo sát. Việc ghép Django, RAG, PostGIS và XGBoost tự nó
không chứng minh đóng góp khoa học mới.

### 3.1. Nhu cầu vận hành bán lẻ và dịch vụ trong một cổng

- **Vấn đề của kịch bản:** nhân viên cần truy cập đơn hàng, tồn kho và phiếu dịch vụ trong phạm vi được phân quyền; khách hàng cần cổng riêng theo dõi giao dịch.
- **Cách triển khai:** các app retail/service_ops dùng kiến trúc chung và dữ liệu workspace-scoped. Workspace bán lẻ và dịch vụ vẫn có thể tách nhau; không tuyên bố mọi Order đã liên kết với ServiceRequest hoặc có tự động tra bảo hành từ đơn hàng nếu chưa có quan hệ/chức năng đó.
- **Nguồn kiểm tra:** `apps/public_web/fulfillment.py`, `apps/service_ops/services.py`, `apps/workspaces/services.py`; tests `test_checkout_concurrency.py`, `test_service_requests.py`, `test_internal_authorization_regressions.py`.
- **Giới hạn:** demo tích hợp cổng và quyền; chưa đo hiệu quả tài chính hay tiết kiệm thời gian tại doanh nghiệp thật.

### 3.2. Nhu cầu câu trả lời có nguồn và đo chất lượng tách bạch

- **Vấn đề của kịch bản:** trả lời nghiệp vụ cần phân biệt tài liệu, số liệu tool, fallback và câu chưa đủ bằng chứng.
- **Runtime:** `apps/knowledge/services.py` điều phối intent, retrieval, tool có kiểm tra quyền và sinh phản hồi; retrieval ghi provenance/không gian embedding. Nhánh root-cause thiếu dữ liệu yêu cầu bổ sung, không tự đặt giờ SLA hoặc trọng số.
- **Đánh giá ngoại tuyến:** `apps/knowledge/evaluation.py` gọi `evaluation_scoring.py` với rubric có nhãn, kiểm keyword groups, numeric facts và gold chunk IDs. Đây KHÔNG phải bộ chặn runtime tự động từ chối hoặc sửa mọi câu trả lời.
- **Nguồn kiểm tra:** `test_embedding_space_isolation.py`, `test_adversarial_rag_execution.py`, `test_rag_evaluation.py`, `test_root_cause_grounding.py`.
- **Giới hạn:** regex có thể khớp số trong câu phủ định; cần chấm đúng/đủ ngữ nghĩa độc lập. Không có cam kết loại bỏ toàn bộ ảo giác, không dùng test router làm điểm chất lượng LLM.

### 3.3. Nhu cầu kiểm soát hành động từ khuyến nghị

- **Vấn đề của kịch bản:** đề xuất không được mặc nhiên trở thành mutation có quyền quản trị.
- **Cách triển khai:** registry giới hạn action hỗ trợ; kiểm quyền workspace, chặn tự duyệt với reviewer không phải superuser (có bypass superuser tường minh), quản lý trạng thái/idempotency, thực thi transaction đối với dữ liệu database và ghi audit.
- **Nguồn kiểm tra:** `apps/approvals/registry.py`, `apps/approvals/executor.py`; `test_approval_state_integrity.py`, `test_approval_concurrency_evidence.py`, `test_audit_database_evidence.py`.
- **Giới hạn:** DB rollback không tự hoàn tác side effect bên ngoài; trigger audit không bảo vệ trước mọi quyền quản trị database. Stock reorder/workload balancing chưa có contract đủ an toàn vẫn là advisory; không tuyên bố toàn bộ handler đã nghiệm thu production.

**Tiêu chí mục 80:** mô tả đúng vấn đề của kịch bản, cách triển khai và giới hạn,
không tuyên bố phát minh thuật toán hoặc tính mới chỉ nhờ tích hợp công nghệ.
Danh mục tham khảo mục 4 còn cần rà nguồn theo yêu cầu thầy (mục 89), không được
coi việc đóng ranh giới ứng dụng là đã duyệt tất cả tài liệu tham khảo.

---

## 4. DANH MỤC TÀI LIỆU THAM KHẢO KHOA HỌC CHUẨN IEEE

```text
[1] R. S. Sandhu, E. J. Coyne, H. L. Feinstein, and C. E. Youman, "Role-Based Access Control Models," IEEE Computer, vol. 29, no. 2, pp. 38-47, Feb. 1996, doi: 10.1109/2.485845.
[2] D. F. Ferraiolo, R. Sandhu, S. Gavrila, D. R. Kuhn, and R. Chandramouli, "Proposed NIST standard for role-based access control," ACM Transactions on Information and System Security (TISSEC), vol. 4, no. 3, pp. 224-274, Aug. 2001, doi: 10.1145/501978.501980.
[3] C.-P. Bezemer and A. Zaidman, "Multi-tenant SaaS applications: Maintenance dream or nightmare?," in Proc. 4th Int. Joint ERCIM/IWPSE Symp. Software Evolution (IWPSE-EVOL), Antwerp, Belgium, 2010, pp. 88–92. [Online]. Available: https://azaidman.github.io/publications/bezemerIWPSE2010.pdf [Accessed: Oct. 5, 2026].
[4] R. Krebs, C. Momm, and S. Kounev, "Architectural concerns in multi-tenant SaaS applications," in Proc. 2nd Int. Conf. Cloud Computing and Services Science (CLOSER), vol. 1, Porto, Portugal, 2012, pp. 426–431, doi: 10.5220/0003957604260431.
[5] D. L. Parnas, "On the criteria to be used in decomposing systems into modules," Communications of the ACM, vol. 15, no. 12, pp. 1053–1058, 1972, doi: 10.1145/361598.361623.
[6] S. Newman, Building Microservices: Designing Fine-Grained Systems, 2nd ed. Sebastopol, CA, USA: O'Reilly Media, 2021.
[7] H. Garcia-Molina and K. Salem, "Sagas," in Proc. 1987 ACM SIGMOD Int. Conf. on Management of Data, pp. 249-259, 1987, doi: 10.1145/38713.38742.
[8] A. Vaswani et al., "Attention Is All You Need," in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, pp. 5998-6008, 2017.
[9] P. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," in Advances in Neural Information Processing Systems (NeurIPS), vol. 33, pp. 9459-9474, 2020.
[10] K. Guu, K. Lee, Z. Tung, P. Pasupat, and M. Chang, "Retrieval Augmented Language Model Pre-Training," in Proc. 37th Int. Conf. on Machine Learning (ICML '20), vol. 119, pp. 3929-3938, 2020.
[11] Z. Ji et al., "Survey of Hallucination in Natural Language Generation," ACM Computing Surveys, vol. 55, no. 12, pp. 1-38, 2023, doi: 10.1145/3571730.
[12] J. Maynez, S. Narayan, B. Bohnet, and R. McDonald, "On Faithfulness and Factuality in Abstractive Summarization," in Proc. 58th Annual Meeting of the Assoc. for Computational Linguistics (ACL '20), pp. 1906-1919, 2020, doi: 10.18653/v1/2020.acl-main.173.
[13] Z. Chen et al., "FinQA: A Dataset of Numerical Reasoning over Financial Data," in Proc. EMNLP, pp. 3697–3711, 2021, doi: 10.18653/v1/2021.emnlp-main.300.
[14] T. Chen and C. Guestrin, "XGBoost: A Scalable Tree Boosting System," in Proc. 22nd ACM SIGKDD Int. Conf. on Knowledge Discovery and Data Mining (KDD '16), pp. 785-794, 2016, doi: 10.1145/2939672.2939785.
[15] G. Ke et al., "LightGBM: A Highly Efficient Gradient Boosting Decision Tree," in Advances in Neural Information Processing Systems (NeurIPS), vol. 30, pp. 3146-3154, 2017.
[16] S. Makridakis, E. Spiliotis, and V. Assimakopoulos, "The M4 Competition: Results, findings, conclusion and way forward," International Journal of Forecasting, vol. 34, no. 4, pp. 802–808, 2018, doi: 10.1016/j.ijforecast.2018.06.001.
[17] R. J. Hyndman and G. Athanasopoulos, Forecasting: principles and practice, 2nd ed. Melbourne, Australia: OTexts, 2018.
[18] B. N. Oreshkin, D. Carpov, N. Chapados, and Y. Bengio, "N-BEATS: Neural basis expansion analysis for interpretable time series forecasting," in Proc. 8th Int. Conf. on Learning Representations (ICLR '20), 2020.
[19] C. Bergmeir and J. M. Benítez, "On the use of cross-validation for time series predictor evaluation," Information Sciences, vol. 191, pp. 192-213, 2012, doi: 10.1016/j.ins.2011.12.028.
[20] Open Geospatial Consortium (OGC), "OpenGIS Implementation Standard for Geographic Information - Simple feature access - Part 1: Common architecture," Standard OGC 06-103r4, 2011.
[21] C. F. F. Karney, "Algorithms for geodesics," Journal of Geodesy, vol. 87, no. 1, pp. 43-55, 2013, doi: 10.1007/s00190-012-0578-z.
[22] PostGIS Project Steering Committee, "PostGIS 3.6 Spatial Database Extension for PostgreSQL," Technical Documentation, 2025. [Online]. Available: https://postgis.net/documentation/
[23] Z. Drezner and H. W. Hamacher, Eds., Facility Location: Applications and Theory. Berlin, Heidelberg: Springer, 2004.
[24] R. L. Church and A. T. Murray, Business Site Selection, Location Analysis, and GIS. Hoboken, NJ: John Wiley & Sons, 2009.
```
