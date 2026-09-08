"""
Standard Data Model (SDM) Canonical Schema Contracts.
Defines canonical field specifications, types, constraints, and alias ontologies
for all platform entities across Retail and Service Operations.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class CanonicalFieldType:
    STRING = "STRING"
    DECIMAL = "DECIMAL"
    INTEGER = "INTEGER"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    DATETIME = "DATETIME"
    LIST = "LIST"
    ENUM = "ENUM"


@dataclass
class CanonicalFieldDef:
    name: str
    field_type: str
    required: bool = False
    description: str = ""
    choices: Optional[List[str]] = None
    aliases: List[str] = field(default_factory=list)
    default: Optional[Any] = None


@dataclass
class CanonicalModelDef:
    entity_name: str
    display_name: str
    domain: str  # "RETAIL" or "SERVICE"
    target_model_path: str
    description: str
    fields: Dict[str, CanonicalFieldDef]

    def get_field(self, field_name: str) -> Optional[CanonicalFieldDef]:
        return self.fields.get(field_name)

    def get_required_fields(self) -> List[str]:
        return [fname for fname, fdef in self.fields.items() if fdef.required]


# ==============================================================================
# CANONICAL SCHEMA DEFINITIONS
# ==============================================================================

CANONICAL_MODELS: Dict[str, CanonicalModelDef] = {
    "Customer": CanonicalModelDef(
        entity_name="Customer",
        display_name="Customer Directory",
        domain="RETAIL",
        target_model_path="apps.retail.models.Customer",
        description="Unified commercial or service client profile",
        fields={
            "customer_id": CanonicalFieldDef(
                name="customer_id",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Unique customer code / identifier",
                aliases=["ma_kh", "ma_khach_hang", "cust_id", "customer_code", "client_id", "id_khach_hang"],
            ),
            "name": CanonicalFieldDef(
                name="name",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Customer full name or business entity name",
                aliases=["ten_khach_hang", "ho_ten", "ten_kh", "customer_name", "full_name", "client_name"],
            ),
            "phone": CanonicalFieldDef(
                name="phone",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Primary contact telephone number",
                aliases=["sdt", "dien_thoai", "so_dien_thoai", "phone_number", "telephone", "mobile"],
            ),
            "email": CanonicalFieldDef(
                name="email",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Email address for notifications",
                aliases=["dia_chi_email", "mail", "email_address"],
            ),
            "address": CanonicalFieldDef(
                name="address",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Physical street address",
                aliases=["dia_chi", "noi_o", "street_address", "location_address", "dia_chi_giao"],
            ),
            "latitude": CanonicalFieldDef(
                name="latitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="WGS84 GPS Latitude coordinate (-90 to 90)",
                aliases=["vi_do", "lat", "latitude", "gps_lat", "vi_tri_y"],
            ),
            "longitude": CanonicalFieldDef(
                name="longitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="WGS84 GPS Longitude coordinate (-180 to 180)",
                aliases=["kinh_do", "lng", "lon", "longitude", "gps_lng", "vi_tri_x"],
            ),
            "segment": CanonicalFieldDef(
                name="segment",
                field_type=CanonicalFieldType.ENUM,
                required=False,
                choices=["STANDARD", "VIP", "ENTERPRISE"],
                default="STANDARD",
                description="Client classification segment",
                aliases=["phan_khuc", "loai_khach", "tier", "customer_segment", "hang_khach"],
            ),
        },
    ),
    "Product": CanonicalModelDef(
        entity_name="Product",
        display_name="Commercial Product",
        domain="RETAIL",
        target_model_path="apps.retail.models.Product",
        description="Retail catalog commercial item for sale (Scope Note: Commercial catalog only; warehouse/inventory tracking workflows and stock levels are non-core external data).",
        fields={
            "sku": CanonicalFieldDef(
                name="sku",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Stock keeping unit barcode / unique code",
                aliases=["ma_sp", "ma_hang", "ma_san_pham", "item_code", "product_code", "barcode"],
            ),
            "name": CanonicalFieldDef(
                name="name",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Product title / full display name",
                aliases=["ten_sp", "ten_san_pham", "ten_hang", "product_name", "item_name"],
            ),
            "category_code": CanonicalFieldDef(
                name="category_code",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Parent category code reference",
                aliases=["ma_danh_muc", "ma_loai", "category", "category_id", "nhom_hang"],
            ),
            "unit": CanonicalFieldDef(
                name="unit",
                field_type=CanonicalFieldType.STRING,
                required=False,
                default="cái",
                description="Measurement unit (e.g. cái, chai, lon, kg, hộp)",
                aliases=["don_vi_tinh", "dvt", "unit_of_measure", "uom"],
            ),
            "unit_price": CanonicalFieldDef(
                name="unit_price",
                field_type=CanonicalFieldType.DECIMAL,
                required=True,
                description="Standard selling retail price in VND",
                aliases=["gia_ban", "don_gia", "gia_niem_yet", "sale_price", "price", "retail_price"],
            ),
            "cost_price": CanonicalFieldDef(
                name="cost_price",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                default="0.00",
                description="Wholesale acquisition / production cost in VND",
                aliases=["gia_von", "gia_nhap", "cost", "cost_price", "purchase_price"],
            ),
            "stock_quantity": CanonicalFieldDef(
                name="stock_quantity",
                field_type=CanonicalFieldType.INTEGER,
                required=False,
                default=None,
                description="Optional non-core external supplier stock count (Note: Platform is not an inventory/WMS system; core domain is commercial sales & revenue analytics)",
                aliases=["so_luong_ton", "ton_kho", "stock_qty", "inventory_count", "on_hand"],
            ),
            "is_active": CanonicalFieldDef(
                name="is_active",
                field_type=CanonicalFieldType.BOOLEAN,
                required=False,
                default=True,
                description="Whether product is active in sales catalog",
                aliases=["dang_kinh_doanh", "kich_hoat", "active", "status"],
            ),
        },
    ),
    "Order": CanonicalModelDef(
        entity_name="Order",
        display_name="Retail Sales Order",
        domain="RETAIL",
        target_model_path="apps.retail.models.Order",
        description="Commercial sales order with canonical revenue tracking",
        fields={
            "order_number": CanonicalFieldDef(
                name="order_number",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Unique invoice receipt / order ID",
                aliases=["so_hoa_don", "ma_don_hang", "ma_don", "receipt_no", "order_id", "invoice_no"],
            ),
            "customer_id": CanonicalFieldDef(
                name="customer_id",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Customer code placing transaction",
                aliases=["ma_kh", "ma_khach_hang", "customer_code", "client_id"],
            ),
            "branch_code": CanonicalFieldDef(
                name="branch_code",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Fulfilling retail branch code",
                aliases=["ma_chi_nhanh", "chi_nhanh", "branch_id", "store_code", "chi_nhanh_giao"],
            ),
            "order_date": CanonicalFieldDef(
                name="order_date",
                field_type=CanonicalFieldType.DATE,
                required=True,
                description="Transaction calendar date (YYYY-MM-DD)",
                aliases=["ngay_dat_hang", "ngay_ban", "ngay_tao", "order_date", "txn_date", "ngay_lap"],
            ),
            "order_timestamp": CanonicalFieldDef(
                name="order_timestamp",
                field_type=CanonicalFieldType.DATETIME,
                required=False,
                description="Precise transaction timestamp with timezone",
                aliases=["thoi_gian_dat", "ngay_gio_tao", "timestamp", "created_time"],
            ),
            "total_amount": CanonicalFieldDef(
                name="total_amount",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                description="Transaction amount physically stored on the order (Order.total_amount)",
                aliases=["tong_tien", "thanh_tien", "tong_thanh_toan", "total_amount", "gross_amount", "amount", "tien"],
            ),
            "revenue": CanonicalFieldDef(
                name="revenue",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                description="Realized order revenue / transaction monetary amount (maps directly to Order.total_amount)",
                aliases=["doanh_thu", "tong_doanh_thu", "revenue", "sales_revenue"],
            ),
            "discount_amount": CanonicalFieldDef(
                name="discount_amount",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                default="0.00",
                description="Order-level discount deduction",
                aliases=["giam_gia", "chiet_khau", "discount", "discount_total"],
            ),
            "tax_amount": CanonicalFieldDef(
                name="tax_amount",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                default="0.00",
                description="Order tax / VAT amount",
                aliases=["thue", "vat", "tax"],
            ),
            "status": CanonicalFieldDef(
                name="status",
                field_type=CanonicalFieldType.ENUM,
                required=False,
                choices=["PENDING", "CONFIRMED", "PROCESSING", "SHIPPED", "COMPLETED", "CANCELLED", "REFUNDED"],
                default="COMPLETED",
                description="Order execution status",
                aliases=["trang_thai", "trang_thai_don", "order_status", "tinh_trang"],
            ),
            "payment_method": CanonicalFieldDef(
                name="payment_method",
                field_type=CanonicalFieldType.ENUM,
                required=False,
                choices=["CASH", "BANK_TRANSFER", "CARD", "E_WALLET"],
                default="CASH",
                description="Payment channel",
                aliases=["phuong_thuc_tt", "hinh_thuc_thanh_toan", "payment_type", "payment_method"],
            ),
            "notes": CanonicalFieldDef(
                name="notes",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Order notes or customer remarks",
                aliases=["ghi_chu", "remark", "notes"],
            ),
        },
    ),
    "OrderItem": CanonicalModelDef(
        entity_name="OrderItem",
        display_name="Order Line Item",
        domain="RETAIL",
        target_model_path="apps.retail.models.OrderItem",
        description="Individual item line within a retail order",
        fields={
            "order_number": CanonicalFieldDef(
                name="order_number",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Parent order receipt number",
                aliases=["so_hoa_don", "ma_don_hang", "order_id"],
            ),
            "sku": CanonicalFieldDef(
                name="sku",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Product SKU code",
                aliases=["ma_sp", "ma_hang", "product_code", "item_code"],
            ),
            "quantity": CanonicalFieldDef(
                name="quantity",
                field_type=CanonicalFieldType.INTEGER,
                required=True,
                description="Item units purchased",
                aliases=["so_luong", "qty", "quantity"],
            ),
            "unit_price": CanonicalFieldDef(
                name="unit_price",
                field_type=CanonicalFieldType.DECIMAL,
                required=True,
                description="Price per unit at purchase time",
                aliases=["don_gia", "gia_ban", "price", "unit_price"],
            ),
            "discount": CanonicalFieldDef(
                name="discount",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                default="0.00",
                description="Line item discount",
                aliases=["giam_gia", "chiet_khau", "discount"],
            ),
            "subtotal": CanonicalFieldDef(
                name="subtotal",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                description="Line item subtotal (quantity * unit_price - discount)",
                aliases=["thanh_tien", "subtotal", "line_total"],
            ),
        },
    ),
    "Branch": CanonicalModelDef(
        entity_name="Branch",
        display_name="Retail Store Branch",
        domain="RETAIL",
        target_model_path="apps.retail.models.Branch",
        description="Physical retail outlet or warehouse node",
        fields={
            "branch_code": CanonicalFieldDef(
                name="branch_code",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Store / branch code",
                aliases=["ma_chi_nhanh", "ma_cn", "branch_id", "store_code"],
            ),
            "name": CanonicalFieldDef(
                name="name",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Branch display name",
                aliases=["ten_chi_nhanh", "ten_cn", "branch_name", "store_name"],
            ),
            "region": CanonicalFieldDef(
                name="region",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Geographical region or administrative district",
                aliases=["khu_vuc", "vung", "region", "district", "quan_huyen"],
            ),
            "address": CanonicalFieldDef(
                name="address",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Physical street address",
                aliases=["dia_chi", "address", "street"],
            ),
            "phone": CanonicalFieldDef(
                name="phone",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Contact phone number",
                aliases=["sdt", "dien_thoai", "phone"],
            ),
            "latitude": CanonicalFieldDef(
                name="latitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="GPS Latitude coordinate",
                aliases=["vi_do", "lat", "latitude"],
            ),
            "longitude": CanonicalFieldDef(
                name="longitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="GPS Longitude coordinate",
                aliases=["kinh_do", "lng", "lon", "longitude"],
            ),
            "is_active": CanonicalFieldDef(
                name="is_active",
                field_type=CanonicalFieldType.BOOLEAN,
                required=False,
                default=True,
                description="Store operational status",
                aliases=["hoat_dong", "active", "is_active"],
            ),
        },
    ),
    "Service": CanonicalModelDef(
        entity_name="Service",
        display_name="IT Technical Service",
        domain="SERVICE",
        target_model_path="apps.service_ops.models.Service",
        description="Catalog of IT and technical service offerings",
        fields={
            "code": CanonicalFieldDef(
                name="code",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Standardized service code",
                aliases=["ma_dich_vu", "ma_dv", "service_code", "code"],
            ),
            "name": CanonicalFieldDef(
                name="name",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Service title",
                aliases=["ten_dich_vu", "ten_dv", "service_name", "title"],
            ),
            "category": CanonicalFieldDef(
                name="category",
                field_type=CanonicalFieldType.ENUM,
                required=False,
                choices=["INSTALLATION", "MAINTENANCE", "DATABASE_CONSULTING", "DEVICE_REPAIR"],
                default="INSTALLATION",
                description="Approved IT service category: INSTALLATION, MAINTENANCE, DATABASE_CONSULTING, DEVICE_REPAIR. Stale INSPECTION category is prohibited.",
                aliases=["loai_dich_vu", "danh_muc", "category", "service_type"],
            ),
            "standard_duration_minutes": CanonicalFieldDef(
                name="standard_duration_minutes",
                field_type=CanonicalFieldType.INTEGER,
                required=False,
                default=60,
                description="Baseline duration in minutes",
                aliases=["thoi_luong_phut", "thoi_gian_chuan", "standard_duration", "duration"],
            ),
            "base_fee": CanonicalFieldDef(
                name="base_fee",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                default="0.00",
                description="Base service charge in VND",
                aliases=["phi_co_ban", "gia_dich_vu", "base_fee", "fee"],
            ),
            "is_active": CanonicalFieldDef(
                name="is_active",
                field_type=CanonicalFieldType.BOOLEAN,
                required=False,
                default=True,
                description="Active catalog status",
                aliases=["dang_cung_cap", "kich_hoat", "is_active"],
            ),
        },
    ),
    "Employee": CanonicalModelDef(
        entity_name="Employee",
        display_name="Field Technician / Staff",
        domain="SERVICE",
        target_model_path="apps.service_ops.models.Employee",
        description="Operational field technician or engineer profile",
        fields={
            "employee_code": CanonicalFieldDef(
                name="employee_code",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Technician / employee code",
                aliases=["ma_nhan_vien", "ma_nv", "ma_ky_thuat_vien", "emp_code", "employee_id", "staff_code"],
            ),
            "full_name": CanonicalFieldDef(
                name="full_name",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Employee full name",
                aliases=["ho_ten", "ten_nhan_vien", "full_name", "employee_name", "staff_name"],
            ),
            "phone": CanonicalFieldDef(
                name="phone",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Mobile phone number",
                aliases=["sdt", "dien_thoai", "phone", "mobile"],
            ),
            "email": CanonicalFieldDef(
                name="email",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Corporate email address",
                aliases=["email", "mail"],
            ),
            "skills": CanonicalFieldDef(
                name="skills",
                field_type=CanonicalFieldType.LIST,
                required=False,
                default=[],
                description="List of verified skills (e.g. NETWORKING, DATABASE, HARDWARE)",
                aliases=["ky_nang", "chuyen_mon", "skills", "certifications"],
            ),
            "hourly_labor_rate": CanonicalFieldDef(
                name="hourly_labor_rate",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                default="150000.00",
                description="Standard hourly labor rate in VND",
                aliases=["don_gia_gio", "luong_gio", "hourly_rate", "rate_per_hour"],
            ),
            "latitude": CanonicalFieldDef(
                name="latitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="Last known GPS latitude",
                aliases=["vi_do", "lat", "latitude"],
            ),
            "longitude": CanonicalFieldDef(
                name="longitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="Last known GPS longitude",
                aliases=["kinh_do", "lng", "lon", "longitude"],
            ),
            "is_available": CanonicalFieldDef(
                name="is_available",
                field_type=CanonicalFieldType.BOOLEAN,
                required=False,
                default=True,
                description="Duty readiness flag",
                aliases=["san_sang", "available", "is_available", "trang_thai_lam_viec"],
            ),
        },
    ),
    "ServiceRequest": CanonicalModelDef(
        entity_name="ServiceRequest",
        display_name="Service Incident Ticket",
        domain="SERVICE",
        target_model_path="apps.service_ops.models.ServiceRequest",
        description="IT service incident ticket tracking resolution & SLA",
        fields={
            "request_number": CanonicalFieldDef(
                name="request_number",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Unique incident ticket number (SR-YYYYMMDD-XXXX)",
                aliases=["ma_yeu_cau", "so_phieu", "ma_ticket", "ticket_id", "request_no", "incident_id"],
            ),
            "customer_id": CanonicalFieldDef(
                name="customer_id",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Requesting client customer code",
                aliases=["ma_kh", "khach_hang", "customer_code", "client_id"],
            ),
            "service_code": CanonicalFieldDef(
                name="service_code",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Catalog service code requested",
                aliases=["ma_dich_vu", "dich_vu", "loai_dich_vu", "service_id", "service_code"],
            ),
            "title": CanonicalFieldDef(
                name="title",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Short summary of the technical problem",
                aliases=["tieu_de", "noi_dung", "title", "subject", "problem_description"],
            ),
            "priority": CanonicalFieldDef(
                name="priority",
                field_type=CanonicalFieldType.ENUM,
                required=False,
                choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                default="MEDIUM",
                description="Severity tier",
                aliases=["muc_do_uu_tien", "do_uu_tien", "priority", "severity"],
            ),
            "status": CanonicalFieldDef(
                name="status",
                field_type=CanonicalFieldType.ENUM,
                required=False,
                choices=["OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED", "CANCELLED"],
                default="OPEN",
                description="Ticket workflow status",
                aliases=["trang_thai", "tinh_trang", "status", "ticket_status"],
            ),
            "latitude": CanonicalFieldDef(
                name="latitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="Incident site latitude coordinate",
                aliases=["vi_do", "lat", "latitude", "dia_diem_lat"],
            ),
            "longitude": CanonicalFieldDef(
                name="longitude",
                field_type=CanonicalFieldType.FLOAT,
                required=False,
                description="Incident site longitude coordinate",
                aliases=["kinh_do", "lng", "lon", "longitude", "dia_diem_lng"],
            ),
            "assigned_employee_code": CanonicalFieldDef(
                name="assigned_employee_code",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Assigned technician code",
                aliases=["ky_thuat_vien", "nhan_vien_phu_trach", "assigned_to", "tech_id", "assigned_employee"],
            ),
            "response_deadline_at": CanonicalFieldDef(
                name="response_deadline_at",
                field_type=CanonicalFieldType.DATETIME,
                required=False,
                description="SLA first-response deadline timestamp",
                aliases=["han_phan_hoi", "response_deadline"],
            ),
            "resolution_deadline_at": CanonicalFieldDef(
                name="resolution_deadline_at",
                field_type=CanonicalFieldType.DATETIME,
                required=False,
                description="SLA resolution deadline timestamp",
                aliases=["han_chot", "han_xu_ly", "due_date", "resolution_deadline"],
            ),
        },
    ),
    "Task": CanonicalModelDef(
        entity_name="Task",
        display_name="Service Task Item",
        domain="SERVICE",
        target_model_path="apps.service_ops.models.Task",
        description="Discrete operational work item for a ticket",
        fields={
            "task_id": CanonicalFieldDef(
                name="task_id",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="External task identifier",
                aliases=["ma_cong_viec", "task_id", "ma_task"],
            ),
            "request_number": CanonicalFieldDef(
                name="request_number",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Parent service ticket request number",
                aliases=["ma_yeu_cau", "so_phieu", "ticket_id", "request_number"],
            ),
            "title": CanonicalFieldDef(
                name="title",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Task title / action description",
                aliases=["ten_cong_viec", "tieu_de", "title", "task_name"],
            ),
            "assigned_employee_code": CanonicalFieldDef(
                name="assigned_employee_code",
                field_type=CanonicalFieldType.STRING,
                required=False,
                description="Assigned technician code",
                aliases=["ma_nv", "ky_thuat_vien", "assigned_to", "employee_code"],
            ),
            "status": CanonicalFieldDef(
                name="status",
                field_type=CanonicalFieldType.ENUM,
                required=False,
                choices=["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"],
                default="PENDING",
                description="Task execution state",
                aliases=["trang_thai", "status", "task_status"],
            ),
            "estimated_duration": CanonicalFieldDef(
                name="estimated_duration",
                field_type=CanonicalFieldType.INTEGER,
                required=False,
                default=60,
                description="Estimated work duration in minutes",
                aliases=["thoi_luong_du_kien", "estimated_minutes", "duration"],
            ),
            "actual_duration": CanonicalFieldDef(
                name="actual_duration",
                field_type=CanonicalFieldType.INTEGER,
                required=False,
                description="Actual completed duration in minutes",
                aliases=["thoi_luong_thuc_te", "actual_minutes"],
            ),
        },
    ),
    "LaborEntry": CanonicalModelDef(
        entity_name="LaborEntry",
        display_name="Labor Time & Cost Entry",
        domain="SERVICE",
        target_model_path="apps.service_ops.models.LaborEntry",
        description="Labor time tracking and immutable hourly rate snapshot",
        fields={
            "task_id": CanonicalFieldDef(
                name="task_id",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Parent task reference",
                aliases=["ma_cong_viec", "task_id"],
            ),
            "employee_code": CanonicalFieldDef(
                name="employee_code",
                field_type=CanonicalFieldType.STRING,
                required=True,
                description="Technician code who performed the work",
                aliases=["ma_nv", "ky_thuat_vien", "employee_code"],
            ),
            "started_at": CanonicalFieldDef(
                name="started_at",
                field_type=CanonicalFieldType.DATETIME,
                required=True,
                description="Work commencement timestamp",
                aliases=["bat_dau", "started_at", "start_time"],
            ),
            "ended_at": CanonicalFieldDef(
                name="ended_at",
                field_type=CanonicalFieldType.DATETIME,
                required=True,
                description="Work completion timestamp",
                aliases=["ket_thuc", "ended_at", "end_time"],
            ),
            "duration_minutes": CanonicalFieldDef(
                name="duration_minutes",
                field_type=CanonicalFieldType.INTEGER,
                required=False,
                description="Duration in minutes",
                aliases=["so_phut", "duration_minutes", "minutes"],
            ),
            "hourly_rate_snapshot": CanonicalFieldDef(
                name="hourly_rate_snapshot",
                field_type=CanonicalFieldType.DECIMAL,
                required=False,
                description="Hourly labor rate in VND snapshot",
                aliases=["gia_gio", "don_gia_gio", "hourly_rate"],
            ),
        },
    ),
}


def get_canonical_model(entity_name: str) -> Optional[CanonicalModelDef]:
    """Look up a canonical model definition by name."""
    return CANONICAL_MODELS.get(entity_name)


def get_available_entities(domain: Optional[str] = None) -> List[Dict[str, Any]]:
    """Returns metadata for all available canonical models, optionally filtered by domain."""
    results = []
    for name, model_def in CANONICAL_MODELS.items():
        if domain and model_def.domain.upper() != domain.upper():
            continue
        results.append({
            "entity_name": model_def.entity_name,
            "display_name": model_def.display_name,
            "domain": model_def.domain,
            "description": model_def.description,
            "field_count": len(model_def.fields),
            "required_fields": model_def.get_required_fields(),
        })
    return results
