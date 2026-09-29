# Bandit — phân loại và xử lý lỗi AI

Baseline 68 finding: output/bandit_provider_admin_final_20260925.json.
Danh sách từng vị trí/rule/căn cứ: BANDIT_FINDING_TRIAGE_2026_09_25.md (68 dòng,
gắn SHA256 bản gốc; số dòng là baseline). Không có giá trị credential trong bảng.

## Phân loại

- B104: denylist SSRF, không là lệnh bind; giữ cảnh báo, không suppression.
- B105: tách credential demo công khai có guard khỏi rubric/thông báo/URL
  không phải credential. Helper seed đặc quyền không được dùng ở DB nghiệp vụ.
- B311: dữ liệu random của demo và ID hiển thị, không dùng cho token xác thực.
  ID random vẫn có khả năng va chạm; không coi đây là bảo đảm unique.
- B404/B603: worker dùng argv list với executable/manage.py và PK/UUID;
  phụ thuộc runtime đáng tin, không có shell. Chưa chứng nhận recovery production.
- B110: sửa nhóm mutation/provider; giữ mở các nhóm storage cleanup, vector
  parsing, lookup tùy chọn, telemetry và reset-email còn cần kiểm tra riêng.

## Sửa mã

Sáu nhánh mutation truyền failure đến handler hiện có thay vì bỏ qua. Handler
ghi phản hồi thất bại với mã PERMISSION_DENIED hoặc MUTATION_FAILED; không trả
raw exception hoặc ghi nó vào assistant ChatMessage. Không sinh approval giả
và không tiếp tục retrieval sau khi thao tác đã thất bại.

Ba fallback provider giữ nguyên None/fallback nhưng thêm log mã cố định.
Không dùng exception text, prompt, API key hay exc_info trong các log mới.
Không thay threshold Bandit, không nosec, không xóa/skip test.

## Kiểm chứng

```powershell
python manage.py test tests.test_ai_error_boundary tests.test_generation_provenance tests.test_embedding_provenance --settings=config.settings_evidence_test --noinput -v 1
```

16 tests OK, 0.111s. Test mới kiểm propagation của nhánh chỉnh giá, không
retrieval khi mutation thất bại, phân loại denial, redaction và log fallback.
Không suy ra mọi nhánh nghiệp vụ đã được chạy từ các unit test này.

Scan mới: output/bandit_error_boundary_20260925.json — **59 findings (58 LOW,
1 MEDIUM)**, exit 1. Giảm 9 B110 nhờ thay đổi xử lý lỗi, không nhờ bỏ rule.
Đây không phải trạng thái GitHub CI; nguyên nhân hai nhóm CI test fail vẫn chưa
có traceback để kết luận. Giữ nguyên 84/97 và các cổng external chưa kiểm chứng.

Follow-up 26/09 tiếp tục xử lý các B110 còn lại bằng log mã cố định, thu hẹp
exception phù hợp và giữ nguyên semantics cleanup/fallback. Hai mã hiển thị công
khai không dùng cho xác thực chuyển sang UUID-derived. Scan
`output/bandit_observability_20260926.json`: **46 findings (45 LOW, 1 MEDIUM)**,
exit 1. Bảng credential demo trên internal login đồng thời được ẩn mặc định và
chỉ hiện khi DEBUG cộng opt-in rõ ràng; việc này không làm giảm số Bandit vì
chuỗi fixture vẫn tồn tại trong source và vẫn được scanner nhìn thấy.

Finding MEDIUM B104 cuối cùng là literal `0.0.0.0` trong denylist, trong khi
mọi raw IP đã đi qua `ipaddress` và bị chặn bởi thuộc tính loopback/private/
link-local/reserved/unspecified cùng kiểm tra CGNAT. Các raw-IP literals trùng
lặp được bỏ khỏi tập hostname; hostname metadata vẫn giữ nguyên. Đây là hợp nhất
chính sách SSRF, không `nosec`; test SSRF hiện hữu cho `0.0.0.0`, loopback,
metadata và CGNAT phải pass trước khi chốt scan cuối.

Kết quả: SSRF **8 tests OK (17.983s)**. Scan cuối
`output/bandit_final_20260926.json`: **45 LOW, 0 MEDIUM, 0 HIGH**, exit 1.
45 LOW gồm 31 random cho dữ liệu demo tổng hợp, 4 credential fixture của seed
có guard, 8 chuỗi rubric/error-code bị nhận nhầm và 2 finding subprocess worker
dùng argv cố định. Chúng vẫn được scanner hiển thị; chưa phải CI xanh.

Hồi quy cuối của đợt follow-up: auth/readiness **27 tests OK (92.850s)**;
AI error boundary + approval state + approval + recommendation **26 tests OK
(86.312s)**. Đây là các lượt độc lập, không cộng với 179 test trước đó để tạo
một tổng test duy nhất.

Lượt hồi quy rộng hơn dùng test DB ngẫu nhiên riêng, không reset DB nghiệp vụ:

```powershell
python manage.py test tests.test_rag_grounding_assistant tests.test_phase10_demonstration_scenarios tests.test_ai_error_boundary tests.test_generation_provenance tests.test_embedding_provenance tests.test_academic_test_manifest_audit --settings=config.settings_evidence_test --noinput -v 1
```

Log: output/bandit_error_boundary_tests_20260925.log. Không cộng số lượt test
lặp với lượt 16 để tính tiến độ. Không push/deploy hay sửa tài khoản hiện hữu.
