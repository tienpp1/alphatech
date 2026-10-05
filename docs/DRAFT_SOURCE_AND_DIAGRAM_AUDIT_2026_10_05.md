# Đối chiếu bản nháp: nguồn, sơ đồ và hợp đồng triển khai

## Phạm vi và ranh giới

Rà các bản Markdown chương1–5 và related-work, không sửa bản Word đã duyệt,
không thay ID/cấu trúc/tiến độ sổ97. Chủ dự án xác nhận chưa có báo cáo/slide
nộp cuối khác; sửa draft không phải nghiệm thu bản nộp cuối. Không tự đóng mọi
tiêu chí bằng số file hoặc test. Không sửa database, role, mật khẩu hoặc provider.

## Những sai khác đã sửa theo source

| Nhóm | Sai khác cũ | Hiệu chỉnh và nguồn đối chiếu |
|---|---|---|
| RBAC | Kế thừa4role, gộpVIEWER/CUSTOMER; cấmEMPLOYEE đọc forecast | Role grants tường minh, customer không membership; seed cho forecasting.view_forecast; Google identity chỉ public |
| Workspace | Middleware giả tên và mọiORM tự lọc; workspace là chi nhánh | WorkspaceMiddleware và scoped query; entity con theo cha, không global filter/RLS |
| ERD | UserMembership, KnowledgeEmbedding, TeamChatChannel; audit FK giả |22FK thật dùng label ORM, optionality theo field; audit entity_type/entity_id không FK |
| Checkout | Tạo CONFIRMED ngay; luôn trừ kho; NotificationOutbox giả | Public checkout tạoPENDING, policy strict opt-in, CustomerEmailDelivery sau commit |
| Dịch vụ | Tự dispatch/đóng phiếu theoGIS/ghi giờ | Inquiry tạoOPEN vớiCustomer cùngworkspace; assign và labor là thao tác riêng có quyền |
| RAG | SELECT cosinepgvector LIMIT3; retrieved chunks tự làgold | READY/workspace/embedding provenance filter, cosine+lexicalPython, top_ksettings; gold là nhãn evaluation |
| Chat/bản tin | request.user.role, push tức thời | Active membership vàcan_manage_bulletins; since_idpolling3giây |
| Hạ tầng | BrevoSMTP587, Argon2 mặc định, HNSW/IVFFlat mặc định | Backend theo môi trường, BrevoHTTPS trênFree; hasherDjango; không suyindex từ extension |
| Audit | Bất biến chống gian lận, saga bồi hoàn tổng quát | Append-only/trigger theo quyền; DBowner có thể can thiệp, rollbackDB không rollback ngoại dịch vụ |
| Trích dẫn | Thiếu[1]/[4]/[6] ở giải thích lý thuyết | Thêm sốIEEE gắn đoạnSandhu/Chen/Güting; chưa tự duyệt mọicitation |
| Kết quả và giới hạn | Chỉ ghi full lỗi cũ; chưa có recursive mới; giả thuyết là nguyên nhân | Giữ lịch sử, thêm full1201 và CI58% đúng SHA; bảng recursive180 ngày, XGBoost kém lag7; không gọi nguyên nhân đã chứng minh |
| Approval/GIS | Field created_by giả và chặn mọi self-approval; chỉ có đường chim bay | requester_id, bypass superuser; phân biệt OSRM đường bộ, spheroid backend và Haversine browser |

Nguồn đọc: apps/workspaces/models.py vàmiddleware.py; accounts/seed_demo.py;
retail/models.py; service_ops/models.py vàservices.py; public_web/views.py và
fulfillment.py; notifications/models.py/chat_service.py/bulletin_service.py;
knowledge/models.py/retrieval.py/services.py; audit/models.py; approvals/registry.py.
seed_demo.py nằm trong apps/accounts/management/commands/. Không chạy seed.

Snapshot mới: output/model_contract_20261005_closure/model_contract.json,
routes.json và diagram từngapp. Exporter đã chạy:48model, không phát query dữ
liệu bởi exporter. Đây là metadata ORM khai báo, không xác nhận schema deployed,
quyền, migration đã apply hoặc adequacy. ERD draft chỉ là sơ đồ con22FK, không
phải toàn48model. Regression test kiểm từng endpoint model, field FK, target và
null/optionality trực tiếp từ Django registry; sequence được đối chiếu source,
không tự coi string guard là thực thi mọi workflow.

## Đối chiếu nguồn nhà xuất bản

Ngày truy cập05/10/2026. Chọn bản hội nghịCLOSER2012 cho nguồn[4] của
TONG_QUAN_NGHIEN_CUU_VA_KHOANG_TRONG_UNG_DUNG.md: tên tác giả/tựa, vol.1,
pp.426–431, DOI10.5220/0003957604260431 khớp metadata
[SciTePress](https://www.scitepress.org/Link.aspx?doi=10.5220%2F0003957604260431).
Không tiếp tục dùng thông số chươngSpringer2013 chưa xác minh. Bài thảo luận
chia sẻ ứng dụng và các mối quan tâm kiến trúc; không chứng minh performance
isolation của code đồ án hoặc shared-schema tối ưu mọiSME. Fetch trang có lần
internal-error, nhưng kết quả indexed của trang nhà xuất bản có metadata;
không ghi đã đọc/chấm toànPDF.

Nguồn[3] related-work và[2] chương1–2 ban đầu trộn tựa/hội nghị/DOI.
Đã thay bằng “Maintenance dream or nightmare?”, IWPSE-EVOL2010, pp.88–92,
đối chiếu [danh sách công trình tác giả](https://azaidman.github.io/publications.html)
và [bản bài báo của tác giả](https://azaidman.github.io/publications/bezemerIWPSE2010.pdf).
Bài là position paper: trình bày các thách thức vận hành ứng dụng dùng chung,
không đo lợi ích của AlphaTech. Không inventDOI cho bản này. Giữ sốtrích dẫn
trong từngdraft, không áp sốrelated-work vàoWord.

Sửa diễn giảiGIS theo [PostGIS ST_Distance](https://postgis.net/docs/ST_Distance.html):
geometry phụ thuộc đơn vịSRID; geography mặc định dùng spheroid. Không quy định
mọiSimpleFeatures làWGS84, không gán tỷ lệ lỗiHaversine cố định hoặc chứng nhận
indexusage từ sự tồn tạiGiST. Luồng đồ án phải đọc cùng apps/gis/services.py.

Karney được đối chiếu [trang Springer](https://link.springer.com/article/10.1007/s00190-012-0578-z):
tác giả Charles F. F. Karney, volume 87, pp.43–55, năm issue 2013 (online 2012).
Không trộn năm online với năm issue hoặc dùng bài này chứng nhận đường bộ OSRM.

Đọc abstract và Methods (pp.1–3) của
[Lewis et al., NeurIPS 2020](https://proceedings.nips.cc/paper/2020/file/6b493230205f780e1bc26945df7481e5-Paper.pdf):
sửa mô tả trước đó gán cosine và không-fine-tuning cho bài RAG gốc. Bài dùng
MIPS và huấn luyện retriever/generator chung; runtime đồ án không tái hiện
training đó. Truy cập ACM Ji và ScienceDirect M4 có lỗi; không ghi đã đọc toàn
văn các bài này từ search snippet hoặc lấy nguồn arXiv thay cho bản xuất bản.

## Các việc vẫn chưa thể ký nghiệm thu

- Nguồn3/4 đã xử lý bằng edition xác minh; vẫn chưa duyệt mọinguồn khác chỉ
  vì một vài URL mở được. Bảng so sánh5nguồn hiện ghi rõ phạm vi và giới hạn.
- Bibliography của related-work, chương1–5 và Word duyệt là các namespace khác
  nhau. Không ghép[4] ởWord với[4] ởrelated-work. Trước bản nộp phải thống nhất
  một bibliography, thứ tự lần xuất hiện, mọi đoạn được nguồn hỗ trợ, ngày truy
  cập và hangingindent. Không chuyển25nguồn draft vào12nguồn Word tự động.
- Một số tài liệu liệt kê ở chương3–5 chưa được trích vào nội dung; danh sách
  nguồn không tự là related-work. Chưa có fullpaper-review mọinguồn hoặc bảng
  so sánh nghiên cứu5–10năm gần đây đã được thầy duyệt. Sách cũ dùng làm cơ sở
  lý thuyết, không thay nghiên cứu cập nhật.
- User chốt ngày05/10 chỉ nghiệm thu5IND đã chấm, ghi rõ khôngholdoutmù.
  Đây là thay đổi phạm vi đã xác nhận, không phải bằng chứng thực hiệnholdout.
- Chưa chứng nhận visualchat hai phiên hoặc toàn hình của bản nộp tương lai
  từAPItests; scope local/advisory/offsitehoãn giữ nguyên theo chủ dự án.

## Kiểm chứng của đợt này

Lệnh kiểm thử sau sửa:

`python -X utf8 manage.py test tests.test_academic_diagram_contract tests.test_academic_current_claims tests.test_academic_scope_contract --settings=config.settings_evidence_test --noinput`

- Kết quả cuối sau bổ sung guard kết quả/GIS/approval: **12 tests / 0.045s, OK**, check tích hợp không có lỗi. Các lượt 11 test trước đó giữ riêng, không cộng số lần chạy.
- `python -X utf8 manage.py check`: không có lỗi.
- `python -X utf8 manage.py makemigrations --check --dry-run`: No changes detected.
- `git diff --check`: đạt; cảnh báo chuẩn hóa CRLF không phải lỗi whitespace.
- Những lần chạy trước phát hiện đoạn Brevo SMTP còn sót và một string contract
  không khớp chữ hoa; đã sửa nội dung, không bỏ assertion. Test ERD kiểm đủ 22 FK.
- CI đã thêm bước chạy nhóm guard này trong quality.yml, **chưa có remote run
  trên source mới của đợt tài liệu**. Không hồi gán CI xanh của ea18f14.
- Browser mở cổng nội bộ production đúng; ban đầu Render Free cold-start.
  Chưa đăng nhập, chưa gửi tin/bản tin, chưa quan sát hai phiên. Đã yêu cầu
  chủ dự án đăng nhập tài khoản nội bộ thử nghiệm, không gửi mật khẩu vào chat.

Word duyệt giữ SHA256
`9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816`.
Sổ 97 giữ hash đầu đợt
`1d532616a6e9c9b780aa47c6ea680793ecbcc7c9f58ee3989d5fae5f0daeec20`.

Đây là sửa tài liệu và test guard local; không cần deploy ứng dụng chỉ để sửa
tài liệu học thuật. Full 1201 thuộc release trước, không gán cho source mới.
Không tuyên bố 97/97 PASS hoặc bỏ qua phần tài liệu nộp cuối chưa tồn tại.
