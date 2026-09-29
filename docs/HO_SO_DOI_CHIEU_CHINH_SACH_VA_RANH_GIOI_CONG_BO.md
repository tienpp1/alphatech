> **ĐÍNH CHÍNH 23/09/2026:** Các mốc bảo hành/đổi trả/SLA trong bản này chưa có nguồn phê duyệt công khai. Không dùng chúng làm cam kết khách hàng. POLICY_PUBLICATION_REVIEW.md vẫn là ranh giới công bố; mục 46 mở lại.

# HỒ SƠ ĐỐI CHIẾU CHÍNH SÁCH VÀ RANH GIỚI CÔNG BỐ KHÁCH HÀNG
## RÀ SOÁT CAM KẾT THƯƠNG MẠI, SOP TRI THỨC, TRỢ LÝ AI & KÊNH GIAO TIẾP
*(Nghiệm thu Học thuật Đợt 47; đính chính bằng chứng Cổng 46 ngày 26/09/2026)*

---

- **Tên đề tài chuẩn:** **Xây dựng nền tảng quản lý vận hành doanh nghiệp tích hợp trợ lí AI (AlphaTech AI Platform)**
- **Ngày hoàn thành đối chiếu:** 23/09/2026
- **Căn cứ rà soát:**
  - Danh mục 97 tiêu chí nghiệm thu học thuật ([docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md))
  - Cổng đóng các cụm việc còn mở ([docs/NEXT_CLOSURE_GATES.md](file:///d:/ai_business_platform/docs/NEXT_CLOSURE_GATES.md) — Hàng 14: Cụm 43–48)
  - Hồ sơ Rà soát Tuyên bố Hệ thống ([docs/CLAIM_AUDIT_INVENTORY.md](file:///d:/ai_business_platform/docs/CLAIM_AUDIT_INVENTORY.md))
  - Đánh giá Ranh giới Công bố Chính sách ([docs/POLICY_PUBLICATION_REVIEW.md](file:///d:/ai_business_platform/docs/POLICY_PUBLICATION_REVIEW.md))

---

## 1. Bối cảnh & Nguyên tắc Cốt lõi của Hồ sơ

Trong quá trình xây dựng hệ thống quản lý tích hợp trợ lý AI, một lỗi phổ biến trong các đồ án và hệ thống phần mềm doanh nghiệp là **đánh đồng giữa kịch bản dữ liệu kiểm thử (demo data / test fixtures / SOPs) với chính sách pháp lý thực tế đã được doanh nghiệp ban hành**. 

Đồng thời, sự xuất hiện của Trợ lý AI (Grounded RAG Assistant) dễ dẫn đến hiểu lầm rằng **"nội dung tư vấn của chatbot" đồng nghĩa với "chức năng giao dịch đã được hệ thống thực thi"** (ví dụ: Chatbot giải thích thủ tục trả góp không đồng nghĩa website có cổng thanh toán trả góp tự động).

Để bảo vệ tính trung thực học thuật và tính pháp lý minh bạch theo yêu cầu của Hội đồng chấm đề tài:
1. **Phân định ranh giới dữ liệu (Mục 45)**: Toàn bộ 24 tài liệu SOP trong thư mục `data/knowledge/` và dữ liệu tạo bởi `seed_demo` là **kịch bản mô phỏng kỹ thuật và dữ liệu kiểm thử hệ thống RAG**, không phải văn bản cam kết pháp lý thương mại đã được ban giám đốc doanh nghiệp phê duyệt áp dụng công khai.
2. **Loại bỏ cam kết thương mại không có căn cứ (Mục 43)**: Rà soát và loại bỏ triệt để các tuyên bố chưa được kiểm chứng độc lập: bồi hoàn 200%, trả góp 0%, liên kết ngân hàng, xuất hóa đơn e-VAT tự động, cam kết giao hàng hỏa tốc trong ngày.
3. **Loại bỏ tuyên bố an ninh phóng đại (Mục 44)**: Loại bỏ các tuyên bố chứng nhận ISO 27001 hoặc mã hóa dữ liệu cá nhân tuyệt đối. Hệ thống sử dụng phân lập logic theo Workspace và mã hóa mật khẩu tiêu chuẩn PBKDF2/Argon2 của Django.
4. **Thống nhất ranh giới công bố đa kênh (Mục 46)**: Chủ dự án xác nhận chưa có văn bản chính sách thương mại được doanh nghiệp bên ngoài ký duyệt. Vì vậy, SOP/seed chỉ là dữ liệu mô phỏng nội bộ; Chatbot, Web công khai và Email không được suy ra hoặc công bố thời hạn bảo hành, đổi trả hay SLA từ các dữ liệu đó. “Thống nhất” ở đây là thống nhất trạng thái *chưa xác minh*, không phải chuẩn hóa thành một con số chưa có căn cứ.
5. **Phân định Tư vấn vs Giao dịch thực thi (Mục 48)**: Mọi câu trả lời của Trợ lý AI về các dịch vụ tài chính hoặc kỹ thuật đều đi kèm thông điệp định hướng rõ ràng: đây là thông tin hướng dẫn tham khảo; khách hàng phải nộp biểu mẫu yêu cầu chính thức hoặc liên hệ trực tiếp nhân viên để xác nhận điều kiện áp dụng.

---

## 2. Ma trận Đối chiếu 8 Nhóm Cam kết Thương mại xuyên suốt 5 Bề mặt

Hệ thống tiến hành rà soát 8 nhóm chính sách qua 5 bề mặt tương tác:
1. **SOP nội bộ**: 24 file Markdown trong `data/knowledge/`
2. **Dữ liệu mẫu**: `apps/accounts/management/commands/seed_demo.py`
3. **Giao diện Web công khai**: Các template trong `templates/public/`
4. **Trợ lý AI (Chatbot)**: `apps/public_web/alphatech_ai.py`
5. **Email khách hàng**: `apps/public_web/email_service.py` & `templates/emails/`

| Nhóm Cam kết | Tuyên bố Cũ / Rủi ro Tiềm ẩn | Trạng thái SOP & Seed Demo | Hiện trạng Web Công khai | Hành vi Trợ lý AI (`alphatech_ai.py`) | Hành vi Email Giao dịch | Phân loại & Ranh giới Học thuật |
|---|---|---|---|---|---|---|
| **1. Bồi hoàn 200% & CO/CQ** *(Mục 43)* | Hứa bồi hoàn 200% nếu phát hiện hàng giả; cam kết 100% hàng có CO/CQ | SOP_RETAIL_WARRANTY có quy tắc kiểm tra serial nhưng không cam kết bồi thường 200% pháp lý | Đã dọn sạch: `about.html`, `products.html` không còn cụm từ "bồi hoàn 200%" hay "100% CO/CQ" | `handle_authenticity_and_cocq` từ chối cam kết mức bồi hoàn, hướng dẫn kiểm tra Serial/Service Tag trước khi mua | Không bao giờ hứa hẹn bồi thường tiền tệ trong email xác nhận | **Cam kết chưa xác minh**: Chỉ tư vấn quy trình kiểm tra phần cứng, không ban hành bảo lãnh tài chính |
| **2. Trả góp 0% & Đối tác Ngân hàng** *(Mục 43, 48)* | Cam kết mua trả góp 0%, liên kết 24 ngân hàng, duyệt hồ sơ qua CCCD 15 phút | `SOP_RETAIL_FINANCIAL_MARGIN` chỉ nói về tỷ lệ ký quỹ đại lý, không có hợp đồng đối tác ngân hàng | Giao diện thanh toán chỉ hỗ trợ thanh toán khi nhận hàng (`CASH`) và chuyển khoản; không có cổng trả góp | `handle_installment_procedure` tuyên bố rõ: *"Tôi chưa có chính sách trả góp đã xác minh... Không thể xác nhận trả góp có sẵn tại bước thanh toán."* Cảnh báo không gửi CCCD/OTP qua chat | Email không đề cập trả góp | **Tư vấn hướng dẫn (Advisory Only)**: Hệ thống chưa tích hợp cổng tài chính trả góp; chatbot không nhận vơ tính năng |
| **3. Thuế VAT & e-VAT tức thì** *(Mục 43)* | Tuyên bố giá đã gồm VAT, tự động xuất hóa đơn đỏ e-VAT tức thì | SOP chỉ nêu đệm thuế 3% trong giá sàn thanh lý; không có cổng kết nối Tổng cục Thuế | Bỏ nhãn "Đã bao gồm VAT"; hiển thị tách bạch tiền hàng, phí vận chuyển; ghi rõ hóa đơn cần liên hệ riêng | `handle_shipping_payment_vat` tuyên bố rõ: *"Tôi chưa có bằng chứng về dịch vụ phát hành hóa đơn VAT tự động... Email xác nhận không thay thế hóa đơn VAT."* | Email xác nhận không đóng dấu "Đã gồm VAT", ghi rõ hướng dẫn cung cấp MST khi nhận hàng | **Ranh giới kế toán**: Hệ thống là nền tảng quản trị vận hành nội bộ, không phải phần mềm hóa đơn điện tử kết nối thuế |
| **4. Giao hàng Hỏa tốc & Phí Ship** *(Mục 43)* | Cam kết giao hỏa tốc 2 giờ nội thành, miễn phí ship toàn quốc mọi đơn | Không có SLA cam kết phút giao hàng ngoại bộ trong SOP vận hành | Tính phí giao hàng minh bạch qua `cart.calculate_shipping_fee` (nội thành 30k, liên tỉnh 50k, miễn phí > 5 triệu) | `handle_shipping_payment_vat` thông báo phí hiển thị tại giỏ hàng; không cam kết mốc giờ giao hỏa tốc | Email ghi nhận chi phí vận chuyển thực tế được tính từ giỏ hàng | **Ranh giới logistics**: Phân định rõ tính toán phí tự động với thời gian vận chuyển thực tế của đơn vị vận chuyển thứ ba |
| **5. Đổi trả DOA & Bảo hành 12–24 tháng** *(Mục 43, 46)* | Cam kết 1 đổi 1 trong 30 ngày, bảo hành mặc định 12–24 tháng, cho mượn máy | SOP_RETAIL_WARRANTY mô tả quy trình tiếp nhận kỹ thuật; catalog có mô tả riêng từng sản phẩm | Bỏ cam kết bảo hành gộp; `product_detail.html` bảo lưu mô tả riêng của từng sản phẩm trong database | `handle_warranty_and_doa` và `handle_return_and_refund` hướng dẫn chuẩn bị chứng từ, không tự cam kết thời hạn đổi trả/mượn máy | Email gửi mã đơn hàng và hướng dẫn liên hệ bảo hành theo phiếu mua hàng | **Đồng bộ đa kênh**: Thống nhất quy chuẩn đổi trả theo tình trạng thực tế và chứng từ mua hàng, không áp đặt số ngày chung |
| **6. Chứng nhận ISO 27001 & Bảo mật PII** *(Mục 44)* | Khẳng định hệ thống đạt chuẩn ISO 27001, mã hóa dữ liệu cá nhân tuyệt đối | SOP_SVC_CHANGE_MANAGEMENT mô tả quy trình CAB nội bộ, không phải chứng chỉ ISO bên ngoài | Đã dọn sạch: Đổi "bảo mật tuyệt đối" $\to$ "phân lập logic đa khách thuê và kiểm soát truy cập phân cấp" | `handle_privacy_and_data_security` tuyên bố rõ: *"Tôi chưa có bằng chứng xác minh chứng nhận ISO 27001 hoặc các cam kết bảo mật tuyệt đối..."* | Email giao dịch loại bỏ hoàn toàn các dòng cam kết ISO 27001 hay NDA tuyệt đối | **Ranh giới an ninh**: Đạt chuẩn phân quyền RBAC và phân lập logic CSDL, không nhận vơ chứng chỉ tổ chức quốc tế |
| **7. Phân biệt Dữ liệu Mẫu vs Chính sách Thật** *(Mục 45)* | Xem dữ liệu seed trong demo là cam kết kinh doanh chính thức | `seed_demo.py` có cờ kiểm tra an toàn `is_demo_seed=True`, cảnh báo nghiêm ngặt về môi trường thử nghiệm | Gắn nhãn dữ liệu thử nghiệm trong báo cáo điều hành và giao diện demo | Chatbot chỉ sử dụng tri thức SOP làm ngữ cảnh gợi ý, luôn nhắc nhở xác nhận với nhân viên | Email chỉ xác nhận giao dịch mẫu trong môi trường demo | **Nguyên tắc học thuật**: Dữ liệu seed là fixture phục vụ kiểm chứng chức năng, không có giá trị pháp lý |
| **8. Ranh giới Tư vấn vs Giao dịch Thực thi** *(Mục 48)* | Hiểu nhầm tư vấn kỹ thuật/tài chính là hệ thống đã kích hoạt giao dịch | Kịch bản hỏi đáp trong tri thức là văn bản tham chiếu thông tin | Người dùng phải chủ động nộp biểu mẫu `/yeu-cau-dich-vu/` hoặc đặt hàng qua giỏ hàng để ghi nhận database | Toàn bộ handler (`handle_onsite_booking_guide`, `handle_hardware_upgrade_maintenance`) đều khẳng định: *"Gửi biểu mẫu chưa đồng nghĩa lịch hẹn đã được duyệt."* | Email chỉ phát sinh khi có bản ghi Transaction/Request thật trong CSDL | **Kiến trúc rõ ràng**: Tách bạch tầng Hội thoại (Conversation Layer) với tầng Giao dịch ACID (Transactional Core) |

---

## 3. Chi tiết Xử lý Kỹ thuật & Bằng chứng Mã nguồn

### 3.1. Dọn dẹp Cam kết Tuyệt đối trên Giao diện Web Công khai
Đã tiến hành rà soát tự động toàn bộ 23 template tại `templates/public/`:
- **`templates/public/about.html`**:
  - Loại bỏ hoàn toàn các con số phóng đại: `"99.8% hài lòng"`, `"10,000+ khách hàng"`, `"2,400+ dự án"`, `"100% CO/CQ"`, `"ISO 27001"`.
  - Thay thế bằng mô tả kiến trúc kỹ thuật: Nền tảng quản lý vận hành tích hợp Bán lẻ, Dịch vụ kỹ thuật, Trợ lý AI và Bản đồ số GIS.
- **`templates/public/home.html`**:
  - Loại bỏ các cụm từ: `"Bảo mật tuyệt đối"`, `"Xuất VAT tức thì"`, `"SLA 15 - 30 phút"`.
  - Thay thế bằng: Cơ chế phân lập logic đa khách thuê theo Workspace, tích hợp quy trình phê duyệt an toàn Human-in-the-Loop và kiểm soát số học kép.
- **`templates/public/product_detail.html`**:
  - Không chèn chuỗi mặc định chung `"Bảo hành 12-24 tháng chính hãng / 1 đổi 1 trong 30 ngày"`.
  - Hiển thị trung thực nội dung trường `description` và `unit_price` của từng bản ghi sản phẩm trong cơ sở dữ liệu.
- **`templates/public/contact.html`**:
  - Loại bỏ cam kết `"Phản hồi trong 24 giờ làm việc"`.
  - Thay thế bằng thông báo: *"Yêu cầu của Quý khách sẽ được tiếp nhận và nhân viên hỗ trợ sẽ liên hệ xác nhận trong thời gian sớm nhất."*

### 3.2. Chuẩn hóa Phản hồi Trợ lý AI (`apps/public_web/alphatech_ai.py`)
Mọi handler tư vấn nghiệp vụ đều được lập trình với cơ chế phòng vệ trung thực (Honest Guardrails):
1. **Thủ tục trả góp (`handle_installment_procedure`)**:
   ```python
   reply = (
       "**Thông tin mua trả góp**\n\n"
       "Tôi chưa có chính sách trả góp đã xác minh về đối tác, lãi suất, phí, kỳ hạn hay điều kiện duyệt hồ sơ. "
       "Không thể xác nhận trả góp có sẵn tại bước thanh toán.\n\n"
       "Quý khách vui lòng liên hệ tư vấn để được xác nhận bằng văn bản trước khi quyết định. "
       "Không gửi ảnh CCCD, số thẻ, mật khẩu hay mã OTP trong cuộc trò chuyện này."
   )
   ```
2. **Cam kết chính hãng & bồi hoàn (`handle_authenticity_and_cocq`)**:
   ```python
   reply = (
       "**Nguồn gốc và giấy tờ sản phẩm**\n\n"
       "Tôi chưa có hồ sơ đã xác minh để cam kết xuất xứ, CO/CQ hoặc mức bồi hoàn cho từng sản phẩm. "
       "Quý khách nên yêu cầu thông tin Serial/Service Tag, chứng từ và điều kiện bảo hành của đúng mã hàng trước khi mua."
   )
   ```
3. **Bảo mật dữ liệu & ISO 27001 (`handle_privacy_and_data_security`)**:
   ```python
   reply = (
       "**Thông tin bảo mật dữ liệu**\n\n"
       "Tôi chưa có bằng chứng xác minh chứng nhận ISO 27001 hoặc các cam kết bảo mật tuyệt đối của đơn vị. "
       "Không thể xác nhận điều kiện camera, lưu trữ hay mã hóa chỉ từ cuộc trò chuyện này."
   )
   ```
4. **Thanh toán, vận chuyển & hóa đơn VAT (`handle_shipping_payment_vat`)**:
   ```python
   reply = (
       "**Thanh toán, giao hàng và hóa đơn VAT**\n\n"
       "Quý khách hãy xem phương thức thanh toán và phí giao hàng đang hiển thị tại Giỏ hàng và bước thanh toán. "
       "Tôi chưa có bằng chứng về dịch vụ phát hành hóa đơn VAT tự động hoặc thời hạn giao hỏa tốc.\n\n"
       "Email xác nhận đơn hàng không thay thế hóa đơn VAT; gửi đơn cũng không đồng nghĩa tiền đã được nhận."
   )
   ```
5. **Dịch vụ kỹ thuật tận nơi (`handle_onsite_booking_guide`)**:
   ```python
   reply = (
       "**Yêu cầu kỹ thuật tận nơi**\n\n"
       "Quý khách có thể gửi mô tả sự cố, địa điểm và thời gian mong muốn tại Yêu cầu dịch vụ. "
       "Gửi biểu mẫu chưa đồng nghĩa lịch hẹn đã được duyệt. "
       "Phạm vi phục vụ, chi phí và thời gian đến cần được nhân viên xác nhận."
   )
   ```

### 3.3. Rào chắn Email Khách hàng (`apps/public_web/email_service.py`)
- **Email Đơn hàng**: Chặn đứng hoàn toàn việc trích xuất văn bản SOP nội bộ; chỉ gửi danh sách chi tiết các mặt hàng đã mua (`OrderItem`), đơn giá, số lượng, tổng tiền và hướng dẫn liên hệ bảo hành theo phiếu mua hàng.
- **Email Phiếu Dịch vụ**: Giữ nguyên mã phiếu và mức ưu tiên (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), ghi rõ thông điệp: *"Email này xác nhận hệ thống đã tiếp nhận yêu cầu, không xác lập cam kết SLA mới vượt ngoài hợp đồng dịch vụ đã ký kết."* Loại bỏ toàn bộ các câu chữ tự gán như `"Phản hồi trong 30 phút"` hay `"Hỗ trợ 24/7"`.
- **Email Liên hệ**: Xác nhận thông tin gửi thành công, loại bỏ mốc thời gian hứa hẹn `"24 giờ làm việc"`.

---

## 4. Kết luận Nghiệm thu Cụm Cổng 43–48

1. **Khép lại Mục 43**: Đã rà soát và loại bỏ toàn bộ các cam kết thương mại soạn sẵn thiếu căn cứ (bồi hoàn 200%, trả góp 0%, đối tác ngân hàng, e-VAT, giao hỏa tốc).
2. **Khép lại Mục 44**: Đã loại bỏ các tuyên bố chứng nhận ISO 27001 và mã hóa tuyệt đối; thay bằng ranh giới bảo mật logic phân quyền RBAC và mã hóa mật khẩu hiện hành.
3. **Khép lại Mục 45**: Đã xác lập ranh giới rõ ràng: 24 file SOP và dữ liệu seed là kịch bản mô phỏng kỹ thuật, không phải chính sách pháp lý chính thức của doanh nghiệp.
4. **Khép lại Mục 46 theo ranh giới không công bố**: SOP/seed được gắn nhãn mô phỏng; Chatbot, Web và Email cùng từ chối khẳng định các mốc đổi trả, bảo hành và SLA khi chưa có nguồn được duyệt. Không dùng các mốc 7 ngày/12 tháng/24 giờ trong hồ sơ cũ làm chính sách khách hàng.
5. **Khép lại Mục 48**: Tách bạch rạch ròi giữa năng lực tư vấn giải đáp của Chatbot và chức năng giao dịch kế toán/thanh toán thực tế của hệ thống.
