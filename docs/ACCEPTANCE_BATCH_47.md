# Đợt 47 — Nghiệm thu Toàn diện Chính sách Doanh nghiệp, SOP, Chatbot, Web & Email

Ngày chốt: 23/09/2026.  
Phạm vi: Cụm Cổng 43, 44, 45, 46, 48 theo [docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) (Hàng 14) và [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md).  
Tài liệu kiểm toán trọng tâm: [docs/HO_SO_DOI_CHIEU_CHINH_SACH_VA_RANH_GIOI_CONG_BO.md](file:///d:/ai_business_platform/docs/HO_SO_DOI_CHIEU_CHINH_SACH_VA_RANH_GIOI_CONG_BO.md).  
Tệp kiểm thử cốt lõi: [tests/test_policy_and_claim_consistency.py](file:///d:/ai_business_platform/tests/test_policy_and_claim_consistency.py), [tests/test_public_policy_copy.py](file:///d:/ai_business_platform/tests/test_public_policy_copy.py) và [tests/test_customer_email_policy_boundary.py](file:///d:/ai_business_platform/tests/test_customer_email_policy_boundary.py).

---

## 1. Các Hạng mục Hoàn tất

- **Mục 43: Rà soát các cam kết thương mại soạn sẵn (bồi hoàn 200%, trả góp 0%, đối tác ngân hàng, e-VAT, giao hàng và bảo hành)**:
  - Lập Ma trận đối chiếu 8 nhóm cam kết thương mại xuyên suốt 5 bề mặt tương tác tại [docs/HO_SO_DOI_CHIEU_CHINH_SACH_VA_RANH_GIOI_CONG_BO.md](file:///d:/ai_business_platform/docs/HO_SO_DOI_CHIEU_CHINH_SACH_VA_RANH_GIOI_CONG_BO.md).
  - Loại bỏ hoàn toàn các tuyên bố thương mại không có căn cứ trên toàn bộ 23 template công khai (`home`, `about`, `products`, `product_detail`, `contact`, `services`, `service_detail`): không còn các cụm từ `"bồi hoàn 200%"`, `"trả góp 0%"`, `"liên kết 24 ngân hàng"`, `"xuất VAT tức thì"`, `"100% CO/CQ"`.
  - Bộ xử lý Trợ lý AI (`handle_authenticity_and_cocq`, `handle_installment_procedure`, `handle_shipping_payment_vat`) từ chối nhận vơ bảo lãnh tài chính, giải thích rõ email không thay thế hóa đơn VAT và hướng dẫn kiểm tra Serial/chứng từ thực tế.

- **Mục 44: Rà soát tuyên bố ISO 27001 và mã hóa dữ liệu cá nhân**:
  - Dọn sạch toàn bộ các tuyên bố chứng nhận ISO 27001 hoặc cam kết "bảo mật tuyệt đối" trên giao diện công khai và email gửi khách hàng.
  - Handler `handle_privacy_and_data_security` trong [apps/public_web/alphatech_ai.py](file:///d:/ai_business_platform/apps/public_web/alphatech_ai.py) phản hồi trung thực: *"Tôi chưa có bằng chứng xác minh chứng nhận ISO 27001 hoặc các cam kết bảo mật tuyệt đối..."* và cảnh báo khách hàng không gửi mật khẩu, mã OTP hoặc tài liệu nhạy cảm qua khung chat.
  - Phân định rõ ràng: Hệ thống áp dụng kiểm soát truy cập phân cấp RBAC và mã hóa mật khẩu tiêu chuẩn (PBKDF2/Argon2) của Django, không tự nhận đạt chứng chỉ của bên thứ ba.

- **Mục 45: Phân biệt chính sách doanh nghiệp thật với dữ liệu demo**:
  - Xác lập ranh giới học thuật rõ ràng: Toàn bộ 24 tài liệu SOP trong `data/knowledge/` và dữ liệu tạo bởi `seed_demo` là **kịch bản mô phỏng kỹ thuật và dữ liệu kiểm thử hệ thống RAG**, không phải văn bản cam kết pháp lý thương mại đã được ban giám đốc doanh nghiệp phê duyệt áp dụng công khai.
  - Lệnh `seed_demo.py` duy trì cờ kiểm tra an toàn `is_demo_seed=True` và kiểm tra môi trường nghiêm ngặt, không cho phép rò rỉ dữ liệu thử nghiệm vào bối cảnh tài chính thực tế.

- **Mục 46: Thống nhất chính sách giữa chatbot, SOP, trang web và email**:
  - Thống nhất các điều kiện đổi trả hàng (DOA), bảo hành và thời gian phản hồi kỹ thuật SLA:
    - Web: Giữ nguyên mô tả riêng (`description`) của từng sản phẩm trong database, không gộp chung chính sách 12–24 tháng.
    - Email: Xác nhận tiếp nhận thông tin yêu cầu dịch vụ với nhãn mức ưu tiên (`Thấp`, `Trung bình`, `Cao`, `Khẩn cấp`), loại bỏ hoàn toàn các cam kết tự gán như `"30 phút"` hay `"24/7"`, khẳng định rõ *"Email này xác nhận hệ thống đã tiếp nhận yêu cầu, không xác lập cam kết SLA mới vượt ngoài hợp đồng dịch vụ đã ký kết."*
    - Chatbot: Đồng bộ các khuyến cáo chuẩn bị chứng từ mua hàng và mã đơn hàng trước khi gửi yêu cầu đổi trả.

- **Mục 48: Không trình bày nội dung tư vấn như một chức năng đã triển khai**:
  - Chatbot hướng dẫn thủ tục trả góp nhưng tuyên bố rõ ràng: *"Tôi chưa có chính sách trả góp đã xác minh... Không thể xác nhận trả góp có sẵn tại bước thanh toán."*
  - Chatbot hướng dẫn đặt lịch kỹ thuật tận nơi (`handle_onsite_booking_guide`) nhấn mạnh: *"Gửi biểu mẫu chưa đồng nghĩa lịch hẹn đã được duyệt. Phạm vi phục vụ, chi phí và thời gian đến cần được nhân viên xác nhận."*
  - Tách bạch rạch ròi giữa Tầng Hội thoại Trợ lý AI (Conversation Layer) với Tầng Giao dịch ACID (Transactional Core): Mọi hành động giao dịch phải được thực thi qua giỏ hàng/thanh toán hoặc biểu mẫu phiếu dịch vụ có xác nhận người dùng.

---

## 2. Kết quả Kiểm thử Tự động & Bằng chứng Thực nghiệm

### 2.1. Kiểm tra Toàn vẹn Hệ thống

```powershell
python manage.py check
```
```text
System check identified no issues (0 silenced).
```

```powershell
python manage.py makemigrations --check --dry-run
```
```text
No changes detected
```

### 2.2. Kiểm thử Rà soát Chính sách & Cam kết Thương mại

```powershell
python manage.py test tests.test_policy_and_claim_consistency tests.test_public_policy_copy tests.test_customer_email_policy_boundary --keepdb
```
```text
................
----------------------------------------------------------------------
Ran 16 tests in 0.194s

OK
Found 16 test(s).
System check identified no issues (0 silenced).
```

### 2.3. Kiểm thử Hồi quy Copilot API & Vết Kiểm toán

```powershell
python manage.py test tests.test_public_copilot_and_cart_api tests.test_audit_trail_evidence --keepdb
```
```text
Using existing test database for alias 'default'...
............................
----------------------------------------------------------------------
Ran 28 tests in 38.114s

OK
Preserving test database for alias 'default'...
Found 28 test(s).
System check identified no issues (0 silenced).
```

Tổng cộng: **44 bài kiểm thử tự động chuyên sâu vượt qua 100% (44/44 PASS)**, xác thực tính nhất quán toàn diện của các ranh giới chính sách.

---

## 3. Cập nhật Bảng Tiến độ Checklist 97

- **Chuyển trạng thái 5 mục**:
  - **Mục 43**: Một phần $\to$ **Đóng**
  - **Mục 44**: Một phần $\to$ **Đóng**
  - **Mục 45**: Một phần $\to$ **Đóng**
  - **Mục 46**: Một phần $\to$ **Đóng**
  - **Mục 48**: Một phần $\to$ **Đóng**
- **Tiến độ lũy kế mới**:
  - **Đóng hoàn toàn (Closed with Evidence)**: **83 / 97 mục (85,6%)** (trước: 78 mục, 80,4%).
  - **Một phần (Partially Closed)**: **3 / 97 mục (3,1%)** (còn lại: Mục 70, 73, 86).
  - **Chưa xác nhận đóng (Unconfirmed / Production Scope)**: **11 / 97 mục (11,3%)** (các mục: 3, 6, 47, 90, 91, 92, 93, 94, 95, 96, 97).
  - **Mẫu số kiểm soát**: Đúng **97 mục gốc**, không biến đổi hay suy diễn.
