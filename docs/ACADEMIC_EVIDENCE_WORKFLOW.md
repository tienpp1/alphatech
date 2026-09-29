# Xuất bằng chứng học thuật — đợt 1

## Mục tiêu

Sửa tính trung thực của báo cáo trước khi nâng chất lượng mô hình. Không đồng nhất có mã nguồn, có dữ liệu seed hoặc test pass với đã đạt hiệu quả thực nghiệm.

## Lệnh dành cho người vận hành

```powershell
python manage.py evaluate_academic_metrics --workspace abc-retail --output output/academic-retail-20260914.md
python manage.py evaluate_academic_metrics --workspace xyz-service --output output/academic-service-20260914.md
```

Thay code workspace bằng code thực tế. Có thể thêm `--run-id 12 --run-id 13` để chọn run; tất cả phải thuộc workspace được chọn. Không chọn mặc định workspace đầu tiên. Không có tham số chọn run thì xuất tất cả run của workspace, gồm cả run thất bại. Đây là lệnh CLI cho người có quyền truy cập môi trường quản trị, không phải endpoint cho khách hàng.

Lệnh chỉ đọc dữ liệu và tạo file mới, không huấn luyện, gọi LLM, seed hoặc gửi email. File tồn tại sẽ bị từ chối ghi đè; đổi tên output cho lần xuất tiếp theo. Lệnh không tự kiểm định provenance của dữ liệu gốc.

## Quy tắc diễn giải

- Thiếu, NaN, vô cực, kiểu dữ liệu sai, run chưa hoàn thành hoặc không có mẫu test: không công bố sai số như một phép đo hợp lệ.
- MAE/RMSE/MAPE không âm; R² âm được giữ nguyên. Không thay giá trị thiếu bằng 0.
- Cải thiện MAE = `(baseline - model) / baseline * 100`; âm nghĩa là kém baseline. Baseline 0 không có tỷ lệ phần trăm xác định.
- Giữ run ID, workspace, config ID, target, kích thước train/test, khoảng dữ liệu, tham số job. Đây chưa phải snapshot đầy đủ để tái lập: còn cần dữ liệu/hash, cấu hình model tại thời điểm train, phiên bản thư viện và dự đoán từng mẫu.
- Backtest one-step không chứng minh chất lượng dự báo đệ quy nhiều ngày.
- RAG/GIS không được thực thi trong lệnh này. Đếm approval không đo được tuân thủ, rollback, concurrency hay audit bất biến.

## Phần tiếp theo chưa hoàn thành

1. RAG: rubric đủ ý, đúng nguồn, kiểm tra từ chối với mẫu số đúng; tách lexical proxy khỏi đánh giá ngữ nghĩa và API thật khỏi fallback.
2. Phê duyệt: ma trận ca thực thi/từ chối/tự duyệt/sai quyền/khác workspace/lặp/đồng thời/rollback với bằng chứng test, không suy rộng thành 100% hệ thống.
3. Bổ sung thực nghiệm dự báo tái lập, baseline phù hợp và phân tích sai số; không sửa số liệu lịch sử.
4. Rà lại tài liệu phạm vi và nội dung tư vấn công khai chưa có căn cứ (ISO, trả góp, VAT, bồi hoàn).

Đây là đợt đầu của checklist 97 mục, không phải xác nhận đã giải quyết toàn bộ checklist.

## Kiểm chứng đợt 1

- `python manage.py test tests.test_academic_reporting tests.test_academic_report_command --keepdb`: 13/13 qua; database được mock, không gọi API. Kiểm tra giá trị thiếu/không hợp lệ, kết quả âm, zero baseline, run lỗi/không có test, nhiều run, workspace bắt buộc, ID ngoài phạm vi và bảo toàn file cũ.
- `python manage.py check`: 0 vấn đề.
- `python manage.py makemigrations --check --dry-run`: không có thay đổi.
- `git diff --check`: không có lỗi whitespace.
- Windows sandbox chặn thư mục tạm của Python; cùng bộ test được chạy thành công ngoài sandbox, không bỏ test. Không chạy full suite, không xuất báo cáo từ database thật, không xác nhận lại các tỷ lệ lịch sử.

## Đợt 2 — Bộ chấm RAG (14/09/2026)

Đã thay cách chấm một từ khóa bằng `2.0-lexical-evidence-proxy`:

- Mọi nhóm từ khóa bắt buộc đều phải có; biến thể tương đương chỉ được dùng khi khai báo trong `required_keyword_groups`. Danh sách `expected_keywords` cũ được hiểu là mỗi từ/cụm là một nhóm bắt buộc. Đây là rubric từ vựng, chưa phải đáp án chuẩn được thẩm định.
- Cần đúng tên nguồn đã chuẩn hóa; câu hybrid cần thêm tool mong đợi với trạng thái SUCCESS. Chưa đánh giá nội dung từng chunk có thực sự hỗ trợ kết luận hay không.
- `lexical_evidence_pass_rate` chỉ tính trên câu hỏi có thể trả lời, không trộn câu ngoài phạm vi để nâng điểm. `grounded_correctness_rate` chỉ là alias tương thích đã deprecated.
- Precision từ chối = TP/(TP+FP); recall = TP/(TP+FN). Xuất cả số đếm; mẫu số 0 ghi null. Chỉ nhận câu từ chối chuẩn sau chuẩn hóa hoa/thường/khoảng trắng, nên các cách từ chối diễn đạt khác cần người đánh giá xem lại.
- `semantic_correctness_rate=null`; mode sinh câu trả lời UNKNOWN. Không suy luận rằng có API key là đã chạy LLM thật. Kết quả lưu toàn văn trả lời, nguồn và tool trong bộ nhớ trả về; không tự xuất lên public/log. Khi lưu artifact, cần bảo vệ dữ liệu nội bộ và phân quyền người xem.

Kiểm thử: 15 ca mới về scorer/runner + 8 ca báo cáo đợt 1 đều qua (23/23). Check không lỗi, không migration mới. Bài tích hợp cũ vẫn giữ ngưỡng 80% nhưng chưa chạy vì DB cấu hình hiện tại là remote; cần test DB riêng. Kiểm thử mock không chứng minh chất lượng trả lời thực tế.

### Bằng chứng còn thiếu trước khi dùng số liệu trong đồ án

1. Chốt đáp án chuẩn/nguồn chuẩn trên snapshot tài liệu và dữ liệu nghiệp vụ; thẩm định nhóm từ khóa thay vì lấy chúng làm chân lý.
2. Chạy integration offline trên database cô lập, ghi ca thất bại; không hạ ngưỡng chỉ để pass.
3. Bổ sung provenance thực tế của embedding và sinh câu trả lời trước khi tách kết quả API/offline; không tự gán nhãn LIVE.
4. Người đánh giá kiểm tra từng ý, số liệu, phủ định/mâu thuẫn, độ đầy đủ và trích dẫn. Một câu chứa tất cả từ khóa nhưng phủ định sai vẫn có thể qua proxy; regression test ghi rõ giới hạn này, không coi là đúng ngữ nghĩa.
5. Chạy benchmark mới và giữ nguyên kết quả lịch sử để đối chiếu; chưa có tỷ lệ chính xác RAG mới được chứng nhận.
