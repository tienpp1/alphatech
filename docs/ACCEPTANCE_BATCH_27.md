# Đợt 27 — AI minh bạch chế độ, demo dự phòng và GIS tham chiếu

Ngày 16/09/2026. Đóng 3 mục: 50, 51, 88; tiến độ 40/97 = 41,2%.

## Các nhóm hoàn tất

1. API normal synthesis/audit/benchmark lưu cách tạo câu trả lời thực sự. UI
   hiển thị trạng thái bằng chữ và role=status. Có key nhưng provider lỗi vẫn
   ghi DETERMINISTIC/PROVIDER_UNAVAILABLE. Mode cũ/nhánh đặc biệt chưa ghi nhận
   giữ UNKNOWN. Model là mã yêu cầu gửi provider, không phải version được xác thực.
2. Kịch bản demo dự phòng và preview template riêng không chạm dữ liệu nghiệp vụ.
   Xem DEMO_FALLBACK_RUNBOOK.md. UI bỏ câu cam kết chính xác cho mọi kết quả.
3. Đối chiếu khoảng cách GIS với nguồn công bố và công thức độc lập với ứng dụng.
   Sửa thiếu spheroid=True ở cả distance và radius để đúng contract đã ghi.
   Xem GIS_REFERENCE_EVIDENCE.md cho tọa độ, nguồn và tolerance.
4. Sửa grid ba cột tràn ngang ở cửa sổ hẹp; thêm nhãn accessible cho ô câu hỏi.

## Kiểm chứng

```text
python manage.py test tests.test_generation_provenance tests.test_simulation_evidence tests.test_rag_evaluation_scoring tests.test_rag_evaluation_runner tests.test_rag_grounding_assistant --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

32/32 qua, 38.697s. Sau đó thêm hai ca transport timeout/invalid JSON:

```text
python manage.py test tests.test_generation_provenance --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

7/7 qua, 0.102s. Năm ca trong nhóm này đã chạy ở nhóm 32; không cộng trùng thành
39 test độc lập. Các response provider trong test là mô phỏng.

```text
python manage.py test tests.test_gis_reference_distances tests.test_gis_spatial --settings=config.settings_evidence_test --keepdb --noinput -v 1
```

10/10 qua, 0.520s. Tổng cộng 44 test phân biệt trong đợt.
`manage.py check`: no issues; `makemigrations --check --dry-run`: no changes.

Browser: mở http://127.0.0.1:8012/ với template thật trong shell preview, gửi câu
“Doanh thu mẫu”, thấy câu trả lời mẫu 100 VND và trạng thái trả lời theo quy tắc.
Ảnh ban đầu phát hiện tràn ngang; sau chỉnh CSS, ảnh xác nhận bố cục một cột và
nhãn đọc được ở cửa sổ hẹp. Đây là fixture API, không chứng minh login, dữ liệu
thật, browser production hoặc API Gemini live. Skill ui-ux-pro-max hỗ trợ lựa
chọn thông báo có text/role và bố cục; không thay đổi brand/design system chung.

## Còn mở

Mục 35/36 vẫn một phần: chưa chứng minh embedding đang dùng thực tế, chưa lưu
metadata cho mọi early-return và lịch sử cũ, chưa nghiệm thu provider thật.
Mục 39 chờ người đánh giá trên snapshot nguồn chuẩn. Không tự chấm để nâng tỷ lệ.
Chưa push/deploy toàn worktree tích lũy; không chạy lại toàn bộ test suite.
