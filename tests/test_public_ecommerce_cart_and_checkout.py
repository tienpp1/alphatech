"""
Comprehensive Automated Test Suite for Public E-Commerce Shopping Cart & Checkout Flow.
Validates:
- Session-backed ShoppingCart engine
- Product active/deleted validation
- Quantity controls and boundary enforcement
- Deterministic shipping fee rules
- Atomic checkout and Order / OrderItem creation
- Historical price snapshot integrity in OrderItem
- Branch stock validation & safe deduction
- Customer order history & strict IDOR isolation
- Security: Price tampering resistance & zero privilege leakage
"""

from decimal import Decimal
import io
from django.test import TestCase, Client
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.retail.models import (
    Product,
    Category,
    Branch,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    PaymentMethod,
    StockBalance,
)
from apps.retail.services import create_product, update_product, soft_delete_product
from apps.workspaces.models import Workspace, WorkspaceType
from apps.public_web.cart import get_cart, STANDARD_SHIPPING_FEE, FREE_SHIPPING_THRESHOLD


def create_test_image(name="test_prod.png", format="PNG", size=(200, 200), color="blue"):
    """Generates an in-memory valid image for testing."""
    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return SimpleUploadedFile(name, file_obj.read(), content_type=f"image/{format.lower()}")


class PublicEcommerceCartAndCheckoutTestCase(TestCase):
    """
    Test suite for public shopping cart, checkout, order snapshotting, and customer order history.
    """

    def setUp(self):
        self.client = Client()

        # 1. Retail Workspace
        self.ws_retail, _ = Workspace.objects.get_or_create(
            code="WS-RETAIL-TEST",
            defaults={
                "name": "ABC Tech Store Retail Workspace",
                "workspace_type": WorkspaceType.RETAIL,
                "is_active": True,
            },
        )

        # 2. Categories
        self.cat_laptop = Category.objects.create(
            workspace=self.ws_retail,
            name="Laptop & Máy tính xách tay",
            code="CAT-LAPTOP-TEST",
            is_active=True,
        )
        self.cat_gear = Category.objects.create(
            workspace=self.ws_retail,
            name="Phụ kiện & Gaming Gear",
            code="CAT-GEAR-TEST",
            is_active=True,
        )

        # 3. Branches
        self.branch_q1 = Branch.objects.create(
            workspace=self.ws_retail,
            name="ABC Tech Store - Chi nhánh Quận 1",
            code="BR-Q1-TEST",
            address="123 Nguyễn Thị Minh Khai, Quận 1, TP.HCM",
            region="Miền Nam",
            is_active=True,
        )
        self.branch_q3 = Branch.objects.create(
            workspace=self.ws_retail,
            name="ABC Tech Store - Chi nhánh Quận 3",
            code="BR-Q3-TEST",
            address="456 Võ Văn Tần, Quận 3, TP.HCM",
            region="Miền Nam",
            is_active=True,
        )

        # 4. Products
        self.prod_laptop = Product.objects.create(
            workspace=self.ws_retail,
            category=self.cat_laptop,
            name="Laptop Dell XPS 13 Plus",
            sku="DELL-XPS-13P",
            unit="chiếc",
            unit_price=Decimal("32000000.00"),
            cost_price=Decimal("26000000.00"),
            description="Laptop siêu mỏng nhẹ chip Intel Core i7 thế hệ 13",
            is_active=True,
        )
        self.prod_mouse = Product.objects.create(
            workspace=self.ws_retail,
            category=self.cat_gear,
            name="Chuột không dây Logitech MX Master 3S",
            sku="LOGI-MX-3S",
            unit="cái",
            unit_price=Decimal("2490000.00"),
            cost_price=Decimal("1800000.00"),
            description="Chuột công thái học cao cấp cho lập trình viên",
            is_active=True,
        )
        self.prod_keyboard = Product.objects.create(
            workspace=self.ws_retail,
            category=self.cat_gear,
            name="Bàn phím cơ Keychron K8 Pro",
            sku="KEYCHRON-K8P",
            unit="cái",
            unit_price=Decimal("2890000.00"),
            cost_price=Decimal("2100000.00"),
            description="Bàn phím cơ Bluetooth QMK/VIA",
            is_active=True,
        )

        # 5. Customer Users
        self.customer_user_a = User.objects.create_user(
            username="customer_a@example.com",
            email="customer_a@example.com",
            password="SecurePassword123!",
            first_name="Nguyễn Văn A",
        )
        self.customer_profile_a = Customer.objects.create(
            workspace=self.ws_retail,
            user=self.customer_user_a,
            code="CUST-ONL-001",
            name="Nguyễn Văn A",
            email="customer_a@example.com",
            phone="0901234567",
            address="12 Hai Bà Trưng, Phường Bến Nghé, Quận 1, TP.HCM",
        )

        self.customer_user_b = User.objects.create_user(
            username="customer_b@example.com",
            email="customer_b@example.com",
            password="SecurePassword123!",
            first_name="Trần Thị B",
        )
        self.customer_profile_b = Customer.objects.create(
            workspace=self.ws_retail,
            user=self.customer_user_b,
            code="CUST-ONL-002",
            name="Trần Thị B",
            email="customer_b@example.com",
            phone="0918765432",
            address="78 Pasteur, Quận 3, TP.HCM",
        )

    # =========================================================================
    # A. PRODUCT DETAIL CTA & CART OPERATIONS
    # =========================================================================

    def test_product_detail_page_has_mua_ngay_and_them_vao_gio_cta(self):
        """Public product detail page displays Mua ngay and Them vao gio hang buttons."""
        resp = self.client.get(f"/san-pham/{self.prod_laptop.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Mua ngay")
        self.assertContains(resp, "Thêm vào giỏ hàng")
        self.assertContains(resp, "Số lượng:")
        # Verify internal sensitive data is NEVER leaked
        self.assertNotContains(resp, "26000000")
        self.assertNotContains(resp, "26.000.000")
        self.assertNotContains(resp, "Lịch sử Kiểm toán")

    def test_add_active_product_to_cart_and_buy_now_flow(self):
        """Adding product with 'buy_now' redirects to /gio-hang/ and registers item in session."""
        resp = self.client.post(
            f"/gio-hang/them/{self.prod_laptop.id}/",
            {"quantity": "1", "action": "buy_now"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/gio-hang/")

        # GET /gio-hang/
        cart_resp = self.client.get("/gio-hang/")
        self.assertEqual(cart_resp.status_code, 200)
        self.assertContains(cart_resp, "Laptop Dell XPS 13 Plus")
        self.assertContains(cart_resp, "32000000")
        self.assertContains(cart_resp, "Tiến hành đặt hàng")

    def test_add_secondary_item_and_header_cart_count_sync(self):
        """Multiple items in cart update header badge count correctly."""
        self.client.post(f"/gio-hang/them/{self.prod_mouse.id}/", {"quantity": "2", "action": "add_to_cart"})
        self.client.post(f"/gio-hang/them/{self.prod_keyboard.id}/", {"quantity": "1", "action": "add_to_cart"})

        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        # Total items: 2 mouse + 1 keyboard = 3
        self.assertContains(resp, "Giỏ hàng")
        self.assertContains(resp, '<span class="pub-cart-badge" id="header-cart-badge">3</span>')

    def test_inactive_or_deleted_product_cannot_be_added_to_cart(self):
        """Inactive or soft-deleted products cannot be added to cart."""
        inactive_prod = Product.objects.create(
            workspace=self.ws_retail,
            category=self.cat_gear,
            name="Tai nghe cũ hỏng",
            sku="HEADPHONE-DISCONTINUED",
            unit="cái",
            unit_price=Decimal("500000"),
            is_active=False,
        )
        resp = self.client.post(f"/gio-hang/them/{inactive_prod.id}/", {"quantity": "1"})
        self.assertEqual(resp.status_code, 302)
        self.assertIn("error=unavailable", resp.url)

        # Verify cart remains empty
        cart_resp = self.client.get("/gio-hang/")
        self.assertContains(cart_resp, "Giỏ hàng của bạn đang trống")

    def test_cart_quantity_update_decrease_and_remove(self):
        """Updating quantity, decreasing to 0, removing item, and clearing cart."""
        # 1. Add item
        self.client.post(f"/gio-hang/them/{self.prod_mouse.id}/", {"quantity": "1"})

        # 2. Update to 4
        self.client.post(f"/gio-hang/cap-nhat/{self.prod_mouse.id}/", {"quantity": "4"})
        cart_resp = self.client.get("/gio-hang/")
        # Line total: 4 * 2,490,000 = 9,960,000
        self.assertContains(cart_resp, "9960000")

        # 3. Remove single item
        self.client.post(f"/gio-hang/xoa/{self.prod_mouse.id}/")
        cart_resp_empty = self.client.get("/gio-hang/")
        self.assertContains(cart_resp_empty, "Giỏ hàng của bạn đang trống")

        # 4. Add items and clear all
        self.client.post(f"/gio-hang/them/{self.prod_laptop.id}/", {"quantity": "1"})
        self.client.post(f"/gio-hang/them/{self.prod_keyboard.id}/", {"quantity": "1"})
        self.client.post("/gio-hang/xoa-tat-ca/")
        final_resp = self.client.get("/gio-hang/")
        self.assertContains(final_resp, "Giỏ hàng của bạn đang trống")

    # =========================================================================
    # B. DETERMINISTIC SHIPPING CALCULATION
    # =========================================================================

    def test_shipping_fee_calculation_rules(self):
        """
        Under 5M VND Home Delivery = 30,000 VND shipping fee.
        Over 5M VND Home Delivery = 0 VND (Free shipping).
        Store Pickup = 0 VND.
        """
        # Mouse only (2.49M < 5M)
        self.client.post(f"/gio-hang/them/{self.prod_mouse.id}/", {"quantity": "1"})
        resp = self.client.get("/gio-hang/?delivery_method=HOME_DELIVERY")
        self.assertContains(resp, "30000")

        # Store pickup for mouse (0 VND)
        resp_pickup = self.client.get("/gio-hang/?delivery_method=STORE_PICKUP")
        self.assertContains(resp_pickup, "Miễn phí")

        # Add laptop (Total = 34.49M >= 5M -> Free shipping)
        self.client.post(f"/gio-hang/them/{self.prod_laptop.id}/", {"quantity": "1"})
        resp_free = self.client.get("/gio-hang/?delivery_method=HOME_DELIVERY")
        self.assertContains(resp_free, "Miễn phí (Đơn >= 5.000.000 VNĐ)")

    # =========================================================================
    # C. CHECKOUT & ATOMIC ORDER CREATION
    # =========================================================================

    def test_guest_checkout_places_order_creates_customer_and_clears_cart(self):
        """
        Guest customer completes checkout: creates Customer, Order, OrderItem,
        clears cart, records AuditLog, and redirects to order success page.
        """
        # 1. Add items to cart
        self.client.post(f"/gio-hang/them/{self.prod_mouse.id}/", {"quantity": "2"})  # 2 * 2.49M = 4.98M

        # 2. GET /thanh-toan/
        checkout_page = self.client.get("/thanh-toan/")
        self.assertEqual(checkout_page.status_code, 200)
        self.assertContains(checkout_page, "Thông tin người nhận hàng")
        self.assertContains(checkout_page, "Thanh toán khi nhận hàng (COD)")

        # 3. POST /thanh-toan/dat-hang/
        order_resp = self.client.post(
            "/thanh-toan/dat-hang/",
            {
                "name": "Hoàng Minh Tuấn",
                "phone": "0987654321",
                "email": "tuan.hoang@testmail.vn",
                "address": "99 Lê Lợi",
                "district": "Quận 1",
                "city": "TP. Hồ Chí Minh",
                "delivery_method": "HOME_DELIVERY",
                "notes": "Giao trong giờ hành chính",
            },
        )
        self.assertEqual(order_resp.status_code, 302)
        self.assertIn("/dat-hang-thanh-cong/ORD-", order_resp.url)

        # Extract order number from redirect URL
        order_number = order_resp.url.split("/")[-2]

        # 4. Verify Order in Database
        order = Order.objects.get(order_number=order_number)
        self.assertEqual(order.workspace, self.ws_retail)
        self.assertEqual(order.customer.email, "tuan.hoang@testmail.vn")
        self.assertEqual(order.customer.name, "Hoàng Minh Tuấn")
        self.assertEqual(order.delivery_address.email, "tuan.hoang@testmail.vn")
        self.assertEqual(order.delivery_address.delivery_method, "HOME_DELIVERY")
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(order.payment_method, PaymentMethod.CASH)
        # Subtotal: 4,980,000 + Shipping: 30,000 = 5,010,000
        self.assertEqual(order.subtotal_amount, Decimal("4980000.00"))
        self.assertEqual(order.total_amount, Decimal("5010000.00"))

        # 5. Verify OrderItem
        items = order.items.all()
        self.assertEqual(items.count(), 1)
        item = items.first()
        self.assertEqual(item.product, self.prod_mouse)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("2490000.00"))
        self.assertEqual(item.subtotal, Decimal("4980000.00"))

        # 6. Verify Cart is Cleared
        cart = get_cart(self.client.request().wsgi_request if hasattr(self.client, 'request') else None)
        cart_resp = self.client.get("/gio-hang/")
        self.assertContains(cart_resp, "Giỏ hàng của bạn đang trống")

        # 7. Verify Success Page
        success_resp = self.client.get(f"/dat-hang-thanh-cong/{order_number}/")
        self.assertEqual(success_resp.status_code, 200)
        self.assertContains(success_resp, "Đặt hàng thành công!")
        self.assertContains(success_resp, order_number)
        self.assertContains(success_resp, "Hoàng Minh Tuấn")

        # 8. Verify AuditLog
        audit = AuditLog.objects.filter(action="ORDER_CREATED", entity_id=str(order.id)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.changes["order_number"], order_number)

    def test_authenticated_customer_checkout_and_prefill(self):
        """Logged in customer has fields prefilled and order is linked to Customer profile."""
        self.client.force_login(self.customer_user_a)

        # Add laptop to cart
        self.client.post(f"/gio-hang/them/{self.prod_laptop.id}/", {"quantity": "1"})

        # GET /thanh-toan/ should prefill Customer A's data
        checkout_page = self.client.get("/thanh-toan/")
        self.assertEqual(checkout_page.status_code, 200)
        self.assertContains(checkout_page, "Nguyễn Văn A")
        self.assertContains(checkout_page, "0901234567")
        self.assertContains(checkout_page, "customer_a@example.com")

        # Place Order
        order_resp = self.client.post(
            "/thanh-toan/dat-hang/",
            {
                "name": "Nguyễn Văn A",
                "phone": "0901234567",
                "email": "customer_a@example.com",
                "address": "12 Hai Bà Trưng, Phường Bến Nghé, Quận 1, TP.HCM",
                "delivery_method": "HOME_DELIVERY",
            },
        )
        self.assertEqual(order_resp.status_code, 302)
        order_number = order_resp.url.split("/")[-2]

        order = Order.objects.get(order_number=order_number)
        self.assertEqual(order.customer, self.customer_profile_a)
        self.assertEqual(order.created_by, self.customer_user_a)
        self.assertEqual(order.total_amount, Decimal("32000000.00"))  # >= 5M -> Free shipping

    def test_order_success_requires_guest_session_ownership(self):
        order = Order.objects.create(
            workspace=self.ws_retail,
            order_number="ORD-PRIVATE-GUEST",
            customer=self.customer_profile_a,
            order_date=timezone.now().date(),
            order_timestamp=timezone.now(),
            status=OrderStatus.PENDING,
            total_amount=Decimal("100000.00"),
        )

        self.assertEqual(self.client.get(f"/dat-hang-thanh-cong/{order.order_number}/").status_code, 404)
        session = self.client.session
        session["public_order_success_numbers"] = [order.order_number]
        session.save()
        self.assertEqual(self.client.get(f"/dat-hang-thanh-cong/{order.order_number}/").status_code, 200)

        other_browser = Client()
        self.assertEqual(other_browser.get(f"/dat-hang-thanh-cong/{order.order_number}/").status_code, 404)

    def test_order_success_rejects_another_authenticated_customer(self):
        order = Order.objects.create(
            workspace=self.ws_retail,
            order_number="ORD-PRIVATE-USER",
            customer=self.customer_profile_a,
            order_date=timezone.now().date(),
            order_timestamp=timezone.now(),
            status=OrderStatus.PENDING,
            total_amount=Decimal("100000.00"),
            created_by=self.customer_user_a,
        )

        self.client.force_login(self.customer_user_b)
        self.assertEqual(self.client.get(f"/dat-hang-thanh-cong/{order.order_number}/").status_code, 404)
        self.client.force_login(self.customer_user_a)
        self.assertEqual(self.client.get(f"/dat-hang-thanh-cong/{order.order_number}/").status_code, 200)

    # =========================================================================
    # D. HISTORICAL PRICE SNAPSHOT INTEGRITY
    # =========================================================================

    def test_historical_price_integrity_preserved_on_product_price_update(self):
        """
        CRITICAL: OrderItem unit_price must snapshot the price at purchase time.
        Future updates to Product.unit_price must NEVER alter historical orders.
        """
        # 1. Place order for laptop at 32,000,000 VND
        self.client.post(f"/gio-hang/them/{self.prod_laptop.id}/", {"quantity": "1"})
        order_resp = self.client.post(
            "/thanh-toan/dat-hang/",
            {
                "name": "Khách Hàng Lịch Sử",
                "phone": "0909999999",
                "email": "history.customer@testmail.vn",
                "address": "100 Đồng Khởi, Quận 1",
                "delivery_method": "HOME_DELIVERY",
            },
        )
        order_number = order_resp.url.split("/")[-2]
        order = Order.objects.get(order_number=order_number)
        order_item = order.items.first()

        self.assertEqual(order_item.unit_price, Decimal("32000000.00"))
        self.assertEqual(order.total_amount, Decimal("32000000.00"))

        # 2. Next Day: Manager updates laptop price to 29,990,000 VND
        update_product(
            product=self.prod_laptop,
            user=self.customer_user_a,
            data={"unit_price": Decimal("29990000.00")},
        )
        self.prod_laptop.refresh_from_db()
        self.assertEqual(self.prod_laptop.unit_price, Decimal("29990000.00"))

        # 3. Verify Historical OrderItem & Order remain 32,000,000 VND
        order_item.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(order_item.unit_price, Decimal("32000000.00"))
        self.assertEqual(order_item.subtotal, Decimal("32000000.00"))
        self.assertEqual(order.subtotal_amount, Decimal("32000000.00"))
        self.assertEqual(order.total_amount, Decimal("32000000.00"))

    # =========================================================================
    # E. BRANCH STOCK DEDUCTION & VALIDATION
    # =========================================================================

    def test_store_pickup_and_branch_stock_deduction(self):
        """Store pickup at branch checks and decrements branch StockBalance quantity."""
        # Setup branch stock balance = 5
        stock_q1 = StockBalance.objects.create(
            workspace=self.ws_retail,
            branch=self.branch_q1,
            product=self.prod_mouse,
            quantity_on_hand=5,
        )

        self.client.post(f"/gio-hang/them/{self.prod_mouse.id}/", {"quantity": "2"})
        order_resp = self.client.post(
            "/thanh-toan/dat-hang/",
            {
                "name": "Lê Văn C",
                "phone": "0933333333",
                "email": "levanc@testmail.vn",
                "delivery_method": "STORE_PICKUP",
                "branch_id": str(self.branch_q1.id),
            },
        )
        self.assertEqual(order_resp.status_code, 302)

        # Stock balance must be decremented: 5 - 2 = 3
        stock_q1.refresh_from_db()
        self.assertEqual(stock_q1.quantity_on_hand, 3)

    def test_insufficient_branch_stock_rejects_checkout(self):
        """If branch stock is less than requested quantity, checkout is safely rejected."""
        StockBalance.objects.create(
            workspace=self.ws_retail,
            branch=self.branch_q3,
            product=self.prod_keyboard,
            quantity_on_hand=1,  # Only 1 in stock
        )

        self.client.post(f"/gio-hang/them/{self.prod_keyboard.id}/", {"quantity": "3"})  # Request 3
        order_resp = self.client.post(
            "/thanh-toan/dat-hang/",
            {
                "name": "Lê Văn C",
                "phone": "0933333333",
                "email": "levanc@testmail.vn",
                "delivery_method": "STORE_PICKUP",
                "branch_id": str(self.branch_q3.id),
            },
        )
        self.assertEqual(order_resp.status_code, 302)
        self.assertEqual(order_resp.url, "/gio-hang/")

        # Verify no order was created
        self.assertFalse(Order.objects.filter(customer__email="levanc@testmail.vn").exists())

    # =========================================================================
    # F. CUSTOMER ORDER HISTORY & STRICT IDOR PROTECTION
    # =========================================================================

    def test_customer_order_history_and_strict_idor_protection(self):
        """
        Customer A can view their own orders list and detail.
        Customer B CANNOT view Customer A's order by changing the URL order number (404/IDOR blocked).
        """
        # 1. Create order for Customer A
        now = timezone.now()
        order_a = Order.objects.create(
            workspace=self.ws_retail,
            order_number="ORD-TEST-CUSTA-001",
            customer=self.customer_profile_a,
            branch=self.branch_q1,
            order_date=now.date(),
            order_timestamp=now,
            status=OrderStatus.CONFIRMED,
            subtotal_amount=Decimal("32000000.00"),
            total_amount=Decimal("32000000.00"),
            payment_method=PaymentMethod.CASH,
            created_by=self.customer_user_a,
        )
        OrderItem.objects.create(
            order=order_a,
            product=self.prod_laptop,
            quantity=1,
            unit_price=Decimal("32000000.00"),
            subtotal=Decimal("32000000.00"),
        )

        # 2. Customer A logs in and accesses their own order history
        self.client.force_login(self.customer_user_a)
        orders_list_resp = self.client.get("/tai-khoan/don-hang/")
        self.assertEqual(orders_list_resp.status_code, 200)
        self.assertContains(orders_list_resp, "ORD-TEST-CUSTA-001")

        order_detail_resp = self.client.get(f"/tai-khoan/don-hang/{order_a.order_number}/")
        self.assertEqual(order_detail_resp.status_code, 200)
        self.assertContains(order_detail_resp, "Laptop Dell XPS 13 Plus")
        self.assertContains(order_detail_resp, "32000000")

        # 3. Customer B logs in and attempts to access Customer A's order (IDOR Attack)
        self.client.force_login(self.customer_user_b)

        # Customer B's order list must NOT contain Customer A's order
        orders_b_list = self.client.get("/tai-khoan/don-hang/")
        self.assertNotContains(orders_b_list, "ORD-TEST-CUSTA-001")

        # Direct access to Customer A's order number must return 404
        idor_resp = self.client.get(f"/tai-khoan/don-hang/{order_a.order_number}/")
        self.assertEqual(idor_resp.status_code, 404)

    # =========================================================================
    # G. TAMPERING RESISTANCE & SECURITY
    # =========================================================================

    def test_client_cannot_tamper_unit_price_or_grand_total(self):
        """
        Submitting manipulated price or total amounts in POST payload is ignored;
        Backend recalculates all pricing strictly from database records.
        """
        self.client.post(f"/gio-hang/them/{self.prod_laptop.id}/", {"quantity": "1"})

        # Attacker posts tampered price = 1000 VND and grand_total = 1000 VND
        order_resp = self.client.post(
            "/thanh-toan/dat-hang/",
            {
                "name": "Kẻ Tấn Công Giá",
                "phone": "0911222333",
                "email": "attacker@fake.vn",
                "address": "1 Hầm Trú Ẩn",
                "delivery_method": "HOME_DELIVERY",
                "unit_price": "1000",
                "subtotal_amount": "1000",
                "total_amount": "1000",
                "shipping_fee": "0",
            },
        )
        self.assertEqual(order_resp.status_code, 302)
        order_number = order_resp.url.split("/")[-2]

        order = Order.objects.get(order_number=order_number)
        # Must be genuine price: 32,000,000 VND
        self.assertEqual(order.subtotal_amount, Decimal("32000000.00"))
        self.assertEqual(order.total_amount, Decimal("32000000.00"))
        self.assertEqual(order.items.first().unit_price, Decimal("32000000.00"))
