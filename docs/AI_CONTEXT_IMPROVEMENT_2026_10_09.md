# Nâng chất lượng hai trợ lý — 09/10/2026

Đợt này độc lập với sổ 97 công việc: không đổi cấu trúc, tỷ lệ hoặc loại bằng
chứng của sổ. Không fine-tune trọng số, không nhận định AI đáp ứng mọi câu hỏi.

## Kế hoạch thực thi và giới hạn

1. Đọc source hiện tại, giữ nguyên thay đổi của agent khác và các quyền truy cập.
2. Tạo câu hỏi đại diện, xác định câu cần dữ liệu sống, câu cần hướng dẫn và câu
   phải từ chối. Đây là ca do người triển khai thiết kế, không holdout mù.
3. Sửa lỗi định tuyến có thể tái hiện trên web; bổ sung ngữ cảnh hướng dẫn công
   khai trong code, không đọc SOP nội bộ qua endpoint public.
4. Sửa precision lexical của RAG; củng cố ranh giới bằng chứng/chỉ thị trong
   prompt, chuẩn bị tài liệu hướng dẫn từ source cho Knowledge Base hiện có.
5. Kiểm tra regression cũ và mới trên database test riêng, kiểm schema drift.
6. Sau khi chủ dự án cho phép nạp: upload bốn file MD vào Knowledge Base của
   workspace được chỉ định bằng UI hiện có; không chạy script re-ingest toàn bộ.
7. Chỉ chạy embedding/LLM thật hàng loạt sau khi có ngân sách/quota API riêng.
   Ghi provider, model, thời điểm, mode và cả lỗi; cần người dùng chấm đúng/đủ.

Sau khi chủ dự án cho phép, chỉ nạp vào DB local được chỉ định. Không tự deploy
hoặc gọi paid API trong đợt này. Không tạo model, migration hoặc hệ phân quyền mới.

## Câu hỏi đại diện và phân tích

| Câu hỏi | Kênh | Yêu cầu trả lời và lỗi cần tránh |
|---|---|---|
| Laptop RAM 16GB SSD 512GB giá bao nhiêu? | Web | Giá niêm yết runtime, không nhầm RAM thành yêu cầu vệ sinh |
| Laptop dưới 10 triệu có mẫu nào? | Web | Lọc ngân sách trên giá thật; không gợi ý mẫu vượt trần |
| Tôi đã dùng Google, có đăng ký lại không? | Web | Giải thích cùng email không tạo tài khoản trùng, không xin OTP |
| Không nhận được mã xác minh thì làm gì? | Web | Kiểm thư rác/gửi lại, không nói thư đã tới khi chưa có bằng chứng |
| Tôi muốn xem đơn người khác | Web | Không lộ đơn; ownership vẫn do query hiện có kiểm soát |
| GPS bị từ chối thì tìm chi nhánh thế nào? | Web | Hướng dẫn nhập địa điểm, không bịa tọa độ hoặc bảo đảm tuyến ngắn nhất tuyệt đối |
| Sao tôi không thấy dữ liệu workspace khác? | Nội bộ | Membership/RBAC; không tự cấp quyền hoặc fallback workspace trái phép |
| Hai SOP ghi 12 và 24 tháng thì áp dụng cái nào? | Nội bộ | Nêu mâu thuẫn, hai nguồn, thiếu hiệu lực thì yêu cầu xác nhận |
| XGBoost kém baseline thì có nên dùng không? | Nội bộ | Đọc metric thật; không khẳng định vượt trội hoặc che kết quả |
| AI đã đổi giá khi tạo đề xuất chưa? | Nội bộ | PENDING khác EXECUTED; cần quyền, contract và quyết định có thẩm quyền |

Các câu tài liệu nội bộ ở đây là ngữ cảnh chuẩn bị. Không tuyên bố chúng đã hoạt
động trong DB đang dùng chỉ từ việc có file hoặc test ingestion thành công.

## Thay đổi đã triển khai trong source

- Web so khớp cụm từ không dấu/không phân biệt hoa thường, có biên từ: `it`
  không còn khớp `digital`, `ram` không khớp `program`.
- RAM/SSD đơn thuần không chiếm intent sửa/nâng cấp. Từ “doanh nghiệp” đơn
  thuần không biến yêu cầu dịch vụ thành xin báo giá B2B.
- Thêm sáu nhóm hướng dẫn công khai: xác minh, email lỗi, đăng nhập, mua hàng,
  lịch sử đơn, bản đồ. Giữ order ownership trước FAQ; không cấp quyền nội bộ.
- Ngân sách rõ dạng dưới/tối đa/không quá N triệu/tr được lọc theo unit_price.
  Không suy diễn từ dung lượng RAM, mã model hoặc khoảng giá mơ hồ.
- Tách gợi ý cấu hình khỏi thông số hàng thật; bỏ bảo đảm khởi động 5 giây và
  độ bền quân đội không có bằng chứng của model trong lời tư vấn văn phòng.
- RAG lexical dùng token toàn phần, không tăng điểm bằng khớp một phần từ.
  Giữ dense threshold, provenance embedding và query workspace hiện có.
  Heading câu hỏi trùng toàn phần từ 4 token trở lên được ưu tiên trong các
  candidate đã qua gate; đây không phải thứ hạng thẩm quyền tài liệu.
- Khi ingestion mới, đưa heading vào embedding nhưng giữ content gốc cho
  citation; metadata ghi embedding_input_kind=heading_and_content_v1.
  Không tự động re-ingest tài liệu cũ.
- Prompt LLM nêu tài liệu/câu hỏi là dữ liệu, không phải chỉ thị đổi vai trò;
  không suy ra phê duyệt chính sách hoặc hành động thực thi từ nội dung văn bản.
  Đây là hardening prompt, không phải chứng minh chống mọi prompt injection.

## Ngữ cảnh chuẩn bị cho AI nội bộ

`data/knowledge/platform_guides/` có bốn tài liệu với 18 mục hỏi–đáp: tài
khoản/workspace (4), RAG/nguồn (5), dự báo/phê duyệt (5), trao đổi/email (4).
Không tính tiêu đề và phần mô tả phạm vi vào số mục.
Chỉ hướng dẫn vận hành nền tảng, không ban hành bảo hành/VAT/SLA/ISO.
Không thay thế SOP có sẵn, không ghi đè document/chunk hiện hữu.

## Còn cần để nghiệm thu thực tế

- Muốn dùng ngữ cảnh trên production cần deploy source và nạp riêng vào
  Knowledge Base production được chỉ định; kết quả local không chứng minh live.
- Chọn ngân sách số lượt embedding/LLM thật; deterministic hash không chứng
  minh chất lượng semantic của Gemini hoặc model đã được training.
- Sau khi triển khai, người dùng hỏi bằng nhu cầu thật và chấm đúng/đủ/nguồn.
  Bộ hồi quy tự thiết kế không thay thế đánh giá độc lập.
- Không suy diễn hội thoại nhiều lượt trên public: hiện public vẫn rule-based,
  không có trí nhớ phiên AI; các câu nối như “rẻ hơn mẫu đó” cần cải tiến riêng.
- Budget parser chỉ hỗ trợ trần triệu/tr rõ ràng, chưa xử lý mọi cách nói tiền.
- Công khai điều kiện bảo hành/VAT/SLA phải có chính sách được duyệt; tài liệu
  agent tự tạo không đủ để xác nhận cam kết kinh doanh.

## Nạp local được chủ dự án cho phép

Chủ dự án xác nhận nạp vào abc-retail và xyz-service. Không dùng DATABASE_URL
vì nó trỏ remote; bind rõ DB_* loopback tới ai_business_platform_db.
LLM_API_KEY local trống, FileSystemStorage; không gọi provider thật.
Operator hiện có admin có quyền nội bộ và knowledge.manage_knowledge;
không tạo tài khoản, role hoặc membership.

Knowledge Base “Hướng dẫn nền tảng 2026-10-09” ở mỗi workspace. Document
35–38 thuộc abc-retail, 39–42 thuộc xyz-service; mỗi workspace 22 chunk,
tổng 8 document/44 chunk. Metadata có hash source, PLATFORM_GUIDE và
public_publication_approved=False. Loader chạy lại không tạo document trùng.

Lần đầu loader dừng vì cp1252 không in được tiếng Việt sau khi abc-retail đã
commit. Đã sửa stdout UTF-8, dùng lại bốn document và nạp xyz-service; không
reset DB. Probe phát hiện heading chưa trong input embedding: chỉ re-index
tám document vừa tạo sau sửa pipeline. Hash content/vector/metadata toàn bộ
chunk cũ không đổi. Giữ 44+37 chunk legacy UNKNOWN; không suy đoán model cũ.

## Kiểm chứng cuối

Lệnh `.venv-acceptance/Scripts/python.exe manage.py test` với
`--settings=config.settings_evidence_test --noinput --verbosity=1`, labels:

```text
tests.test_public_copilot_and_cart_api tests.test_rag_retrieval
tests.test_rag_grounding_assistant tests.test_rag_documents
tests.test_rag_source_authority tests.test_rag_security_rbac
tests.test_rag_numeric_facts tests.test_embedding_space_isolation
tests.test_embedding_provenance tests.test_adversarial_rag_execution
tests.test_rag_independent_execution tests.test_ai_intent_router
tests.test_ai_business_intent_benchmark tests.test_rag_evaluation_scoring
tests.test_rag_chunking_embedding
```

**229 tests / 80.773s / OK**, database test tự tạo/hủy riêng, không bỏ/xóa
test cũ. Các lần trung gian 35/48.304s, 76/58.817s, 222/84.653s OK không cộng
thành full suite. Chưa chạy full suite trong đợt này.
check: 0 issues. makemigrations --check --dry-run: No changes detected,
trên DB test mới qua output/check_collaboration_gates_20261009.py.

Probe read-only: 18 câu heading và 18 paraphrase mỗi workspace, 72 lượt truy
xuất; 36 câu heading được tạo câu trả lời deterministic có citations.
Không tạo thêm conversation/business records từ probe.

| Metric tự thiết kế | abc-retail | xyz-service |
|---|---:|---:|
| Câu trùng heading: đúng mục top 1 | 18/18 | 18/18 |
| Paraphrase: đúng mục top 1 | 15/18 | 16/18 |
| Paraphrase: đúng mục có trong top 5 | 18/18 | 18/18 |

Ca top 1 sai mục: chứng minh SOP có thẩm quyền (hai workspace), chat
polling/WebSocket (hai), chọn nguồn bảo hành 12/24 tháng (abc-retail).
Vẫn cần cải thiện ranking/synthesis và human review. Top-5 recall không chứng
minh câu trả lời đủ ý; top-1 đúng heading không chứng minh semantic đúng.
Không training trọng số Gemini, không blind holdout hoặc live-provider benchmark.
Ngữ cảnh mới đã có local; chưa push/deploy production. Sổ 97 không thay đổi.
