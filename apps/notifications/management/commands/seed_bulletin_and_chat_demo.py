"""
Management command to seed realistic demo data for:
1. Internal Bulletin Board (Bảng tin Điều hành Nội bộ)
2. Workspace Team Chat (Kênh Trao đổi Nội bộ Nhân sự)
Supports multi-tenant isolation across Retail and Service workspaces.
Idempotent and safe to run multiple times.
"""

import sys
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import User
from apps.workspaces.models import Workspace, WorkspaceType
from apps.notifications.models import (
    InternalBulletin,
    BulletinPriority,
    TeamChatMessage,
)


class Command(BaseCommand):
    help = "Seed realistic demo bulletins and team chat messages for Retail and Service workspaces."

    def handle(self, *args, **options):
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError, ValueError):
                self.stderr.write("STDOUT_UTF8_RECONFIGURE_FAILED")

        self.stdout.write("--- Seed Demo: Internal Bulletins & Team Chat ---")

        # 1. Resolve Workspaces
        ws_retail = Workspace.objects.filter(workspace_type=WorkspaceType.RETAIL).first()
        ws_service = Workspace.objects.filter(workspace_type=WorkspaceType.SERVICE).first()

        if not ws_retail and not ws_service:
            self.stdout.write(self.style.WARNING("Chưa tìm thấy Workspace nào. Vui lòng chạy `python manage.py seed_demo` trước."))
            return

        # 2. Resolve Key Users
        admin_user = User.objects.filter(username="admin").first() or User.objects.filter(is_superuser=True).first()
        manager_user = User.objects.filter(username="manager").first() or admin_user
        employee_user = User.objects.filter(username="employee").first() or admin_user
        viewer_user = User.objects.filter(username="viewer").first() or employee_user

        if not admin_user:
            self.stdout.write(self.style.WARNING("Chưa tìm thấy người dùng quản trị để gán tác giả."))
            return

        now = timezone.now()

        # =====================================================================
        # 3. SEED RETAIL WORKSPACE (ABC Tech Store)
        # =====================================================================
        if ws_retail:
            self.stdout.write(f"Đang tạo dữ liệu cho Không gian Bán lẻ: {ws_retail.name} ({ws_retail.code})...")

            # Retail Bulletins
            retail_bulletins = [
                {
                    "title": "Quy chế kiểm kê hàng hóa định kỳ & Chuẩn an toàn thông tin khách hàng Q3",
                    "content": (
                        "Ban Giám đốc thông báo kế hoạch kiểm kê toàn diện quý 3/2026 bắt đầu từ 21h00 thứ Sáu.\n"
                        "- Toàn thể nhân viên bán hàng và thủ kho quét mã vạch đối soát 100% SKU trên hệ thống.\n"
                        "- Nghiêm cấm trích xuất thông tin số điện thoại hoặc lịch sử mua hàng của khách hàng sang thiết bị cá nhân.\n"
                        "- Mọi trường hợp chênh lệch tồn kho thực tế vượt quá 0.5% phải lập biên bản giải trình chi tiết."
                    ),
                    "priority": BulletinPriority.PINNED,
                    "pinned_until": now + timedelta(days=30),
                    "views_count": 42,
                    "author": manager_user or admin_user,
                },
                {
                    "title": "Cảnh báo tồn kho: Điều phối nguồn cung iPhone 16 Pro Max giữa các chi nhánh",
                    "content": (
                        "Phân hệ Dự báo AI ghi nhận nguy cơ đứt hàng dòng iPhone 16 Pro Max 256GB tại Chi nhánh Quận 1 trong 48 giờ tới.\n"
                        "- Bộ phận điều phối kho lập tức xuất chuyển 15 máy từ Kho tổng Thủ Đức sang Quận 1 trước 14h00 hôm nay.\n"
                        "- Thu ngân ưu tiên xuất hàng cho các đơn hàng đã đặt cọc và xác nhận giao tại cửa hàng."
                    ),
                    "priority": BulletinPriority.URGENT,
                    "pinned_until": now + timedelta(days=7),
                    "views_count": 28,
                    "author": manager_user or admin_user,
                },
                {
                    "title": "Chương trình ưu đãi thanh toán số qua VNPay-QR và Thẻ tín dụng tháng 9",
                    "content": (
                        "Nhằm kích cầu tiêu dùng và nâng cao trải nghiệm mua sắm không tiền mặt:\n"
                        "- Khách hàng thanh toán qua mã VNPay-QR được giảm trực tiếp 5% (tối đa 200.000 VNĐ).\n"
                        "- Nhân viên quầy tư vấn hướng dẫn khách hàng quét mã trực tiếp trên màn hình POS của cửa hàng.\n"
                        "- Chiết khấu tự động ghi nhận vào báo cáo doanh thu theo ca làm việc."
                    ),
                    "priority": BulletinPriority.NORMAL,
                    "pinned_until": None,
                    "views_count": 15,
                    "author": admin_user,
                },
            ]

            for b_data in retail_bulletins:
                b, created = InternalBulletin.objects.get_or_create(
                    workspace=ws_retail,
                    title=b_data["title"],
                    defaults={
                        "author": b_data["author"],
                        "content": b_data["content"],
                        "priority": b_data["priority"],
                        "pinned_until": b_data["pinned_until"],
                        "views_count": b_data["views_count"],
                        "is_published": True,
                    },
                )
                status_str = "Đã tạo mới" if created else "Đã tồn tại"
                self.stdout.write(f"  [{status_str}] Bản tin: {b.title[:45]}...")

            # Retail Team Chat
            retail_chat = [
                (manager_user, "Chào cả team bán lẻ, hôm nay kho tổng vừa về lô phụ kiện và MacBook Air M3 mới nhé."),
                (employee_user, "Dạ em đã nhận phiếu nhập kho điện tử trên hệ thống rồi ạ, đang kiểm đếm số lượng."),
                (manager_user, "Nhớ kiểm tra kỹ tem niêm phong và chụp ảnh lưu lại trước khi nhập vào kệ trưng bày."),
                (employee_user, "Vâng anh! Chi nhánh Quận 1 có khách hàng vừa đặt đơn online giao gấp trong chiều nay ạ."),
                (manager_user, "Được em, duyệt đơn ngay và chọn đối tác vận chuyển hỏa tốc nhé!"),
            ]

            for sender, msg in retail_chat:
                if sender:
                    TeamChatMessage.objects.get_or_create(
                        workspace=ws_retail,
                        sender=sender,
                        message=msg,
                    )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Đã nạp hội thoại trao đổi cho Workspace {ws_retail.name}."))

        # =====================================================================
        # 4. SEED SERVICE WORKSPACE (XYZ IT Services)
        # =====================================================================
        if ws_service:
            self.stdout.write(f"\nĐang tạo dữ liệu cho Không gian Dịch vụ Kỹ thuật: {ws_service.name} ({ws_service.code})...")

            # Service Bulletins
            service_bulletins = [
                {
                    "title": "Quy trình ứng cứu sự cố hạ tầng Cloud & Cam kết SLA khẩn cấp P1",
                    "content": (
                        "Khung vận hành kỹ thuật áp dụng cam kết SLA mới cho toàn bộ hợp đồng dịch vụ doanh nghiệp:\n"
                        "- Sự cố mức độ Khẩn cấp (P1): Kỹ thuật viên phải phản hồi tiếp nhận trong vòng 15 phút và có mặt tại hiện trường/truy cập từ xa trong tối đa 45 phút.\n"
                        "- Mọi can thiệp vào máy chủ cơ sở dữ liệu production đều phải ghi log và được quản lý phê duyệt qua module Audit."
                    ),
                    "priority": BulletinPriority.PINNED,
                    "pinned_until": now + timedelta(days=45),
                    "views_count": 36,
                    "author": manager_user or admin_user,
                },
                {
                    "title": "Kế hoạch nâng cấp Firmware hệ thống Switch Cisco Core cho khách hàng TechCorp",
                    "content": (
                        "Thông báo tới nhóm Kỹ sư hạ tầng mạng:\n"
                        "- Thời gian thực hiện: 23h00 ngày 25/09 đến 03h00 ngày 26/09.\n"
                        "- Yêu cầu backup cấu hình chạy (running-config) ra máy chủ lưu trữ an toàn trước khi nạp image mới.\n"
                        "- Test kiểm thử kết nối VPN và đường truyền thoại IP sau khi khởi động lại thiết bị."
                    ),
                    "priority": BulletinPriority.NORMAL,
                    "pinned_until": None,
                    "views_count": 19,
                    "author": admin_user,
                },
                {
                    "title": "Chương trình chứng chỉ kỹ thuật viên Cloud AWS/Azure đợt 2/2026",
                    "content": (
                        "Công ty tài trợ 100% chi phí thi chứng chỉ quốc tế cho các kỹ thuật viên đạt đánh giá hiệu suất loại A.\n"
                        "- Các kỹ thuật viên đăng ký nguyện vọng qua Quản lý trực tiếp trước ngày 30/09.\n"
                        "- Ưu tiên chứng chỉ Quản trị hệ thống Cloud và An toàn thông tin mạng."
                    ),
                    "priority": BulletinPriority.NORMAL,
                    "pinned_until": None,
                    "views_count": 22,
                    "author": manager_user or admin_user,
                },
            ]

            for b_data in service_bulletins:
                b, created = InternalBulletin.objects.get_or_create(
                    workspace=ws_service,
                    title=b_data["title"],
                    defaults={
                        "author": b_data["author"],
                        "content": b_data["content"],
                        "priority": b_data["priority"],
                        "pinned_until": b_data["pinned_until"],
                        "views_count": b_data["views_count"],
                        "is_published": True,
                    },
                )
                status_str = "Đã tạo mới" if created else "Đã tồn tại"
                self.stdout.write(f"  [{status_str}] Bản tin: {b.title[:45]}...")

            # Service Team Chat
            service_chat = [
                (manager_user, "Các bạn kỹ thuật chú ý: Phiếu yêu cầu #SR-1002 của khách hàng Alpha đang báo lỗi ngắt mạng chập chờn."),
                (employee_user, "Em đã liên hệ với IT bên Alpha rồi anh, em đang kiểm tra log trên router Fortinet từ xa."),
                (employee_user, "Phát hiện port quang số 4 có tỷ lệ drop gói tin cao, có thể dây nhảy quang bị suy hao."),
                (manager_user, "Tốt lắm, mang theo module quang và dây nhảy dự phòng đến tận nơi thay thế ngay nhé. Nhớ tuân thủ SLA P2 dưới 2 giờ!"),
                (employee_user, "Rõ anh, em xuất kho vật tư và di chuyển qua văn phòng khách hàng ngay bây giờ."),
            ]

            for sender, msg in service_chat:
                if sender:
                    TeamChatMessage.objects.get_or_create(
                        workspace=ws_service,
                        sender=sender,
                        message=msg,
                    )
            self.stdout.write(self.style.SUCCESS(f"  ✓ Đã nạp hội thoại trao đổi cho Workspace {ws_service.name}."))

        self.stdout.write(self.style.SUCCESS("\n==> Hoàn tất khởi tạo dữ liệu mẫu Bảng tin và Trao đổi an toàn!"))
