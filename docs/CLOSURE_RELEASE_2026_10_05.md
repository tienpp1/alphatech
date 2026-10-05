# Bàn giao đợt đối chiếu và repair — 05/10/2026

## Đã thực hiện ba cụm được đồng ý

1. Lập phụ lục riêng đủ97 ID, nguồn và giới hạn; không thay cấu trúc/tiến độ
   ledger.35 UC có source/test được nối với actual full log, không missing hoặc
   unobserved test file. Đây không là chứng chỉ đầy đủ nghiệp vụ/visual.
2. Chạy năm câu IND trên pipeline offline thật, phát hiện và sửa hai lỗi routing/
   irrelevant retrieval. Giữ output trước sửa, thêm regression và CI group.
   Chủ dự án chấm5/5ĐẠT trong review.md lúc09:40, được chuyển nguyên nguồn
   sang JSON fingerprint-bound; không tự gán điểm semantic.
3. Đóng gói Word duyệt nguyên trạng, chỉ mục bằng chứng, thực nghiệm forecast,
   phiếu/summary human và hướng dẫn demo. Chủ dự án xác nhận chưa có báo cáo/
   slide cuối khác: **chưa nghiệm thu bản nộp cuối**.

## Root causes và những thay đổi

- Query dự báo giá vàng được chọn như forecast workspace; hash retrieval lấy
  SOP bảo hành không liên quan. Scope guard từ chối external market, không
  retrieval/tool domain. Không coi đây là bộ phân loại OOD tổng quát.
- “Yêu cầu kỹ thuật” thiếu trong service ticket synonyms; “còn bao nhiêu” rơi
  xuống stock balance. Bổ sung phrase ở service branch, không nâng permissions.
- Bộ IND trước chỉ test scorer bằng mock; execution mới dùng actor thường,
  fixtures synthetic, network guard, output/time/provenance thật.
- Hồ sơ audit còn gọi timestamp tamper-evident và trigger ngăn100% can thiệp;
  sửa giới hạn DB owner và phạm vi test. Không thay schema hoặc reset dữ liệu.

## Validation và phiên bản

- Focused RAG trước assertion/variant cuối:83tests/109.188sOK.
- Full staged tree c80048022ab604cb3a807dee49b5f77a0fecb532:
  **1201tests/414.870sOK**,0failure/error/skip. Source application/config/tests/
  scripts/templates/static/data khớp commit phát hành; hồ sơ và workflow được
  bổ sung sau full run, không tự gọi đó là full run trên mọi file commit cuối.
- Full log/summary: output/policy_release_jx0ekuc9/.
- Django check0issues; makemigrations --check --dry-run: No changes detected.
- Source known-pattern scan806files/0findings, không chứng nhận mọi secret.
- GitHub main: ea18f14410c760f36dcd4055d1c73e789540c6ef đã push.
- https://github.com/tienpp1/alphatech/actions/runs/37256797585 completed/success
  đúng SHA; job111595502068 mọi bước success. RAG group12tests/0.434sOK,
  integrations77/32.159sOK; dependency audit no known vulnerabilities,
  Bandit/secret guard success. Coverage workflow58%, không100%; không cộng
  nhóm overlapping thành full-suite count.
- Render dep-db1h2hegekts73dptdbg **live đúng ea18f14**, đã đối chiếu API.
  Probe HTTPS thật5 trang public200, nội dung boundary/HSTS/CSP/nosniff giữ
  đúng baseline: output/closure_public_live_20261005.json. Không live Gemini
  quality hoặc tạo business event. Hồ sơ sau deploy này đang bổ sung local,
  không coi nó là nội dung đã có trong commit trước khi biết deploy success.

## Ranh giới không tự thay đổi

Local Storage; async production tắt trên Render Free; offsite backup hoãn;
reorder/workload advisory; CSP baseline còn inline/eval; credential demo theo
chọn lựa chủ dự án. Restore file dump độc lập local đã đạt nhưng không bao gồm
cloud failover, offsite hoặc recovery toàn bộ media/model production.

RAG5/5 là Human Evaluation trên mẫu synthetic đã dùng để repair, không holdout
mù/Gemini live accuracy. Email/Sentry/GPS và UAT cũ giữ loại nguồn riêng.
Word duyệt giữ SHA2569daeefdb61d1f0241b601e71882d2babb3ace148173acbba57fa40d4b8fd1816.
Ledger giữ hash đầu phiên1d532616a6e9c9b780aa47c6ea680793ecbcc7c9f58ee3989d5fae5f0daeec20.
Không tạo thêm đơn production, không đụng dữ liệu/sửa mật khẩu. Các thay đổi
unrelated của agent khác vẫn ở worktree và không nằm trong commit này.

**Không công bố97/97 tiêu chí production PASS.** Có thể dùng gói này để đối
chiếu phạm vi đồ án đã chốt; bản báo cáo/slide cuối và nghiên cứu quality tổng
quát vẫn cần nghiệm thu riêng khi có. Không nâng tỷ lệ bằng việc đổi tiêu chí.
