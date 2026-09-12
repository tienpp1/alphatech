# QUY CHUẨN HỢP ĐỒNG MUA HÀNG, CHẾ TÀI PHẠT GIAO HÀNG TRỄ & THU HỒI LÔ HÀNG LỖI 2026
**Mã hiệu:** SOP-PROC-PEN-2026  
**Áp dụng:** Khối Thu Mua & Quản Trị Chuỗi Cung Ứng ABC Tech Store (`abc-retail`)  
**Hiệu lực:** Từ ngày 01/01/2026  

---

## 1. Chế Tài Phạt Vi Phạm Giao Hàng Chậm (Supplier Delivery Delay Penalties)
Nhằm duy trì tính liên tục của chuỗi cung ứng và định mức tồn kho an toàn tại các chi nhánh:
1. **Mức Phạt Vi Phạm Hạn Định Giao Hàng:**
   - Trường hợp nhà phân phối (Viễn Sơn, Synnex FPT, DGW) giao hàng chậm so với ngày cam kết trong Đơn đặt hàng (Purchase Order - PO) đã ký xác nhận:
   - Mức phạt được áp dụng: **0.5% tổng giá trị lô hàng cho mỗi ngày làm việc giao trễ**.
   - Mức phạt lũy kế tối đa được khống chế ở mức **8.0% tổng giá trị PO**.
   - Khoản tiền phạt được khấu trừ trực tiếp vào công nợ của kỳ thanh toán tiếp theo theo biên bản cấn trừ công nợ.
2. **Quyền Hủy Đơn Hàng Đơn Phương Khi Trễ Hạn Nghiêm Trọng:**
   - Nếu nhà cung cấp giao trễ quá **10 ngày làm việc**, ABC Tech Store có toàn quyền đơn phương hủy bỏ PO mà không phải chịu bất kỳ chi phí bồi thường nào.
   - Đồng thời, nhà cung cấp phải bồi thường thêm khoản thiệt hại kinh doanh tương đương **15.0% giá trị hợp đồng** do làm gián đoạn kế hoạch kinh doanh bán lẻ.

---

## 2. Tiêu Chuẩn Nghiệm Thu Chất Lượng AQL & Từ Chối Lô Hàng Lỗi (Batch Rejection)
1. **Tiêu Chuẩn Lấy Mẫu Ngẫu Nhiên MIL-STD-105E:**
   - Khi tiếp nhận lô hàng từ 50 sản phẩm trở lên tại Tổng kho hoặc Chi nhánh:
   - Bộ phận Kiểm soát Chất lượng (QC) tiến hành kiểm tra xác suất lấy mẫu ngẫu nhiên (Sample Inspection).
   - Ngưỡng Giới hạn Chất lượng Cho phép (Acceptance Quality Limit - AQL): **2.0%**.
2. **Cơ Chế Từ Chối Nhận Hàng Toàn Lô (Total Batch Rejection):**
   - Nếu phát hiện tỷ lệ sản phẩm lỗi phần cứng, móp méo bao bì, sai mã SKU hoặc thiếu phụ kiện vượt quá **2.0%** trên tổng số mẫu kiểm tra:
   - Thủ kho trưởng lập biên bản vi phạm và **từ chối tiếp nhận toàn bộ lô hàng (100% lô hàng bị từ chối)**.
   - Nhà cung cấp có nghĩa vụ thu hồi toàn bộ lô hàng trong vòng **48 giờ** và chịu mọi chi phí vận chuyển, bốc dỡ, lưu kho bãi phát sinh.
   - Lô hàng thay thế đạt chuẩn 100% phải được giao bù trong vòng **05 ngày làm việc** tiếp theo.

---

## 3. Chính Sách Bảo Hộ Giá 30 Ngày (Price Protection Guarantee Policy)
1. **Cam Kết Bảo Hộ Giá Bán Lẻ Từ Hãng:**
   - Mọi hợp đồng cung ứng thiết bị công nghệ (Laptop, CPU, VGA, Smartphone) đều bắt buộc bao gồm điều khoản Bảo hộ giá trong vòng **30 ngày** kể từ ngày giao hàng.
2. **Cơ Chế Bù Trừ Chênh Lệch Giá Giảm (Credit Note Rebate):**
   - Nếu nhà sản xuất hoặc nhà phân phối chính thức công bố giảm giá bán lẻ niêm yết của dòng sản phẩm đó trên thị trường:
   - Nhà phân phối có trách nhiệm phát hành Phiếu ghi có (Credit Note) bù trừ khoản chênh lệch giá cho toàn bộ số lượng sản phẩm còn tồn kho chưa bán được tại hệ thống ABC Tech Store tính đến thời điểm công bố giảm giá.
   - Thời gian đối soát và phát hành Credit Note: Tối đa **07 ngày làm việc**.

---

## 4. Kiểm Soát Phê Duyệt Khiếu Nại & Phạt Nhà Cung Cấp (HITL Protocol)
1. Trợ lý AI khi phát hiện PO trễ hạn hoặc biên bản kiểm hàng vượt ngưỡng AQL 2.0% sẽ tự động tính toán số tiền phạt và đề xuất tạo bản ghi Yêu cầu Phê duyệt (`ApprovalRequest`) với mã `supplier_penalty_claim`.
2. Giám đốc Chuỗi cung ứng ký duyệt trên hệ thống `/noibo/approvals/` trước khi phòng Kế toán chính thức gửi công văn yêu cầu khấu trừ tiền phạt tới nhà phân phối.
