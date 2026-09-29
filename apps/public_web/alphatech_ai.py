"""
AI AlphaTech — Chuyên viên Tư vấn & Điều phối Dịch vụ Công nghệ Trực tuyến.
Hệ sinh thái AlphaTech: ABC Tech Store (Bán lẻ thiết bị) & XYZ IT Services (Dịch vụ CNTT).

Đảm bảo:
- Trợ lý tự động; không thay thế xác nhận chính sách từ người phụ trách.
- Nguyên tắc bảo mật nội bộ: Không tiết lộ giá vốn (cost_price), nhà cung cấp, tỷ lệ lợi nhuận hay chi phí nội bộ.
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
            "suggestions": ["Chính sách đổi trả bảo hành", "Yêu cầu kỹ thuật cài đặt", "Liên hệ Hotline hỗ trợ"]
        }
    else:
        return {
            "reply": (
                f"Dạ, AlphaTech không tìm thấy đơn hàng mã `{matched_code}` gắn với tài khoản hoặc phiên duyệt hiện tại của Quý khách.\n\n"
                f"Quý khách vui lòng kiểm tra lại chính xác ký tự mã đơn, hoặc đăng nhập tại "
                f"[Tài khoản khách hàng](/tai-khoan/) để xem toàn bộ danh sách đơn hàng đã mua."
            ),
            "suggestions": ["Đăng nhập xem lịch sử", "Tư vấn sản phẩm mới", "Liên hệ hỗ trợ"]
        }


def handle_authenticity_and_cocq(q_lower):
    """Tư vấn cam kết hàng chính hãng 100%, nguồn gốc xuất xứ CO/CQ và cách kiểm tra Serial/Service Tag."""
    keywords = [
        "chính hãng", "nguồn gốc", "xuất xứ", "co/cq", "co cq", "hàng giả", "hàng nhái",
        "hàng dựng", "mới 100%", "nguyên seal", "fullbox", "serial", "imei", "service tag",
        "kiểm tra máy", "check hãng", "hàng thật", "chất lượng máy", "bồi hoàn", "bồi thường"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = "**Nguồn gốc và giấy tờ sản phẩm**\n\nTôi chưa có hồ sơ đã xác minh để cam kết xuất xứ, CO/CQ hoặc mức bồi hoàn cho từng sản phẩm. Quý khách nên yêu cầu thông tin Serial/Service Tag, chứng từ và điều kiện bảo hành của đúng mã hàng trước khi mua.\n\nVui lòng [liên hệ tư vấn](/lien-he/) hoặc xem [sản phẩm](/san-pham/) để được xác nhận."
    return {
        "reply": reply,
        "suggestions": ["Xem danh mục Laptop Dell", "Hỏi điều kiện bảo hành", "Hệ thống Showroom"]
    }


def handle_installment_procedure(q_lower):
    """Tư vấn chi tiết thủ tục mua hàng trả góp 0% qua Thẻ tín dụng và CCCD gắn chip."""
    keywords = [
        "thủ tục trả góp", "trả góp qua cccd", "căn cước", "hồ sơ trả góp", "home credit",
        "fe credit", "hd saison", "duyệt hồ sơ", "trả trước bao nhiêu", "trả góp 0%",
        "trả góp thẻ tín dụng", "lãi suất trả góp", "hướng dẫn trả góp", "mua góp"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = "**Thông tin mua trả góp**\n\nTôi chưa có chính sách trả góp đã xác minh về đối tác, lãi suất, phí, kỳ hạn hay điều kiện duyệt hồ sơ. Không thể xác nhận trả góp có sẵn tại bước thanh toán.\n\nQuý khách vui lòng [liên hệ tư vấn](/lien-he/) để được xác nhận bằng văn bản trước khi quyết định. Không gửi ảnh CCCD, số thẻ, mật khẩu hay mã OTP trong cuộc trò chuyện này."
    return {
        "reply": reply,
        "suggestions": ["Xem giỏ hàng", "Tư vấn Laptop dưới 20 triệu", "Hotline tư vấn trả góp"]
    }


def handle_return_and_refund(q_lower):
    """Tư vấn chính sách đổi trả theo nhu cầu cá nhân, nhầm cấu hình và quy trình hoàn tiền."""
    keywords = [
        "đổi trả theo nhu cầu", "không thích", "nhầm cấu hình", "trả hàng", "hoàn tiền",
        "phí đổi trả", "trả lại máy", "mua nhầm", "đổi máy khác", "chính sách đổi hàng"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = "**Yêu cầu đổi trả và hoàn tiền**\n\nQuý khách vui lòng chuẩn bị mã đơn hàng và mô tả tình trạng sản phẩm tại [Liên hệ](/lien-he/). Tôi chưa có chính sách đã xác minh để xác nhận thời hạn đổi trả, mức phí hoặc thời gian hoàn tiền cho đơn hàng này. Cần được nhân viên xác nhận điều kiện áp dụng trước khi gửi trả hàng."
    return {
        "reply": reply,
        "suggestions": ["Chính sách bảo hành bảo hành", "Chi nhánh gần nhất", "Tư vấn chọn đúng cấu hình"]
    }


def handle_hardware_upgrade_maintenance(user_query, q_lower):
    """Tư vấn dịch vụ nâng cấp RAM, SSD NVMe lấy liền, vệ sinh máy tính và tra keo tản nhiệt chuyên sâu."""
    keywords = [
        "nâng cấp", "ram", "ssd", "ổ cứng", "vệ sinh", "keo tản nhiệt", "tra keo",
        "nóng máy", "quạt kêu", "mất bảo hành", "bảo dưỡng", "thay ram", "thay ổ cứng",
        "vệ sinh laptop", "vệ sinh máy tính"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = "**Nâng cấp RAM/SSD và vệ sinh máy**\n\nQuý khách có thể gửi model máy và nhu cầu tại [Yêu cầu dịch vụ](/yeu-cau-dich-vu/). Cần được kỹ thuật viên xác nhận tính tương thích, ảnh hưởng đến bảo hành, chi phí và thời gian thực hiện. Tôi chưa có chính sách đã xác minh về bảo dưỡng miễn phí hay linh kiện tặng kèm."
    return {
        "reply": reply,
        "suggestions": ["Đặt lịch kỹ thuật viên", "Địa chỉ trạm kỹ thuật", "Tư vấn phụ kiện máy tính"]
    }


def handle_software_and_remote_support(q_lower):
    """Tư vấn dịch vụ cài đặt phần mềm, Windows bản quyền, chuyển dữ liệu và hỗ trợ từ xa."""
    keywords = [
        "cài win", "windows", "office", "phần mềm", "bản quyền", "chuyển dữ liệu",
        "ultraviewer", "anydesk", "từ xa", "cài lại win", "diệt virus", "hỗ trợ từ xa",
        "cài phần mềm", "cài đặt máy"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = "**Cài đặt phần mềm và chuyển dữ liệu**\n\nQuý khách có thể gửi nhu cầu tại [Yêu cầu dịch vụ](/yeu-cau-dich-vu/). Cần xác nhận phạm vi công việc, chi phí và giấy phép phần mềm trước khi thực hiện; tôi chưa có căn cứ xác nhận máy được tặng bản quyền. Hãy sao lưu dữ liệu cần thiết và không gửi mật khẩu, mã OTP hoặc mã truy cập từ xa vào cuộc trò chuyện."
    return {
        "reply": reply,
        "suggestions": ["Yêu cầu hỗ trợ kỹ thuật", "Tư vấn thiết bị mới", "Bảo hành chính hãng"]
    }


def handle_b2b_corporate_quotation(q_lower):
    """Tư vấn chính sách khách hàng doanh nghiệp, báo giá dự án số lượng lớn và điều khoản công nợ."""
    b2b_direct_keywords = [
        "doanh nghiệp", "b2b", "chiết khấu số lượng", "mua sỉ", "mua số lượng lớn",
        "công nợ", "hợp đồng mua bán", "hợp đồng kinh tế", "nghiệm thu", "procurement",
        "phòng mua hàng", "mua cho công ty", "trang bị công ty", "trang bị cho công ty",
        "dự án công ty", "chính sách b2b", "cung cấp số lượng lớn"
    ]
    is_quotation_request = "báo giá" in q_lower and any(
        k in q_lower for k in ["công ty", "dự án", "số lượng", "b2b", "hợp đồng", "pháp nhân", "sỉ", "đối tác"]
    )
    if not (any(k in q_lower for k in b2b_direct_keywords) or is_quotation_request):
        return None

    reply = "**Yêu cầu báo giá doanh nghiệp B2B**\n\nVui lòng cung cấp loại thiết bị, số lượng và yêu cầu sử dụng qua [Liên hệ](/lien-he/). Tôi chưa có chính sách đã xác minh về chiết khấu, công nợ hoặc thời hạn cấp báo giá. Giá và điều kiện giao dịch cần được nhân viên xác nhận cho yêu cầu cụ thể."
    return {
        "reply": reply,
        "suggestions": ["Gửi yêu cầu báo giá B2B", "Tư vấn Laptop văn phòng", "Dịch vụ IT Outsourcing"]
    }


def handle_privacy_and_data_security(q_lower):
    """Tư vấn cam kết bảo mật dữ liệu riêng tư và an toàn thông tin khách hàng."""
    keywords = [
        "bảo mật dữ liệu", "lộ thông tin", "riêng tư", "bán thông tin", "xem trộm",
        "dữ liệu cá nhân", "quyền riêng tư", "an toàn dữ liệu", "bảo mật thông tin", "iso 27001", "iso27001"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = "**Thông tin bảo mật dữ liệu**\n\nTôi chưa có bằng chứng xác minh chứng nhận ISO 27001 hoặc các cam kết bảo mật tuyệt đối của đơn vị. Không thể xác nhận điều kiện camera, lưu trữ hay mã hóa chỉ từ cuộc trò chuyện này.\n\nTrước khi bàn giao thiết bị, Quý khách nên sao lưu dữ liệu cần thiết và yêu cầu xác nhận phạm vi truy cập, xử lý dữ liệu. Không gửi mật khẩu, mã OTP hoặc tài liệu nhạy cảm ở đây. Có thể [liên hệ](/lien-he/) để yêu cầu chính sách áp dụng."
    return {
        "reply": reply,
        "suggestions": ["Xem trạm kỹ thuật gần nhất", "Quy trình sửa chữa minh bạch", "Liên hệ hỗ trợ"]
    }


def handle_onsite_booking_guide(q_lower):
    """Tư vấn quy trình đặt lịch kỹ thuật viên đến tận nơi, bảng phí minh bạch và hỗ trợ ngoài giờ."""
    # Never intercept emergency network/server outage questions
    if any(k in q_lower for k in ["rớt mạng", "sập server", "khẩn cấp", "p1", "sự cố mạng", "gấp"]):
        return None

    keywords = [
        "đặt lịch tận nơi", "sửa tại nhà", "thợ đến nhà", "on-site", "onsite",
        "chi phí tận nơi", "giá sửa tận nơi", "ngoài giờ", "cuối tuần", "đặt thợ",
        "kỹ thuật viên đến nhà", "đến tận nhà", "sửa tận nhà", "sửa tận nơi", "đặt kỹ thuật",
        "kỹ thuật đến nhà", "kỹ thuật đến tận nhà", "thợ kỹ thuật", "kỹ thuật tận nơi", "đặt lịch sửa",
        "kỹ thuật viên đến tận nơi", "kỹ thuật đến tận nơi"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = "**Yêu cầu kỹ thuật tận nơi**\n\nQuý khách có thể gửi mô tả sự cố, địa điểm và thời gian mong muốn tại [Yêu cầu dịch vụ](/yeu-cau-dich-vu/). Gửi biểu mẫu chưa đồng nghĩa lịch hẹn đã được duyệt. Phạm vi phục vụ, chi phí và thời gian đến cần được nhân viên xác nhận; tôi chưa có bảng phí hay lịch trực đã xác minh."
    return {
        "reply": reply,
        "suggestions": ["Đặt lịch kỹ thuật viên ngay", "Sự cố mạng khẩn cấp ", "Liên hệ hỗ trợ"]
    }


def handle_warranty_and_doa(q_lower):
    """Tư vấn chính sách bảo hành chính hãng và quy chuẩn 1 đổi 1 trong 72h (DOA)."""
    warranty_keywords = [
        "bảo hành", "đổi trả", "doa", "lỗi", "1 đổi 1", "hư", "hỏng", "sửa chữa",
        "chính sách bảo hành", "mượn máy", "bảo hành ở đâu", "thời gian bảo hành"
    ]
    if not any(k in q_lower for k in warranty_keywords):
        return None

    reply = "**Thông tin bảo hành và đổi trả**\n\nĐiều kiện bảo hành cần được kiểm tra theo đúng sản phẩm và chứng từ mua hàng. Tôi chưa có chính sách đã xác minh để cam kết thời hạn, đổi máy ngay hoặc cho mượn máy thay thế.\n\nQuý khách vui lòng gửi mã đơn hàng và mô tả tình trạng tại [Liên hệ](/lien-he/) để được xác nhận điều kiện áp dụng."
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

    reply = "**Thanh toán, giao hàng và hóa đơn VAT**\n\nQuý khách hãy xem phương thức thanh toán và phí giao hàng đang hiển thị tại [Giỏ hàng](/gio-hang/) và bước thanh toán. Tôi chưa có bằng chứng về dịch vụ phát hành hóa đơn VAT tự động hoặc thời hạn giao hỏa tốc.\n\nNếu cần hóa đơn hoặc giao hàng theo yêu cầu, vui lòng [liên hệ](/lien-he/) để được xác nhận. Email xác nhận đơn hàng không thay thế hóa đơn VAT; gửi đơn cũng không đồng nghĩa tiền đã được nhận."
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

    reply = "**Nhu cầu thu cũ đổi mới (Trade-In)**\n\nTôi chưa có chương trình thu cũ hoặc mức trợ giá đã xác minh. Quý khách có thể gửi model và tình trạng thiết bị qua [Liên hệ](/lien-he/) để hỏi khả năng tiếp nhận và định giá. Không nên gửi thiết bị trước khi điều kiện được xác nhận."
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
    lines = ["**Chi nhánh đang được niêm yết:**\n", "Giờ làm việc cần được chi nhánh xác nhận trước khi đến."]
    if branches:
        for b in branches:
            lines.append(
                f"📍 **{b.name}**\n"
                f"   • Địa chỉ: {b.address or 'Chưa cập nhật địa chỉ'}\n"
                f"   • Hotline: `{b.phone or 'Chưa cập nhật số điện thoại'}` (Hỗ trợ bán hàng & kỹ thuật)"
            )
    else:
        lines.append("Chưa có chi nhánh được niêm yết. Vui lòng xem [Liên hệ](/lien-he/).")

    lines.append("\n👉 Quý khách có thể bật định vị GPS để xem gợi ý tuyến đường tại [Bản đồ tương tác Chi nhánh](/chi-nhanh/).")
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

    services = Service.objects.filter(is_active=True, workspace__workspace_type=WorkspaceType.SERVICE)
    srv_matches = []
    for word in user_query.split():
        if len(word) >= 3:
            srv_matches.extend(services.filter(Q(name__icontains=word) | Q(description__icontains=word) | Q(category__icontains=word)))
    matched_services = list({s.id: s for s in srv_matches}.values()) if srv_matches else list(services[:3])

    lines = ["⚡ **Dịch Vụ Kỹ Thuật & Giải Pháp Hạ Tầng CNTT Doanh Nghiệp (XYZ IT Services):**\n"]

    if is_emergency:
        lines.append("**Yêu cầu KHẨN CẤP:** Hãy liên hệ người phụ trách kỹ thuật và mô tả mức độ ảnh hưởng. "
                     "Không tự ngắt hệ thống đang vận hành khi chưa có hướng dẫn của người phụ trách.")
    lines.append("Thời gian phản hồi, xử lý và điều kiện SLA cần được xác nhận cho yêu cầu hoặc hợp đồng cụ thể; "
                 "tôi chưa có lịch trực hay cam kết thời gian đã xác minh.")

    lines.append("📋 **Các gói dịch vụ tiêu biểu:**")
    for s in matched_services[:3]:
        lines.append(
            f"🔹 **{s.name}** ({s.category})\n"
            f"   • [Đặt yêu cầu dịch vụ này](/yeu-cau-dich-vu/?service_id={s.id})"
        )

    lines.append("\n👉 Quý khách có thể gửi mô tả sự cố trực tiếp tại [Biểu mẫu Điều phối Dịch vụ 3 bước](/yeu-cau-dich-vu/) để được xem xét và liên hệ xác nhận.")
    return {
        "reply": "\n".join(lines),
        "suggestions": ["Báo sự cố khẩn cấp ", "Bảo trì hệ thống định kỳ", "Tư vấn cấu hình máy chủ", "Hỏi mua thiết bị"]
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
        advice_lines.append("Các thông tin dưới đây lấy từ danh mục sản phẩm đang niêm yết. Chứng từ xuất xứ cần được xác nhận theo mã hàng.")

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
        advice_lines.append("🌟 **Các sản phẩm đang được niêm yết (tồn kho cần xác nhận):**")
        for p in prod_matches:
            price_str = format_vnd(p.unit_price)
            cat_name = p.category.name if p.category else "Thiết bị"
            advice_lines.append(
                f"• **{p.name}**\n"
                f"  - Mã SKU: `{p.sku}` | Phân khúc: {cat_name}\n"
                f"  - Giá niêm yết: **{price_str}**\n"
                f"  - [Xem chi tiết & Mua ngay](/san-pham/{p.id}/)"
            )

    advice_lines.append(
        "\n**Thông tin trước khi mua:**\n"
        "• Quà tặng và dịch vụ đi kèm cần được xác nhận theo sản phẩm.\n"
        "• Điều kiện thanh toán, giao hàng và tồn kho cần được xác nhận trước khi mua."
    )

    return {
        "reply": "\n".join(advice_lines),
        "suggestions": ["Xem toàn bộ sản phẩm", "Hỏi điều kiện bảo hành", "Dịch vụ IT đi kèm", "Tìm chi nhánh gần nhất"]
    }


def process_alphatech_query(request, user_query):
    """
    Main consultation pipeline for AI AlphaTech.
    Routes queries across 16 customer service, sales, and technical consulting domains.
    """
    if not user_query:
        return {
            "reply": "Xin chào Quý khách! Tôi là **AI AlphaTech**, trợ lý tự động hỗ trợ tìm sản phẩm, dịch vụ, chi nhánh và tra cứu đơn hàng. Với bảo hành, trả góp, hóa đơn hoặc lịch hẹn, tôi sẽ nêu rõ khi chưa có thông tin được xác minh. Quý khách đang cần hỗ trợ nội dung nào?",
            "suggestions": [
                "💻 Tư vấn Laptop theo nhu cầu",
                "⚡ Báo sự cố mạng / Server ",
                "🛡️ Hỏi điều kiện bảo hành (DOA)",
                "💳 Hỏi điều kiện trả góp",
                "🚚 Giao hàng & Hóa đơn VAT",
                "🛠️ Nâng cấp RAM/SSD & Vệ sinh máy",
                "🏢 Báo giá Doanh nghiệp B2B",
                "🔄 Thu cũ đổi mới (Trade-In)",
                "📍 Chi nhánh & Liên hệ",
                "📦 Tra cứu đơn hàng"
            ]
        }

    q_lower = user_query.lower()

    # 1. Order tracking
    res = handle_order_tracking(request, user_query, q_lower)
    if res:
        return res

    # 2. Authenticity, CO/CQ, Serial check
    res = handle_authenticity_and_cocq(q_lower)
    if res:
        return res

    # 3. Installment procedure (0% credit card or CCCD)
    res = handle_installment_procedure(q_lower)
    if res:
        return res

    # 4. Return, Exchange & Refund policy (satisfaction / wrong model)
    res = handle_return_and_refund(q_lower)
    if res:
        return res

    # 5. Hardware upgrade (RAM, SSD) & Cleaning / Thermal paste
    res = handle_hardware_upgrade_maintenance(user_query, q_lower)
    if res:
        return res

    # 6. Software installation, Windows license, Data migration & Remote support
    res = handle_software_and_remote_support(q_lower)
    if res:
        return res

    # 7. B2B Corporate quotations, volume discounts & credit terms
    res = handle_b2b_corporate_quotation(q_lower)
    if res:
        return res

    # 8. Privacy & Data Security guarantee
    res = handle_privacy_and_data_security(q_lower)
    if res:
        return res

    # 9. On-site technician booking & rates guide
    res = handle_onsite_booking_guide(q_lower)
    if res:
        return res

    # 10. Warranty & bảo hành policy
    res = handle_warranty_and_doa(q_lower)
    if res:
        return res

    # 11. Shipping, Payment & VAT
    res = handle_shipping_payment_vat(q_lower)
    if res:
        return res

    # 12. Trade-in Upgrade
    res = handle_trade_in_upgrade(q_lower)
    if res:
        return res

    # 13. Branch Locator & Contact
    res = handle_branch_locator(q_lower)
    if res:
        return res

    # 14. Technical Services & SLA
    res = handle_technical_services(user_query, q_lower)
    if res:
        return res

    # 15. Laptop & Hardware Catalog Consulting
    res = handle_laptop_and_product_consulting(user_query, q_lower)
    if res:
        return res

    # 16. Default courteous guidance
    return {
        "reply": "Xin chào Quý khách! Tôi là **AI AlphaTech**, trợ lý tự động hỗ trợ tìm sản phẩm, dịch vụ, chi nhánh và tra cứu đơn hàng. Với bảo hành, trả góp, hóa đơn hoặc lịch hẹn, tôi sẽ nêu rõ khi chưa có thông tin được xác minh. Quý khách đang cần hỗ trợ nội dung nào?",
        "suggestions": [
            "💻 Tư vấn Laptop theo nhu cầu",
            "💳 Hỏi điều kiện trả góp",
            "🛡️ Hỏi điều kiện bảo hành",
            "🛠️ Nâng cấp RAM/SSD & Vệ sinh",
            "⚡ Báo sự cố mạng ",
            "🏢 Báo giá Doanh nghiệp B2B"
        ]
    }
