# Chốt 97 công việc trong phạm vi đồ án ngày 09 tháng 10 năm 2026

Đã xử lý đủ 97/97 mục theo phạm vi đồ án và các quyết định điều chỉnh của chủ
dự án. “Hoàn thành” ở đây là hoàn thành công việc/tiêu chí được chốt và công bố
giới hạn bằng chứng ở từng dòng. Không có kết luận mọi chức năng an toàn tuyệt
đối, AI đúng mọi câu, coverage 100% hoặc production được chứng nhận toàn diện.

Sổ CHECKLIST_97_PROGRESS.md được giữ nguyên SHA-256
`1d532616a6e9c9b780aa47c6ea680793ecbcc7c9f58ee3989d5fae5f0daeec20` theo AGENTS Rule 12. Bảng này là biên bản
hiện hành bổ sung, không đổi ID, nội dung gốc hoặc cấu trúc sổ lịch sử.

## Công việc đã hoàn tất trong đợt cuối

Rà lại phạm vi và bằng chứng của đủ 97 ID; sửa mô tả vượt source trong bản nháp,
thêm nghiên cứu tiếng Việt UIT-ViQuAD và nguồn bối cảnh OECD, thống nhất citation
IEEE theo lần xuất hiện ở chương 1–2, bỏ bibliography không được sử dụng ở
chương 3–5. Sửa manifest nghiệm thu thiếu tên hai test mới. Cập nhật ma trận
truy vết và trạng thái hiện hành, đóng gói bản tổng kết Word riêng.

Full suite lần đầu: 1207 tests / 340.008s, FAILED 1 (manifest thiếu
test_academic_diagram_contract.py và test_team_chat_display_time.py). Giữ log
output/policy_release_ew_h2a4e/tests.log. Sau bổ sung danh mục, full suite chạy
**1207 tests / 335.450s, OK,
0 failure/error/skip**, tree `0c1324e6258e5a87bb3f3c388183240c35c42bbc`; log
output/policy_release_282b_uwu/tests.log. Test database local mới được tạo và
hủy trong từng run, không reset database nghiệp vụ. Fast password hasher chỉ
áp dụng trong process test; provider/email offline theo evidence settings.

Runtime apps/config/tests cùng release 0c618c7. CI37286413162 của release đó
completed/success và Render dep-db1mb8vavr4c73ckipfg live đúng SHA khi kiểm lại
09/10. Tài liệu bổ sung có kiểm tra riêng; không tự gán bằng chứng production
cho nội dung chưa deploy hoặc nhận local test là inbox/provider live.

Guard tài liệu hiện hành: 13 tests / 6.997s OK; check 0 issues; makemigrations
--check --dry-run: No changes detected trên DB test mới. 12 guard của ba file
test untracked cũng OK / 0.153s, ghi riêng, không có trong snapshot full 1207.
Audit 35 UC: không missing file hoặc unobserved test file. Runtime diff Git
giữa snapshot/full, HEAD và worktree bằng 0; khác CRLF/LF được chuẩn hóa khi
đối chiếu bytes. Không sửa schema hoặc dữ liệu nghiệp vụ.

Lần migration gate đầu dùng utility DB postgres báo InconsistentMigrationHistory;
log giữ nguyên. Gate chạy lại trên DB test mới đạt và chỉ hủy DB test do run
tạo. Đây không phải thao tác chữa/reset DB utility hoặc DB đang chạy.

## Quyết định phạm vi được tính đã hoàn tất

- RAG: nghiệm thu 5 IND đã được người dùng chấm, đã dùng sửa router; không yêu cầu holdout mù.
- Worker: nghiệm thu lifecycle local, async production tắt trên Render Free.
- Storage: nghiệm thu Local Storage; không có bucket R2 thật, không yêu cầu S3 production.
- Backup: diễn tập DB độc lập đã đạt; bản mã hóa ở ổ D, offsite hoãn theo chủ dự án.
- Policy: học thuật/demo, không tuyên bố ISO hoặc điều kiện thương mại doanh nghiệp chưa ký duyệt.
- Reorder/workload: advisory, không triển khai action thiếu transaction/rollback.
- CSP: baseline hiện có; strict nonce và bỏ toàn bộ inline/eval không nằm trong nghiệm thu này.
- Tài liệu: nghiệm thu đề cương được duyệt và bản nháp hiện có; báo cáo/slide nộp mới cần sinh viên hoàn thiện và thầy duyệt sau.

## Cách đọc bằng chứng

D: tài liệu/source; T: test local có log; P: quan sát deployment/CI thật;
H: xác nhận người dùng; C: phạm vi được chủ dự án điều chỉnh. Các loại có thể
cùng áp dụng. Với H, không tự bổ sung Message ID, Sentry Event ID hoặc kết quả
quan sát độc lập. Số mẫu và kịch bản hữu hạn không suy rộng thành mọi trường hợp.

Nguồn viết tắt và các đường dẫn gốc của từng mục được giữ tại
CLOSURE_97_EVIDENCE_2026_10_05.md; đọc cùng ACADEMIC_SOURCE_REVIEW_2026_10_09.md,
ACADEMIC_REQUIREMENTS_MATRIX.md và COLLABORATION_UAT_2026_10_05.md.

## Đối chiếu đủ 97 mục

| ID | Nội dung gốc | Kết luận trong phạm vi | Bằng chứng và ranh giới |
|---|---|---|---|
| 1 | **Thống nhất tên đề tài.** Một số tài liệu cũ vẫn dùng tên dài khác với tên bạn xác nhận: “Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI”. | Hoàn thành trong phạm vi bằng chứng (D) | Tên đề tài — S/W; tên chuẩn trong bản duyệt, tên cũ ở nhật ký không là tên bản nộp. |
| 2 | **Chốt danh sách chức năng bắt buộc và mở rộng.** Không biến mọi gợi ý trước đây thành yêu cầu phải hoàn thành. | Hoàn thành theo phạm vi đã chốt (D/T/P/C) | Bắt buộc/mở rộng — S/B; docs/COLLABORATION_UAT_2026_10_05.md; Chat/bản tin đã triển khai và UAT MANAGER/EMPLOYEE theo thứ tự; polling hai tab cùng phiên. Phạm vi bắt buộc/mở rộng đã chốt. |
| 3 | **Xác nhận phạm vi phụ lục lộ trình mở rộng.** Đề cương còn phụ lục trong khi thầy có góp ý “không triển khai thì bỏ”; cần xác định giữ như hướng phát triển hay bỏ khỏi bản nộp. | Hoàn thành trong phạm vi bằng chứng (H/D) | Phụ lục — W; chủ dự án xác nhận bản duyệt giữ hướng tương lai. |
| 4 | **Không gọi hệ thống là ERP/WMS hoàn chỉnh.** Tồn kho, nhập hàng là nghiệp vụ hỗ trợ; chưa tương đương quản lý kho chuyên sâu. | Hoàn thành trong phạm vi bằng chứng (D) | ERP/WMS — S/Q; không chứng nhận ERP/WMS đầy đủ. |
| 5 | **Không trình bày ví dụ của thầy thành công nghệ bắt buộc.** LSTM, GRU, Transformer và bài toán LST trong hình chỉ minh họa cách lập luận. | Hoàn thành trong phạm vi bằng chứng (D) | Ví dụ LST/deep learning — S; không tự bổ sung model theo hình minh họa. |
| 6 | **Phân biệt lịch phát triển với hạn nộp và bảo vệ.** Lịch hai tuần cuối theo thầy cần đối chiếu lại mốc hành chính của khoa. | Hoàn thành trong phạm vi bằng chứng (D) | Lịch khoa — docs/ACCEPTANCE_REAUDIT_2026_09_23.md; hạn hành chính tách lịch phát triển, chưa chứng nhận đã nộp. |
| 7 | **Bỏ kết luận “hoàn thành 100%” chưa có tiêu chí nghiệm thu.** Báo cáo cũ đang đưa ra kết luận này cho nhiều nhóm chức năng. | Hoàn thành theo phạm vi đã chốt (D/C) | Tuyên bố 100% — Q/L; Chốt 97/97 công việc trong phạm vi điều chỉnh bằng bảng này; không khôi phục claims 100% chất lượng AI/an toàn/production. |
| 8 | **Bỏ tỷ trọng 15% website công khai và 85% nội bộ nếu không có phép đo.** | Hoàn thành trong phạm vi bằng chứng (D) | Tỷ trọng 15/85 — S; không có phép đo tỷ trọng. |
| 9 | **Sửa thuật ngữ “air-gap”.** Hệ thống sử dụng cách ly logic bằng workspace và quyền, không phải cách ly vật lý. | Hoàn thành trong phạm vi bằng chứng (D) | Air-gap — S; chỉ cách ly logic/RBAC. |
| 10 | **Sửa mô tả “mọi bảng đều có workspace và mọi truy vấn tự động được lọc”.** Một số bảng con kế thừa phạm vi qua đối tượng cha; việc lọc còn phụ thuộc đường thực thi. | Hoàn thành trong phạm vi bằng chứng (D/T) | Workspace bảng con — docs/PROJECT_CONTEXT.md; phạm vi kế thừa qua cha, không tự động lọc mọi query. |
| 11 | **Không dùng “an toàn tuyệt đối”, “không ảo giác”, “không rò rỉ 100%”.** Chỉ báo cáo kết quả trên các ca đã kiểm thử. | Hoàn thành trong phạm vi bằng chứng (D/T) | Tuyệt đối/không ảo giác — Q; guard nội dung không chứng minh an toàn tuyệt đối. |
| 12 | **Phân biệt nạp SOP, viết handler và huấn luyện mô hình.** Những việc này không đồng nghĩa huấn luyện lại Gemini. | Hoàn thành trong phạm vi bằng chứng (D) | Ingestion/handler/training — docs/AI_METHOD_BOUNDARIES.md; không fine-tune Gemini. |
| 13 | **Đồng bộ tài liệu trạng thái.** Có mục lịch sử đã lỗi thời hoặc mâu thuẫn với cập nhật mới. | Hoàn thành trong phạm vi bằng chứng (D/T) | Đồng bộ trạng thái — L/phụ lục này; Báo cáo 09/10 và CURRENT_STATUS là trạng thái hiện hành; giữ nhật ký và log cũ, nhận diện từng source/test tree. |
| 14 | **Không cộng các nhóm test chồng lặp.** Các con số test ở nhiều thời điểm không tạo thành tổng số test độc lập hay tỷ lệ toàn hệ thống. | Hoàn thành trong phạm vi bằng chứng (T) | Không cộng test trùng — L; dùng một log full riêng và các focused run riêng. |
| 15 | **Sửa nhận xét trái với bảng kết quả.** Báo cáo ghi doanh thu và số ticket kém baseline nhưng phần nhận xét lại nói mô hình vượt trội. | Hoàn thành trong phạm vi bằng chứng (T/D) | Nhận xét metric — F/X; XGBoost kém lag7 về MAE/RMSE vẫn được ghi nhận. |
| 16 | **Sửa diễn giải R² âm.** Không thể dùng kết quả này để nói mô hình giải thích được phần lớn phương sai. | Hoàn thành trong phạm vi bằng chứng (T/D) | R² âm — F; không diễn giải là giải thích phần lớn phương sai. |
| 17 | **Giữ kết quả kém và phân tích nguyên nhân.** Không bỏ bài toán thất bại để chỉ trình bày số đơn tốt hơn. | Hoàn thành trong phạm vi bằng chứng (D) | Giữ kết quả kém — F/X; kết quả cũ và recursive mới đều không bị xóa. |
| 18 | **Phân biệt đánh giá một bước với dự báo nhiều ngày.** Backtesting hiện mô tả `one-step observed-history`, chưa chứng minh chất lượng dự báo đệ quy 14 ngày. | Hoàn thành trong phạm vi bằng chứng (T) | One-step/recursive — F; 14 ngày một origin synthetic, không suy rộng nhiều origin. |
| 19 | **Chọn chính xác run để xuất báo cáo.** Script hiện gộp theo target, chưa phân biệt đầy đủ workspace, cấu hình và chiều dự báo. | Hoàn thành trong phạm vi bằng chứng (T) | Chọn run/workspace — tests/test_academic_report_command.py; selection tường minh, không gộp mọi run theo target. |
| 20 | **Không thay metric thiếu bằng 0.** Phải báo thiếu dữ liệu hoặc không đánh giá được. | Hoàn thành trong phạm vi bằng chứng (T) | Metric thiếu — F; tests/test_academic_reporting.py; unmeasured/null, RMSE zero khác RMSE thiếu. |
| 21 | **Giữ đủ số lẻ trong bảng.** Làm tròn MAE thành “1 so với 1” che mất khác biệt nhưng vẫn hiển thị phần trăm cải thiện. | Hoàn thành trong phạm vi bằng chứng (T) | Độ chính xác hiển thị — tests/test_academic_reporting.py; xem renderer, không làm tròn để che chênh lệch. |
| 22 | **Ghi rõ dữ liệu train/validation/test.** Cần khoảng ngày, số mẫu, target, đơn vị và cách xử lý ngày thiếu. | Hoàn thành trong phạm vi bằng chứng (T/D) | Train/calibration/test — F/X; snapshot mới có split, run lịch sử thiếu không hồi điền. |
| 23 | **Ghi rõ tham số, phiên bản và dữ liệu của mỗi lần chạy.** | Hoàn thành trong phạm vi bằng chứng (T) | Tham số/phiên bản — F/X; provenance và manifest, không là backup dữ liệu sản xuất. |
| 24 | **Kiểm tra baseline có cùng điều kiện thông tin và horizon với mô hình.** | Hoàn thành trong phạm vi bằng chứng (T) | Baseline cùng horizon — F; recursive baseline tự roll-forward, không đọc actual tương lai. |
| 25 | **Giải thích giới hạn MAPE ở dữ liệu gần 0.** | Hoàn thành trong phạm vi bằng chứng (T/D) | MAPE gần zero — tests/test_forecasting_training.py; điều kiện mẫu số phải đi cùng số liệu. |
| 26 | **Không coi dải dự báo hiển thị là khoảng tin cậy đã được hiệu chỉnh nếu chưa đo độ bao phủ.** | Hoàn thành trong phạm vi bằng chứng (T) | Dải tham khảo — F; không calibrated; coverage one-step không dùng cho recursive. |
| 27 | **Không suy rộng kết quả seed thành hiệu quả kinh doanh thực tế.** | Hoàn thành trong phạm vi bằng chứng (D) | Seed/hiệu quả thật — F/S; synthetic không chứng minh hiệu quả thương mại. |
| 28 | **Chốt ít nhất một bài toán dự báo để đánh giá sâu**, thay vì mở thêm nhiều target nhưng không đủ thực nghiệm. | Hoàn thành theo phạm vi đã chốt (D/C) | Bài toán chính — F; doanh thu ngày, chưa nghiên cứu đa origin/dữ liệu doanh nghiệp thật. |
| 29 | **Sửa cách chấm đúng bằng một keyword.** | Hoàn thành trong phạm vi bằng chứng (T) | Keyword không là semantic — R; required groups/numeric chỉ proxy. |
| 30 | **Sửa cách đo retrieval.** | Hoàn thành trong phạm vi bằng chứng (T) | Chunk retrieval — R; tests/test_rag_chunk_metrics.py; gold IDs khác nguồn do chính answer trả về. |
| 31 | **Sửa tiêu chí câu hỏi hybrid.** Không nên đạt khi chỉ có tài liệu **hoặc** tool nếu câu hỏi cần cả hai. | Hoàn thành trong phạm vi bằng chứng (T/H) | Hybrid cả hai nguồn — tests/test_rag_evaluation_scoring.py; user đã chấm IND-HYB ngày05/10 trên output offline thật; không đánh giá mọi câu hybrid. |
| 32 | **Xuất chỉ số citation đầy đủ.** Có kiểm tra tên tài liệu nhưng chưa tổng hợp thành thước đo đủ rõ. | Hoàn thành trong phạm vi bằng chứng (T) | Citation rate — R; source presence không tự chứng minh entailment. |
| 33 | **Sửa tên hoặc công thức `fallback_precision`.** Công thức hiện chưa đo precision trên toàn bộ câu bị từ chối. | Hoàn thành trong phạm vi bằng chứng (T) | Fallback precision — R; TP/(TP+FP), không dùng recall thay precision. |
| 34 | **Đo cả từ chối nhầm.** Không chỉ kiểm tra câu ngoài phạm vi có bị từ chối. | Hoàn thành trong phạm vi bằng chứng (T) | Từ chối nhầm — R; false positive có mẫu số riêng. |
| 35 | **Tách kết quả API thật và fallback.** | Hoàn thành trong phạm vi bằng chứng (T) | API/fallback — tests/test_generation_provenance.py; simulated provider không gọi live API. |
| 36 | **Ghi nhận model/embedding thực sự được sử dụng.** | Hoàn thành trong phạm vi bằng chứng (T) | Embedding thực dùng — tests/test_embedding_provenance.py; legacy UNKNOWN giữ UNKNOWN. |
| 37 | **Chuẩn bị bộ câu hỏi độc lập với quá trình sửa router/prompt.** | Hoàn thành theo phạm vi đã chốt (H/C) | Bộ độc lập — apps/knowledge/independent_benchmark.py; Chủ dự án nghiệm thu 5 IND đã chấm; đã dùng sửa router, không phải holdout mù. Hoàn thành theo phạm vi được chọn. |
| 38 | **Lưu câu trả lời đầy đủ, nguồn, tool, thời gian và lỗi của từng ca.** | Hoàn thành trong phạm vi bằng chứng (T) | Output/time/error — tests/test_rag_evaluation_runner.py; mới bổ sung IND execution, không chỉ mock runner. |
| 39 | **Đánh giá đủ ý và đúng số liệu.** | Hoàn thành trong phạm vi bằng chứng (H/T) | Đúng/đủ/số liệu — docs/RAG_REVIEW_FORM_2026_09_30.md; docs/RAG_INDEPENDENT_EXECUTION_2026_10_05.md; 5 IND được người dùng chấm ĐẠT theo output lưu; giữ nhãn offline, không suy ra accuracy live Gemini. |
| 40 | **Bổ sung ca hỏi khác cách diễn đạt, không đủ dữ liệu, mâu thuẫn tài liệu và sai quyền.** | Hoàn thành trong phạm vi bằng chứng (T/H) | Đối kháng — tests/test_adversarial_rag_execution.py; bốn answer/two denials, không quality tổng quát. |
| 41 | **Kiểm tra việc trả lời theo đúng workspace và vai trò**, không chỉ chạy benchmark bằng superuser. | Hoàn thành trong phạm vi bằng chứng (T) | Workspace/role RAG — tests/test_rag_security_rbac.py; actor không superuser ở bộ IND mới. |
| 42 | **Không gọi test intent/router là đánh giá năng lực LLM.** | Hoàn thành trong phạm vi bằng chứng (D/T) | Router không là LLM — R/S; mode phải đi cùng kết quả. |
| 43 | **Rà soát các cam kết thương mại soạn sẵn:** bồi hoàn 200%, trả góp 0%, đối tác ngân hàng, e-VAT, giao hàng và bảo hành. | Hoàn thành trong phạm vi bằng chứng (T/P) | Cam kết thương mại — Q; không công bố cam kết từ SOP demo. |
| 44 | **Rà soát tuyên bố ISO 27001 và mã hóa dữ liệu cá nhân.** Chưa có bằng chứng tương ứng trong phần đã kiểm tra. | Hoàn thành theo phạm vi đã chốt (D/T/C) | ISO/mã hóa — Q/S; Bỏ claims ISO/mã hóa tuyệt đối; không cần chứng chỉ doanh nghiệp thật trong phạm vi học thuật. |
| 45 | **Phân biệt chính sách doanh nghiệp thật với dữ liệu demo.** | Hoàn thành theo phạm vi đã chốt (D/T/C) | Chính sách/demo — Q; Chính sách là hồ sơ kịch bản học thuật, chưa có doanh nghiệp ký duyệt; nội dung công khai yêu cầu xác nhận điều kiện. |
| 46 | **Thống nhất chính sách giữa chatbot, SOP, trang web và email.** Cần kiểm tra các mốc đổi trả, bảo hành, SLA có mâu thuẫn không. | Hoàn thành theo phạm vi đã chốt (T/P/C) | Đồng nhất các kênh — Q/L; đóng bằng ranh giới không công bố điều kiện chưa duyệt. |
| 47 | **Giảm tài liệu ngoài trọng tâm.** Nhân sự, lương thưởng, pháp lý và datacenter chuyên sâu không nên làm loãng hai nghiệp vụ chính. | Hoàn thành theo phạm vi đã chốt (D/C) | Trọng tâm — S; nhân sự/pháp lý chuyên sâu ngoài phạm vi. |
| 48 | **Không trình bày nội dung tư vấn như một chức năng đã triển khai.** Chatbot nói “có trả góp” không chứng minh hệ thống có xử lý trả góp. | Hoàn thành trong phạm vi bằng chứng (D) | Tư vấn/triển khai — Q; trả góp không được coi đã triển khai chỉ từ lời chatbot. |
| 49 | **Gắn nhãn rõ kết quả mô phỏng/giả định.** Không dùng what-if như sự kiện quan sát được. | Hoàn thành trong phạm vi bằng chứng (T) | What-if/giả định — tests/test_simulation_evidence.py; cần nhãn giả định, không là quan sát thật. |
| 50 | **Có nguồn tham chiếu độc lập cho kiểm tra khoảng cách.** Hai giá trị chuẩn trong script chưa có nguồn giải thích. | Hoàn thành trong phạm vi bằng chứng (D/T) | Nguồn khoảng cách — G; kiểm selected reference cases. |
| 51 | **Không dùng hai cặp Haversine để kết luận PostGIS đúng 100%.** | Hoàn thành trong phạm vi bằng chứng (D) | PostGIS không 100% — G; kiểm reference không chứng nhận mọi operation. |
| 52 | **Kiểm thử điểm trong, ngoài và đúng biên bán kính.** | Hoàn thành trong phạm vi bằng chứng (T) | Biên radius — tests/test_gis_reference_distances.py; phân biệt spheroid nội bộ/Haversine public. |
| 53 | **Kiểm thử tọa độ thiếu, tọa độ không hợp lệ và dữ liệu khác workspace.** | Hoàn thành trong phạm vi bằng chứng (T) | Invalid/foreign coordinates — tests/test_gis_security.py; không cho client chọn workspace ngoài quyền. |
| 54 | **Phân biệt khoảng cách đường chim bay với quãng đường giao thông.** | Hoàn thành trong phạm vi bằng chứng (D/T) | Chim bay/đường bộ — G; hai loại khoảng cách khác nhau. |
| 55 | **Không tuyên bố tuyến ngắn nhất tuyệt đối hoặc có giao thông trực tiếp.** | Hoàn thành trong phạm vi bằng chứng (D) | Không shortest tuyệt đối — G/S; lựa chọn trong tuyến provider, không live traffic. |
| 56 | **Xác nhận tìm địa chỉ Nominatim hoạt động thật.** | Hoàn thành trong phạm vi bằng chứng (P ngày 26/09) | Nominatim — G; không uptime SLA. |
| 57 | **Xác nhận GPS trên thiết bị thật**, bao gồm từ chối quyền, sai số lớn và không lấy được vị trí. | Hoàn thành trong phạm vi bằng chứng (H) | GPS thiết bị — L; user xác nhận deny/unavailable/low accuracy. |
| 58 | **Ghi rõ giới hạn provider công cộng** và cách giao diện xử lý timeout. | Hoàn thành trong phạm vi bằng chứng (T/D) | Provider timeout — tests/test_public_branch_finder.py; best-effort, rate/cache theo contract. |
| 59 | **Bỏ các kết luận tuân thủ được gán sẵn trong script đánh giá.** | Hoàn thành trong phạm vi bằng chứng (T) | Approval không gán điểm — A; tests/test_academic_reporting.py; không suy compliance từ count. |
| 60 | **Không dùng số lượng approval để chứng minh quy trình hoạt động đúng.** | Hoàn thành trong phạm vi bằng chứng (D) | Count không là workflow — A; kiểm tác động thực cần chuỗi execution. |
| 61 | **Chạy trọn chuỗi:** đề xuất → duyệt → thực thi → thay đổi dữ liệu → audit. | Hoàn thành trong phạm vi bằng chứng (T) | Proposal→audit — tests/test_approvals.py; action hỗ trợ, không mọi tư vấn. |
| 62 | **Kiểm thử từ chối, tự duyệt, sai quyền và tham số sai.** | Hoàn thành trong phạm vi bằng chứng (T/D) | Reject/self/role/params — tests/test_approvals.py; Reject/role/params/reviewer self-approval có test; công bố ngoại lệ superuser thực sự tồn tại trong executor. |
| 63 | **Kiểm thử thao tác lặp và đồng thời**, xác nhận không thực thi hai lần. | Hoàn thành trong phạm vi bằng chứng (T) | Replay/concurrency — tests/test_approval_concurrency_evidence.py; DB unique/locks, không exactly-once mọi ngoại dịch vụ. |
| 64 | **Kiểm thử lỗi thực thi và hành vi rollback/bù trừ ở hành động có hỗ trợ.** | Hoàn thành trong phạm vi bằng chứng (T) | Rollback/compensation — tests/test_approval_state_integrity.py; giới hạn hành động hỗ trợ. |
| 65 | **Phân biệt khuyến nghị tư vấn với khuyến nghị thực thi được.** | Hoàn thành trong phạm vi bằng chứng (D/T) | Advisory/action — apps/approvals/registry.py; chỉ action contract đã đăng ký. |
| 66 | **Không mở mapping reorder/workload khi chưa có handler an toàn.** Đây có thể giữ ngoài phạm vi. | Hoàn thành theo phạm vi đã chốt (C/D/T) | Reorder/workload — S/A; Stock reorder/workload giữ advisory theo quyết định; không ánh xạ execution khi thiếu contract/rollback. |
| 67 | **Đo audit từ sự kiện thực tế**, không tự kết luận đủ actor, thời gian và thay đổi dữ liệu. | Hoàn thành trong phạm vi bằng chứng (T) | Audit thực — tests/test_audit_trail_evidence.py; actor/time/changes từ sự kiện, không gán sẵn. |
| 68 | **Phân biệt bảo vệ audit ở ứng dụng với trigger database đã được áp dụng và kiểm chứng.** | Hoàn thành trong phạm vi bằng chứng (T) | Trigger DB — tests/test_audit_database_evidence.py; restore; DB owner vẫn có quyền, không bất khả sửa tuyệt đối. |
| 69 | **Nghiệm thu bằng từng vai trò**, không chỉ tài khoản admin. | Hoàn thành trong phạm vi bằng chứng (T/P) | Role matrix — B; tests/test_internal_authorization_regressions.py; Google identity chỉ public, password nội bộ theo role. |
| 70 | **Đối chiếu tác vụ EMPLOYEE với đề cương.** Nhân viên phải làm được đúng tác vụ được mô tả. | Hoàn thành trong phạm vi bằng chứng (D/T) | EMPLOYEE — B; không nâng quyền mutation ngoài seeded capabilities. |
| 71 | **Kiểm tra xuyên suốt luồng đơn hàng và dịch vụ**, bao gồm chuyển trạng thái không hợp lệ. | Hoàn thành trong phạm vi bằng chứng (T) | Order/service lifecycle — B; chuyển trạng thái sai có regression. |
| 72 | **Kiểm tra lại Customer–Workspace và ownership sau các cập nhật mới.** | Hoàn thành trong phạm vi bằng chứng (T/P) | Customer/ownership — tests/test_public_ecommerce_cart_and_checkout.py; khác tài khoản không xem được TEST 162. |
| 73 | **Kiểm tra nhất quán tồn kho giữa các hình thức giao/nhận.** Không mặc nhiên coi có bảng tồn kho là checkout đã xử lý mọi trường hợp. | Hoàn thành trong phạm vi bằng chứng (T) | Fulfillment/inventory — tests/test_fulfillment_inventory_consistency.py; strict policy opt-in, không giả định bật production. |
| 74 | **Kiểm tra thất bại email không làm mất nghiệp vụ**, đồng thời cảnh báo đúng và retry không gửi trùng. | Hoàn thành trong phạm vi bằng chứng (T) | Email failure/retry — tests/test_brevo_email_backend.py; provider acceptance khác receipt, timeout có trạng thái bất định. |
| 75 | **Kiểm tra thông báo cảm ơn đúng người và đúng thời điểm**, không lặp vô hạn. | Hoàn thành trong phạm vi bằng chứng (P/H) | Celebration — L; đúng owner, người khác không thấy, ack/reload; TEST đã hủy. |
| 76 | **Chạy lại các ca đăng ký trùng, xác minh hết hạn, replay và xác minh khác thiết bị.** | Hoàn thành trong phạm vi bằng chứng (T/H) | Registration/replay — tests/test_registration_codes.py; L; cross-device user UAT riêng. |
| 77 | **Kiểm chứng import → mapping → dữ liệu chuẩn**, có dữ liệu sai, trùng và khác workspace. | Hoàn thành trong phạm vi bằng chứng (T) | Import→mapping — tests/test_import_mapping_acceptance.py; scoped invalid/duplicate, không replay-idempotency mọi child entity. |
| 78 | **Không sửa quyền rộng hơn hoặc làm yếu assertion để đạt test.** | Hoàn thành trong phạm vi bằng chứng (T/D) | Không yếu assertion — L; cleanup connection sửa teardown, không skip/keepdb để che lỗi. |
| 79 | **Bổ sung tổng quan nghiên cứu có phân tích so sánh.** Tài liệu công cụ chính thức chưa thay thế được nghiên cứu liên quan. | Hoàn thành trong phạm vi bằng chứng (D) | Nghiên cứu so sánh — docs/RESEARCH_SOURCE_CHECK_2026_09_25.md; docs/DRAFT_SOURCE_AND_DIAGRAM_AUDIT_2026_10_05.md; Hoàn tất đối chiếu nghiên cứu có chọn lọc, bổ sung UIT-ViQuAD của UIT/VNU-HCM và bảng ưu/nhược/giới hạn; không nhận systematic review. |
| 80 | **Chứng minh khoảng trống ở mức ứng dụng**, không tự tuyên bố tính mới chỉ vì kết hợp nhiều công nghệ. | Hoàn thành trong phạm vi bằng chứng (D) | Gap ứng dụng — S/W; tích hợp không tự là tính mới thuật toán. |
| 81 | **Hoàn thiện ma trận yêu cầu → code → test → bằng chứng.** | Hoàn thành trong phạm vi bằng chứng (T/D) | Requirement→evidence — B; 35 UC matched log, không chứng nhận adequacy/visual tự động. |
| 82 | **Hoàn thiện use case, ERD, kiến trúc và sequence**, đối chiếu với code hiện tại. | Hoàn thành theo phạm vi đã chốt (D/T/C) | Sơ đồ/code — B; tests/test_academic_diagram_contract.py; 22 FK ERD khớp model, 4 sequence và kiến trúc/use-case đối chiếu source; nghiệm thu bộ tài liệu hiện có. Bản nộp mới chưa được tạo/duyệt. |
| 83 | **Chuẩn hóa hồ sơ dữ liệu:** nguồn, cách tạo, kích thước, phiên bản và giới hạn. | Hoàn thành trong phạm vi bằng chứng (D/T) | Data catalog — X; synthetic nguồn/seed/hash; dữ liệu production không đưa vào gói công khai. |
| 84 | **Chuẩn hóa bộ kết quả thực nghiệm có thể chạy lại.** | Hoàn thành trong phạm vi bằng chứng (T) | Replay experiment — F/X; CSV/model/manifest replay, không multi-origin generalization. |
| 85 | **Chạy test theo nhóm ở cùng commit và tổng hợp kết quả rõ ràng.** | Hoàn thành trong phạm vi bằng chứng (T) | Cùng source/run — F/L; Full 1207 của tree ghi trong manifest 09/10; apps/config/tests tương ứng runtime release 0c618c7. Các hiệu chỉnh tài liệu sau snapshot có focused guard riêng. |
| 86 | **Ghi đầy đủ failure, skipped và phần chưa chạy.** | Hoàn thành trong phạm vi bằng chứng (D/T) | Fail/skip — F/L; Giữ log 1207 lần đầu FAILED 1 do manifest thiếu 2 file; lần chạy lại có log riêng. Không cộng lần chạy, không skip/xóa assertion. |
| 87 | **Hoàn thiện README, migration, tài khoản demo theo vai trò và kịch bản trình diễn.** | Hoàn thành trong phạm vi bằng chứng (D/T) | README/demo/migrations — docs/DEMO_IDENTITY_RUNBOOK.md; B; seed chỉ DB local trống, không reseed/reset hệ thống hiện hành. |
| 88 | **Chuẩn bị phương án demo khi mạng/API ngoài lỗi**, nhưng phải ghi rõ đang dùng fallback. | Hoàn thành trong phạm vi bằng chứng (D/T) | Demo mạng lỗi — docs/DEMO_FALLBACK_RUNBOOK.md; phải ghi offline/deterministic, không giả live API. |
| 89 | **Rà soát IEEE, tên đề tài và các kết luận trên toàn bộ tài liệu.** | Hoàn thành theo phạm vi đã chốt (D/C) | IEEE/tên/claims — W/Q; docs/DRAFT_SOURCE_AND_DIAGRAM_AUDIT_2026_10_05.md; IEEE chương 1–2 theo lần xuất hiện; bỏ nguồn không dùng chương 3–5, đối chiếu claims/nguồn bản nháp. Word được duyệt giữ hash. Chỉ nghiệm thu tài liệu hiện có. |
| 90 | Xác nhận phiên bản đang deploy khớp phiên bản nghiệm thu. | Hoàn thành trong phạm vi bằng chứng (P/D) | Deploy SHA — L; Render dep-db1mb8vavr4c73ckipfg live SHA 0c618c7, kiểm lại 09/10. Đợt này chỉ sửa tài liệu; deployment chức năng giữ cùng source. |
| 91 | Có bằng chứng email cho từng sự kiện nghiệp vụ, không chỉ thư chẩn đoán. | Hoàn thành trong phạm vi bằng chứng (H) | Inbox bốn event — L; không Message ID độc lập cho release cuối. |
| 92 | Xác nhận worker dự báo được vận hành và phục hồi đúng khi restart nếu dùng async trên production. | Hoàn thành theo phạm vi đã chốt (C/T) | Worker production — F; Render Free tắt async production; worker đã kiểm local. Hoàn thành cấu hình/giới hạn phạm vi, không chứng nhận worker cloud. |
| 93 | Kiểm tra kết quả CI hiện tại; xử lý findings bảo mật, không dùng cấu hình bỏ qua lỗi để gọi CI xanh. | Hoàn thành trong phạm vi bằng chứng (P/T) | CI/security — L; CI run 37286413162 completed/success SHA 0c618c7; full local 09/10 riêng. Không coi local thay runner hoặc suy coverage 100%. |
| 94 | Xác nhận Sentry/observability nhận được sự kiện thật nếu tuyên bố đã vận hành. | Hoàn thành theo phạm vi đã chốt (H/C) | Sentry — L; Chủ dự án xác nhận Sentry nhận event thật; ghi nhận Human Evaluation, không tự tạo Event ID độc lập. |
| 95 | Theo dõi cấu hình HTTPS, cookie và CSP phù hợp. | Hoàn thành trong phạm vi bằng chứng (P) | HTTPS/cookie/CSP — L/F; baseline enforcement, còn inline/eval, không strict nonce CSP. |
| 96 | Giữ mục `pg_dump → pg_restore` là **chưa kiểm chứng và đang hoãn theo yêu cầu của bạn**. | Hoàn thành theo phạm vi đã chốt (T/H/C) | pg_dump→pg_restore — docs/PRODUCTION_RESTORE_DRILL_2026_10_02.md; pg_dump→pg_restore 02/10 sang DB local mới: 60 bảng/10576 dòng khớp snapshot, constraints/trigger. Backup ổ D; offsite hoãn, media/model nghiệm thu Local Storage. |
| 97 | Quản lý secret an toàn; xác nhận rotate trước đây của bạn không thay thế việc bảo vệ secret trong các lần phát triển tiếp theo. | Hoàn thành theo phạm vi đã chốt (T/H/C) | Secrets — F/L; Known-pattern source/history scan và rotation theo xác nhận người dùng; không ghi secret/password vào bộ công khai. Mật khẩu demo giữ theo chủ dự án. |

## Điều kiện mở lại sau nghiệm thu

Bật worker async production, dùng S3/offsite, đưa chính sách thương mại thật
vào trợ lý, đổi provider/model hoặc phát hành báo cáo nộp mới cần kiểm lại phần
liên quan. Đây là công việc tương lai ngoài lựa chọn hiện tại; không để chúng
thành việc thiếu âm thầm trong bảng đã chốt. Không tạo thêm giao dịch production
trong đợt này; các đơn TEST trước đã hủy theo biên bản.

Bản Word được duyệt vẫn có SHA-256
9daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816.
Không sửa database schema, mật khẩu, membership hoặc migrations trong đợt cuối.
