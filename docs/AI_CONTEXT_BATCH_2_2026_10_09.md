# Bổ sung ngữ cảnh AI — đợt 2, 09/10/2026

Phạm vi local theo yêu cầu tiếp tục và quyền nạp abc-retail/xyz-service đã được
chủ dự án xác nhận. Không fine-tune trọng số, không gọi API trả phí, không deploy.
Không thay đổi tiến độ hoặc cấu trúc sổ 97.

## Nội dung mới

Ba file trong data/knowledge/platform_guides, tổng 12 mục:

- 05_don_hang_va_ton_kho.md: xác nhận khác thu tiền/giao hàng; hủy khác hoàn
  tiền; snapshot giá; danh mục khác tồn chi nhánh. Source: retail/services.py.
- 06_nhap_du_lieu_va_mapping.md: staging khác canonical; chuẩn bị upload;
  AI mapping cần preview/validation/quyền apply; thông tin chẩn đoán đã bỏ PII.
  Source: integration/services.py và mapping/services.py.
- 07_tiep_nhan_dich_vu_va_chan_doan.md: request khác hoàn thành; SLA UNKNOWN;
  dữ liệu chứng minh nguyên nhân; bảo vệ bí mật khi gửi log. Source:
  service_ops/services.py, knowledge/tools.py và PROJECT_CONTEXT.md.

Web thêm ba nhóm hướng dẫn: sửa/hủy đơn, báo sự cố/log an toàn, chọn laptop
theo nhu cầu. Không thực hiện hủy/hoàn tiền qua chat, không hứa SLA hoặc hiệu
năng model chưa xác minh. Cụm từ cụ thể ưu tiên trước FAQ giỏ hàng chung.
Thêm 24 biến thể câu hỏi có dấu/không dấu/viết hoa trong test public; test
ingestion mở rộng ba tài liệu và test orchestration kiểm không tạo approval
khi hỏi thông tin vận hành.

## Nạp và kiểm dữ liệu local

Bind rõ DB_* loopback tới ai_business_platform_db, không dùng DATABASE_URL
remote. Chỉ dùng operator admin hiện có sau kiểm tra internal role và permission.
Local LLM_API_KEY trống; embedding hash-projection, FileSystemStorage.

Đợt này thêm document 43–45 abc-retail và 46–48 xyz-service. Cuối đợt:
6 document mới/34 chunk. Cộng guide đợt trước: 14 document/78 chunk, 30 mục
hướng dẫn nội bộ; web có 9 nhóm FAQ. Không tính số chunk là số kiến thức độc lập.
Metadata giữ SHA-256 source, PLATFORM_GUIDE, public_publication_approved=False.
Đã đối chiếu byte file lưu thực với source hash của đủ 14 document: đều khớp.
Hash content/vector/metadata các chunk ngoài sáu document mới không đổi.

## Vòng sửa theo lỗi quan sát

12 câu heading + 12 paraphrase, mỗi workspace: 48 lượt retrieval read-only.
Lần đầu: exact 12/12, paraphrase đúng mục top1/top5 10/12 ở cả hai workspace.
Hai paraphrase chưa đạt: CONFIRMED có chứng minh đã thu tiền; AI mapping rule
có được apply không cần validation. Bổ sung cách hỏi tương đương có câu trả
lời an toàn vào đúng mục, không thêm cam kết nghiệp vụ.

Lần reindex đầu còn đọc bản file upload trước sửa; chỉ cập nhật metadata không
đủ làm nội dung thay đổi. Đã sửa helper để so byte source với file lưu, ghi bản
file mới cho đúng sáu guide của đợt này và giữ file trước đó, rồi mới ingest.
Không sửa tài liệu cũ hoặc reset DB. Kết quả chạy lại cả bộ:

| Metric regression tự thiết kế | abc-retail | xyz-service |
|---|---:|---:|
| Heading đúng mục top1 | 12/12 | 12/12 |
| Paraphrase đúng mục top1 | 12/12 | 12/12 |
| Paraphrase đúng mục trong top5 | 12/12 | 12/12 |

Các câu đã dùng chỉnh ngữ cảnh không phải holdout mù. Kết quả không chứng minh
mọi paraphrase mới đúng, không đo semantic correctness của câu trả lời Gemini.
Các giới hạn và ca chưa đạt ở đợt 1 chưa được coi là tự động sửa bởi đợt 2.

## Validation

Chạy các label:
tests.test_public_copilot_and_cart_api, tests.test_rag_documents,
tests.test_rag_retrieval, tests.test_rag_grounding_assistant,
tests.test_rag_source_authority, tests.test_rag_security_rbac,
tests.test_ai_intent_router, tests.test_ai_business_intent_benchmark
với .venv-acceptance/Scripts/python.exe manage.py test
--settings=config.settings_evidence_test --noinput --verbosity=1.

Lần trước test orchestration mới: 188 tests/92.477s OK. Test orchestration mới
riêng: 1 test/6.461s OK. Không cộng các lần thành một full-suite run.
check 0 issues; makemigrations --check --dry-run No changes detected trên DB
test mới qua helper output/check_collaboration_gates_20261009.py.
Nhóm cuối trên source sau sửa: **189 tests/104.870s OK**, không failure/error/skip.
Database test riêng được tạo và hủy; không full-suite claim.

## Chưa kiểm chứng

Chưa có ngân sách/provider key cho batch LLM thật; chưa có human review độc lập
cho bộ mới. Web vẫn rule-based; internal local có deterministic fallback.
Chưa push/deploy/nạp production. Không mở truy cập SOP nội bộ cho khách hàng,
không đổi role, schema hoặc nghiệp vụ bán hàng để cải thiện điểm test.
