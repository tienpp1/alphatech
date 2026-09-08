"""
Management command to seed development demo data:
Roles, Permissions, Workspaces, Users, Memberships, Tokens, and Retail Domain Dataset.
"""

import random
from decimal import Decimal
from datetime import date, datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.contrib.gis.geos import Point

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import (
    Category,
    Product,
    Branch,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    CustomerSegment,
    Supplier,
    GoodsReceipt,
    GoodsReceiptItem,
    GoodsReceiptStatus,
    StockBalance,
)
from apps.service_ops.models import (
    ServiceCategory,
    Service,
    Employee,
    SLA,
    SLAPriority,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceRequestPriority,
    Task,
    TaskStatus,
    Schedule,
    ScheduleStatus,
    LaborEntry,
)
from apps.integration.models import (
    DataSource,
    ImportJob,
    RawImportRecord,
    SourceType,
    EntityType,
    ImportStatus,
)
from apps.integration.services import execute_import_job


class Command(BaseCommand):
    help = "Seeds initial development demo data (Roles, Workspaces, Users, Retail & Service Domains)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.WARNING(
                "\n=======================================================\n"
                "[SECURITY NOTICE] SEEDING LOCAL DEVELOPMENT DEMO DATA\n"
                "These accounts & tokens are for LOCAL DEVELOPMENT ONLY.\n"
                "NEVER USE THESE CREDENTIALS IN PRODUCTION ENVIRONMENTS.\n"
                "=======================================================\n"
            )
        )
        self.stdout.write(self.style.NOTICE("==> 1. Seeding Core Permissions..."))

        permissions_data = [
            # Retail Domain
            ("retail.view_product", "View product catalog", "retail"),
            ("retail.manage_product", "Create, update, or delete products and categories", "retail"),
            ("retail.view_order", "View retail orders and sales metrics", "retail"),
            ("retail.create_order", "Create retail orders", "retail"),
            ("retail.manage_order", "Update order status and cancel orders", "retail"),
            ("retail.view_customer", "View customer directory", "retail"),
            ("retail.manage_customer", "Create and manage customer profiles", "retail"),
            ("retail.view_branch", "View branch store network", "retail"),
            ("retail.manage_branch", "Create and manage branch store locations", "retail"),
            ("retail.view_analytics", "View sales and revenue analytics dashboards", "retail"),
            # Service Operations Domain
            ("service.view_service", "View service catalog", "service_ops"),
            ("service.manage_service", "Create and configure services", "service_ops"),
            ("service.view_employee", "View technician roster", "service_ops"),
            ("service.manage_employee", "Manage technicians and availability", "service_ops"),
            ("service.view_request", "View service incident requests and tasks", "service_ops"),
            ("service.create_request", "Log service incident requests", "service_ops"),
            ("service.manage_request", "Update request status, resolve or close tickets", "service_ops"),
            ("service.assign_request", "Assign tasks to field technicians", "service_ops"),
            ("service.view_task", "View discrete tasks", "service_ops"),
            ("service.manage_task", "Create and update tasks", "service_ops"),
            ("service.view_schedule", "View technician schedules", "service_ops"),
            ("service.manage_schedule", "Create and manage dispatch schedules", "service_ops"),
            ("service.view_sla", "View SLA policies", "service_ops"),
            ("service.manage_sla", "Configure SLA response and resolution targets", "service_ops"),
            ("service.view_analytics", "View service operations analytics", "service_ops"),
            # Spatial GIS Domain (Phase 5)
            ("gis.view_spatial_layers", "View spatial map layers and business GIS", "gis"),
            ("gis.view_customer_locations", "View customer geographic coordinates and details", "gis"),
            # Data Integration & Ingestion (Phase 6)
            ("integration.view_datasource", "View data sources and import history", "integration"),
            ("integration.manage_datasource", "Create and configure data sources", "integration"),
            ("integration.execute_import", "Upload files and trigger data ingestion jobs", "integration"),
            # Data Mapping Engine & Standard Data Model (Phase 7)
            ("mapping.view_mapping", "View mapping profiles and rules", "mapping"),
            ("mapping.manage_mapping", "Create, edit, and configure mapping profiles and rules", "mapping"),
            ("mapping.apply_mapping", "Apply mappings and load canonical domain records", "mapping"),
            # RAG + Knowledge Base + Grounded AI Assistant (Phase 8)
            ("knowledge.view_knowledge", "View knowledge bases, documents and chunks", "knowledge"),
            ("knowledge.manage_knowledge", "Upload, re-index and manage knowledge documents", "knowledge"),
            # Workspaces & Tenancy
            ("workspaces.view_workspace", "View workspace settings and members", "workspaces"),
            ("workspaces.manage_workspace", "Manage workspace configuration and memberships", "workspaces"),
            # Accounts & RBAC
            ("accounts.view_user", "View user accounts and roles", "accounts"),
            ("accounts.manage_user", "Manage user credentials and role assignments", "accounts"),
            # AI & Analytics
            ("ai.chat", "Interact with grounded AI assistant", "ai"),
            ("ai.view_forecast", "View time-series ML forecasts and metrics", "ai"),
            ("ai.view_insights", "View automated recommendations and insights", "ai"),
            # Predictive Analytics & XGBoost Forecasting (Phase 9)
            ("forecasting.view_forecast", "View time-series ML forecasts and accuracy metrics", "forecasting"),
            ("forecasting.manage_forecast", "Configure forecast targets and trigger model training", "forecasting"),
            # Decision Support & Recommendations (Phase 10)
            ("recommendations.view_recommendation", "View operational recommendations", "recommendations"),
            ("recommendations.manage_recommendation", "Accept, reject, or trigger recommendations", "recommendations"),
            # Controlled Tool Calling & Approvals (Phase 10)
            ("approvals.view_approval", "View pending approval requests", "approvals"),
            ("approvals.manage_approval", "Approve or reject mutation requests", "approvals"),
        ]

        permission_objs = {}
        for codename, name, module in permissions_data:
            perm, _ = Permission.objects.update_or_create(
                codename=codename,
                defaults={"name": name, "module": module},
            )
            permission_objs[codename] = perm

        self.stdout.write(f"    Created/Updated {len(permission_objs)} permissions.")

        # =========================================================================
        # 2. Roles & Permissions Binding
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 2. Seeding Roles and binding Permissions..."))

        roles_spec = {
            "ADMIN": {
                "desc": "System and Workspace Administrator with full privileges.",
                "perms": list(permission_objs.values()),
            },
            "MANAGER": {
                "desc": "Store/Operations Manager with management and analytics privileges.",
                "perms": [
                    p
                    for code, p in permission_objs.items()
                    if not code.startswith("accounts.manage_user")
                    and not code.startswith("workspaces.manage_workspace")
                ],
            },
            "EMPLOYEE": {
                "desc": "Front-line operational staff (Order creation, customer lookup, task viewing).",
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
                    permission_objs["gis.view_spatial_layers"],
                    permission_objs["integration.view_datasource"],
                    permission_objs["integration.execute_import"],
                    permission_objs["mapping.view_mapping"],
                    permission_objs["mapping.apply_mapping"],
                    permission_objs["knowledge.view_knowledge"],
                    permission_objs["ai.chat"],
                    permission_objs["forecasting.view_forecast"],
                ],
            },
            "VIEWER": {
                "desc": "Read-only auditor with dashboard viewing permissions.",
                "perms": [
                    permission_objs["retail.view_product"],
                    permission_objs["retail.view_order"],
                    permission_objs["retail.view_customer"],
                    permission_objs["retail.view_branch"],
                    permission_objs["retail.view_analytics"],
                    permission_objs["service.view_service"],
                    permission_objs["service.view_request"],
                    permission_objs["gis.view_spatial_layers"],
                    permission_objs["integration.view_datasource"],
                    permission_objs["mapping.view_mapping"],
                    permission_objs["knowledge.view_knowledge"],
                    permission_objs["workspaces.view_workspace"],
                    permission_objs["forecasting.view_forecast"],
                ],
            },
        }

        roles = {}
        for r_name, r_spec in roles_spec.items():
            role, _ = Role.objects.update_or_create(
                name=r_name,
                defaults={"description": r_spec["desc"]},
            )
            role.permissions.set(r_spec["perms"])
            roles[r_name] = role

        self.stdout.write(f"    Created/Updated {len(roles)} roles.")

        # =========================================================================
        # 3. Workspaces
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 3. Seeding Dual Workspaces (Retail & Service)..."))

        retail_ws, _ = Workspace.objects.update_or_create(
            code="abc-retail",
            defaults={
                "name": "ABC Tech Store",
                "workspace_type": WorkspaceType.RETAIL,
                "description": "Cửa hàng bán thiết bị công nghệ và phụ kiện tại TP.HCM.",
                "is_active": True,
            },
        )

        service_ws, _ = Workspace.objects.update_or_create(
            code="xyz-service",
            defaults={
                "name": "XYZ IT Technical Services",
                "workspace_type": WorkspaceType.SERVICE,
                "description": "Công ty dịch vụ cài đặt, bảo trì hệ thống, tư vấn quản trị cơ sở dữ liệu và sửa chữa thiết bị.",
                "is_active": True,
            },
        )

        self.stdout.write(f"    Workspaces: '{retail_ws.name}' ({retail_ws.code}), '{service_ws.name}' ({service_ws.code}).")

        # =========================================================================
        # 4. Users & Memberships
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 4. Seeding Demo Users & Memberships..."))

        demo_users_spec = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "AdminPass123!",
                "first_name": "System",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "memberships": [
                    {"workspace": retail_ws, "role": roles["ADMIN"], "is_default": True},
                    {"workspace": service_ws, "role": roles["ADMIN"], "is_default": False},
                ],
            },
            {
                "username": "manager",
                "email": "manager@example.com",
                "password": "ManagerPass123!",
                "first_name": "Store",
                "last_name": "Manager",
                "is_staff": False,
                "is_superuser": False,
                "memberships": [
                    {"workspace": retail_ws, "role": roles["MANAGER"], "is_default": True},
                    {"workspace": service_ws, "role": roles["EMPLOYEE"], "is_default": False},
                ],
            },
            {
                "username": "employee",
                "email": "employee@example.com",
                "password": "EmployeePass123!",
                "first_name": "Frontline",
                "last_name": "Staff",
                "is_staff": False,
                "is_superuser": False,
                "memberships": [
                    {"workspace": retail_ws, "role": roles["EMPLOYEE"], "is_default": True},
                    {"workspace": service_ws, "role": roles["VIEWER"], "is_default": False},
                ],
            },
            {
                "username": "viewer",
                "email": "viewer@example.com",
                "password": "ViewerPass123!",
                "first_name": "Audit",
                "last_name": "Viewer",
                "is_staff": False,
                "is_superuser": False,
                "memberships": [
                    {"workspace": retail_ws, "role": roles["VIEWER"], "is_default": True},
                    {"workspace": service_ws, "role": roles["VIEWER"], "is_default": False},
                ],
            },
        ]

        for u_spec in demo_users_spec:
            user, _ = User.objects.update_or_create(
                username=u_spec["username"],
                defaults={
                    "email": u_spec["email"],
                    "first_name": u_spec["first_name"],
                    "last_name": u_spec["last_name"],
                    "is_staff": u_spec["is_staff"],
                    "is_superuser": u_spec["is_superuser"],
                    "is_active": True,
                },
            )
            user.set_password(u_spec["password"])
            user.save()

            # Create DRF Token
            token, _ = Token.objects.get_or_create(user=user)

            # Create Workspace Memberships
            for m_spec in u_spec["memberships"]:
                WorkspaceMembership.objects.update_or_create(
                    user=user,
                    workspace=m_spec["workspace"],
                    defaults={
                        "role": m_spec["role"],
                        "is_default": m_spec["is_default"],
                        "is_active": True,
                    },
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"    User: {user.username:<10} | Password: {u_spec['password']:<16} | Token: {token.key}"
                )
            )

        # =========================================================================
        # =========================================================================
        # 5. Retail Domain Dataset (ABC Tech Store - Technology Store & Accessories)
        # =========================================================================
        self.stdout.write(self.style.NOTICE("\n==> 5. Seeding Retail Domain (ABC Tech Store)..."))
        random.seed(42)  # Reproducible synthetic dataset

        # Safe Development Clean: Remove obsolete demo orders, products, and categories for ABC Tech Store
        Order.objects.for_workspace(retail_ws).delete()
        Product.objects.filter(workspace=retail_ws).delete()
        Category.objects.filter(workspace=retail_ws).delete()

        # 5.1 Categories (8 Approved Technology Categories)
        categories_data = [
            ("laptop", "Laptop & Máy tính xách tay", "Máy tính xách tay văn phòng, mỏng nhẹ, đồ họa và gaming chuyên nghiệp"),
            ("smartphone", "Điện thoại thông minh", "Điện thoại di động thông minh, smartphone Android và iOS chính hãng"),
            ("mouse", "Chuột máy tính", "Chuột quang có dây, chuột không dây, chuột công thái học, chuột gaming"),
            ("keyboard", "Bàn phím máy tính", "Bàn phím cơ không dây, bàn phím Bluetooth, bàn phím văn phòng tiêu chuẩn"),
            ("headset", "Tai nghe & Âm thanh", "Tai nghe chụp tai chống ồn chủ động, tai nghe True Wireless, tai nghe gaming có mic"),
            ("webcam", "Webcam & Hội nghị", "Webcam Full HD 1080p, 2K họp trực tuyến, học tập từ xa và livestream"),
            ("components", "Linh kiện máy tính", "Ổ cứng SSD NVMe, bộ nhớ RAM DDR4/DDR5, bộ nguồn PSU, CPU và bo mạch chủ"),
            ("networking", "Thiết bị mạng & Wi-Fi", "Router Wi-Fi 6, bộ phát Access Point doanh nghiệp, Switch mạng Gigabit, phụ kiện mạng"),
        ]

        cat_map = {}
        for code, name, desc in categories_data:
            cat, _ = Category.objects.update_or_create(
                workspace=retail_ws,
                code=code,
                defaults={"name": name, "description": desc, "is_active": True},
            )
            cat_map[code] = cat
        self.stdout.write(f"    Categories: {len(cat_map)} technology product categories created.")

        # 5.2 Branches (HCMC Technology Store Outlets with WGS84 Coordinates)
        branches_data = [
            ("BR-D1", "Chi nhánh Flagship Công nghệ Quận 1", "68 Nguyễn Huệ, Phường Bến Nghé, Quận 1, TP.HCM", "Quận 1", 10.7745, 106.7032, "028-38210001"),
            ("BR-D7", "Chi nhánh Trung tâm Công nghệ Quận 7", "101 Tôn Dật Tiên, Phường Tân Phong, Quận 7, TP.HCM", "Quận 7", 10.7288, 106.7196, "028-54120002"),
            ("BR-BT", "Chi nhánh Trải nghiệm Công nghệ Bình Thạnh", "561A Điện Biên Phủ, Phường 25, Bình Thạnh, TP.HCM", "Bình Thạnh", 10.7997, 106.7185, "028-35120003"),
        ]

        branch_list = []
        for code, name, addr, region, lat, lon, phone in branches_data:
            b, _ = Branch.objects.update_or_create(
                workspace=retail_ws,
                code=code,
                defaults={
                    "name": name,
                    "address": addr,
                    "region": region,
                    "latitude": Decimal(str(lat)),
                    "longitude": Decimal(str(lon)),
                    "location": Point(lon, lat, srid=4326),
                    "phone": phone,
                    "is_active": True,
                },
            )
            branch_list.append(b)
        self.stdout.write(f"    Branches: {len(branch_list)} technology retail store branches created.")

        # 5.3 Products (42 realistic technology products)
        products_data = [
            # 1. Laptops
            ("SP-LAP-001", "Laptop ASUS VivoBook 15 OLED A1505VA (i5-13500H, 16GB, 512GB SSD)", "laptop", "chiếc", 17490000, 14800000),
            ("SP-LAP-002", "Laptop Lenovo IdeaPad Slim 5 14IAH8 (i5-12450H, 16GB, 512GB SSD)", "laptop", "chiếc", 15290000, 12900000),
            ("SP-LAP-003", "Laptop Acer Aspire 5 A515-58M (i5-1335U, 16GB, 512GB SSD)", "laptop", "chiếc", 14990000, 12500000),
            ("SP-LAP-004", "Laptop Dell Inspiron 15 3520 (i7-1255U, 16GB, 512GB SSD)", "laptop", "chiếc", 18990000, 16100000),
            ("SP-LAP-005", "Laptop Gaming ASUS TUF Gaming F15 FX506HF (i5-11400H, RTX 2050)", "laptop", "chiếc", 17990000, 15200000),
            ("SP-LAP-006", "Laptop Apple MacBook Air 13 inch M2 (8GB RAM, 256GB SSD)", "laptop", "chiếc", 24990000, 21500000),

            # 2. Smartphones
            ("SP-PHN-001", "Điện thoại Samsung Galaxy A54 5G 128GB", "smartphone", "chiếc", 7490000, 6200000),
            ("SP-PHN-002", "Điện thoại Samsung Galaxy S23 5G 256GB", "smartphone", "chiếc", 16990000, 14200000),
            ("SP-PHN-003", "Điện thoại Xiaomi Redmi Note 13 Pro 8GB/256GB", "smartphone", "chiếc", 6290000, 5100000),
            ("SP-PHN-004", "Điện thoại Xiaomi 13T 5G 12GB/256GB Leica", "smartphone", "chiếc", 10990000, 9100000),
            ("SP-PHN-005", "Điện thoại OPPO Reno11 5G 256GB", "smartphone", "chiếc", 8990000, 7400000),
            ("SP-PHN-006", "Điện thoại iPhone 15 128GB Chính Hãng VN/A", "smartphone", "chiếc", 19790000, 17200000),

            # 3. Chuột (Mouse)
            ("SP-MOU-001", "Chuột không dây Logitech M331 Silent Plus", "mouse", "cái", 350000, 240000),
            ("SP-MOU-002", "Chuột không dây công thái học Logitech MX Master 3S", "mouse", "cái", 2190000, 1690000),
            ("SP-MOU-003", "Chuột Gaming Razer DeathAdder Essential", "mouse", "cái", 490000, 340000),
            ("SP-MOU-004", "Chuột Gaming không dây Logitech G304 Lightspeed", "mouse", "cái", 790000, 560000),
            ("SP-MOU-005", "Chuột quang có dây Fuhlen L102 USB", "mouse", "cái", 120000, 80000),

            # 4. Bàn phím (Keyboard)
            ("SP-KBD-001", "Bàn phím cơ không dây DareU EK871 Bluetooth", "keyboard", "cái", 790000, 550000),
            ("SP-KBD-002", "Bàn phím cơ AKKO 3087 v2 DS Matcha Red Switch", "keyboard", "cái", 1190000, 850000),
            ("SP-KBD-003", "Bàn phím cơ không dây Keychron K2 Pro QMK/VIA", "keyboard", "cái", 2150000, 1650000),
            ("SP-KBD-004", "Bàn phím không dây Logitech K380 Multi-Device", "keyboard", "cái", 590000, 410000),
            ("SP-KBD-005", "Bàn phím văn phòng có dây Dell KB216 USB", "keyboard", "cái", 190000, 130000),

            # 5. Tai nghe (Headset)
            ("SP-EAR-001", "Tai nghe không dây Sony WH-1000XM5 Chống ồn chủ động", "headset", "chiếc", 6990000, 5600000),
            ("SP-EAR-002", "Tai nghe chụp tai Gaming HyperX Cloud II Red", "headset", "chiếc", 1890000, 1390000),
            ("SP-EAR-003", "Tai nghe True Wireless Samsung Galaxy Buds2 Pro", "headset", "bộ", 2790000, 2100000),
            ("SP-EAR-004", "Tai nghe văn phòng có mic Logitech H111", "headset", "chiếc", 220000, 150000),
            ("SP-EAR-005", "Tai nghe True Wireless Apple AirPods Pro 2 MagSafe Type-C", "headset", "bộ", 5490000, 4650000),

            # 6. Webcam
            ("SP-CAM-001", "Webcam Logitech C922 Pro Stream Full HD 1080p 60fps", "webcam", "cái", 1890000, 1420000),
            ("SP-CAM-002", "Webcam Logitech C270 HD 720p có Mic khử ồn", "webcam", "cái", 490000, 340000),
            ("SP-CAM-003", "Webcam Rapoo C260 Full HD 1080p góc rộng", "webcam", "cái", 420000, 290000),
            ("SP-CAM-004", "Webcam Razer Kiyo Pro Full HD cảm biến ánh sáng thích ứng", "webcam", "cái", 2490000, 1890000),

            # 7. Linh kiện máy tính (Components)
            ("SP-COM-001", "Ổ cứng SSD Samsung 980 Pro 1TB M.2 NVMe PCIe 4.0", "components", "hộp", 2450000, 1850000),
            ("SP-COM-002", "Ổ cứng SSD Kingston NV2 500GB M.2 NVMe PCIe 4.0", "components", "hộp", 990000, 720000),
            ("SP-COM-003", "RAM Kingston Fury Beast 16GB (2x8GB) DDR4 3200MHz", "components", "bộ", 1090000, 810000),
            ("SP-COM-004", "RAM Corsair Vengeance RGB 32GB (2x16GB) DDR5 5600MHz", "components", "bộ", 2890000, 2200000),
            ("SP-COM-005", "Nguồn máy tính Corsair RM750e 750W 80 Plus Gold", "components", "hộp", 2690000, 2050000),
            ("SP-COM-006", "CPU Intel Core i5-13400 (Turbo 4.6GHz, 10 nhân 16 luồng)", "components", "hộp", 4890000, 4100000),
            ("SP-COM-007", "Bo mạch chủ ASUS TUF Gaming B760M-PLUS WIFI DDR4", "components", "hộp", 3790000, 3050000),

            # 8. Thiết bị mạng (Networking)
            ("SP-NET-001", "Router Wi-Fi 6 TP-Link Archer AX10 Chuẩn AX1500", "networking", "bộ", 990000, 710000),
            ("SP-NET-002", "Router Wi-Fi 6 ASUS RT-AX53U Băng tần kép Gigabit", "networking", "bộ", 1290000, 950000),
            ("SP-NET-003", "Bộ phát Wi-Fi Access Point Ruijie Reyee RG-RAP2200(E)", "networking", "bộ", 1750000, 1320000),
            ("SP-NET-004", "Switch mạng 8 cổng TP-Link TL-SG108 Gigabit Vỏ kim loại", "networking", "cái", 490000, 340000),
            ("SP-NET-005", "Switch PoE 8 cổng Hikvision DS-3E0109P-E/M 100Mbps", "networking", "cái", 890000, 640000),
            ("SP-NET-006", "Cáp mạng đúc sẵn Cat6 UTP Ugreen 5m", "networking", "sợi", 95000, 55000),
        ]

        product_list = []
        for sku, name, cat_code, unit, uprice, cprice in products_data:
            p, _ = Product.objects.update_or_create(
                workspace=retail_ws,
                sku=sku,
                defaults={
                    "name": name,
                    "category": cat_map[cat_code],
                    "unit": unit,
                    "unit_price": Decimal(str(uprice)),
                    "cost_price": Decimal(str(cprice)),
                    "is_active": True,
                },
            )
            product_list.append(p)
        self.stdout.write(f"    Products: {len(product_list)} technology products created.")

        # 5.4 Customers (60 realistic customer profiles in HCMC)
        first_names = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương"]
        middle_names = ["Văn", "Thị", "Đức", "Minh", "Thanh", "Quốc", "Hữu", "Thái", "Hồng", "Tuấn", "Ngọc"]
        last_names = ["An", "Bình", "Cường", "Dũng", "Em", "Giang", "Hải", "Hùng", "Khoa", "Linh", "Long", "Nam", "Phúc", "Quân", "Sơn", "Tâm", "Thắng", "Trang", "Việt", "Yến"]

        customer_list = []
        for i in range(1, 61):
            code = f"CUST-{i:04d}"
            name = f"{random.choice(first_names)} {random.choice(middle_names)} {random.choice(last_names)}"
            phone = f"09{random.randint(10000000, 99999999)}"
            email = f"customer_{i}@example.com"
            segment = random.choices(
                [CustomerSegment.STANDARD, CustomerSegment.VIP, CustomerSegment.ENTERPRISE],
                weights=[70, 20, 10],
            )[0]
            lat = round(10.72 + random.random() * 0.12, 6)
            lon = round(106.65 + random.random() * 0.10, 6)

            cust, _ = Customer.objects.update_or_create(
                workspace=retail_ws,
                code=code,
                defaults={
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "address": f"{random.randint(1, 500)} Đường số {random.randint(1, 30)}, TP.HCM",
                    "latitude": Decimal(str(lat)),
                    "longitude": Decimal(str(lon)),
                    "location": Point(lon, lat, srid=4326),
                    "customer_segment": segment,
                    "is_active": True,
                },
            )
            customer_list.append(cust)
        self.stdout.write(f"    Customers: {len(customer_list)} customer profiles created.")

        # 5.5 Orders (160 realistic multi-item commercial orders over last 90 days)
        now = timezone.now()
        admin_user = User.objects.get(username="admin")
        payment_choices = [PaymentMethod.CASH, PaymentMethod.BANK_TRANSFER, PaymentMethod.CREDIT_CARD, PaymentMethod.E_WALLET]
        payment_weights = [30, 35, 25, 10]

        created_orders_count = 0
        total_revenue_accum = Decimal("0.00")

        # Clean existing demo orders for fresh seeding
        Order.objects.for_workspace(retail_ws).delete()

        for i in range(1, 161):
            # Spread orders across past 90 days with daily volume variation
            days_ago = random.randint(0, 89)
            order_date_val = (now - timedelta(days=days_ago)).date()
            hour = random.randint(8, 21)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            order_dt = datetime(
                order_date_val.year,
                order_date_val.month,
                order_date_val.day,
                hour,
                minute,
                second,
                tzinfo=timezone.get_current_timezone(),
            )

            order_num = f"ORD-{order_date_val.strftime('%Y%m%d')}-{i:04d}"
            customer = random.choice(customer_list)
            branch = random.choice(branch_list)
            payment = random.choices(payment_choices, weights=payment_weights)[0]

            # 90% completed, 5% confirmed, 3% pending, 2% cancelled
            status_val = random.choices(
                [OrderStatus.COMPLETED, OrderStatus.CONFIRMED, OrderStatus.PENDING, OrderStatus.CANCELLED],
                weights=[90, 5, 3, 2],
            )[0]

            # 1 to 4 distinct items per order
            num_items = random.randint(1, 4)
            selected_products = random.sample(product_list, num_items)

            items_to_create = []
            subtotal_sum = Decimal("0.00")

            for prod in selected_products:
                qty = random.randint(1, 2)
                item_discount = Decimal("0.00")
                if random.random() < 0.12:  # 12% promotional item discount
                    item_discount = Decimal(str(random.randint(5, 20) * 10000))

                line_subtotal = max(Decimal("0.00"), (Decimal(qty) * prod.unit_price) - item_discount)
                subtotal_sum += line_subtotal
                items_to_create.append((prod, qty, prod.unit_price, item_discount, line_subtotal))

            order_discount = Decimal("0.00")
            if customer.customer_segment == CustomerSegment.VIP:
                order_discount = round(subtotal_sum * Decimal("0.05"), -3)  # 5% VIP discount
            elif customer.customer_segment == CustomerSegment.ENTERPRISE:
                order_discount = round(subtotal_sum * Decimal("0.10"), -3)  # 10% Enterprise discount

            total_amount_val = max(Decimal("0.00"), subtotal_sum - order_discount)

            order = Order.objects.create(
                workspace=retail_ws,
                order_number=order_num,
                customer=customer,
                branch=branch,
                order_date=order_date_val,
                order_timestamp=order_dt,
                status=status_val,
                subtotal_amount=subtotal_sum,
                discount_amount=order_discount,
                tax_amount=Decimal("0.00"),
                total_amount=total_amount_val,
                payment_method=payment,
                created_by=admin_user,
            )

            for prod, qty, uprice, disc, line_tot in items_to_create:
                OrderItem.objects.create(
                    order=order,
                    product=prod,
                    quantity=qty,
                    unit_price=uprice,
                    discount=disc,
                    subtotal=line_tot,
                )

            created_orders_count += 1
            if status_val != OrderStatus.CANCELLED:
                total_revenue_accum += total_amount_val

        self.stdout.write(
            self.style.SUCCESS(
                f"    Orders: {created_orders_count} multi-item orders generated.\n"
                f"    Realized Revenue: {total_revenue_accum:,.0f} VND across past 90 days."
            )
        )

        # 5.6 Wholesale Suppliers
        self.stdout.write(self.style.NOTICE("==> 5.6 Seeding Retail Suppliers..."))
        suppliers_raw = [
            ("SUP-ASUS", "ASUS Global Pte Ltd - Chi nhánh Việt Nam", "Nguyễn Văn Hùng", "hung.nguyen@asus.com", "02838123456", "Tòa nhà Viettel, 285 CMT8, Q.10, TP.HCM"),
            ("SUP-LENOVO", "Lenovo Vietnam Co., Ltd", "Trần Thị Mai", "mai.tran@lenovo.com", "02439876543", "Tòa nhà Keangnam Landmark 72, Nam Từ Liêm, Hà Nội"),
            ("SUP-LOGITECH", "Logitech Southeast Asia Distribution", "Lê Hoàng Long", "long.le@logitech.com", "02839998877", "Khu chế xuất Tân Thuận, Q.7, TP.HCM"),
            ("SUP-KINGSTON", "Kingston Technology Far East Corp", "Phạm Quốc Bảo", "bao.pham@kingston.com", "02837776655", "Khu công nghệ cao, TP. Thủ Đức, TP.HCM"),
            ("SUP-DELL", "Dell Technologies Vietnam", "Vũ Minh Tuấn", "tuan.vu@dell.com", "02838221100", "Saigon Tower, 29 Lê Duẩn, Q.1, TP.HCM"),
            ("SUP-TPLINK", "TP-Link Technologies Vietnam Co., Ltd", "Hoàng Thu Trang", "trang.hoang@tp-link.com", "02838445566", "Tòa nhà E-Town, 364 Cộng Hòa, Tân Bình, TP.HCM"),
        ]

        supplier_list = []
        for code, name, contact, email, phone, addr in suppliers_raw:
            sup, _ = Supplier.objects.update_or_create(
                workspace=retail_ws,
                code=code,
                defaults={
                    "name": name,
                    "contact_name": contact,
                    "email": email,
                    "phone": phone,
                    "address": addr,
                    "is_active": True,
                },
            )
            supplier_list.append(sup)
        self.stdout.write(f"    Suppliers: {len(supplier_list)} technology suppliers created.")

        # 5.7 Branch Stock Balances (Branch-aware Inventory with realistic risk distribution)
        self.stdout.write(self.style.NOTICE("==> 5.7 Seeding Branch Stock Balances (Branch-aware Inventory)..."))
        StockBalance.objects.for_workspace(retail_ws).delete()

        # Specific custom stock setups to realistically demonstrate OUT_OF_STOCK, HIGH, MEDIUM, and LOW risk tiers
        # Asus VivoBook: Branch A=4 (HIGH RISK < 7d), Branch B=18, Branch C=9
        # Lenovo IdeaPad: Branch A=22, Branch B=6 (HIGH/MEDIUM RISK), Branch C=14
        # Dell Vostro (if exists): Branch A=0 (OUT_OF_STOCK)
        for prod in product_list:
            for br in branch_list:
                p_name_lower = prod.name.lower()
                br_code = br.code

                if "vivobook" in p_name_lower:
                    if "A" in br_code or "Q1" in br_code or br == branch_list[0]:
                        stock_qty = 4  # High Risk (runs out in ~2.2 days)
                    elif "B" in br_code or len(branch_list) > 1 and br == branch_list[1]:
                        stock_qty = 18
                    else:
                        stock_qty = 9
                elif "ideapad" in p_name_lower:
                    if "B" in br_code or len(branch_list) > 1 and br == branch_list[1]:
                        stock_qty = 6  # High Risk
                    elif "A" in br_code or br == branch_list[0]:
                        stock_qty = 22
                    else:
                        stock_qty = 14
                elif "g pro" in p_name_lower or "gaming" in p_name_lower:
                    if br == branch_list[0]:
                        stock_qty = 0  # Out of stock!
                    else:
                        stock_qty = random.randint(15, 45)
                elif "laptop" in p_name_lower:
                    stock_qty = random.randint(5, 30)
                elif "mouse" in p_name_lower or "chuột" in p_name_lower or "bàn phím" in p_name_lower or "keyboard" in p_name_lower:
                    stock_qty = random.randint(25, 80)
                elif "ssd" in p_name_lower or "ram" in p_name_lower:
                    stock_qty = random.randint(15, 60)
                else:
                    stock_qty = random.randint(8, 50)

                StockBalance.objects.create(
                    workspace=retail_ws,
                    branch=br,
                    product=prod,
                    quantity_on_hand=stock_qty,
                )

        stock_count = StockBalance.objects.for_workspace(retail_ws).count()
        self.stdout.write(f"    StockBalances: {stock_count} branch stock balances configured across {len(branch_list)} branches.")

        # 5.8 Goods Receipts (Inbound Inventory Receipts across statuses)
        self.stdout.write(self.style.NOTICE("==> 5.8 Seeding Goods Receipts (Inbound Logistics)..."))
        GoodsReceipt.objects.for_workspace(retail_ws).delete()

        receipt_configs = [
            ("PN-20260815-001", supplier_list[0], branch_list[0], date(2026, 8, 15), date(2026, 8, 17), GoodsReceiptStatus.RECEIVED, "Lô hàng Laptop ASUS đợt 1 tháng 8"),
            ("PN-20260820-002", supplier_list[1], branch_list[1] if len(branch_list) > 1 else branch_list[0], date(2026, 8, 20), date(2026, 8, 22), GoodsReceiptStatus.RECEIVED, "Nhập máy tính xách tay Lenovo IdeaPad và phụ kiện"),
            ("PN-20260825-003", supplier_list[2], branch_list[0], date(2026, 8, 25), date(2026, 8, 27), GoodsReceiptStatus.RECEIVED, "Nhập chuột Logitech và bàn phím cơ"),
            ("PN-20260828-004", supplier_list[3], branch_list[1] if len(branch_list) > 1 else branch_list[0], date(2026, 8, 28), date(2026, 8, 30), GoodsReceiptStatus.RECEIVED, "Nhập RAM Kingston Fury và SSD NVMe"),
            ("PN-20260830-005", supplier_list[0], branch_list[0], date(2026, 8, 30), date(2026, 9, 3), GoodsReceiptStatus.CONFIRMED, "Đơn đặt hàng bổ sung ASUS VivoBook cho chi nhánh chính"),
            ("PN-20260901-006", supplier_list[4], branch_list[0], date(2026, 9, 1), date(2026, 9, 5), GoodsReceiptStatus.DRAFT, "Dự thảo đơn nhập máy chủ Dell và màn hình"),
            ("PN-20260901-007", supplier_list[5], branch_list[1] if len(branch_list) > 1 else branch_list[0], date(2026, 9, 1), date(2026, 9, 6), GoodsReceiptStatus.DRAFT, "Dự thảo đơn nhập thiết bị mạng Router TP-Link Archer"),
        ]

        created_receipts = 0
        for r_num, sup, br, r_date, exp_date, stat, notes in receipt_configs:
            receipt = GoodsReceipt.objects.create(
                workspace=retail_ws,
                receipt_number=r_num,
                supplier=sup,
                branch=br,
                receipt_date=r_date,
                expected_date=exp_date,
                status=stat,
                notes=notes,
                created_by=admin_user,
                received_by=admin_user if stat == GoodsReceiptStatus.RECEIVED else None,
                received_at=datetime(r_date.year, r_date.month, r_date.day, 14, 30, tzinfo=timezone.get_current_timezone()) if stat == GoodsReceiptStatus.RECEIVED else None,
            )

            # Assign 2 to 4 products to each receipt
            rec_prods = random.sample(product_list, random.randint(2, 4))
            tot_amt = Decimal("0.00")
            for p in rec_prods:
                qty = random.randint(5, 20)
                cost = p.cost_price or (p.unit_price * Decimal("0.75"))
                l_tot = Decimal(qty) * cost
                tot_amt += l_tot
                GoodsReceiptItem.objects.create(
                    receipt=receipt,
                    product=p,
                    quantity=qty,
                    unit_cost=cost,
                    line_total=l_tot,
                )

            receipt.total_amount = tot_amt
            receipt.save(update_fields=["total_amount"])
            created_receipts += 1

        self.stdout.write(f"    GoodsReceipts: {created_receipts} goods receipts created across DRAFT, CONFIRMED, and RECEIVED statuses.")

        # =========================================================================
        # 6. Service Operations Domain (XYZ IT Technical Services)
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 6. Seeding Service Domain (XYZ IT Technical Services)..."))

        # Safe Development Clean: Remove obsolete demo service requests and services for XYZ IT Technical Services
        ServiceRequest.objects.filter(workspace=service_ws).delete()
        Service.objects.filter(workspace=service_ws).delete()

        # 6.1 Services Catalog (4 Categories, 18 IT Services)
        services_raw = [
            # 1. Cài đặt hệ thống (INSTALLATION)
            ("INST-OS", "Cài đặt hệ điều hành Windows / Linux Server", ServiceCategory.INSTALLATION, "Cài đặt chuẩn hóa Windows/Linux Server kèm thiết lập bảo mật baseline", 90, "350000.00"),
            ("INST-SOFT", "Triển khai phần mềm quản trị doanh nghiệp ERP / CRM", ServiceCategory.INSTALLATION, "Cài đặt, triển khai và cấu hình phần mềm ERP, CRM trên máy trạm doanh nghiệp", 120, "600000.00"),
            ("INST-SRV", "Cài đặt và thiết lập máy chủ chuyên dụng", ServiceCategory.INSTALLATION, "Lắp đặt máy chủ tủ rack, cấu hình RAID mảng đĩa và khởi tạo hệ điều hành", 240, "1500000.00"),
            ("INST-NET", "Cấu hình hạ tầng mạng và switch văn phòng", ServiceCategory.INSTALLATION, "Thiết lập phân mạng VLAN, định tuyến Router và cấu hình tường lửa Firewall", 180, "950000.00"),
            ("INST-BAK", "Cấu hình hệ thống sao lưu dự phòng tự động", ServiceCategory.INSTALLATION, "Thiết lập lịch trình sao lưu dữ liệu tự động lên NAS và điện toán đám mây", 120, "750000.00"),

            # 2. Bảo trì hệ thống (MAINTENANCE)
            ("MAIN-PC", "Bảo trì máy tính và máy trạm định kỳ", ServiceCategory.MAINTENANCE, "Vệ sinh phần cứng, kiểm tra nhiệt độ, dọn dẹp hệ điều hành và tối ưu hóa ổ cứng", 60, "250000.00"),
            ("MAIN-SRV", "Bảo trì máy chủ và cập nhật bản vá bảo mật", ServiceCategory.MAINTENANCE, "Cập nhật bản vá lỗ hổng OS, kiểm tra dịch vụ nền tảng và đánh giá tải phần cứng", 120, "700000.00"),
            ("MAIN-NET", "Bảo trì và đo kiểm hệ thống mạng nội bộ", ServiceCategory.MAINTENANCE, "Đo kiểm băng thông, chẩn đoán cáp mạng, kiểm tra switch và rà soát luật tường lửa", 90, "500000.00"),
            ("MAIN-DRILL", "Kiểm tra hệ thống và diễn tập phục hồi thảm họa", ServiceCategory.MAINTENANCE, "Kiểm tra tính toàn vẹn của bản sao lưu và diễn tập khôi phục hệ thống thử nghiệm", 120, "800000.00"),

            # 3. Tư vấn quản trị cơ sở dữ liệu (DATABASE_CONSULTING)
            ("DB-DESIGN", "Thiết kế kiến trúc và lược đồ cơ sở dữ liệu", ServiceCategory.DATABASE_CONSULTING, "Đánh giá mô hình thực thể ERD, chuẩn hóa bảng dữ liệu và lập chiến lược chỉ mục", 180, "1800000.00"),
            ("DB-OPT", "Tối ưu truy vấn SQL và chẩn đoán chỉ mục chậm", ServiceCategory.DATABASE_CONSULTING, "Phân tích kế hoạch thực thi EXPLAIN, tinh chỉnh truy vấn chậm và cấu hình bộ đệm", 120, "1200000.00"),
            ("DB-RECOV", "Tư vấn sao lưu và phục hồi thảm họa DB (Backup/Restore)", ServiceCategory.DATABASE_CONSULTING, "Thiết lập cấu hình nhân bản Replication, sao lưu WAL và phục hồi điểm thời gian PITR", 150, "1400000.00"),
            ("DB-ADMIN", "Tư vấn hiệu năng PostgreSQL / MySQL / SQL Server", ServiceCategory.DATABASE_CONSULTING, "Tối ưu thông số memory buffer, connection pool và chẩn đoán tắc nghẽn I/O hệ thống", 90, "1000000.00"),

            # 4. Sửa chữa thiết bị (DEVICE_REPAIR)
            ("REP-LAP", "Sửa chữa laptop phần cứng và thay thế linh kiện", ServiceCategory.DEVICE_REPAIR, "Chẩn đoán đường nguồn bo mạch, thay thế màn hình hiển thị, bàn phím và pin laptop", 120, "500000.00"),
            ("REP-DESK", "Sửa chữa máy tính để bàn PC và máy trạm Workstation", ServiceCategory.DEVICE_REPAIR, "Xử lý sự cố nguồn PSU, kiểm tra card màn hình GPU, RAM và thay thế linh kiện lỗi", 90, "400000.00"),
            ("REP-SRV", "Sửa chữa và thay thế linh kiện máy chủ Rack Server", ServiceCategory.DEVICE_REPAIR, "Thay thế nguồn kép Redundant PSU, ổ cứng Hot-swap, bo mạch điều khiển RAID", 180, "1600000.00"),
            ("REP-PRN", "Sửa chữa máy in văn phòng và máy in mạng đa chức năng", ServiceCategory.DEVICE_REPAIR, "Xử lý kẹt giấy, thay thế cụm sấy fuser, trục lăn cao su và cấu hình print server", 60, "350000.00"),
            ("REP-NET", "Sửa chữa và phục hồi cấu hình thiết bị mạng Router/Switch", ServiceCategory.DEVICE_REPAIR, "Xử lý lỗi cổng mạng, nạp lại firmware bị lỗi và thay thế biến áp nguồn thiết bị", 90, "450000.00"),
        ]

        service_objects = []
        for code, name, cat, desc, duration, fee in services_raw:
            svc, _ = Service.objects.update_or_create(
                workspace=service_ws,
                code=code,
                defaults={
                    "name": name,
                    "category": cat,
                    "description": desc,
                    "standard_duration_minutes": duration,
                    "base_fee": Decimal(fee),
                    "is_active": True,
                },
            )
            service_objects.append(svc)
        self.stdout.write(f"    Services: {len(service_objects)} IT service catalog items created across 4 categories.")

        # 6.2 SLA Policies
        sla_raw = [
            ("Critical Priority SLA (2h/4h)", SLAPriority.CRITICAL, 2, 4),
            ("High Priority SLA (4h/8h)", SLAPriority.HIGH, 4, 8),
            ("Medium Priority SLA (12h/24h)", SLAPriority.MEDIUM, 12, 24),
            ("Low Priority SLA (24h/48h)", SLAPriority.LOW, 24, 48),
        ]

        sla_objects = {}
        for name, priority, resp_h, resol_h in sla_raw:
            sla_obj, _ = SLA.objects.update_or_create(
                workspace=service_ws,
                priority=priority,
                defaults={
                    "name": name,
                    "response_time_hours": resp_h,
                    "resolution_time_hours": resol_h,
                    "is_active": True,
                },
            )
            sla_objects[priority] = sla_obj
        self.stdout.write(f"    SLA Policies: {len(sla_objects)} priority tiers configured.")

        # 6.3 Technical Staff / Field Engineers (10 IT Engineers with Hourly Rates)
        techs_raw = [
            ("TECH-001", "Trần Văn Minh", "0908111222", "minh.tran@xyzservice.vn", ["SERVER", "LINUX", "WINDOWS", "INSTALLATION"], "220000.00", 10.7760, 106.7000, True),
            ("TECH-002", "Lê Thị Thu Hà", "0908222333", "ha.le@xyzservice.vn", ["DATABASE", "POSTGRESQL", "SQL_SERVER", "DATABASE_CONSULTING"], "280000.00", 10.7820, 106.6950, True),
            ("TECH-003", "Phạm Quốc Bảo", "0908333444", "bao.pham@xyzservice.vn", ["NETWORK", "ROUTER", "SWITCH", "MAINTENANCE"], "200000.00", 10.7650, 106.6820, True),
            ("TECH-004", "Hoàng Văn Đức", "0908444555", "duc.hoang@xyzservice.vn", ["DEVICE_REPAIR", "LAPTOP_REPAIR", "DESKTOP_REPAIR"], "180000.00", 10.7950, 106.7120, True),
            ("TECH-005", "Nguyễn Thanh Sơn", "0908555666", "son.nguyen@xyzservice.vn", ["DATABASE", "DATABASE_CONSULTING", "OPTIMIZATION"], "250000.00", 10.7380, 106.7150, True),
            ("TECH-006", "Đỗ Thị Mai", "0908666777", "mai.do@xyzservice.vn", ["SERVER", "LINUX", "WINDOWS", "INSTALLATION"], "210000.00", 10.8010, 106.6600, True),
            ("TECH-007", "Vũ Hoàng Nam", "0908777888", "nam.vu@xyzservice.vn", ["DEVICE_REPAIR", "SERVER", "PRINTER"], "190000.00", 10.7550, 106.6700, True),
            ("TECH-008", "Bùi Văn Tài", "0908888999", "tai.bui@xyzservice.vn", ["NETWORK", "MAINTENANCE", "SWITCH"], "195000.00", 10.7680, 106.6900, True),
            ("TECH-009", "Ngô Minh Khang", "0908999111", "khang.ngo@xyzservice.vn", ["SERVER", "LINUX", "BACKUP"], "205000.00", 10.7900, 106.7050, True),
            ("TECH-010", "Đặng Thùy Linh", "0908999222", "linh.dang@xyzservice.vn", ["DATABASE", "POSTGRESQL", "DATABASE_CONSULTING"], "260000.00", 10.7720, 106.6980, True),
        ]

        employee_objects = []
        for code, name, phone, email, skills, rate, lat, lng, avail in techs_raw:
            emp, _ = Employee.objects.update_or_create(
                workspace=service_ws,
                code=code,
                defaults={
                    "full_name": name,
                    "phone": phone,
                    "email": email,
                    "skills": skills,
                    "hourly_labor_rate": Decimal(rate),
                    "current_location": Point(lng, lat, srid=4326),
                    "latitude": Decimal(str(lat)),
                    "longitude": Decimal(str(lng)),
                    "location_updated_at": timezone.now(),
                    "is_available": avail,
                    "is_active": True,
                },
            )
            employee_objects.append(emp)
        self.stdout.write(f"    Technicians: {len(employee_objects)} IT engineers provisioned with hourly labor rates.")

        # 6.4 Service Customers (25 Corporate & Enterprise Clients)
        svc_customers_raw = [
            ("CUST-SVC-001", "Vingroup Landmark Tower", "02839990001", "720A Dien Bien Phu, Binh Thanh, HCMC", 10.7950, 106.7218, CustomerSegment.ENTERPRISE),
            ("CUST-SVC-002", "Bitexco Financial Tower Management", "02839990002", "2 Hai Trieu, District 1, HCMC", 10.7716, 106.7044, CustomerSegment.ENTERPRISE),
            ("CUST-SVC-003", "Saigon Centre Property Operations", "02839990003", "65 Le Loi, District 1, HCMC", 10.7735, 106.7010, CustomerSegment.ENTERPRISE),
            ("CUST-SVC-004", "Sunwah Tower Office Administration", "02839990004", "115 Nguyen Hue, District 1, HCMC", 10.7740, 106.7035, CustomerSegment.VIP),
            ("CUST-SVC-005", "Crescent Mall Facility Team", "02839990005", "101 Ton Dat Tien, District 7, HCMC", 10.7285, 106.7180, CustomerSegment.ENTERPRISE),
            ("CUST-SVC-006", "Techcombank Head Office HCMC", "02839990006", "23 Le Duan, District 1, HCMC", 10.7810, 106.7000, CustomerSegment.VIP),
            ("CUST-SVC-007", "FPT Software F-Town Campus", "02839990007", "Saigon Hi-Tech Park, District 9, HCMC", 10.8520, 106.7900, CustomerSegment.ENTERPRISE),
            ("CUST-SVC-008", "VNG Campus Technical Office", "02839990008", "Tan Thuan EPZ, District 7, HCMC", 10.7510, 106.7400, CustomerSegment.ENTERPRISE),
            ("CUST-SVC-009", "Estella Place Management", "02839990009", "88 Song Hanh, An Phu, Thu Duc, HCMC", 10.8015, 106.7490, CustomerSegment.VIP),
            ("CUST-SVC-010", "Diamond Plaza Engineering", "02839990010", "34 Le Duan, District 1, HCMC", 10.7795, 106.6990, CustomerSegment.VIP),
            ("CUST-SVC-011", "Sofitel Plaza Hotel Engineering", "02839990011", "17 Le Duan, District 1, HCMC", 10.7830, 106.7015, CustomerSegment.VIP),
            ("CUST-SVC-012", "Caravelle Saigon Hotel Facilities", "02839990012", "19 Lam Son Square, District 1, HCMC", 10.7765, 106.7030, CustomerSegment.VIP),
            ("CUST-SVC-013", "Shopee Logistics Hub Tan Binh", "02839990013", "Truong Son, Tan Binh, HCMC", 10.8120, 106.6620, CustomerSegment.STANDARD),
            ("CUST-SVC-014", "Lazada Fulfillment Warehouse D7", "02839990014", "Huynh Tan Phat, District 7, HCMC", 10.7420, 106.7320, CustomerSegment.STANDARD),
            ("CUST-SVC-015", "Tiki Express Distribution Center", "02839990015", "Quang Trung Software City, District 12, HCMC", 10.8540, 106.6280, CustomerSegment.STANDARD),
            ("CUST-SVC-016", "Vincom Mega Mall Thao Dien", "02839990016", "159 Hanoi Highway, Thu Duc, HCMC", 10.8040, 106.7410, CustomerSegment.VIP),
            ("CUST-SVC-017", "Giga Mall Thu Duc Maintenance", "02839990017", "240 Pham Van Dong, Thu Duc, HCMC", 10.8280, 106.7210, CustomerSegment.STANDARD),
            ("CUST-SVC-018", "E-Town Central Building", "02839990018", "51 Doan Van Bo, District 4, HCMC", 10.7620, 106.7020, CustomerSegment.VIP),
            ("CUST-SVC-019", "Lim Tower III Technical Team", "02839990019", "29A Nguyen Dinh Chieu, District 1, HCMC", 10.7870, 106.6970, CustomerSegment.VIP),
            ("CUST-SVC-020", "Vietcombank Tower Maintenance", "02839990020", "5 Me Linh Square, District 1, HCMC", 10.7730, 106.7060, CustomerSegment.ENTERPRISE),
            ("CUST-SVC-021", "Saigon Pavillon Residence", "02839990021", "53 Ba Huyen Thanh Quan, District 3, HCMC", 10.7780, 106.6850, CustomerSegment.STANDARD),
            ("CUST-SVC-022", "Leman Luxury Apartments", "02839990022", "117 Nguyen Dinh Chieu, District 3, HCMC", 10.7790, 106.6890, CustomerSegment.STANDARD),
            ("CUST-SVC-023", "Sherwood Residence Operations", "02839990023", "127 Pasteur, District 3, HCMC", 10.7830, 106.6920, CustomerSegment.STANDARD),
            ("CUST-SVC-024", "Masteri An Phu Facilities", "02839990024", "179 Hanoi Highway, Thu Duc, HCMC", 10.8030, 106.7460, CustomerSegment.STANDARD),
            ("CUST-SVC-025", "Vinhomes Central Park Park 5", "02839990025", "208 Nguyen Huu Canh, Binh Thanh, HCMC", 10.7930, 106.7200, CustomerSegment.STANDARD),
        ]

        svc_customer_objs = []
        for code, name, phone, addr, lat, lng, seg in svc_customers_raw:
            c_obj, _ = Customer.objects.update_or_create(
                workspace=service_ws,
                code=code,
                defaults={
                    "name": name,
                    "phone": phone,
                    "address": addr,
                    "location": Point(lng, lat, srid=4326),
                    "latitude": Decimal(str(lat)),
                    "longitude": Decimal(str(lng)),
                    "customer_segment": seg,
                    "is_active": True,
                },
            )
            svc_customer_objs.append(c_obj)
        self.stdout.write(f"    Service Customers: {len(svc_customer_objs)} corporate client accounts registered.")

        # 6.5 Realistic IT Incident Tickets, Tasks, Schedules & Labor Entries (120 tickets across past 90 days)
        self.stdout.write("    Generating 120 realistic IT incident tickets with labor tracking & SLA metrics...")
        incident_templates = [
            # 1. Cài đặt hệ thống (INSTALLATION)
            ("Cài đặt và triển khai máy chủ Linux Ubuntu Server cho cụm microservices", "INST-SRV"),
            ("Triển khai phần mềm quản trị doanh nghiệp ERP trên máy trạm nhân viên", "INST-SOFT"),
            ("Cấu hình hạ tầng phân mạng VLAN và switch quản lý cho văn phòng mới", "INST-NET"),
            ("Cài đặt máy chủ Windows Server Active Directory và cấu hình chính sách GPO", "INST-OS"),
            ("Thiết lập hệ thống sao lưu dữ liệu tự động lên thiết bị lưu trữ NAS", "INST-BAK"),

            # 2. Bảo trì hệ thống (MAINTENANCE)
            ("Bảo trì máy chủ định kỳ và rà soát cập nhật bản vá an ninh bảo mật", "MAIN-SRV"),
            ("Vệ sinh phần cứng, dọn dẹp hệ điều hành máy tính văn phòng định kỳ quý", "MAIN-PC"),
            ("Đo kiểm băng thông, độ trễ và bảo trì thiết bị switch mạng trung tâm", "MAIN-NET"),
            ("Diễn tập khôi phục dữ liệu định kỳ từ hệ thống sao lưu dự phòng", "MAIN-DRILL"),

            # 3. Tư vấn quản trị cơ sở dữ liệu (DATABASE_CONSULTING)
            ("Tối ưu truy vấn SQL chậm và chẩn đoán chỉ mục bảng cơ sở dữ liệu sản xuất", "DB-OPT"),
            ("Tư vấn thiết kế lại cấu trúc lược đồ cơ sở dữ liệu phục vụ thương mại điện tử", "DB-DESIGN"),
            ("Điều tra và khắc phục lỗi đồng bộ sao chép dữ liệu Replication cơ sở dữ liệu", "DB-RECOV"),
            ("Kiểm toán hiệu năng, phân bổ bộ đệm buffer và kết nối connection pool PostgreSQL", "DB-ADMIN"),

            # 4. Sửa chữa thiết bị (DEVICE_REPAIR)
            ("Sửa chữa lỗi bo mạch chủ và đường nguồn laptop phòng kỹ thuật không khởi động", "REP-LAP"),
            ("Khắc phục sự cố máy tính để bàn văn phòng phát tiếng bíp liên tục và lỗi nguồn", "REP-DESK"),
            ("Thay thế bộ nguồn kép dự phòng Redundant PSU cho máy chủ dữ liệu Rack Server", "REP-SRV"),
            ("Sửa chữa máy in laser mạng đa chức năng bị kẹt giấy và mòn cụm sấy", "REP-PRN"),
            ("Sửa chữa và phục hồi cấu hình thiết bị bộ định tuyến Router văn phòng", "REP-NET"),
        ]

        now = timezone.now()
        created_requests = 0
        total_labor_entries_count = 0
        total_labor_cost_accum = Decimal("0.00")

        # Clean existing demo tickets for fresh idempotent seeding
        ServiceRequest.objects.filter(workspace=service_ws).delete()

        # Deterministic pseudo-random seed for repeatable generation
        rand_gen = random.Random(42)

        for i in range(1, 121):
            title_template, svc_code = rand_gen.choice(incident_templates)
            svc = next(s for s in service_objects if s.code == svc_code)
            cust = rand_gen.choice(svc_customer_objs)
            priority = rand_gen.choices(
                [SLAPriority.CRITICAL, SLAPriority.HIGH, SLAPriority.MEDIUM, SLAPriority.LOW],
                weights=[15, 30, 45, 10],
            )[0]
            sla_policy = sla_objects[priority]

            # Date distribution over past 90 days
            days_ago = rand_gen.randint(1, 90)
            hours_ago = rand_gen.randint(1, 23)
            ticket_created_at = now - timedelta(days=days_ago, hours=hours_ago)

            response_deadline = ticket_created_at + timedelta(hours=sla_policy.response_time_hours)
            resolution_deadline = ticket_created_at + timedelta(hours=sla_policy.resolution_time_hours)

            # Ticket lifecycle distribution based on age
            if days_ago > 7:
                # Older tickets are mostly RESOLVED or CLOSED
                status_choice = rand_gen.choices(
                    [ServiceRequestStatus.CLOSED, ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CANCELLED],
                    weights=[70, 25, 5],
                )[0]
            elif days_ago > 2:
                status_choice = rand_gen.choices(
                    [ServiceRequestStatus.RESOLVED, ServiceRequestStatus.IN_PROGRESS, ServiceRequestStatus.ASSIGNED],
                    weights=[45, 35, 20],
                )[0]
            else:
                status_choice = rand_gen.choices(
                    [ServiceRequestStatus.IN_PROGRESS, ServiceRequestStatus.ASSIGNED, ServiceRequestStatus.OPEN],
                    weights=[40, 40, 20],
                )[0]

            assigned_tech = rand_gen.choice(employee_objects) if status_choice != ServiceRequestStatus.OPEN else None

            # SLA outcome: 75% on-time, 15% at risk, 10% breached
            sla_outcome = rand_gen.choices(["ON_TIME", "AT_RISK", "BREACHED"], weights=[75, 15, 10])[0]

            responded_at = None
            resolved_at = None
            closed_at = None

            if status_choice != ServiceRequestStatus.OPEN:
                if sla_outcome == "BREACHED":
                    responded_at = ticket_created_at + timedelta(hours=sla_policy.response_time_hours + rand_gen.randint(1, 5))
                else:
                    responded_at = ticket_created_at + timedelta(hours=max(0.5, sla_policy.response_time_hours * 0.4))

            if status_choice in [ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED]:
                if sla_outcome == "BREACHED":
                    resolved_at = ticket_created_at + timedelta(hours=sla_policy.resolution_time_hours + rand_gen.randint(2, 10))
                else:
                    resolved_at = ticket_created_at + timedelta(hours=max(1.0, sla_policy.resolution_time_hours * 0.6))

                if status_choice == ServiceRequestStatus.CLOSED:
                    closed_at = resolved_at + timedelta(hours=rand_gen.randint(1, 24))

            req_num = f"SR-{ticket_created_at.strftime('%Y%m%d')}-{i:04d}"

            req = ServiceRequest.objects.create(
                workspace=service_ws,
                request_number=req_num,
                customer=cust,
                service=svc,
                sla=sla_policy,
                assigned_employee=assigned_tech,
                title=f"{title_template} ({cust.name})",
                description=f"Phiếu dịch vụ IT cho {cust.name}. Phân loại: {svc.get_category_display()}. Mã dịch vụ: {svc.code}.",
                location=cust.location,
                latitude=cust.latitude,
                longitude=cust.longitude,
                priority=priority,
                status=status_choice,
                scheduled_at=ticket_created_at + timedelta(hours=2) if assigned_tech else None,
                response_deadline_at=response_deadline,
                resolution_deadline_at=resolution_deadline,
                responded_at=responded_at,
                resolved_at=resolved_at,
                closed_at=closed_at,
            )
            # Override auto_now_add for historical distribution
            ServiceRequest.objects.filter(id=req.id).update(created_at=ticket_created_at)

            # Create operational Task
            task_status = TaskStatus.PENDING
            if status_choice == ServiceRequestStatus.IN_PROGRESS:
                task_status = TaskStatus.IN_PROGRESS
            elif status_choice in [ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED]:
                task_status = TaskStatus.COMPLETED
            elif status_choice == ServiceRequestStatus.CANCELLED:
                task_status = TaskStatus.CANCELLED

            actual_duration = svc.standard_duration_minutes + rand_gen.randint(-15, 30) if task_status == TaskStatus.COMPLETED else None

            task_obj = Task.objects.create(
                service_request=req,
                assigned_to=assigned_tech,
                title=f"Thực hiện: {svc.name}",
                description=f"Thao tác kỹ thuật IT cho khách hàng {cust.name}",
                status=task_status,
                priority=priority,
                estimated_duration_minutes=svc.standard_duration_minutes,
                actual_duration_minutes=actual_duration,
                started_at=responded_at if task_status in [TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED] else None,
                completed_at=resolved_at if task_status == TaskStatus.COMPLETED else None,
                due_at=resolution_deadline,
            )

            # Create technician schedule slot
            if assigned_tech and status_choice != ServiceRequestStatus.CANCELLED:
                sch_start = (responded_at or ticket_created_at + timedelta(hours=1))
                sch_end = sch_start + timedelta(minutes=svc.standard_duration_minutes)
                sch_status = ScheduleStatus.DONE if task_status == TaskStatus.COMPLETED else (
                    ScheduleStatus.IN_PROGRESS if task_status == TaskStatus.IN_PROGRESS else ScheduleStatus.SCHEDULED
                )
                Schedule.objects.create(
                    task=task_obj,
                    employee=assigned_tech,
                    start_time=sch_start,
                    end_time=sch_end,
                    status=sch_status,
                    notes=f"Dispatch for ticket #{req_num}",
                )

            # Create Labor Entries for active / completed work
            if assigned_tech and status_choice in [ServiceRequestStatus.IN_PROGRESS, ServiceRequestStatus.RESOLVED, ServiceRequestStatus.CLOSED]:
                work_duration = actual_duration or rand_gen.randint(45, svc.standard_duration_minutes)
                work_start = responded_at or (ticket_created_at + timedelta(hours=1))
                work_end = work_start + timedelta(minutes=work_duration)

                rate_snapshot = assigned_tech.hourly_labor_rate
                hours_dec = Decimal(str(work_duration)) / Decimal("60.0")
                labor_cost_val = round(hours_dec * rate_snapshot, 2)

                LaborEntry.objects.create(
                    task=task_obj,
                    employee=assigned_tech,
                    started_at=work_start,
                    ended_at=work_end,
                    duration_minutes=work_duration,
                    hourly_rate_snapshot=rate_snapshot,
                    labor_cost=labor_cost_val,
                    notes=f"Completed technical service tasks for ticket #{req_num}.",
                )
                total_labor_entries_count += 1
                total_labor_cost_accum += labor_cost_val

            created_requests += 1

        # Recalculate all technician workload scores
        for tech in employee_objects:
            active_cnt = Task.objects.filter(assigned_to=tech, status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS]).count()
            overdue_cnt = Task.objects.filter(assigned_to=tech, status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS], due_at__lt=now).count()
            tech.current_workload_score = round(active_cnt * 1.0 + (overdue_cnt * 1.5), 2)
            tech.save(update_fields=["current_workload_score"])

        self.stdout.write(
            self.style.SUCCESS(
                f"    Service Requests: {created_requests} tickets, tasks, and schedules created.\n"
                f"    Labor Entries: {total_labor_entries_count} labor records ({total_labor_cost_accum:,.0f} VND realized labor cost).\n"
                f"    Workload & SLA indicators calibrated across XYZ IT Technical Services."
            )
        )

        # =========================================================================
        # 7. Seeding Data Integration Sources & Initial Staging (Phase 6)
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 7. Seeding Data Integration Sources (Phase 6)..."))

        # Retail Data Sources
        ds_retail_csv, _ = DataSource.objects.update_or_create(
            workspace=retail_ws,
            name="Legacy POS Orders CSV Feed",
            defaults={
                "source_type": SourceType.CSV,
                "connection_config": {"delimiter": ","},
                "is_active": True,
                "created_by": admin_user,
            },
        )
        ds_retail_excel, _ = DataSource.objects.update_or_create(
            workspace=retail_ws,
            name="Supplier Product Catalog Excel",
            defaults={
                "source_type": SourceType.EXCEL,
                "connection_config": {"sheet_name": "Customers"},
                "is_active": True,
                "created_by": admin_user,
            },
        )
        ds_retail_api, _ = DataSource.objects.update_or_create(
            workspace=retail_ws,
            name="Partner E-Commerce Orders Mock API",
            defaults={
                "source_type": SourceType.MOCK_API,
                "connection_config": {"url": "/api/v1/mock-external/retail/orders/"},
                "is_active": True,
                "created_by": admin_user,
            },
        )

        # Service Data Sources
        ds_service_csv, _ = DataSource.objects.update_or_create(
            workspace=service_ws,
            name="Helpdesk Incident Tickets CSV",
            defaults={
                "source_type": SourceType.CSV,
                "connection_config": {"delimiter": ","},
                "is_active": True,
                "created_by": admin_user,
            },
        )
        ds_service_excel, _ = DataSource.objects.update_or_create(
            workspace=service_ws,
            name="Subcontractor Technicians Excel",
            defaults={
                "source_type": SourceType.EXCEL,
                "connection_config": {"sheet_name": "Technicians"},
                "is_active": True,
                "created_by": admin_user,
            },
        )
        ds_service_api, _ = DataSource.objects.update_or_create(
            workspace=service_ws,
            name="Corporate Client Ticketing Mock API",
            defaults={
                "source_type": SourceType.MOCK_API,
                "connection_config": {"url": "/api/v1/mock-external/service/tickets/"},
                "is_active": True,
                "created_by": admin_user,
            },
        )

        # Execute mock API ingestion jobs for demo workspaces
        if not ImportJob.objects.for_workspace(retail_ws).filter(data_source=ds_retail_api).exists():
            execute_import_job(
                workspace=retail_ws,
                user=admin_user,
                data_source=ds_retail_api,
                entity_type=EntityType.RETAIL_ORDERS,
            )

        if not ImportJob.objects.for_workspace(service_ws).filter(data_source=ds_service_api).exists():
            execute_import_job(
                workspace=service_ws,
                user=admin_user,
                data_source=ds_service_api,
                entity_type=EntityType.SERVICE_REQUESTS,
            )

        # =========================================================================
        # 10. Seeding Data Mapping Profiles & Canonical Rules (Phase 7)
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 10. Seeding Mapping Profiles & Canonical Rules..."))
        from apps.mapping.models import MappingProfile, MappingRule, RuleType, AIConfirmationStatus

        # Retail Orders Mapping Profile
        mp_retail_orders, _ = MappingProfile.objects.update_or_create(
            workspace=retail_ws,
            name="Partner E-Commerce Orders Mapping",
            defaults={
                "target_entity": "Order",
                "data_source": ds_retail_api,
                "description": "Transforms mock external retail order feeds into canonical Order records.",
                "is_active": True,
                "created_by": admin_user,
            },
        )

        retail_rules = [
            ("ma_don_hang", "order_number", RuleType.FIELD_MAPPING, {}, 1.0, 1),
            ("ma_khach_hang", "customer_id", RuleType.FIELD_MAPPING, {}, 1.0, 2),
            ("chi_nhanh_giao", "branch_code", RuleType.FIELD_MAPPING, {}, 1.0, 3),
            ("ngay_dat_hang", "order_date", RuleType.TYPE_CONVERSION, {"target_type": "DATE"}, 1.0, 4),
            ("tong_thanh_toan", "revenue", RuleType.TYPE_CONVERSION, {"target_type": "DECIMAL"}, 1.0, 5),
            ("trang_thai_don", "status", RuleType.VALUE_MAPPING, {"value_map": {"da_giao": "COMPLETED", "cho_xu_ly": "PENDING", "da_huy": "CANCELLED"}, "default": "COMPLETED"}, 1.0, 6),
        ]
        for src, tgt, rtype, cfg, conf, ord_num in retail_rules:
            MappingRule.objects.update_or_create(
                workspace=retail_ws,
                profile=mp_retail_orders,
                target_field=tgt,
                defaults={
                    "source_field": src,
                    "rule_type": rtype,
                    "transformation_config": cfg,
                    "confidence_score": conf,
                    "ai_status": AIConfirmationStatus.ACCEPTED,
                    "is_active": True,
                    "order": ord_num,
                    "created_by": admin_user,
                },
            )

        # Service Incident Tickets Mapping Profile
        mp_service_tickets, _ = MappingProfile.objects.update_or_create(
            workspace=service_ws,
            name="Corporate Ticketing Incidents Mapping",
            defaults={
                "target_entity": "ServiceRequest",
                "data_source": ds_service_api,
                "description": "Maps external IT helpdesk incident tickets into canonical ServiceRequests.",
                "is_active": True,
                "created_by": admin_user,
            },
        )

        service_rules = [
            ("ma_ticket", "request_number", RuleType.FIELD_MAPPING, {}, 1.0, 1),
            ("khach_hang", "customer_id", RuleType.FIELD_MAPPING, {}, 1.0, 2),
            ("loai_dich_vu", "service_code", RuleType.FIELD_MAPPING, {}, 1.0, 3),
            ("dia_diem_su_co", "title", RuleType.FIELD_MAPPING, {}, 1.0, 4),
            ("muc_do_uu_tien", "priority", RuleType.VALUE_MAPPING, {"value_map": {"cao": "HIGH", "trung_binh": "MEDIUM", "thap": "LOW", "khan_cap": "CRITICAL"}, "default": "MEDIUM"}, 1.0, 5),
        ]
        for src, tgt, rtype, cfg, conf, ord_num in service_rules:
            MappingRule.objects.update_or_create(
                workspace=service_ws,
                profile=mp_service_tickets,
                target_field=tgt,
                defaults={
                    "source_field": src,
                    "rule_type": rtype,
                    "transformation_config": cfg,
                    "confidence_score": conf,
                    "ai_status": AIConfirmationStatus.ACCEPTED,
                    "is_active": True,
                    "order": ord_num,
                    "created_by": admin_user,
                },
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"    Mapping Profiles: Configured default mapping profiles for Retail Orders and Service Tickets."
            )
        )

        # =========================================================================
        # 8. Knowledge Bases & Grounded RAG Documentation (Phase 8)
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 8. Seeding Knowledge Bases & Ingesting Grounded Documents..."))

        import io
        import docx
        from django.core.files.base import ContentFile
        from apps.knowledge.models import KnowledgeBase
        from apps.knowledge.services import upload_and_ingest_document

        def _make_docx_file(title: str, sections: list) -> ContentFile:
            doc = docx.Document()
            doc.add_heading(title, level=0)
            for heading, text in sections:
                if heading:
                    doc.add_heading(heading, level=1)
                doc.add_paragraph(text)
            bio = io.BytesIO()
            doc.save(bio)
            safe_name = title.lower().replace(" ", "_").replace("(", "").replace(")", "")[:40] + ".docx"
            return ContentFile(bio.getvalue(), name=safe_name)

        # 8.1 Retail Knowledge Base & 4 Policies
        kb_retail, _ = KnowledgeBase.objects.update_or_create(
            workspace=retail_ws,
            name="Quy chế Bán hàng & Dịch vụ Khách hàng",
            defaults={
                "description": "Kho tri thức chính sách bán hàng, bảo hành sản phẩm và chương trình khách hàng thân thiết.",
                "is_active": True,
                "created_by": admin_user,
            },
        )

        # Ensure fresh re-ingestion of retail documents
        for doc in kb_retail.documents.all():
            doc.delete()

        retail_docs = [
            (
                "Chính Sách Bán Hàng Và Đổi Trả",
                [
                    ("Quy định đổi trả hàng", "Khách hàng mua sản phẩm tại chuỗi cửa hàng công nghệ ABC Tech Store được quyền đổi trả sản phẩm thiết bị, linh kiện hoặc phụ kiện trong vòng 07 ngày kể từ ngày mua hàng. Sản phẩm đổi trả phải còn nguyên tem mác, hộp đóng gói ban đầu và hóa đơn mua hàng hợp lệ. Các sản phẩm giảm giá thanh lý không áp dụng chính sách đổi trả."),
                    ("Điều khoản thanh toán và tín dụng", "Hệ thống hỗ trợ thanh toán qua chuyển khoản ngân hàng, thẻ tín dụng, tiền mặt và ví điện tử. Đơn hàng từ 10.000.000 VND trở lên áp dụng chính sách trả góp 0% lãi suất qua thẻ tín dụng liên kết trong kỳ hạn 3 đến 6 tháng."),
                ]
            ),
            (
                "Chính Sách Bảo Hành Thiết Bị",
                [
                    ("Thời hạn bảo hành tiêu chuẩn", "Thiết bị máy tính xách tay (Laptop) được bảo hành chính hãng 24 tháng kể từ ngày xuất hóa đơn. Điện thoại thông minh và máy tính bảng được bảo hành 12 tháng. Phụ kiện cáp sạc, bàn phím và tai nghe được bảo hành 06 tháng. Màn hình máy tính được bảo hành nếu xuất hiện từ 3 điểm chết trở lên."),
                    ("Chính sách đổi mới 1 đổi 1", "Trong 30 ngày đầu tiên kể từ khi mua, nếu sản phẩm phát sinh lỗi kỹ thuật phần cứng do nhà sản xuất (không lên nguồn, lỗi bo mạch chủ), khách hàng được áp dụng chính sách 1 đổi 1 sang máy mới tương đương nguyên seal."),
                ]
            ),
            (
                "Quy Chế Khách Hàng VIP",
                [
                    ("Phân hạng khách hàng", "Khách hàng được phân loại thành ba phân khúc: Tiêu chuẩn (Standard), Khách hàng VIP và Khách hàng Doanh nghiệp (Enterprise). Hạng VIP yêu cầu tổng chi tiêu tích lũy tối thiểu 50.000.000 VND trong năm tài chính hiện tại."),
                    ("Quyền lợi khách hàng VIP", "Khách hàng hạng VIP được chiết khấu trực tiếp 10% trên tổng giá trị mọi đơn hàng mua sắm tại cửa hàng hoặc trực tuyến, miễn phí giao hàng hỏa tốc trong bán kính 15km và được tặng quà sinh nhật độc quyền."),
                ]
            ),
            (
                "Cẩm Nang Khuyến Mãi Flash Sale",
                [
                    ("Quy định Flash Sale", "Các chương trình khuyến mãi chớp nhoáng (Flash Sale) diễn ra định kỳ vào thứ 6 hàng tuần từ 12h00 đến 14h00. Mỗi khách hàng chỉ được mua tối đa 02 sản phẩm giảm giá sâu trong một lượt đặt hàng."),
                    ("Hạn mức và hiệu lực Voucher", "Mỗi hóa đơn thanh toán chỉ được áp dụng duy nhất 01 mã voucher giảm giá. Voucher không có giá trị quy đổi thành tiền mặt và không được cộng dồn đồng thời cùng các chương trình Flash Sale khác."),
                ]
            ),
        ]

        for doc_title, doc_sections in retail_docs:
            cf = _make_docx_file(doc_title, doc_sections)
            upload_and_ingest_document(
                workspace=retail_ws,
                user=admin_user,
                knowledge_base=kb_retail,
                file_obj=cf,
                title=doc_title,
                file_type="DOCX",
            )

        self.stdout.write(f"    Retail Knowledge: Ingested {len(retail_docs)} organizational policy documents.")

        # 8.2 Service Knowledge Base & 5 SOPs
        kb_service, _ = KnowledgeBase.objects.update_or_create(
            workspace=service_ws,
            name="Quy trình & Tiêu chuẩn Vận hành Dịch vụ",
            defaults={
                "description": "Kho tài liệu tiêu chuẩn quy trình kỹ thuật, bảo trì thiết bị và cam kết mức độ dịch vụ SLA.",
                "is_active": True,
                "created_by": admin_user,
            },
        )

        # Ensure fresh re-ingestion of service documents
        for doc in kb_service.documents.all():
            doc.delete()

        service_docs = [
            (
                "Quy Trình Lắp Đặt Máy Chủ Và Mạng",
                [
                    ("Kiểm tra hạ tầng trước triển khai", "Kỹ thuật viên phải kiểm tra nguồn điện dự phòng UPS, hệ thống điều hòa làm mát và tiếp địa tủ rack trước khi lắp đặt máy chủ. Mọi thao tác phải sử dụng găng tay và vòng đeo chống tĩnh điện ESD."),
                    ("Quy trình kiểm thử tải", "Sau khi lắp đặt hoàn tất, kỹ thuật viên phải chạy kiểm thử tải liên tục trong 24 giờ, theo dõi nhiệt độ CPU dưới 65 độ C trước khi ký biên bản nghiệm thu bàn giao."),
                ]
            ),
            (
                "Quy Trình Bảo Trì Định Kỳ Hạ Tầng IT",
                [
                    ("Lịch trình bảo dưỡng định kỳ", "Bảo dưỡng định kỳ được thực hiện vào cuối mỗi quý. Quy trình bao gồm hút bụi công nghiệp phòng máy chủ, kiểm tra độ mòn quạt tản nhiệt, tra keo tản nhiệt và đo điện áp nguồn cấp."),
                    ("Sao lưu trước khi bảo trì", "Trước khi can thiệp phần cứng hoặc cập nhật firmware, kỹ thuật viên bắt buộc phải sao lưu toàn bộ cấu hình thiết bị (backup config) và kiểm tra khả năng khôi phục dự phòng."),
                ]
            ),
            (
                "Hướng Dẫn Tối Ưu Hóa PostgreSQL",
                [
                    ("Chẩn đoán truy vấn chậm", "Sử dụng pg_stat_statements để nhận diện các câu lệnh SQL tốn CPU và I/O cao nhất. Phân tích kế hoạch thực thi EXPLAIN (ANALYZE, BUFFERS) để tối ưu việc quét bảng Sequential Scan."),
                    ("Chiến lược lập chỉ mục", "Tạo B-tree index cho các khóa ngoại và điều kiện lọc chính xác. Sử dụng BRIN index cho các bảng dữ liệu lịch sử theo thời gian lớn hơn 10 triệu dòng để tiết kiệm bộ nhớ RAM."),
                ]
            ),
            (
                "Quy Chuẩn Sửa Chữa Thiết Bị Phần Cứng",
                [
                    ("Tiếp nhận và lập biên bản", "Khi tiếp nhận thiết bị lỗi từ khách hàng, nhân viên phải lập biên bản kiểm tra tình trạng ngoại quan, chụp ảnh niêm phong và sao chép số serial. Yêu cầu khách hàng xác nhận mật khẩu kiểm thử."),
                    ("Bảo mật dữ liệu khách hàng", "Nghiêm cấm kỹ thuật viên sao chép hoặc xem trộm dữ liệu cá nhân của khách hàng trên ổ cứng. Thiết bị sửa chữa bo mạch phải được khử từ và kiểm tra độ cách điện."),
                ]
            ),
            (
                "Cam Kết Mức Độ Dịch Vụ Kỹ Thuật SLA",
                [
                    ("Sự cố mức độ Critical", "Đối với sự cố dừng toàn bộ hệ thống sản xuất (Critical), đội ngũ kỹ thuật cam kết phản hồi khách hàng trong vòng 15 phút và xử lý dứt điểm sự cố trong vòng 02 giờ."),
                    ("Sự cố mức độ High và Medium", "Sự cố mức độ High cam kết phản hồi trong 01 giờ và giải quyết trong 08 giờ. Sự cố Medium cam kết phản hồi trong 04 giờ và giải quyết trong 24 giờ làm việc."),
                ]
            ),
        ]

        for doc_title, doc_sections in service_docs:
            cf = _make_docx_file(doc_title, doc_sections)
            upload_and_ingest_document(
                workspace=service_ws,
                user=admin_user,
                knowledge_base=kb_service,
                file_obj=cf,
                title=doc_title,
                file_type="DOCX",
            )

        self.stdout.write(f"    Service Knowledge: Ingested {len(service_docs)} SOP and SLA documents.")

        # =========================================================================
        # 10. Predictive Analytics & XGBoost Forecasters (Phase 9)
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 10. Seeding Predictive Analytics & XGBoost Forecasters..."))
        from apps.forecasting.training import train_forecast_model
        from apps.forecasting.models import TargetType
        from apps.forecasting.services import get_or_create_default_config

        # 10.1 Retail Revenue Forecaster
        retail_rev_cfg = get_or_create_default_config(retail_ws, TargetType.RETAIL_REVENUE)
        try:
            rev_run = train_forecast_model(
                workspace=retail_ws,
                target_type=TargetType.RETAIL_REVENUE,
                model_config=retail_rev_cfg,
                user=admin_user,
                horizon_days=14,
            )
            self.stdout.write(f"    Retail Revenue Forecaster: Run #{rev_run.id} trained (MAE: {rev_run.model_metrics.get('mae')}, MAPE: {rev_run.model_metrics.get('mape')}%)")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Retail Revenue training note: {e}"))

        # 10.2 Retail Order Volume Forecaster
        retail_vol_cfg = get_or_create_default_config(retail_ws, TargetType.RETAIL_ORDER_VOLUME)
        try:
            vol_run = train_forecast_model(
                workspace=retail_ws,
                target_type=TargetType.RETAIL_ORDER_VOLUME,
                model_config=retail_vol_cfg,
                user=admin_user,
                horizon_days=14,
            )
            self.stdout.write(f"    Retail Order Volume Forecaster: Run #{vol_run.id} trained (MAE: {vol_run.model_metrics.get('mae')}, MAPE: {vol_run.model_metrics.get('mape')}%)")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Retail Order Volume training note: {e}"))

        # 10.3 Service Ticket Volume Forecaster
        service_vol_cfg = get_or_create_default_config(service_ws, TargetType.SERVICE_TICKET_VOLUME)
        try:
            svc_run = train_forecast_model(
                workspace=service_ws,
                target_type=TargetType.SERVICE_TICKET_VOLUME,
                model_config=service_vol_cfg,
                user=admin_user,
                horizon_days=14,
            )
            self.stdout.write(f"    Service Ticket Volume Forecaster: Run #{svc_run.id} trained (MAE: {svc_run.model_metrics.get('mae')}, MAPE: {svc_run.model_metrics.get('mape')}%)")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Service Ticket Volume training note: {e}"))

        # =========================================================================
        # 11. Initial Recommendations (Retail Stockout Alerts & Service Recommendations)
        # =========================================================================
        self.stdout.write(self.style.NOTICE("==> 11. Seeding Decision Support Recommendations..."))
        from apps.recommendations.rules import evaluate_retail_recommendations, evaluate_service_recommendations
        try:
            r_recs = evaluate_retail_recommendations(retail_ws)
            s_recs = evaluate_service_recommendations(service_ws)
            self.stdout.write(f"    Recommendations generated: {len(r_recs)} Retail (including Stockout Alerts), {len(s_recs)} Service.")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"    Recommendations note: {e}"))

        self.stdout.write(self.style.SUCCESS("\n==> SEED COMPLETED SUCCESSFULLY! All demo users, roles, workspaces, retail, service, GIS, integration, mapping, knowledge & forecasting models ready."))




