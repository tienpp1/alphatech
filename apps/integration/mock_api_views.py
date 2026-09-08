"""
Mock External Partner REST API Endpoints.
Simulates legacy or third-party ERP/CRM external software returning non-canonical,
Vietnamese field names to test the ingestion and staging pipeline.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny


class MockRetailOrdersAPIView(APIView):
    """
    GET /api/v1/mock-external/retail/orders/
    Simulates external POS / e-commerce order feed.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        data = [
            {
                "ma_don_hang": "DH-EXT-202608-001",
                "ma_khach_hang": "KH-EXT-001",
                "tong_thanh_toan": "1,450,000 VND",
                "ngay_dat_hang": "2026-08-20 14:30:00",
                "trang_thai_don": "da_thanh_toan",
                "chi_nhanh_giao": "CN-Q1-HCM",
            },
            {
                "ma_don_hang": "DH-EXT-202608-002",
                "ma_khach_hang": "KH-EXT-002",
                "tong_thanh_toan": "890,000 VND",
                "ngay_dat_hang": "2026-08-20 15:45:00",
                "trang_thai_don": "da_thanh_toan",
                "chi_nhanh_giao": "CN-Q7-HCM",
            },
            {
                "ma_don_hang": "DH-EXT-202608-003",
                "ma_khach_hang": "KH-EXT-003",
                "tong_thanh_toan": "3,200,000 VND",
                "ngay_dat_hang": "2026-08-21 09:15:00",
                "trang_thai_don": "cho_giao_hang",
                "chi_nhanh_giao": "CN-BINHTHANH-HCM",
            },
            {
                "ma_don_hang": "DH-EXT-202608-004",
                "ma_khach_hang": "KH-EXT-001",
                "tong_thanh_toan": "550,000 VND",
                "ngay_dat_hang": "2026-08-22 11:20:00",
                "trang_thai_don": "da_thanh_toan",
                "chi_nhanh_giao": "CN-Q1-HCM",
            },
            {
                "ma_don_hang": "DH-EXT-202608-005",
                "ma_khach_hang": "KH-EXT-004",
                "tong_thanh_toan": "2,100,000 VND",
                "ngay_dat_hang": "2026-08-23 16:50:00",
                "trang_thai_don": "da_huy",
                "chi_nhanh_giao": "CN-Q7-HCM",
            },
        ]
        return Response({"status": "success", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class MockRetailCustomersAPIView(APIView):
    """
    GET /api/v1/mock-external/retail/customers/
    Simulates external CRM customer directory.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        data = [
            {
                "ma_kh": "KH-EXT-001",
                "ho_ten": "Nguyễn Văn Hùng",
                "dien_thoai": "0901234567",
                "email": "hung.nguyen@example.com",
                "dia_chi": "123 Lê Lợi, Phường Bến Nghé, Quận 1, TP.HCM",
                "phan_khuc": "VIP",
            },
            {
                "ma_kh": "KH-EXT-002",
                "ho_ten": "Trần Thị Mai",
                "dien_thoai": "0918765432",
                "email": "mai.tran@example.com",
                "dia_chi": "45 Nguyễn Thị Thập, Tân Phú, Quận 7, TP.HCM",
                "phan_khuc": "DOANH_NGHIEP",
            },
            {
                "ma_kh": "KH-EXT-003",
                "ho_ten": "Lê Hoàng Long",
                "dien_thoai": "0982345678",
                "email": "long.le@example.com",
                "dia_chi": "560 Điện Biên Phủ, Phường 25, Bình Thạnh, TP.HCM",
                "phan_khuc": "TIEU_CHUAN",
            },
            {
                "ma_kh": "KH-EXT-004",
                "ho_ten": "Phạm Quốc Bảo",
                "dien_thoai": "0973456789",
                "email": "bao.pham@example.com",
                "dia_chi": "88 Huỳnh Tấn Phát, Tân Thuận Đông, Quận 7, TP.HCM",
                "phan_khuc": "TIEU_CHUAN",
            },
        ]
        return Response({"status": "success", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class MockRetailProductsAPIView(APIView):
    """
    GET /api/v1/mock-external/retail/products/
    Simulates external supplier product catalog.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        data = [
            {
                "ma_sp": "SP-EXT-001",
                "ten_san_pham": "Laptop Pro 14 M3 16GB 512GB",
                "danh_muc": "Máy tính xách tay",
                "don_vi_tinh": "Chiếc",
                "gia_niem_yet": "29,990,000",
                "trang_thai": "dang_kinh_doanh",
            },
            {
                "ma_sp": "SP-EXT-002",
                "ten_san_pham": "Bàn phím cơ Gaming không dây RGB",
                "danh_muc": "Phụ kiện máy tính",
                "don_vi_tinh": "Cái",
                "gia_niem_yet": "1,450,000",
                "trang_thai": "dang_kinh_doanh",
            },
            {
                "ma_sp": "SP-EXT-003",
                "ten_san_pham": "Chuột công thái học Wireless",
                "danh_muc": "Phụ kiện máy tính",
                "don_vi_tinh": "Cái",
                "gia_niem_yet": "890,000",
                "trang_thai": "dang_kinh_doanh",
            },
        ]
        return Response({"status": "success", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class MockServiceTicketsAPIView(APIView):
    """
    GET /api/v1/mock-external/service/tickets/
    Simulates external helpdesk / incident ticketing feed.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        data = [
            {
                "ma_ticket": "TK-EXT-2026-001",
                "khach_hang": "Tập đoàn VinaTech",
                "loai_dich_vu": "Bảo trì định kỳ máy chủ cơ sở dữ liệu",
                "muc_do_uu_tien": "KHAN_CAP",
                "ngay_yeu_cau": "2026-08-24 08:30:00",
                "dia_diem_su_co": "Tầng 12, Tòa nhà Landmark 81, Bình Thạnh",
                "trang_thai_ve": "chua_xu_ly",
            },
            {
                "ma_ticket": "TK-EXT-2026-002",
                "khach_hang": "Ngân hàng Saigon Finance",
                "loai_dich_vu": "Xử lý sự cố mạng cáp quang nội bộ",
                "muc_do_uu_tien": "CAO",
                "ngay_yeu_cau": "2026-08-24 09:15:00",
                "dia_diem_su_co": "Số 2 Hải Triều, Tòa nhà Bitexco, Quận 1",
                "trang_thai_ve": "dang_xu_ly",
            },
            {
                "ma_ticket": "TK-EXT-2026-003",
                "khach_hang": "Công ty Logistics Phương Nam",
                "loai_dich_vu": "Cài đặt & cấu hình máy in mã vạch văn phòng",
                "muc_do_uu_tien": "TRUNG_BINH",
                "ngay_yeu_cau": "2026-08-24 10:00:00",
                "dia_diem_su_co": "Khu chế xuất Tân Thuận, Quận 7",
                "trang_thai_ve": "da_hoan_thanh",
            },
        ]
        return Response({"status": "success", "count": len(data), "data": data}, status=status.HTTP_200_OK)


class MockServiceTechniciansAPIView(APIView):
    """
    GET /api/v1/mock-external/service/technicians/
    Simulates external subcontractor engineer roster.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        data = [
            {
                "ma_ky_thuat_vien": "KT-EXT-01",
                "ho_ten": "Phan Minh Tuấn",
                "chuyen_mon": "Hệ thống Mạng & Tường lửa",
                "don_gia_gio": "220,000 VND/h",
                "san_sang": "true",
                "dia_ban_phu_trach": "Quận 1, Quận 3, Bình Thạnh",
            },
            {
                "ma_ky_thuat_vien": "KT-EXT-02",
                "ho_ten": "Đặng Quốc Huy",
                "chuyen_mon": "Máy chủ & Sao lưu Dữ liệu",
                "don_gia_gio": "250,000 VND/h",
                "san_sang": "true",
                "dia_ban_phu_trach": "Quận 7, Nhà Bè, Quận 4",
            },
            {
                "ma_ky_thuat_vien": "KT-EXT-03",
                "ho_ten": "Vũ Hải Nam",
                "chuyen_mon": "Phần cứng & Thiết bị đầu cuối",
                "don_gia_gio": "180,000 VND/h",
                "san_sang": "false",
                "dia_ban_phu_trach": "Thành phố Thủ Đức, Bình Thạnh",
            },
        ]
        return Response({"status": "success", "count": len(data), "data": data}, status=status.HTTP_200_OK)
