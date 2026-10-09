# Đối chiếu nguồn và diễn giải học thuật ngày 09 tháng 10 năm 2026

Phạm vi là các bản nháp hiện có, phục vụ đề tài “Xây dựng nền tảng quản lý vận
hành doanh nghiệp tích hợp trợ lí AI”. Bản Word teacher_review_v2 đã duyệt được
giữ nguyên. Đợt này hoàn tất rà soát nguồn đang dùng trong chương 1–2 và sửa
diễn giải triển khai ở chương 3–5; việc thầy duyệt một báo cáo nộp mới là thủ tục
riêng sau khi sinh viên hoàn thiện bản nộp.

## Bối cảnh đến vấn đề và giải pháp

Phần đặt vấn đề dùng bối cảnh chuyển đổi số SMEs từ OECD, sau đó nêu nhu cầu
trong kịch bản bán lẻ và dịch vụ của đồ án. Không suy ra đa số doanh nghiệp nhập
hàng theo cảm tính hoặc chứng minh lợi ích tài chính bằng seed data. Khoảng
trống được trình bày là nhu cầu tích hợp cổng, quyền, hỏi đáp có nguồn và hành
động có kiểm soát trong kịch bản; không nhận là phát minh thuật toán.

## Nguồn thực sự sử dụng ở chương 1 và 2

| Số IEEE | Nguồn chính | Nội dung hỗ trợ và giới hạn |
|---|---|---|
| 1 | OECD 2021, DOI 10.1787/bdb9256a-en | Bối cảnh/rào cản chuyển đổi số SMEs; không khảo sát AlphaTech hoặc đo ROI |
| 2 | Lewis et al., NeurIPS 2020 | Kết hợp sinh với bộ nhớ truy xuất; implementation AlphaTech khác phương pháp huấn luyện trong bài, không chuyển điểm benchmark |
| 3 | Nguyen et al., COLING 2020, DOI 10.18653/v1/2020.coling-main.233 | UIT-ViQuAD, công trình nhóm UIT/VNU-HCM về đọc hiểu tiếng Việt; trích xuất đáp án từ Wikipedia khác SOP/hybrid tool có quyền |
| 4 | Hyndman/Athanasopoulos, FPP3 2021 | Baseline, đánh giá ngoài mẫu và horizon; MAPE có vấn đề với zero, cần báo số mẫu hợp lệ |
| 5 | Sandhu et al., Computer 1996, DOI 10.1109/2.485845 | User–role–permission; role grants hiện tại không có cây kế thừa tự động |
| 6 | Bezemer/Zaidman, IWPSE-EVOL 2010, pp. 88–92 | Position paper về bảo trì multi-tenancy; không chứng minh hiệu năng hoặc chi phí AlphaTech |
| 7 | Chen/Guestrin, KDD 2016, DOI 10.1145/2939672.2939785 | Metadata công trình XGBoost; biểu thức đối chiếu thêm tutorial chính thức, không ghi đã tải được toàn văn ACM trong đợt này |
| 8 | Güting, VLDB Journal 1994, DOI 10.1007/BF01231602 | Khái niệm database không gian; không quy định mọi tọa độ phải dùng WGS84 |

Các bài cũ là cơ sở lý thuyết. Bảng related-work còn có Krebs 2012, M4 2018 và
Ji 2023, cùng UIT-ViQuAD 2020 để đối chiếu hướng nghiên cứu gần hơn và nghiên
cứu của tác giả tại Việt Nam. Đây là tổng quan có chọn lọc, không systematic
review và không tái hiện toàn bộ thí nghiệm của các công trình.

## Đường dẫn đối chiếu chính

- OECD: https://www.oecd.org/en/publications/the-digital-transformation-of-smes_bdb9256a-en.html
- RAG, nhà xuất bản NeurIPS: https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html
- UIT-ViQuAD, ACL Anthology: https://aclanthology.org/2020.coling-main.233/
- FPP3, độ đo: https://otexts.com/fpp3/accuracy.html
- FPP3, temporal cross-validation: https://otexts.com/fpp3/tscv.html
- RBAC, bản tại NIST: https://csrc.nist.gov/csrc/media/projects/role-based-access-control/documents/sandhu96.pdf
- Bezemer/Zaidman, bản tác giả: https://azaidman.github.io/publications/bezemerIWPSE2010.pdf
- XGBoost, DOI: https://doi.org/10.1145/2939672.2939785
- XGBoost, biểu thức mô hình chính thức: https://xgboost.readthedocs.io/en/stable/tutorials/model.html
- Güting, bản tại trường tác giả: https://www.fernuni-hagen.de/pi4pp/papers/IntroSpatialDBMS.pdf
- PostGIS, đơn vị và sphere/spheroid: https://postgis.net/docs/ST_Distance.html

Không dùng blog, arXiv hoặc đồ án đại học làm nguồn bổ sung. Đã bỏ nguồn Prophet
không được sử dụng khỏi chương 1–2 và 19 mục đọc thêm không có citation khỏi
chương 3–5. Số IEEE chương 1–2 được đánh lại theo lần xuất hiện đầu; related-work
là tài liệu riêng có danh mục riêng. Không áp số mới lên Word đã duyệt.

## Các diễn giải triển khai đã hiệu chỉnh

Approval so requester_id và chặn reviewer không phải superuser tự duyệt; ngoại
lệ superuser được ghi rõ. Stock transfer có transaction/lock và tạo EXECUTED,
không khẳng định hai bước duyệt bắt buộc. Kiểm tồn strict là opt-in. Trợ lý
công khai không truy xuất SOP nội bộ. Embedding/index và provider phải theo
đường runtime/provenance thực tế. GIS hỗ trợ vị trí và khoảng cách, không tự
dispatch hoặc chứng minh tuyến tối ưu tuyệt đối. CSRF/escaping được mô tả theo
cơ chế áp dụng, không nhận mọi ngữ cảnh đã an toàn tuyệt đối.

Các claims bất lợi về forecasting, mode offline RAG, coverage, giới hạn audit
và lần test lỗi lịch sử vẫn được giữ. Mục 79/80/89 được xử lý trong bộ bản nháp
hiện có; nội dung sinh viên bổ sung sau này cần kiểm lại trích dẫn tương ứng.
