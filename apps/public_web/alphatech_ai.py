"""
AI AlphaTech — Chuyên viên Tư vấn & Điều phối Dịch vụ Công nghệ Trực tuyến.
Hệ sinh thái AlphaTech: ABC Tech Store (Bán lẻ thiết bị) & XYZ IT Services (Dịch vụ CNTT).

Đảm bảo:
- Phục vụ khách hàng 24/7 với phong thái chuyên viên tư vấn tận tâm, chu đáo, am hiểu kỹ thuật.
- Tuyệt đối bảo mật: Không tiết lộ giá vốn (cost_price), nhà cung cấp, tỷ lệ lợi nhuận hay chi phí nội bộ.
- Dữ liệu thực tế: Trích xuất sản phẩm, dịch vụ, chi nhánh trực tiếp từ cơ sở dữ liệu.
"""

import re
from decimal import Decimal
from django.db.models import Q
from apps.retail.models import Product, Branch, Order
from apps.service_ops.models import Service, ServiceCategory
from apps.workspaces.models import WorkspaceType


def format_vnd(amount):
    """Format currency nicely to Vietnamese Dong (e.g. 18.500.000₫)."""
    try:
        val = int(amount)
        return f"{val:,}₫".replace(",", ".")
    except Exception:
        return f"{amount}₫"


def handle_order_tracking(request, user_query, q_lower):
    """Xử lý tra cứu tiến độ đơn hàng có bảo mật quyền sở hữu."""
    order_match = re.search(r'(ORD-[A-Z0-9\-]+|[0-9]{5,})', user_query, re.IGNORECASE)
    if not (any(k in q_lower for k in ["đơn hàng", "tra cứu", "vận chuyển", "kiểm tra đơn", "order", "mã đơn", "tiến độ đơn"]) and order_match):
        return None

    matched_code = order_match.group(1).upper()
    from .customer_identity import customer_orders
    if request.user.is_authenticated:
        orders = customer_orders(request.user)
    else:
        orders = Order.objects.filter(
            workspace__workspace_type=WorkspaceType.RETAIL,
            created_by__isnull=True,
            order_number__in=request.session.get("public_order_success_numbers", []),
        )

    order = orders.filter(order_number__iexact=matched_code).first()
    if order:
        items_count = order.items.count()
        status_display = order.get_status_display() if hasattr(order, "get_status_display") else order.status
        total_vnd = format_vnd(order.total_amount)
        created_date = order.created_at.strftime("%d/%m/%Y %H:%M")
        reply = (
            f"📦 **Thông tin tiến độ Đơn hàng {order.order_number}:**\n\n"
            f"• **Trạng thái hiện tại:** `{status_display}`\n"
            f"• **Thời gian đặt hàng:** {created_date}\n"
            f"• **Số lượng sản phẩm:** {items_count} mặt hàng\n"
            f"• **Tổng giá trị thanh toán:** **{total_vnd}**\n\n"
            f"Quý khách có thể xem chi tiết hành trình vận chuyển và cập nhật mới nhất tại "
            f"[Chi tiết đơn hàng](/tai-khoan/don-hang/{order.order_number}/)."
        )
        return {
            "reply": reply,
            "suggestions": ["Chính sách đổi trả DOA 72h", "Yêu cầu kỹ thuật cài đặt", "Liên hệ Hotline hỗ trợ"]
        }
    else:
        return {
            "reply": (
                f"Dạ, AlphaTech không tìm thấy đơn hàng mã `{matched_code}` gắn với tài khoản hoặc phiên duyệt hiện tại của Quý khách.\n\n"
                f"Quý khách vui lòng kiểm tra lại chính xác ký tự mã đơn, hoặc đăng nhập tại "
                f"[Tài khoản khách hàng](/tai-khoan/) để xem toàn bộ danh sách đơn hàng đã mua."
            ),
            "suggestions": ["Đăng nhập xem lịch sử", "Tư vấn sản phẩm mới", "Hotline 1900 6868"]
        }


def handle_warranty_and_doa(q_lower):
    """Tư vấn chính sách bảo hành chính hãng và quy chuẩn 1 đổi 1 trong 72h (DOA)."""
    warranty_keywords = [
        "bảo hành", "đổi trả", "doa", "lỗi", "1 đổi 1", "hư", "hỏng", "sửa chữa",
        "chính sách bảo hành", "mượn máy", "bảo hành ở đâu", "thời gian bảo hành"
    ]
    if not any(k in q_lower for k in warranty_keywords):
        return None

    reply = (
        "🛡️ **Chính Sách Bảo Hành Chính Hãng & Đổi Mới DOA 72H Tại AlphaTech:**\n\n"
        "1. **Chính sách 1 Đổi 1 Trong 72 Giờ (DOA - Dead on Arrival):**\n"
        "   • Nếu thiết bị phát sinh lỗi phần cứng do nhà sản xuất trong vòng **72 giờ đầu tiên**, "
        "AlphaTech cam kết **đổi ngay máy mới 100% nguyên seal**, Quý khách không phải chờ đợi gửi hãng thẩm định lâu ngày.\n\n"
        "2. **Bảo Hành Tiêu Chuẩn Chính Hãng (12 – 36 Tháng):**\n"
        "   • 100% máy tính, laptop và linh kiện đều được bảo hành chính hãng theo đúng tiêu chuẩn nhà sản xuất "
        "(Dell ProSupport, HP Onsite, ASUS VIP Service, Lenovo Premier...).\n"
        "   • Quý khách có thể mang trực tiếp đến bất kỳ Showroom AlphaTech nào hoặc các Trung tâm bảo hành ủy quyền của hãng trên toàn quốc.\n\n"
        "3. **Chính Sách Cho Mượn Thiết Bị Thay Thế (Loaner Policy):**\n"
        "   • Đối với khách hàng doanh nghiệp hoặc laptop làm việc cần gửi hãng xử lý trên 48 giờ, "
        "AlphaTech hỗ trợ **cho mượn máy tính có cấu hình tương đương** để công việc của Quý khách không bị gián đoạn.\n\n"
        "👉 Quý khách có thể mang máy đến [Trạm kỹ thuật gần nhất](/chi-nhanh/) hoặc gọi Tổng đài Bảo hành: `1900 6868` (nhánh 2) để được hỗ trợ tức thì."
    )
    return {
        "reply": reply,
        "suggestions": ["Tìm chi nhánh bảo hành", "Báo sự cố kỹ thuật tận nơi", "Tư vấn Laptop thay thế"]
    }


def handle_shipping_payment_vat(q_lower):
    """Tư vấn phương thức thanh toán, giao hàng hỏa tốc và xuất hóa đơn VAT điện tử."""
    finance_keywords = [
        "thanh toán", "giao hàng", "vận chuyển", "ship", "phí ship", "hóa đơn", "vat",
        "hóa đơn đỏ", "cod", "trả góp", "chuyển khoản", "quẹt thẻ", "pos", "vietqr", "hỏa tốc"
    ]
    if not any(k in q_lower for k in finance_keywords):
        return None

    reply = (
        "💳 **Chính Sách Thanh Toán, Vận Chuyển & Hóa Đơn VAT Điện Tử:**\n\n"
        "1. **Phương Thức Thanh Toán Linh Hoạt:**\n"
        "   • **COD (Thanh toán khi nhận hàng):** Áp dụng tiền mặt tận nơi trên toàn quốc.\n"
        "   • **Chuyển khoản QR Code (VietQR):** Hệ thống tự động xác nhận thanh toán chỉ sau 30 giây.\n"
        "   • **Quẹt thẻ POS:** Hỗ trợ mọi loại thẻ Visa, Mastercard, JCB, Napas tại showroom hoặc tận nơi.\n"
        "   • **Trả góp 0% lãi suất:** Kỳ hạn linh hoạt 3 - 12 tháng qua thẻ tín dụng liên kết hơn 25 ngân hàng.\n\n"
        "2. **Hóa Đơn Điện Tử VAT Hợp Pháp:**\n"
        "   • 100% đơn hàng tại AlphaTech đều xuất hóa đơn VAT điện tử đầy đủ theo chuẩn Tổng cục Thuế.\n"
        "   • Hóa đơn gửi trực tiếp qua email đăng ký của Quý khách trong vòng **24 giờ làm việc**.\n\n"
        "3. **Chính Sách Giao Nhận & Phí Vận Chuyển:**\n"
        "   • 🚚 **MIỄN PHÍ VẬN CHUYỂN TOÀN QUỐC** cho mọi đơn hàng từ **5.000.000₫** trở lên.\n"
        "   • ⚡ **Giao hỏa tốc 2 Giờ:** Áp dụng khu vực nội thành TP.HCM (Quận 1, Tân Bình, Phú Nhuận, Bình Thạnh...).\n"
        "   • 📦 **Giao hàng tiêu chuẩn:** 1 – 3 ngày trên toàn quốc với bảo hiểm hàng hóa nguyên vẹn 100%."
    )
    return {
        "reply": reply,
        "suggestions": ["Xem giỏ hàng hiện tại", "Tư vấn Laptop chính hãng", "Chi nhánh mua trực tiếp"]
    }


def handle_trade_in_upgrade(q_lower):
    """Tư vấn chương trình Thu cũ Đổi mới (Trade-In) trợ giá cao và an toàn dữ liệu."""
    trade_in_keywords = [
        "thu cũ", "đổi mới", "trade-in", "trade in", "lên đời", "bán lại",
        "đổi máy cũ", "thu mua máy cũ", "trợ giá"
    ]
    if not any(k in q_lower for k in trade_in_keywords):
        return None

    reply = (
        "🔄 **Chương Trình Thu Cũ Đổi Mới (Trade-In) Trợ Giá Lên Đời Tại AlphaTech:**\n\n"
        "Chương trình giúp Quý khách nâng cấp thiết bị công nghệ mới với chi phí tiết kiệm nhất:\n\n"
        "• **Mức Trợ Giá Lên Đời:** Hỗ trợ trợ giá thêm **15% – 20%** trên giá trị định giá máy cũ khi Quý khách lên đời máy mới tại showroom.\n"
        "• **Quy Trình Thẩm Định 4 Cấp Độ Nhanh Gọn (15 Phút):**\n"
        "  - *Loại 1 (Like-new):* Thân vỏ đẹp, màn hình hoàn hảo, pin tốt, đầy đủ chức năng.\n"
        "  - *Loại 2 (Trầy xước nhẹ):* Ngoại hình có vết xước nhỏ, linh kiện nguyên bản 100%.\n"
        "  - *Loại 3 (Cấn móp):* Có vết cấn góc, các chức năng phần cứng vẫn vận hành bình thường.\n"
        "  - *Loại 4 (Lỗi linh kiện):* Hỏng pin, phím liệt, màn hình ố nhẹ (vẫn được thu mua theo giá linh kiện).\n"
        "• 🔒 **Cam Kết Zero Data Leak (Bảo Mật Dữ Liệu Tuyệt Đối):**\n"
        "  Kỹ thuật viên sẽ hỗ trợ sao lưu toàn bộ tài liệu sang máy mới, sau đó tiến hành **xóa sạch dữ liệu và Factory Reset an toàn** ngay trước sự chứng kiến của Quý khách.\n\n"
        "👉 Quý khách có thể mang máy đến trực tiếp [Các chi nhánh AlphaTech](/chi-nhanh/) để kỹ thuật viên kiểm tra và báo giá trong 15 phút!"
    )
    return {
        "reply": reply,
        "suggestions": ["Xem danh sách Laptop mới", "Chi nhánh gần nhất", "Hotline tư vấn định giá"]
    }


def handle_branch_locator(q_lower):
    """Cung cấp thông tin chi nhánh, trạm kỹ thuật, giờ mở cửa và hotline."""
    branch_keywords = [
        "chi nhánh", "địa chỉ", "ở đâu", "vị trí", "quận", "hà nội", "hồ chí minh",
        "đà nẵng", "hotline", "gần nhất", "bản đồ", "showroom", "cửa hàng",
        "giờ mở cửa", "thời gian làm việc", "số điện thoại"
    ]
    if not any(k in q_lower for k in branch_keywords):
        return None

    branches = Branch.objects.filter(is_active=True, workspace__workspace_type=WorkspaceType.RETAIL).order_by("name")[:5]
    lines = [
        "🏢 **Hệ Thống Showroom & Trạm Kỹ Thuật AlphaTech (ABC Tech & XYZ IT):**\n",
        "Showroom bán lẻ mở cửa phục vụ Quý khách từ **08:00 – 21:30** hàng ngày (kể cả Thứ Bảy & Chủ Nhật). "
        "Riêng đội ngũ Kỹ thuật viên On-site trực khẩn cấp **24/7/365**.\n"
    ]
    if branches:
        for b in branches:
            lines.append(
                f"📍 **{b.name}**\n"
                f"   • Địa chỉ: {b.address or 'Trung tâm công nghệ TP.HCM'}\n"
                f"   • Hotline: `{b.phone or '1900 6868'}` (Hỗ trợ bán hàng & kỹ thuật)"
            )
    else:
        lines.append("📍 **Flagship Showroom Q.1:** 123 Nguyễn Thị Minh Khai, P. Bến Thành, Quận 1, TP.HCM (`1900 6868`)")
        lines.append("📍 **Trạm Kỹ thuật Tân Bình:** 45 Hoàng Hoa Thám, P. 13, Q. Tân Bình, TP.HCM")
        lines.append("📍 **Trạm Kỹ thuật TP. Thủ Đức:** 78 Võ Văn Ngân, P. Linh Chiểu, TP. Thủ Đức")

    lines.append("\n👉 Quý khách có thể bật định vị GPS để tìm đường đi ngắn nhất tại [Bản đồ tương tác Chi nhánh](/chi-nhanh/).")
    return {
        "reply": "\n".join(lines),
        "suggestions": ["Xem bản đồ chi nhánh", "Đặt hẹn kỹ thuật viên", "Tư vấn Laptop"]
    }


def handle_technical_services(user_query, q_lower):
    """Tư vấn dịch vụ kỹ thuật doanh nghiệp, xử lý sự cố mạng, máy chủ và cam kết SLA < 15 phút."""
    service_keywords = [
        "dịch vụ", "kỹ thuật", "sửa", "cài đặt", "mạng", "bảo trì", "server",
        "máy chủ", "sla", "khẩn cấp", "sự cố", "khắc phục", "it", "rớt mạng",
        "chậm mạng", "tường lửa", "firewall", "database", "postgresql", "nas",
        "active directory", "kỹ sư"
    ]
    if not any(k in q_lower for k in service_keywords):
        return None

    # Determine specific problem focus
    is_emergency = any(k in q_lower for k in ["khẩn cấp", "rớt mạng", "sập", "cứu", "cháy", "treo", "p1", "p0", "ngay"])
    is_server = any(k in q_lower for k in ["server", "máy chủ", "linux", "windows server", "raid"])
    is_maintenance = any(k in q_lower for k in ["bảo trì", "định kỳ", "outsourcing", "helpdesk", "hàng tháng"])

    services = Service.objects.filter(is_active=True, workspace__workspace_type=WorkspaceType.SERVICE)
    srv_matches = []
    for word in user_query.split():
        if len(word) >= 3:
            srv_matches.extend(services.filter(Q(name__icontains=word) | Q(description__icontains=word) | Q(category__icontains=word)))
    matched_services = list({s.id: s for s in srv_matches}.values()) if srv_matches else list(services[:3])

    lines = ["⚡ **Dịch Vụ Kỹ Thuật & Giải Pháp Hạ Tầng CNTT Doanh Nghiệp (XYZ IT Services):**\n"]

    if is_emergency:
        lines.append(
            "🚨 **QUY TRÌNH ỨNG CỨU SỰ CỐ KHẨN CẤP (P1) — CAM KẾT SLA:**\n"
            "• **Phản hồi xác nhận:** Trong vòng **< 15 phút** kể từ khi nhận cuộc gọi/yêu cầu.\n"
            "• **Điều phối kỹ sư On-site:** Có mặt tại văn phòng doanh nghiệp trong **30 – 45 phút** (khu vực nội thành TP.HCM).\n"
            "• **Khuyến nghị sơ cứu ban đầu:** Nếu hệ thống mạng bị nghẽn/tấn công, Quý khách vui lòng ngắt kết nối đường WAN chính, "
            "cô lập switch tầng và không khởi động lại máy chủ để bảo toàn log hệ thống.\n"
        )
    elif is_server:
        lines.append(
            "🖥️ **GIẢI PHÁP MÁY CHỦ & DỮ LIỆU CHUYÊN DỤNG:**\n"
            "• Triển khai chuẩn hóa Windows Server / Ubuntu Linux Server kèm thiết lập bảo mật baseline.\n"
            "• Cấu hình lưu trữ mảng đĩa RAID 1/5/10 chịu lỗi cao, sao lưu dữ liệu tự động chống ransomware.\n"
        )
    elif is_maintenance:
        lines.append(
            "🛠️ **DỊCH VỤ BẢO TRÌ HỆ THỐNG ĐỊNH KỲ (IT HELPDESK OUTSOURCING):**\n"
            "• Vệ sinh phần cứng, kiểm tra sức khỏe ổ cứng máy chủ định kỳ hàng tháng.\n"
            "• Tối ưu hệ thống mạng Wi-Fi Mesh / VLAN văn phòng, vá các lỗ hổng bảo mật mới nhất.\n"
            "• Cam kết đường truyền ổn định 99.9% và báo cáo hiệu suất chi tiết cho ban giám đốc.\n"
        )
    else:
        lines.append(
            "🛡️ **Cam kết SLA chất lượng:** Phản hồi xác nhận trong **< 15 phút** cho mọi sự cố. "
            "Đội ngũ kỹ sư đạt chứng chỉ quốc tế (CCNA, MCSA, LPIC, AWS) trực 24/7.\n"
        )

    lines.append("📋 **Các gói dịch vụ tiêu biểu:**")
    for s in matched_services[:3]:
        lines.append(
            f"🔹 **{s.name}** ({s.category})\n"
            f"   • Mô tả: {s.description[:110]}...\n"
            f"   • [Đặt yêu cầu dịch vụ này](/yeu-cau-dich-vu/?service_id={s.id})"
        )

    lines.append("\n👉 Quý khách có thể gửi mô tả sự cố trực tiếp tại [Biểu mẫu Điều phối Dịch vụ 3 bước](/yeu-cau-dich-vu/) để kỹ sư liên hệ ngay.")
    return {
        "reply": "\n".join(lines),
        "suggestions": ["Báo sự cố khẩn cấp (SLA 15m)", "Bảo trì hệ thống định kỳ", "Tư vấn cấu hình máy chủ", "Hỏi mua thiết bị"]
    }


def handle_laptop_and_product_consulting(user_query, q_lower):
    """
    Tư vấn chuyên sâu cấu hình Laptop, PC và phần cứng theo từng nhu cầu công việc cụ thể:
    - Văn phòng / Kế toán / Học tập
    - Đồ họa 2D-3D / Render dựng phim / Kiến trúc CAD
    - Lập trình viên / Developer / Kỹ sư phần mềm
    - Gaming / Streamer
    - Doanh nhân / Di chuyển mỏng nhẹ
    """
    product_keywords = [
        "sản phẩm", "laptop", "máy tính", "chuột", "phím", "thiết bị", "mua",
        "giá", "hardware", "cấu hình", "tư vấn", "dell", "ram", "ssd", "core",
        "văn phòng", "đồ họa", "render", "thiết kế", "lập trình", "dev", "coder",
        "game", "gaming", "doanh nhân", "mỏng nhẹ"
    ]
    if not any(k in q_lower for k in product_keywords):
        return None

    products = Product.objects.filter(
        is_active=True,
        deleted_at__isnull=True,
        workspace__workspace_type=WorkspaceType.RETAIL,
    ).select_related("category")

    # Detect persona / workflow
    is_office = any(k in q_lower for k in ["văn phòng", "kế toán", "học tập", "word", "excel", "sinh viên"])
    is_design = any(k in q_lower for k in ["đồ họa", "render", "thiết kế", "photoshop", "premiere", "cad", "revit", "3d", "kiến trúc"])
    is_dev = any(k in q_lower for k in ["lập trình", "dev", "coder", "code", "it", "docker", "phần mềm", "visual studio"])
    is_gaming = any(k in q_lower for k in ["game", "gaming", "chơi game", "fps", "stream", "streamer"])
    is_executive = any(k in q_lower for k in ["doanh nhân", "mỏng nhẹ", "cao cấp", "sang", "di chuyển", "nhẹ"])

    advice_lines = ["💻 **Tư Vấn Cấu Hình Máy Tính & Laptop Chuyên Nghiệp — AlphaTech:**\n"]

    if is_design:
        advice_lines.append(
            "🎨 **Dành cho Đồ họa 2D/3D, Dựng phim & Kiến trúc (AutoCAD, 3ds Max, Premiere):**\n"
            "• **Tiêu chuẩn đề xuất:** CPU tối thiểu Intel Core i7/i9 hoặc AMD Ryzen 7/9, RAM từ **32GB trở lên** để đa nhiệm không giật lag.\n"
            "• **Đồ họa:** Card rời chuyên dụng **NVIDIA RTX 40-Series** với VRAM tối thiểu 6GB – 8GB giúp tăng tốc Render và khử răng cưa mượt mà.\n"
            "• **Màn hình:** Chuẩn màu cao đạt tối thiểu **100% sRGB hoặc DCI-P3**, độ phân giải từ 2.5K/4K chống mỏi mắt khi làm việc nhiều giờ.\n"
        )
    elif is_dev:
        advice_lines.append(
            "👨‍💻 **Dành cho Lập trình viên, Kỹ sư phần mềm (Docker, Kubernetes, Mobile Dev):**\n"
            "• **Tiêu chuẩn đề xuất:** RAM tối thiểu **16GB – 32GB** (khuyên dùng 32GB nếu chạy nhiều container Docker hoặc máy ảo Android/iOS).\n"
            "• **Ổ cứng:** SSD NVMe tốc độ cao từ **512GB – 1TB** để build source code và load dự án tức thì.\n"
            "• **Bàn phím & Hệ điều hành:** Hành trình phím sâu, độ nảy tốt, tương thích hoàn hảo cả Windows 11 Pro lẫn Linux Ubuntu song song.\n"
        )
    elif is_gaming:
        advice_lines.append(
            "🎮 **Dành cho Game thủ & Streamer (Esports, AAA Games):**\n"
            "• **Tiêu chuẩn đề xuất:** Màn hình tần số quét cao **144Hz – 240Hz**, độ trễ 1ms cho khung hình phản xạ tức thì.\n"
            "• **Hệ thống tản nhiệt:** Tản nhiệt buồng hơi 2 quạt hiệu năng cao, tối ưu luồng gió giúp duy trì xung nhịp CPU/GPU ổn định khi combat dài giờ.\n"
        )
    elif is_executive:
        advice_lines.append(
            "💼 **Dành cho Doanh nhân, Quản lý (Thường xuyên di chuyển, gặp đối tác):**\n"
            "• **Tiêu chuẩn đề xuất:** Trọng lượng siêu nhẹ **dưới 1.2kg**, vỏ hợp kim Nhôm Magie hoặc sợi Carbon sang trọng, chắc chắn.\n"
            "• **Bảo mật & Tiện ích:** Cảm biến vân tay 1 chạm, camera nhận diện khuôn mặt Windows Hello, pin trâu trên 10 tiếng, sạc nhanh Type-C Power Delivery.\n"
        )
    elif is_office:
        advice_lines.append(
            "📊 **Dành cho Công việc Văn phòng, Kế toán & Học tập:**\n"
            "• **Tiêu chuẩn đề xuất:** Intel Core i5 thế hệ mới, RAM **16GB**, SSD **512GB** khởi động máy trong 5 giây, mở hàng chục tab trình duyệt và file Excel nặng không lo tràn RAM.\n"
            "• **Độ bền:** Bàn phím gõ êm, màn hình IPS chống chói (Anti-Glare), độ bền chuẩn quân đội chịu va đập tốt.\n"
        )
    else:
        advice_lines.append(
            "✨ AlphaTech tự hào là đại lý phân phối ủy quyền chính hãng của các thương hiệu hàng đầu: "
            "**Dell, HP, Lenovo, ASUS, ThinkPad, Apple** với đầy đủ chứng chỉ CO/CQ và bảo hành tại hãng.\n"
        )

    # Search products from database matching query or categories
    prod_matches = []
    keywords = [w for w in user_query.split() if len(w) >= 2]
    q_filter = Q()
    for kw in keywords:
        q_filter |= Q(name__icontains=kw) | Q(description__icontains=kw) | Q(sku__icontains=kw) | Q(category__name__icontains=kw)

    if q_filter:
        prod_matches = list(products.filter(q_filter)[:4])
    if not prod_matches:
        prod_matches = list(products[:4])

    if prod_matches:
        advice_lines.append("🌟 **Các dòng sản phẩm nổi bật có sẵn tại kho:**")
        for p in prod_matches:
            price_str = format_vnd(p.unit_price)
            cat_name = p.category.name if p.category else "Thiết bị"
            advice_lines.append(
                f"• **{p.name}**\n"
                f"  - Mã SKU: `{p.sku}` | Phân khúc: {cat_name}\n"
                f"  - Giá ưu đãi: **{price_str}**\n"
                f"  - [Xem chi tiết & Mua ngay](/san-pham/{p.id}/)"
            )

    advice_lines.append(
        "\n🎁 **Ưu đãi độc quyền tại AlphaTech:**\n"
        "• Tặng kèm Balo chống sốc cao cấp + Chuột không dây chính hãng.\n"
        "• Miễn phí cài đặt phần mềm bản quyền & vệ sinh máy trọn đời.\n"
        "• Hỗ trợ trả góp 0% lãi suất và miễn phí vận chuyển tận nhà."
    )

    return {
        "reply": "\n".join(advice_lines),
        "suggestions": ["Xem toàn bộ sản phẩm", "Chính sách bảo hành 1 đổi 1", "Dịch vụ IT đi kèm", "Tìm chi nhánh gần nhất"]
    }


def process_alphatech_query(request, user_query):
    """
    Main consultation pipeline for AI AlphaTech.
    Routes queries across all customer service and technical consulting domains.
    """
    if not user_query:
        return {
            "reply": (
                "Xin chào Quý khách! Tôi là **AI AlphaTech** – Chuyên viên tư vấn & Điều phối dịch vụ công nghệ của hệ sinh thái ABC Tech Store & XYZ IT Services.\n\n"
                "Tôi luôn sẵn sàng trực tuyến 24/7 để đồng hành cùng Quý khách:\n"
                "1. 💻 **Tư vấn cấu hình máy tính & Laptop:** Lựa chọn đúng nhu cầu (Văn phòng, Đồ họa 3D, Lập trình, Doanh nhân).\n"
                "2. ⚡ **Dịch vụ Kỹ thuật Doanh nghiệp:** Tiếp nhận sự cố khẩn cấp với cam kết SLA phản hồi **< 15 phút**.\n"
                "3. 🛡️ **Chính sách Bảo hành & Đổi trả:** Cam kết **1 đổi 1 trong 72h (DOA)** và bảo hành chính hãng 12-36 tháng.\n"
                "4. 💳 **Thanh toán, Giao hàng & VAT:** Trả góp 0%, miễn phí ship từ 5M, giao hỏa tốc 2h, xuất hóa đơn VAT 24h.\n"
                "5. 🔄 **Thu cũ Đổi mới (Trade-In):** Trợ giá lên đời 15-20%, bảo mật dữ liệu an toàn tuyệt đối.\n"
                "6. 📍 **Hệ thống Chi nhánh & Trạm Kỹ thuật:** Địa chỉ 3 showroom trung tâm và hotline hỗ trợ.\n\n"
                "Quý khách có thể bấm chọn một trong các gợi ý bên dưới hoặc nhập trực tiếp câu hỏi nhé!"
            ),
            "suggestions": [
                "💻 Tư vấn Laptop theo nhu cầu",
                "⚡ Báo sự cố mạng / Server (SLA 15m)",
                "🛡️ Chính sách bảo hành & 1 đổi 1 (DOA)",
                "🚚 Giao hàng & Hóa đơn VAT",
                "🔄 Thu cũ đổi mới (Trade-In)",
                "📍 Chi nhánh & Hotline 24/7",
                "📦 Tra cứu đơn hàng"
            ]
        }

    q_lower = user_query.lower()

    # 1. Order tracking
    res = handle_order_tracking(request, user_query, q_lower)
    if res:
        return res

    # 2. Warranty & DOA
    res = handle_warranty_and_doa(q_lower)
    if res:
        return res

    # 3. Shipping, Payment & VAT
    res = handle_shipping_payment_vat(q_lower)
    if res:
        return res

    # 4. Trade-in Upgrade
    res = handle_trade_in_upgrade(q_lower)
    if res:
        return res

    # 5. Branch Locator & Contact
    res = handle_branch_locator(q_lower)
    if res:
        return res

    # 6. Technical Services & SLA
    res = handle_technical_services(user_query, q_lower)
    if res:
        return res

    # 7. Laptop & Hardware Catalog Consulting
    res = handle_laptop_and_product_consulting(user_query, q_lower)
    if res:
        return res

    # 8. Default courteous guidance
    return {
        "reply": (
            "Dạ, tôi là **AI AlphaTech** – Chuyên viên tư vấn & Điều phối dịch vụ công nghệ của ABC Tech Store & XYZ IT Services.\n\n"
            "Để hỗ trợ Quý khách một cách chu đáo và chính xác nhất, Quý khách vui lòng cho tôi biết thêm chi tiết về nhu cầu của mình:\n\n"
            "• Quý khách đang tìm kiếm **mẫu máy tính/laptop** với ngân sách hay công việc thế nào (Văn phòng, Đồ họa, Gaming, Lập trình)?\n"
            "• Quý khách cần hỗ trợ **sự cố kỹ thuật khẩn cấp** hay bảo trì định kỳ cho công ty (SLA < 15m)?\n"
            "• Quý khách muốn tìm hiểu về **chính sách bảo hành 1 đổi 1 trong 72h**, trả góp 0%, hóa đơn VAT hay chương trình Thu cũ đổi mới?\n\n"
            "Hoặc Quý khách có thể chọn nhanh các chủ đề tư vấn được quan tâm nhiều nhất dưới đây ạ:"
        ),
        "suggestions": [
            "💻 Tư vấn Laptop theo nhu cầu",
            "⚡ Dịch vụ IT khẩn cấp (SLA 15m)",
            "🛡️ Chính sách bảo hành & Đổi trả",
            "📍 Chi nhánh & Hotline hỗ trợ"
        ]
    }
