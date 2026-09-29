# Hồ sơ dữ liệu và tái lập — 25/09/2026

Đây là bộ nghiệm thu **offline tổng hợp**, không phải dữ liệu kinh doanh thật.
Không khôi phục provenance còn thiếu của Batch 44 và không thay thế các kết quả
thất bại lịch sử. Những kết quả cũ thiếu snapshot vẫn không tái lập được.

## 1. Dự báo doanh thu

- Nguồn/cách tạo: `scripts/forecast_reproducible_experiment.py`, synthetic_formula_v1,
  seed NumPy 20260924; công thức và giới hạn tại `FORECAST_REPRODUCIBLE_BUNDLE_2026_09_24.md`.
- 180 dòng ngày 01/01–29/06/2026, đơn vị VND; không có dữ liệu cá nhân.
- Sau lag: 99 train, 33 calibration, 34 test, tuần tự thời gian.
- Snapshot: `output/forecast_repro_20260924/`; replay độc lập:
  `output/forecast_repro_20260924_replay/`. Dataset/config/model/predictions/results
  và hashes có trong manifest; không điền dữ liệu còn thiếu bằng kết quả giả.
- XGBoost MAE 165179.49, lag-7 MAE 153289: giữ kết quả model kém baseline.
  Coverage 29/34 chỉ là phép đếm trên tập này, không chứng nhận calibration.

## 2. RAG

- Nguồn: `apps/knowledge/adversarial_cases.py`, tác giả fixture là mã nguồn đồ án,
  không phải chính sách kinh doanh được duyệt hoặc tập benchmark độc lập.
- 5 tình huống, 6 câu hỏi: diễn đạt lại, thiếu dữ liệu, tài liệu mâu thuẫn,
  thiếu quyền và sai workspace.
- Gói `output/academic_replay_20260925/`: `rag_dataset.json` lưu câu hỏi,
  toàn văn tài liệu fixture và expected trước truy vấn; `rag_observations.json`
  lưu đầu ra thật của pipeline offline. `manifest.json` lưu hash từng file,
  phiên bản Python/thư viện và mã nguồn tạo fixture.
- Embedding deterministic/hash và generation offline; không có LLM API thật.
  2 dòng bị từ chối quyền, 4 dòng có phản hồi; **semantic_pass vẫn null**.
  Recall/precision chunk trong fixture không chứng minh đúng/đủ ngữ nghĩa.
- Bản gốc và replay có cùng 6 câu hỏi, trạng thái, câu trả lời và semantic_pass.
  Không đòi DB ID/timestamp giống nhau. Mục 39 vẫn mở để có người chấm độc lập.

## 3. Approval

- Dữ liệu tổng hợp được tạo trong `test_approval_state_integrity.py` và
  `test_approval_concurrency_evidence.py`: users/workspaces/products/proposals
  chỉ tồn tại trong database test riêng; không sao chép đơn hàng production.
- Source snapshot lưu đầy đủ fixture builders, payload, expected assertions;
  không có model ML huấn luyện cho phần này. Giá sản phẩm và hành động thử là
  dữ liệu kiểm thử, không phải giá kinh doanh hoặc chính sách được duyệt.
- Gồm kiểm constraint/idempotency, trạng thái, quyền, concurrency và rollback
  trong các ca được định nghĩa. Không suy ra mọi action đều an toàn hoặc “100% tuân thủ”.

## 4. Thực thi tái lập đã kiểm chứng

```powershell
python scripts/replay_academic_snapshot.py --package output/academic_replay_20260925 --output output/academic-replay-new
```

Output phải là thư mục mới. Runner xác minh hash trước chạy, chỉ nhận PostgreSQL
loopback và dùng database test UUID riêng. Không copy `.env` hoặc secret live;
fixture chứa thông tin đăng nhập tổng hợp cho test. Không chạy trên DB nghiệp vụ.

Lượt đã chạy: `output/academic_replay_execution_20260925/`, **17 tests OK,
64.531s**, exit 0. Log chứa đúng ba suite trong lệnh; không cộng 17 vào full-suite
1.095 vì đây là các ca chạy lại. Package manifest SHA256:
`2d01540dc4a88149c77ebefcc0392ab2c19f92499e9231923e03f73487483241`.

Gói chỉ có source Python phục vụ ba suite trên, không phải bản triển khai đầy
đủ gồm template/static. Kết quả replay không được diễn giải thành UI đã kiểm
chứng. Gói không chứa backup database.

Mục 83/84 được đối chiếu theo hồ sơ và bộ thực nghiệm mới này; không chứng nhận
khả năng tái lập mọi run cũ, hiệu quả kinh doanh, AI thật hoặc kết quả semantic.
