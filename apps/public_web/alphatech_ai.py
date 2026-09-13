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


def handle_authenticity_and_cocq(q_lower):
    """Tư vấn cam kết hàng chính hãng 100%, nguồn gốc xuất xứ CO/CQ và cách kiểm tra Serial/Service Tag."""
    keywords = [
        "chính hãng", "nguồn gốc", "xuất xứ", "co/cq", "co cq", "hàng giả", "hàng nhái",
        "hàng dựng", "mới 100%", "nguyên seal", "fullbox", "serial", "imei", "service tag",
        "kiểm tra máy", "check hãng", "hàng thật", "chất lượng máy"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = (
        "✨ **Cam Kết Hàng Chính Hãng 100% & Chứng Nhận Xuất Xứ (CO/CQ) Tại AlphaTech:**\n\n"
        "AlphaTech hiểu rằng chất lượng và nguồn gốc thiết bị là mối quan tâm hàng đầu của Quý khách. Chúng tôi cam kết tuyệt đối:\n\n"
        "1. **100% Máy Mới Nguyên Đai Nguyên Kiện (Brand New Fullbox):**\n"
        "   • Toàn bộ laptop, linh kiện và thiết bị mạng đều là hàng nhập khẩu chính ngạch, nguyên seal nhà sản xuất.\n"
        "   • Đầy đủ chứng nhận xuất xứ **CO (Certificate of Origin)** và chứng nhận chất lượng **CQ (Certificate of Quality)** từ các đối tác hàng đầu (Dell, HP, Lenovo, ASUS, Apple...).\n\n"
        "2. **Hướng Dẫn Kiểm Tra Serial / Service Tag Trực Tuyến:**\n"
        "   • Mỗi thiết bị đều có số Serial/Service Tag riêng biệt in trên thân máy và vỏ hộp trùng khớp 100%.\n"
        "   • Quý khách có thể tự kiểm tra trực tiếp trên trang chủ của hãng (ví dụ `dell.com/support`, `support.hp.com`, `checkcoverage.apple.com`) để xác thực thời hạn bảo hành gốc.\n\n"
        "3. **Cam Kết Bồi Thường 200%:**\n"
        "   • AlphaTech cam kết **bồi hoàn 200% giá trị đơn hàng** nếu Quý khách phát hiện sản phẩm là hàng giả, hàng dựng hoặc linh kiện bị thay thế.\n\n"
        "👉 Quý khách có thể xem đầy đủ danh mục tại [Sản phẩm chính hãng](/san-pham/) hoặc trải nghiệm trực tiếp tại các [Showroom AlphaTech](/chi-nhanh/)."
    )
    return {
        "reply": reply,
        "suggestions": ["Xem danh mục Laptop Dell", "Chính sách bảo hành 1 đổi 1", "Hệ thống Showroom"]
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

    reply = (
        "💳 **Hướng Dẫn & Thủ Tục Mua Hàng Trả Góp 0% Lãi Suất Tại AlphaTech:**\n\n"
        "AlphaTech hợp tác với các tổ chức tài chính hàng đầu để mang đến 2 hình thức trả góp linh hoạt, tiện lợi nhất:\n\n"
        "1. **Hình thức 1: Trả Góp 0% Qua Thẻ Tín Dụng (Credit Card):**\n"
        "   • **Điều kiện:** Sở hữu thẻ tín dụng (Visa, Mastercard, JCB) của hơn 25 ngân hàng liên kết (Techcombank, Vietcombank, VPBank, MB, ACB, HSBC, Sacombank...).\n"
        "   • **Ưu điểm:** **Lãi suất 0%**, không cần chứng minh thu nhập, không giữ giấy tờ, duyệt tự động chỉ sau **3 phút**.\n"
        "   • **Kỳ hạn linh hoạt:** 3, 6, 9, hoặc 12 tháng.\n\n"
        "2. **Hình thức 2: Trả Góp Qua Căn Cước Công Dân (CCCD Gắn Chip):**\n"
        "   • **Đối tác tài chính:** Hỗ trợ qua Home Credit, HD Saison, Mcredit.\n"
        "   • **Hồ sơ đơn giản:** Chỉ cần **CCCD gắn chip** chính chủ (độ tuổi từ 18 – 60 tuổi).\n"
        "   • **Khoản trả trước:** Chỉ từ **10% – 30%** giá trị sản phẩm.\n"
        "   • **Thời gian duyệt:** Xét duyệt hồ sơ online hoặc tại showroom chỉ trong **15 – 20 phút**, nhận máy ngay sau khi duyệt.\n\n"
        "👉 Quý khách có thể lựa chọn phương thức trả góp trực tiếp tại trang [Giỏ hàng & Thanh toán](/gio-hang/) hoặc đến [Showroom gần nhất](/chi-nhanh/) để nhân viên hỗ trợ làm hồ sơ tận tình!"
    )
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

    reply = (
        "🔄 **Chính Sách Đổi Trả Linh Hoạt & Hoàn Tiền Tại AlphaTech:**\n\n"
        "AlphaTech luôn đặt sự hài lòng của khách hàng lên hàng đầu với chính sách đổi trả minh bạch trong **07 ngày đầu tiên**:\n\n"
        "1. **Đổi Sang Dòng Máy Khác (Mua Nhầm Cấu Hình / Nhu Cầu Thay Đổi):**\n"
        "   • Hỗ trợ đổi sang mẫu laptop hoặc cấu hình khác có giá trị tương đương hoặc bù trừ chênh lệch.\n"
        "   • **Miễn phí phí đổi** trong vòng **07 ngày** nếu máy còn nguyên vẹn như lúc xuất kho (đầy đủ hộp, phụ kiện, không trầy xước, không cấn móp).\n\n"
        "2. **Trả Hàng & Hoàn Tiền Theo Nhu Cầu Cá Nhân:**\n"
        "   • Nếu Quý khách không có nhu cầu sử dụng tiếp, áp dụng trả hàng trong 07 ngày với mức phí khấu hao hợp lý **10% – 15%** (chi phí mở hộp đưa về hàng trưng bày demo).\n"
        "   • Số tiền hoàn lại sẽ được chuyển khoản trực tiếp về tài khoản ngân hàng của Quý khách trong vòng **1 – 3 ngày làm việc**.\n\n"
        "3. **Lỗi Kỹ Thuật Nhà Sản Xuất (Chính sách DOA 72H):**\n"
        "   • Nếu máy phát sinh lỗi phần cứng do nhà sản xuất trong 72 giờ đầu, Quý khách được **1 đổi 1 máy mới 100% nguyên seal hoàn toàn miễn phí**.\n\n"
        "👉 Để được hỗ trợ thủ tục đổi trả nhanh nhất, Quý khách vui lòng liên hệ hotline: `1900 6868` (nhánh 2) hoặc mang máy đến bất kỳ [Chi nhánh AlphaTech](/chi-nhanh/)."
    )
    return {
        "reply": reply,
        "suggestions": ["Chính sách bảo hành DOA 72h", "Chi nhánh gần nhất", "Tư vấn chọn đúng cấu hình"]
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

    reply = (
        "🛠️ **Dịch Vụ Nâng Cấp Phần Cứng, Vệ Sinh & Bảo Dưỡng Máy Tính — AlphaTech:**\n\n"
        "1. **Nâng Cấp RAM & Ổ Cứng SSD NVMe Lấy Liền (15 – 30 Phút):**\n"
        "   • **Linh kiện chuẩn hãng:** Sử dụng RAM/SSD chính hãng từ Samsung, Kingston, Crucial, WD với tốc độ đọc/ghi cao, bảo hành linh kiện **36 tháng**.\n"
        "   • **Trực quan & Minh bạch:** Quý khách ngồi quan sát kỹ thuật viên thao tác trực tiếp tại quầy dịch vụ mở.\n"
        "   • **Bảo toàn bảo hành gốc:** Thao tác chuẩn mực theo tài liệu hướng dẫn tháo lắp của hãng (Dell, HP, ASUS), dán tem niêm phong kỹ thuật AlphaTech, **không làm mất bảo hành chính hãng** của máy.\n\n"
        "2. **Dịch Vụ Vệ Sinh Máy Chuyên Sâu & Tra Keo Tản Nhiệt Cao Cấp:**\n"
        "   • Thổi sạch bụi bẩn khe tản nhiệt, vệ sinh quạt làm mát, tra dầu bôi trơn trục quạt.\n"
        "   • Tra keo tản nhiệt cao cấp nhập khẩu (**Arctic MX-4 / Thermal Grizzly**) giúp nhiệt độ CPU/GPU giảm sâu từ **10°C – 15°C**, máy vận hành êm ái, kéo dài tuổi thọ linh kiện.\n"
        "   • 🎁 **Đặc quyền:** **MIỄN PHÍ vệ sinh máy trọn đời** cho toàn bộ laptop và PC mua tại hệ thống AlphaTech!\n\n"
        "👉 Quý khách có thể mang máy qua [Trạm kỹ thuật AlphaTech gần nhất](/chi-nhanh/) hoặc gửi yêu cầu tại [Đặt lịch dịch vụ](/yeu-cau-dich-vu/)!"
    )
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

    reply = (
        "💻 **Dịch Vụ Cài Đặt Phần Mềm, Windows Bản Quyền & Hỗ Trợ Kỹ Thuật Từ Xa:**\n\n"
        "1. **Cài Đặt Hệ Điều Hành & Phần Mềm Chuẩn Sạch:**\n"
        "   • 100% máy xuất xưởng được kỹ thuật viên kích hoạt bản quyền Windows 11 Pro sạch, không chứa phần mềm rác (bloatware).\n"
        "   • Cài đặt sẵn bộ ứng dụng thiết yếu: Bộ gõ tiếng Việt Unikey, trình duyệt web, phần mềm nén file, bộ ứng dụng văn phòng cơ bản hoàn toàn miễn phí.\n"
        "   • Hỗ trợ tư vấn và cài đặt phần mềm bảo mật diệt virus bản quyền (Kaspersky, Microsoft Defender for Endpoint).\n\n"
        "2. **Dịch Vụ Sao Lưu & Chuyển Dữ Liệu Tốc Độ Cao (Data Migration):**\n"
        "   • Kỹ thuật viên hỗ trợ chuyển toàn bộ tài liệu làm việc, hình ảnh, tài khoản email và bookmarks trình duyệt từ máy tính cũ sang máy tính mới an toàn, không lo thất thoát dữ liệu.\n\n"
        "3. **Hỗ Trợ Kỹ Thuật Trực Tuyến Từ Xa 24/7:**\n"
        "   • Đội ngũ kỹ sư trực tuyến hỗ trợ kết nối từ xa qua **UltraViewer / AnyDesk** để xử lý nhanh các sự cố phần mềm, cấu hình máy in, chia sẻ mạng nội bộ mà Quý khách không cần mang máy ra showroom.\n\n"
        "👉 Quý khách cần hỗ trợ gấp vui lòng gọi Hotline kỹ thuật: `1900 6868` (nhánh 2) hoặc gửi tin nhắn tại đây để chuyên viên hướng dẫn!"
    )
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

    reply = (
        "🏢 **Chính Sách Khách Hàng Doanh Nghiệp (B2B) & Dự Án CNTT — AlphaTech:**\n\n"
        "AlphaTech là đối tác cung cấp thiết bị và giải pháp hạ tầng CNTT tin cậy cho hơn 500+ doanh nghiệp tại Việt Nam:\n\n"
        "1. **Chính Sách Chiết Khấu Bậc Thang Cực Kỳ Ưu Đãi:**\n"
        "   • Chiết khấu trực tiếp từ **5% đến 12%** trên giá niêm yết cho các đơn hàng trang bị số lượng từ 3 máy trở lên.\n"
        "   • Tặng kèm gói bảo trì hệ thống và hỗ trợ kỹ thuật tận nơi trị giá lên đến 10.000.000₫.\n\n"
        "2. **Cung Cấp Bảng Báo Giá Chính Thức (Quotation/BOM) Trong 30 Phút:**\n"
        "   • Phòng giải pháp B2B sẵn sàng xuất bảng chào giá cạnh tranh kèm đầy đủ thông số kỹ thuật, dấu mộc tròn pháp nhân chỉ sau **30 phút** nhận yêu cầu.\n\n"
        "3. **Chính Sách Công Nợ Linh Hoạt (15 – 30 Ngày):**\n"
        "   • Hỗ trợ kỳ hạn thanh toán công nợ từ **15 đến 30 ngày** cho các doanh nghiệp ký kết hợp đồng cung ứng định kỳ.\n\n"
        "4. **Đầy Đủ Hồ Sơ Chứng Từ Chuẩn Kế Toán:**\n"
        "   • Cung cấp Hợp đồng kinh tế, Hóa đơn VAT điện tử, Biên bản giao nhận và nghiệm thu thiết bị theo đúng quy định pháp luật.\n\n"
        "📩 **Kênh tiếp nhận dành riêng cho Doanh nghiệp:**\n"
        "• Email: `b2b@alphatech.vn` | Hotline chuyên trách B2B: `1900 6868` (nhánh 3)\n"
        "• Hoặc Quý khách có thể để lại nhu cầu tại [Biểu mẫu yêu cầu dịch vụ](/yeu-cau-dich-vu/) để chuyên viên B2B gọi lại ngay!"
    )
    return {
        "reply": reply,
        "suggestions": ["Gửi yêu cầu báo giá B2B", "Tư vấn Laptop văn phòng", "Dịch vụ IT Outsourcing"]
    }


def handle_privacy_and_data_security(q_lower):
    """Tư vấn cam kết bảo mật dữ liệu riêng tư và an toàn thông tin khách hàng."""
    keywords = [
        "bảo mật dữ liệu", "lộ thông tin", "riêng tư", "bán thông tin", "xem trộm",
        "dữ liệu cá nhân", "quyền riêng tư", "an toàn dữ liệu", "bảo mật thông tin"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = (
        "🔒 **Cam Kết Bảo Mật Dữ Liệu & Quyền Riêng Tư Của Khách Hàng — AlphaTech:**\n\n"
        "Chúng tôi thấu hiểu rằng dữ liệu trong máy tính là tài sản vô giá và mang tính riêng tư cao của Quý khách. AlphaTech áp dụng quy trình an toàn thông tin chuẩn **ISO 27001**:\n\n"
        "1. **Quy Tắc Tuyệt Đối Không Xâm Phạm Dữ Liệu Khách Hàng:**\n"
        "   • Kỹ thuật viên chỉ được phép kiểm tra các thông số phần cứng và chức năng hệ thống theo biên bản yêu cầu của khách hàng.\n"
        "   • Tuyệt đối **nghiêm cấm sao chép, truy cập hoặc phát tán** bất kỳ hình ảnh, tin nhắn, tài liệu cá nhân nào trong máy.\n\n"
        "2. **Khu Vực Kỹ Thuật Mở & Giám Sát Camera 24/7:**\n"
        "   • Phòng kỹ thuật được thiết kế vách kính trong suốt, Quý khách hoàn toàn có thể ngồi trực tiếp theo dõi từng thao tác sửa chữa.\n"
        "   • Hệ thống camera an ninh độ nét cao ghi hình liên tục 24/7 và lưu trữ dữ liệu 90 ngày để phục vụ đối soát minh bạch.\n\n"
        "3. **Cam Kết Bảo Vệ Dữ Liệu Cá Nhân:**\n"
        "   • Thông tin cá nhân (Họ tên, số điện thoại, địa chỉ, lịch sử đơn hàng) được mã hóa trong cơ sở dữ liệu và **cam kết 100% không bao giờ chia sẻ hay bán cho bên thứ ba**.\n\n"
        "Quý khách hoàn toàn yên tâm gửi gắm thiết bị tại [Các trung tâm dịch vụ AlphaTech](/chi-nhanh/)!"
    )
    return {
        "reply": reply,
        "suggestions": ["Xem trạm kỹ thuật gần nhất", "Quy trình sửa chữa minh bạch", "Hotline 1900 6868"]
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
        "kỹ thuật đến nhà", "kỹ thuật đến tận nhà", "thợ kỹ thuật", "kỹ thuật tận nơi", "đặt lịch sửa"
    ]
    if not any(k in q_lower for k in keywords):
        return None

    reply = (
        "🛵 **Quy Trình Đặt Lịch Kỹ Thuật Viên Phục Vụ Tận Nơi (On-Site IT Service):**\n\n"
        "Nhằm tiết kiệm thời gian cho Quý khách, AlphaTech cung cấp dịch vụ kỹ thuật viên lưu động đến tận nhà hoặc văn phòng công ty:\n\n"
        "1. **Quy Trình Đặt Lịch Nhanh Chóng Trong 3 Bước:**\n"
        "   • **Bước 1:** Quý khách điền thông tin sự cố tại [Biểu mẫu Điều phối Dịch vụ](/yeu-cau-dich-vu/) hoặc gọi Hotline `1900 6868`.\n"
        "   • **Bước 2:** Chuyên viên kỹ thuật liên hệ xác nhận tình trạng, chuẩn bị thiết bị thay thế và hẹn giờ chính xác trong **15 phút**.\n"
        "   • **Bước 3:** Kỹ thuật viên có mặt tại địa chỉ của Quý khách theo đúng lịch hẹn (hỗ trợ hỏa tốc trong **30 – 45 phút** với các sự cố khẩn cấp).\n\n"
        "2. **Bảng Phí Minh Bạch & Không Phát Sinh Phí Ẩn:**\n"
        "   • Phí kiểm tra và xử lý sự cố cơ bản tại chỗ: chỉ từ **150.000₫ – 350.000₫** tùy khu vực.\n"
        "   • **Quy tắc vàng:** Kỹ thuật viên luôn kiểm tra, giải thích nguyên nhân và báo giá chi tiết trước. Quý khách đồng ý mới tiến hành xử lý.\n\n"
        "3. **Linh Hoạt Ngoài Giờ & Cuối Tuần:**\n"
        "   • Đội ngũ kỹ thuật viên phục vụ tất cả các ngày trong tuần (kể cả Thứ Bảy, Chủ Nhật) và hỗ trợ ngoài giờ hành chính đến **21:00**.\n\n"
        "👉 Quý khách có thể gửi yêu cầu ngay tại [Form Điều Phối Kỹ Thuật 3 Bước](/yeu-cau-dich-vu/) để được xếp lịch sớm nhất!"
    )
    return {
        "reply": reply,
        "suggestions": ["Đặt lịch kỹ thuật viên ngay", "Sự cố mạng khẩn cấp (SLA 15m)", "Hotline 1900 6868"]
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
    Routes queries across 16 customer service, sales, and technical consulting domains.
    """
    if not user_query:
        return {
            "reply": (
                "Xin chào Quý khách! Tôi là **AI AlphaTech** – Chuyên viên tư vấn & Điều phối dịch vụ công nghệ của hệ sinh thái ABC Tech Store & XYZ IT Services.\n\n"
                "Tôi luôn sẵn sàng trực tuyến 24/7 để đồng hành cùng Quý khách:\n"
                "1. 💻 **Tư vấn cấu hình Laptop & PC:** Lựa chọn theo đúng nhu cầu (Văn phòng, Đồ họa 3D, Lập trình, Doanh nhân).\n"
                "2. ⚡ **Dịch vụ Kỹ thuật Doanh nghiệp:** Tiếp nhận sự cố khẩn cấp với cam kết SLA phản hồi **< 15 phút**.\n"
                "3. 🛡️ **Bảo hành & 1 Đổi 1 trong 72h (DOA):** 100% hàng chính hãng CO/CQ, chính sách cho mượn máy thay thế.\n"
                "4. 💳 **Trả góp 0% & Thanh toán linh hoạt:** Trả góp qua thẻ tín dụng hoặc CCCD gắn chip, duyệt hồ sơ 15 phút.\n"
                "5. 🚚 **Giao hàng hỏa tốc 2h & Hóa đơn VAT:** Miễn phí ship toàn quốc từ 5M, xuất hóa đơn VAT điện tử 24h.\n"
                "6. 🛠️ **Nâng cấp RAM/SSD & Vệ sinh máy:** Linh kiện chính hãng lấy liền 30 phút, vệ sinh tra keo tản nhiệt MX-4.\n"
                "7. 🏢 **Báo giá Khách hàng Doanh nghiệp B2B:** Chiết khấu bậc thang 5-12%, cấp bảng chào giá sau 30 phút, công nợ linh hoạt.\n"
                "8. 🔄 **Thu cũ Đổi mới (Trade-In):** Trợ giá lên đời 15-20%, cam kết bảo mật xóa dữ liệu Zero Data Leak.\n"
                "9. 📍 **Hệ thống Chi nhánh & Hotline 24/7:** Showroom mở cửa 08:00 - 21:30, hotline hỗ trợ 1900 6868.\n\n"
                "Quý khách có thể bấm chọn một trong các gợi ý bên dưới hoặc nhập trực tiếp câu hỏi nhé!"
            ),
            "suggestions": [
                "💻 Tư vấn Laptop theo nhu cầu",
                "⚡ Báo sự cố mạng / Server (SLA 15m)",
                "🛡️ Chính sách bảo hành & 1 đổi 1 (DOA)",
                "💳 Trả góp 0% qua CCCD / Thẻ",
                "🚚 Giao hàng & Hóa đơn VAT",
                "🛠️ Nâng cấp RAM/SSD & Vệ sinh máy",
                "🏢 Báo giá Doanh nghiệp B2B",
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

    # 10. Warranty & DOA 72h policy
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
        "reply": (
            "Dạ, tôi là **AI AlphaTech** – Chuyên viên tư vấn & Điều phối dịch vụ công nghệ của ABC Tech Store & XYZ IT Services.\n\n"
            "Để hỗ trợ Quý khách một cách chu đáo và chính xác nhất, Quý khách vui lòng cho tôi biết thêm chi tiết về nhu cầu của mình:\n\n"
            "• Quý khách đang tìm kiếm **mẫu máy tính/laptop** với ngân sách hay công việc thế nào (Văn phòng, Đồ họa, Gaming, Lập trình)?\n"
            "• Quý khách cần **mua trả góp 0%**, xin **báo giá doanh nghiệp B2B**, hay muốn **nâng cấp RAM/SSD/vệ sinh máy**?\n"
            "• Quý khách cần hỗ trợ **sự cố kỹ thuật khẩn cấp** tại văn phòng hay đặt lịch kỹ thuật viên đến tận nơi (SLA < 15m)?\n"
            "• Quý khách muốn tìm hiểu về **chính sách bảo hành 1 đổi 1 (DOA 72h)**, đổi trả linh hoạt hay xuất hóa đơn VAT điện tử?\n\n"
            "Hoặc Quý khách có thể chọn nhanh các chủ đề tư vấn được quan tâm nhiều nhất dưới đây ạ:"
        ),
        "suggestions": [
            "💻 Tư vấn Laptop theo nhu cầu",
            "💳 Trả góp 0% qua CCCD / Thẻ",
            "🛡️ Chính sách bảo hành & 1 đổi 1",
            "🛠️ Nâng cấp RAM/SSD & Vệ sinh",
            "⚡ Báo sự cố mạng (SLA 15m)",
            "🏢 Báo giá Doanh nghiệp B2B"
        ]
    }
