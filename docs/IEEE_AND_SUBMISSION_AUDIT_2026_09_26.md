# Rà soát IEEE và bản đề cương nộp — 26/09/2026

## Artifact được kiểm tra

- Bản thầy đã duyệt được giữ nguyên:
  `output/docx_review/teacher_review_v2/De_cuong_Ha_Minh_Tien_sua_gop_y_lan_2.docx`
- Bản đối chiếu học thuật, không ghi đè bản gốc:
  `output/docx_review/teacher_review_v2/De_cuong_Ha_Minh_Tien_doi_chieu_hoc_thuat.docx`
- SHA-256 bản đối chiếu:
  `BCB8C93ED83E26BAE70DAD55DC40C3388340D3051217D380A3A287DBDB38417E`
- Đã render và kiểm tra trực quan 16/16 trang bằng LibreOffice; không có trang
  tràn, mất chữ hay vỡ bảng.

## Hiệu chỉnh kết luận

1. Giữ yêu cầu “chat realtime” của thầy ở mức tên chức năng, đồng thời ghi rõ
   triển khai hiện tại là trải nghiệm gần thời gian thực bằng polling 3 giây,
   không tự nhận WebSocket/push tức thời.
2. Mô tả dữ liệu dự báo theo chia huấn luyện/kiểm thử theo thời gian; chỉ ghi
   tập kiểm định riêng khi cấu hình thực nghiệm thực sự tạo tập này.
3. Bỏ kết luận “Django/GeoDjango vượt trội hoàn toàn”. Công nghệ được chọn vì
   phù hợp với phạm vi dữ liệu quan hệ/GIS của đồ án, không phải do benchmark.
4. Kết quả XGBoost cho hai bài toán đếm chỉ được mô tả là MAE thấp hơn baseline
   trên snapshot đã lưu. Vì R² vẫn âm, không gọi là học quy luật “xuất sắc” hoặc
   ưu thế tổng quát.

## Đối chiếu 12 tài liệu tham khảo

| STT | Nguồn kiểm tra | Kết luận |
|---|---|---|
| 1 | [OECD — The Digital Transformation of SMEs](https://www.oecd.org/en/publications/the-digital-transformation-of-smes_bdb9256a-en.html) | Đúng tên, nhà xuất bản, năm 2021 và DOI. |
| 2 | [NeurIPS — Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html) | Đúng tên, nhóm tác giả, tập 33, trang 9459–9474 và năm 2020. |
| 3 | [DOI — XGBoost: A Scalable Tree Boosting System](https://doi.org/10.1145/2939672.2939785) | DOI, tác giả, hội nghị, trang và năm khớp metadata bài báo ACM; trang ACM chặn fetch tự động 403 nhưng DOI giữ nguyên. |
| 4 | [Django 5.2 documentation](https://docs.djangoproject.com/en/5.2/) | Tài liệu chính thức, đúng nhánh phiên bản được trích dẫn. |
| 5 | [Django REST framework](https://www.django-rest-framework.org/) | Tài liệu chính thức của dự án. |
| 6 | [PostgreSQL documentation](https://www.postgresql.org/docs/current/index.html) | Tài liệu chính thức; đường `current` là phiên bản hiện hành, nên có ngày truy cập. |
| 7 | [pgvector repository](https://github.com/pgvector/pgvector) | Kho nguồn chính thức mô tả vector similarity search cho PostgreSQL. |
| 8 | [Google Gemini API models](https://ai.google.dev/gemini-api/docs/models) | Tài liệu chính thức; chỉ hỗ trợ mô tả API/model, không chứng minh một run live. |
| 9 | [JMLR — Scikit-learn: Machine Learning in Python](https://jmlr.org/papers/v12/pedregosa11a.html) | Đúng tạp chí, tập 12, trang 2825–2830 và năm 2011. |
| 10 | [GeoDjango 5.2](https://docs.djangoproject.com/en/5.2/ref/contrib/gis/) | Tài liệu chính thức cho API GIS của Django. |
| 11 | [PostGIS ST_DWithin](https://postgis.net/docs/ST_DWithin.html) | Tài liệu chính thức cho truy vấn trong khoảng cách. |
| 12 | [Leaflet API reference](https://leafletjs.com/reference.html) | Tài liệu chính thức; trang hiện phản ánh Leaflet 1.9.4. |

Các nguồn là bài báo phản biện, OECD hoặc tài liệu chính thức của công nghệ;
không dùng blog, arXiv hay đồ án đại học. Các trích dẫn trực tuyến trong bản đối
chiếu dùng cấu trúc IEEE `[Online]. Available: ... [Accessed: ...]` và hanging
indent 1 cm để tránh khoảng trắng giãn bất thường ở bản cũ.

## Ranh giới

- Việc URL mở được và metadata khớp không tự chứng minh mọi kết luận trong báo
  cáo; mỗi kết luận vẫn phải giới hạn theo bằng chứng thực nghiệm của repository.
- Bản lịch sử có tên đề tài cũ được giữ để truy vết khi đã có đính chính rõ;
  bản đề cương nộp và hồ sơ hiện hành dùng tên chuẩn “Xây dựng nền tảng quản lý
  vận hành doanh nghiệp tích hợp trợ lí AI”.
