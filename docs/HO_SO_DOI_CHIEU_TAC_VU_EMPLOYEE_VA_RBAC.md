# Hồ sơ Đối chiếu Tác vụ EMPLOYEE với Đề cương & Ma trận Phân quyền Kỹ thuật viên (Cổng 70)

**Thời điểm lập hồ sơ**: 22/09/2026  
**Căn cứ pháp lý & học thuật**:
- Đề cương Đồ án Tốt nghiệp ngành Hệ thống Thông tin / Kỹ thuật Phần mềm.
- Tài liệu kiến trúc phân quyền: [docs/security-design.md](file:///d:/ai_business_platform/docs/security-design.md) (Mục 2.2).
- Tóm tắt giải pháp đồ án: [docs/project-summary.md](file:///d:/ai_business_platform/docs/project-summary.md) (Mục 2.2 & 3.4).
- Quy chuẩn thiết kế kiểm toán: [docs/PROJECT_CONTEXT.md](file:///d:/ai_business_platform/docs/PROJECT_CONTEXT.md) (Service API & UI contract).
- Tiêu chuẩn nghiệm thu: **Cổng 70** trong [docs/CHECKLIST_97_PROGRESS.md](file:///d:/ai_business_platform/docs/CHECKLIST_97_PROGRESS.md).

---

## 1. Mục đích & Bối cảnh Học thuật

Theo yêu cầu tại **Cổng 70**: *"Đối chiếu tác vụ EMPLOYEE với đề cương. Nhân viên phải làm được đúng tác vụ được mô tả"*, đồ án cần xác lập một ma trận phân quyền thực thi (executable RBAC matrix) chuẩn hóa cho vai trò Nhân viên hoạt động cơ sở (`EMPLOYEE`), đảm bảo hai nguyên tắc bất biến:
1. **Tính đầy đủ theo Đề cương (Functional Sufficiency)**: Nhân viên thuộc phân hệ Bán lẻ (`abc-retail`) và Kỹ thuật viên thuộc phân hệ Dịch vụ (`xyz-service`) phải có đầy đủ thẩm quyền để thực hiện toàn vẹn các tác vụ chuyên môn được giao hàng ngày mà không bị chặn bởi rào cản phân quyền thiếu sót.
2. **Nguyên tắc Quyền Tối thiểu & Phân tách Rủi ro (Principle of Least Privilege & Separation of Concerns)**: Nhân viên không được phép tự ý thay đổi chính sách giá, không được duyệt các khuyến nghị hành động kinh doanh (`approvals.manage_approval`), không được can thiệp vào tài khoản nhân sự khác, và không được xem các báo cáo tài chính/biên lợi nhuận cấp chiến lược của doanh nghiệp (`service.view_analytics`).

---

## 2. Ma trận Đối chiếu Tác vụ EMPLOYEE theo Từng Không gian Làm việc

Dưới mô hình Đa khách thuê logic theo không gian (`Workspace`), một người dùng có thể đảm nhận các vai trò khác nhau tùy theo phân hệ công tác. Vai trò `EMPLOYEE` được chuẩn hóa chi tiết như sau:

| Phân hệ Nghiệp vụ | Vai trò Thực tế | Tác vụ Được phép Thực hiện (Allowed Operations) | Tác vụ Bị nghiêm cấm / Giới hạn Quyền (Denied Operations) | Ràng buộc An toàn Tương ứng |
|---|---|---|---|---|
| **BÁN LẺ (`abc-retail`)** | **Nhân viên Bán hàng / Thu ngân (Retail Store Staff)** | - Tra cứu danh mục sản phẩm, bảng giá niêm yết (`retail.view_product`).<br>- Tra cứu và tạo mới hồ sơ khách hàng (`retail.view_customer`, `retail.manage_customer`).<br>- Lập đơn hàng bán lẻ tại quầy hoặc tiếp nhận đơn hàng (`retail.create_order`, `retail.view_order`).<br>- Tương tác với Trợ lý AI để tra cứu thông số kỹ thuật sản phẩm (`ai.chat`, `knowledge.view_knowledge`).<br>- Xem bản đồ mạng lưới chi nhánh cửa hàng (`retail.view_branch`, `gis.view_spatial_layers`). | - Cấm thay đổi giá bán, chiết khấu hoặc xóa sản phẩm (`retail.manage_product` — chỉ dành cho `MANAGER`/`ADMIN`).<br>- Cấm hủy đơn hàng hoặc can thiệp trạng thái đơn khi đã chốt.<br>- Cấm xem báo cáo doanh thu tài chính tổng hợp (`retail.view_analytics`).<br>- Cấm duyệt thay đổi giá sản phẩm (`approvals.manage_approval`). | Quyền `retail.create_order` cho phép bán hàng; kiểm soát mutation độc lập ngăn chặn gian lận giá. |
| **DỊCH VỤ IT & KỸ THUẬT HIỆN TRƯỜNG (`xyz-service`)** | **Kỹ thuật viên Hiện trường / Điều phối viên Sự cố (Field Technician / Service Desk)** | - Xem danh mục dịch vụ sửa chữa, bảo trì (`service.view_service`).<br>- Tiếp nhận và tạo phiếu sự cố kỹ thuật theo yêu cầu khách hàng (`service.create_request`, `service.view_request`).<br>- **Xem danh sách nhiệm vụ kỹ thuật được phân công (`service.view_task`)**.<br>- **Xem lịch trình điều phối công tác (`service.view_schedule`)**.<br>- **Ghi nhận giờ công lao động thực tế của chính mình trên nhiệm vụ (`log_labor` với quyền tự chủ `emp.user_id == request.user.id`)**.<br>- Tra cứu tài liệu quy trình SOP kỹ thuật nội bộ qua AI (`knowledge.view_knowledge`, `ai.chat`). | - Cấm phân công nhiệm vụ cho kỹ thuật viên khác (`service.assign_request` — dành cho Điều phối viên/`MANAGER`).<br>- Cấm chuyển trạng thái đóng/hủy phiếu (`service.manage_request`).<br>- Cấm tạo/xóa các gói dịch vụ hoặc chỉnh sửa đơn giá chuẩn.<br>- **Cấm xem báo cáo tổng chi phí nhân sự và biên lợi nhuận toàn công ty (`service.view_analytics`)**.<br>- Cấm ghi giờ công thay cho kỹ thuật viên khác (bị chặn bởi ngoại lệ `PermissionDenied`). | Giao diện tự động lọc danh sách nhân sự chọn giờ công (`labor_technicians = [request.user]`); cố tình gửi `emp_id` khác sẽ kích hoạt `raise PermissionDenied("Technicians may only log labor for themselves.")`. |

---

## 3. Ranh giới Xem Chi phí Nhân sự & Lợi nhuận Doanh nghiệp (Cost Visibility Boundary)

Một câu hỏi cốt lõi được nêu tại Cổng 70: *"Ai được xem chi phí lao động?"*:

1. **Ở mức độ Nhiệm vụ cụ thể (Task-level Labor)**:
   - Kỹ thuật viên khi thực hiện nhiệm vụ có quyền xem thông tin giờ công mà bản thân đã ghi nhận (`started_at`, `ended_at`, `duration_minutes`, `notes`).
   - Ràng buộc này được bảo vệ bởi quyền `service.view_task` (cho phép đọc dữ liệu nhiệm vụ và các bản ghi `LaborEntry` trực thuộc nhiệm vụ đó).
2. **Ở mức độ Tổng chi phí Phiếu yêu cầu & Doanh nghiệp (Executive Cost & Profit Analytics)**:
   - Các trường đơn giá giờ công của kỹ thuật viên (`hourly_rate_snapshot`) và tổng chi phí lao động tính toán phía máy chủ (`labor_cost = duration * rate`) được bảo vệ nghiêm ngặt.
   - Các API thống kê tổng chi phí phiếu (`get_service_request_cost_breakdown`), bảng tổng hợp chi phí toàn công ty (`/services/labor-cost/`), và chỉ số tài chính vận hành (`/services/dashboard/`) yêu cầu bắt buộc quyền **`service.view_analytics`**.
   - Quyền `service.view_analytics` **chỉ được cấp cho Quản lý (`MANAGER`) và Quản trị viên (`ADMIN`)**, hoàn toàn không cấp cho `EMPLOYEE` hay `VIEWER`.

---

## 4. Chuẩn hóa Cấu hình Mã nguồn & Tài khoản Demo 4 Vai trò

Nhằm bảo đảm tính đồng bộ 100% giữa tài liệu thuyết minh, mã nguồn gieo dữ liệu demo (`seed_demo.py`) và bộ kiểm thử tự động:

### 4.1 Danh mục Quyền của Vai trò `EMPLOYEE` (`roles_spec["EMPLOYEE"]["perms"]`)
```python
"EMPLOYEE": {
    "desc": "Front-line operational staff (Order creation, customer lookup, task/schedule viewing, self-labor logging).",
    "perms": [
        permission_objs["retail.view_product"],
        permission_objs["retail.view_order"],
        permission_objs["retail.create_order"],
        permission_objs["retail.view_customer"],
        permission_objs["retail.manage_customer"],
        permission_objs["retail.view_branch"],
        permission_objs["service.view_service"],
        permission_objs["service.view_request"],
        permission_objs["service.create_request"],
        permission_objs["service.view_task"],       # Bổ sung theo Cổng 70
        permission_objs["service.view_schedule"],   # Bổ sung theo Cổng 70
        permission_objs["gis.view_spatial_layers"],
        permission_objs["integration.view_datasource"],
        permission_objs["integration.execute_import"],
        permission_objs["mapping.view_mapping"],
        permission_objs["mapping.apply_mapping"],
        permission_objs["knowledge.view_knowledge"],
        permission_objs["ai.chat"],
        permission_objs["forecasting.view_forecast"],
    ],
}
```

### 4.2 Ma trận Tài khoản Demo 4 Vai trò Chuẩn hóa
```text
+-----------------------+-------------------------+-------------------------+
| Tài khoản Demo        | Vai trò tại abc-retail  | Vai trò tại xyz-service |
+-----------------------+-------------------------+-------------------------+
| admin                 | ADMIN (Superuser)       | ADMIN (Superuser)       |
| manager               | MANAGER                 | EMPLOYEE                |
| employee              | EMPLOYEE                | EMPLOYEE (Technician)   |
| viewer                | VIEWER                  | VIEWER                  |
+-----------------------+-------------------------+-------------------------+
```

Với cấu hình này:
- Tài khoản `employee` tại `xyz-service` đóng đúng vai trò một Kỹ thuật viên Hiện trường (`Technician`), có thể đăng nhập, mở màn hình `/services/tasks/`, kiểm tra lịch điều phối `/services/schedules/`, và tự ghi giờ công trên nhiệm vụ được phân công.
- Tài khoản `employee` bị chặn hoàn toàn khi cố tình mở màn hình báo cáo chi phí nhân sự (`/services/labor-cost/`), không thể duyệt các đề xuất đổi giá (`/approvals/`), và không thể xóa dữ liệu danh mục.

---

## 5. Kết luận Kiểm định Cổng 70

Hồ sơ này đã giải quyết triệt để và khép lại toàn bộ các câu hỏi còn bỏ ngỏ của **Cổng 70**:
1. Đối chiếu khớp 100% giữa quyền hạn `EMPLOYEE` với mô tả nhiệm vụ trong đề cương.
2. Phân định ranh giới rành mạch về khả năng xem chi phí (chỉ dành cho `MANAGER`/`ADMIN`).
3. Khóa an toàn tự chủ ghi giờ công kỹ thuật viên được bảo vệ ở cả tầng View và tầng Service.
