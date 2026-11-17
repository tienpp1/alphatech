# Sửa tính toàn vẹn vận hành dữ liệu và AI

Ngày tổng hợp: 18/11/2026. Tiếp nối thiết kế và kế hoạch
`docs/superpowers/{specs,plans}/2026-11-17-operational-ai*.md`.
Đây là hồ sơ sửa mã và kiểm chứng riêng, **không sửa cấu trúc/tiến độ 97 mục**,
không sửa Word đã duyệt và không thay thế biên bản chứng nhận doanh nghiệp thật.

## Những thay đổi đã triển khai

### 1. Tích hợp và tiếp nhận

Sửa xử lý JSON rỗng, tham số HTTP, dấu phân cách CSV và giới hạn nguồn nội bộ.
Giữ API/file hiện có, kiểm tra nguồn–hồ sơ–lô cùng workspace. Nguồn đã đăng ký
không thể dùng URL xem trước khác để chuyển tiếp header/params chứa credential.
Chuyển hướng không được mang credential sang origin khác. Chẩn đoán HTTP và
mẫu xem trước/áp dụng che khóa nhạy cảm lồng nhau cùng giá trị bị lặp trong lỗi;
không thay đổi dữ liệu staging gốc chỉ để phục vụ che thông tin trên giao diện.

Lô mới có receipt của **chính bytes đã đọc**, SHA-256, thời điểm và đường vận
chuyển. REMOTE_HTTP chỉ có nghĩa đã đọc qua HTTP; không chứng minh đối tác hay
giao dịch thương mại thật. Nguồn mô phỏng nội bộ được chỉ rõ; receipt lịch sử
chưa có vẫn UNKNOWN/LEGACY_UNRECORDED. Tỷ lệ dòng hợp lệ không phải accuracy AI.

### 2. Ánh xạ

Sửa chọn cấu hình của đích thắng, trùng đích, enum mặc định không an toàn và
kiểm tra trạng thái xác nhận trên mọi loại quy tắc. Quy tắc chờ/bị từ chối không
được âm thầm ghi dữ liệu chuẩn hóa. Tiếp tục dùng dịch vụ áp dụng và audit cũ.

Mặc định là heuristic. Người quản lý có thể **chủ động đồng ý gửi tên cột** để
yêu cầu Groq gợi ý schema; không gửi mẫu dữ liệu, credential, tenant ID hay cấu
hình nguồn. Provider chỉ trả chỉ số cột và đích thuộc allowlist; công thức,
giá trị mặc định và cấu hình thực thi do server quyết định. Đề xuất được ký,
hết hạn sau600giây, gắn người dùng/workspace/hồ sơ/schema hiện hành; cần người
có quyền xác nhận trước khi lưu quy tắc. Thiếu khóa, lỗi mạng hoặc phản hồi
không hợp lệ quay về heuristic và phản ánh đúng nguồn đã dùng.

**Kiểm chứng thực tế:** ba lượt schema đầu không cho kết quả LLM hợp lệ; request
chẩn đoán ghi nhận HTTP403. Hai GET catalog cùng khóa sau đó cho403 với User-Agent
mặc định nhưng200 với định danh ứng dụng `AlphaTech/1.0` đang dùng trong RAG.
Đã bổ sung đúng định danh này cho mapper, không đổi khóa, payload, endpoint hay
quyền truy cập. Một request schema-only thật tiếp theo giữ nguyên SHA payload
Customer cũ đã nhậnHTTP200 và đúng hai ánh xạ, không fallback. Model cấu hình
Render khớp `openai/gpt-oss-120b`. Đây chỉ là một smoke test đã biết đáp án,
**không phải bộ đo accuracy độc lập hoặc chứng minh mọi schema đều đúng**.
Không suy đoán chính xác lớp edge/WAF/policy bên provider thực thi việc chặn.

### 3. Dự báo

Thêm chế độ vận hành chỉ dùng kỳ đóng theo múi giờ hệ thống, kiểm tra ngày/tuần,
độ phủ quan sát và độ mới trước khi chạy. Giao diện mặc định vận hành; API cũ
giữ mặc định lịch sử tương thích. Người dùng vẫn có thể chọn đánh giá lịch sử,
nhưng kết quả này không tự trở thành dự báo hiện tại.

Ngày điền0 để tính toán được phân biệt với ngày có quan sát thật. Chính sách
kỹ thuật hiện tại cần tối thiểu49kỳ quan sát cho guarded hoặc34kỳ cho legacy,
độ phủ ít nhất80%, đủ14kỳ gần nhất và kỳ cuối khớp kỳ đóng. Đây không phải xác
minh nguồn thương mại hay bảo đảm chất lượng tương lai; chưa có cơ chế tự xác
nhận một ngày trống thực sự là ngày không phát sinh giao dịch.

Lưu riêng SHA của giá trị và fingerprint phiên bản1 cho bằng chứng quan sát:
ngày nguồn thật, ngày/kỳ quan sát, workspace/target/dimensions, bounds và chính
sách missing. Mất một ngày quan sát giá trị0 không thể bị che bởi hash giá trị
không đổi. Run cũ thiếu fingerprint giữ trạng thái chưa đánh giá, không tự
backfill hay gán đủ điều kiện. Đối chiếu cấu hình/source hiện hành, giữ nguyên
mọi điểm lịch sử và cơ chế chọn XGBoost/MA7 bằng validation quá khứ.

Tách horizon yêu cầu phục vụ khỏi horizon thực sự đã chấm; bổ sung WAPE và mẫu
số MAPE, độ phủ, biểu đồ ghép ngày không nối sai actual mới với forecast cũ.
Ngày tạo nghiệp vụ mặc định dùng ngày địa phương; ngày nhập rõ ràng được giữ.

**Quan sát read-only thực tế ngày17/11:** retail có143đơn hoàn tất trên76ngày,
nhưng chỉ2đơn trong28ngày gần nhất; 75ngày đóng có quan sát trên159kỳ. Nguồn
thương mại cũ UNKNOWN. Readiness từ chối vận hành; engine offline cũng từ chối
chấm holdout không có observed truth. Không tạo giao dịch để nâng điểm, không
thay MA7 bằng nhãn XGBoost, không xóa MAPE1268,1% cũ.

### 4. Khuyến nghị, phê duyệt và hành động thật

Hàng đợi hiện tại/lịch sử được tính khi đọc, giữ các bản ghi cũ và không ghi
đổi trạng thái trên GET. Trước thực thi kiểm tra lại người yêu cầu/người duyệt,
quyền hiện tại, phạm vi workspace, contract, tham số và độ mới bằng chứng.
Phê duyệt vẫn là quyết định của con người; không tự duyệt để tạo bằng chứng.

Dùng đúng dịch vụ nghiệp vụ hiện có để phân công/chuyển trạng thái; giữ công
việc kết thúc, lịch sử, workload và audit. Ghi nhớ replay đúng người/phạm vi/
payload trước kiểm tra điều kiện nghiệp vụ đã thay đổi, nên replay sau chuyển
kho không tạo giao dịch thứ hai. Khóa chống đề xuất trùng và thứ tự khóa thống
nhất được thử bằng giao dịch PostgreSQL thật trong TEST riêng.

Khóa Workspace dùng NO KEY UPDATE để vẫn tuần tự hóa các thao tác cùng cổng,
nhưng cho phép FK KEY SHARE của giao dịch khác. Khóa domain giữ FOR UPDATE;
không vô tình khóa mạnh cả Workspace/requester qua join. StockBalance khóa
theo branch_id như dịch vụ chuyển/hoàn tác trực tiếp. Đợt kiểm tra khóa retail
cuối đã tái hiện RED, sửa hai join domain và đạt145test liên quan. Review độc lập
SPEC/QUALITY đều PASS; full-suite/phát hành vẫn phải đọc receipt riêng, không
suy ra đã triển khai production từ kết quả này.

## Bằng chứng và phạm vi

Tất cả dữ liệu thay đổi để kiểm thử nằm trong database TEST loopback ngẫu nhiên,
tự hủy sau chạy, không phải Neon nghiệp vụ. Không migration/domain model mới,
không reset database. Bản checkout chính đang bẩn được giữ nguyên; phát hành
nếu đạt sẽ đi từ worktree đã cô lập.

Bằng chứng chi tiết: `D:/ai_business_platform/output/operational_ai_20261117/`.
`progress.md` chỉ dẫn các report Task1/2/3, RED→GREEN, review, full-suite receipts,
browser và các kiểm tra live có giới hạn. Số liệu final/release phải đọc từ
receipt đúng SHA, không suy ra từ focused test hay từ cấu hình workflow.

Gates trước phát hành: full cuối **1782/1782**,404,197s,0failure/error/skip,
receipt completed=true/source_unchanged=true, ownTESTDB tự hủy. JavaScript
80/80,2377,0524ms và5nhóm transport đạt. Browser fixture18/18,0pageerror/
không tràn ngang; check0issues, dry-run migration trong TEST mới không thay đổi.
Bandit apps/config0finding/0error; known-secret scan916sourcefiles0finding.
Các review độc lập và re-review scoped đều đóng blocker đã ghi nhận. Một lượt
full trước đó có lỗi testUTC được giữ trong log, không che hoặc gán PASS.
Đây là bằng chứng phần mềm trước commit; GitHub/Render chỉ được công bố khi
receipt đúngSHA xác nhận sau phát hành.

## Cần dữ liệu/bằng chứng ngoài mã để nghiệm thu rộng hơn

1. Tệp xuất thật hoặc endpoint đối tác được phép, cấu trúc và quyền truy cập;
   chưa có thì không công bố kết nối đối tác thật.
2. Lịch sử giao dịch đầy đủ/mới cùng xác nhận độ đầy đủ của ngày không có đơn;
   chưa đủ thì dùng đánh giá lịch sử, không bảo đảm XGBoost thắng mọi trường hợp.
3. Mở rộng bộ đánh giá schema với đáp án độc lập nếu muốn tuyên bố chất lượng
   ánh xạ; một ca Groq live thành công chưa thay thế đánh giá đó. Không gửi khóa
   trong chat. Lỗi provider/quota tương lai vẫn phải báo fallback trung thực.
4. Khi cần UAT nghiệp vụ production, chủ dự án chọn đúng dữ liệu/hành động thật
   và người duyệt; TEST concurrency không thay thế quyết định này.
