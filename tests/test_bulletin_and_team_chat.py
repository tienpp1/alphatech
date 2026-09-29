"""
Automated Test Suite for Internal Bulletin Board & Workspace Team Chat.
Verifies:
1. Workspace Isolation: Bulletins and Chat messages are strictly partitioned by Workspace.
2. Role-Based Access Control (RBAC):
   - Only ADMIN, MANAGER, and Superuser can publish/pin bulletins.
   - EMPLOYEE and VIEWER can view bulletins and participate in Team Chat.
   - Public Customer accounts and unauthenticated requests are strictly denied (401/403/Redirect).
3. Chat Polling & Incremental Fetching:
   - `since_id` parameter correctly fetches only newer messages.
4. Colleague Discovery:
   - Chat roster lists active members of the current workspace only.
"""

from django.test import TestCase, Client
from apps.accounts.models import User, Role
from apps.retail.models import Customer
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.notifications.models import (
    InternalBulletin,
    BulletinPriority,
    TeamChatMessage,
)
from apps.notifications.bulletin_service import (
    get_workspace_bulletins,
    create_bulletin,
    can_manage_bulletins,
)
from apps.notifications.chat_service import (
    send_team_message,
    get_recent_team_messages,
    verify_chat_access,
    get_workspace_colleagues,
)


class BulletinAndTeamChatTestCase(TestCase):
    """
    Test suite for Internal Bulletin Board and Workspace Team Chat.
    """

    def setUp(self):
        self.client = Client()

        # 1. Workspaces
        self.ws_retail = Workspace.objects.create(
            name="ABC Tech Retail",
            code="WS-RETAIL-CHAT",
            workspace_type=WorkspaceType.RETAIL,
            is_active=True,
        )
        self.ws_service = Workspace.objects.create(
            name="XYZ IT Services",
            code="WS-SERVICE-CHAT",
            workspace_type=WorkspaceType.SERVICE,
            is_active=True,
        )

        # 2. Roles
        self.role_admin, _ = Role.objects.get_or_create(name="ADMIN")
        self.role_manager, _ = Role.objects.get_or_create(name="MANAGER")
        self.role_employee, _ = Role.objects.get_or_create(name="EMPLOYEE")
        self.role_viewer, _ = Role.objects.get_or_create(name="VIEWER")

        # 3. Users in WS Retail
        self.retail_admin = User.objects.create_user(
            username="retail_admin_chat@test.vn",
            email="retail_admin_chat@test.vn",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.retail_admin,
            role=self.role_admin,
            is_default=True,
            is_active=True,
        )

        self.retail_staff = User.objects.create_user(
            username="retail_staff_chat@test.vn",
            email="retail_staff_chat@test.vn",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_retail,
            user=self.retail_staff,
            role=self.role_employee,
            is_default=True,
            is_active=True,
        )

        # 4. Users in WS Service
        self.service_mgr = User.objects.create_user(
            username="service_mgr_chat@test.vn",
            email="service_mgr_chat@test.vn",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_service,
            user=self.service_mgr,
            role=self.role_manager,
            is_default=True,
            is_active=True,
        )

        self.service_staff = User.objects.create_user(
            username="service_staff_chat@test.vn",
            email="service_staff_chat@test.vn",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            workspace=self.ws_service,
            user=self.service_staff,
            role=self.role_employee,
            is_default=True,
            is_active=True,
        )

        # 5. Public Customer
        self.customer_user = User.objects.create_user(
            username="public_customer_chat@test.vn",
            email="public_customer_chat@test.vn",
            password="CustomerPass123!",
        )
        Customer.objects.create(
            workspace=self.ws_retail,
            user=self.customer_user,
            phone="0987654321",
            email="public_customer_chat@test.vn",
            name="Khách Hàng Vãng Lai",
            code="CUST-TEST-CHAT",
        )

    # -------------------------------------------------------------------------
    # Bulletin Board Tests
    # -------------------------------------------------------------------------

    def test_bulletin_creation_and_workspace_isolation(self):
        """
        Bulletins created in WS Retail must not be visible to WS Service.
        """
        # Admin creates bulletin in WS Retail
        bulletin_retail = create_bulletin(
            workspace=self.ws_retail,
            author=self.retail_admin,
            title="Kế hoạch kiểm kê quý 3",
            content="Toàn thể nhân viên cửa hàng chuẩn bị đếm kho vào thứ 6.",
            priority=BulletinPriority.URGENT,
            is_pinned=True,
        )

        # Service manager creates bulletin in WS Service
        bulletin_service = create_bulletin(
            workspace=self.ws_service,
            author=self.service_mgr,
            title="Lịch bảo trì máy chủ trung tâm",
            content="Hạ tầng IT sẽ cập nhật lúc 22h00.",
            priority=BulletinPriority.NORMAL,
        )

        # Query WS Retail
        retail_list = get_workspace_bulletins(self.ws_retail)
        self.assertIn(bulletin_retail, retail_list)
        self.assertNotIn(bulletin_service, retail_list)

        # Query WS Service
        service_list = get_workspace_bulletins(self.ws_service)
        self.assertIn(bulletin_service, service_list)
        self.assertNotIn(bulletin_retail, service_list)

    def test_bulletin_pinned_ordering(self):
        """
        Pinned bulletins should always precede non-pinned bulletins.
        """
        b1 = create_bulletin(
            workspace=self.ws_retail,
            author=self.retail_admin,
            title="Thông báo bình thường 1",
            content="Nội dung 1",
            is_pinned=False,
        )
        b2 = create_bulletin(
            workspace=self.ws_retail,
            author=self.retail_admin,
            title="Thông báo ghim quan trọng",
            content="Nội dung ghim",
            is_pinned=True,
        )

        bulletins = list(get_workspace_bulletins(self.ws_retail))
        self.assertEqual(bulletins[0].id, b2.id)
        self.assertEqual(bulletins[1].id, b1.id)

    def test_bulletin_rbac_permissions(self):
        """
        Only Admin/Manager/Superuser can create bulletins.
        Regular Employee cannot create bulletins.
        """
        self.assertTrue(can_manage_bulletins(self.retail_admin, self.ws_retail))
        self.assertTrue(can_manage_bulletins(self.service_mgr, self.ws_service))
        self.assertFalse(can_manage_bulletins(self.retail_staff, self.ws_retail))

        # Test UI View authorization
        self.client.force_login(self.retail_staff)
        resp = self.client.post("/noibo/bang-tin/tao/", {
            "title": "Hack attempt",
            "content": "Employee unauthorized post",
            "priority": "NORMAL",
        })
        self.assertEqual(resp.status_code, 403)

        # Test API View authorization
        api_resp = self.client.post("/api/v1/notifications/bulletins/", {
            "title": "Hack attempt API",
            "content": "Employee unauthorized post",
        }, content_type="application/json")
        self.assertEqual(api_resp.status_code, 403)

        # Now test with Admin
        self.client.force_login(self.retail_admin)
        post_resp = self.client.post("/noibo/bang-tin/tao/", {
            "title": "Thông báo ban giám đốc",
            "content": "Nội dung chỉ đạo hợp lệ.",
            "priority": "NORMAL",
        })
        self.assertEqual(post_resp.status_code, 302)
        self.assertTrue(InternalBulletin.objects.filter(title="Thông báo ban giám đốc").exists())

    def test_django_staff_does_not_grant_workspace_publishing(self):
        self.retail_staff.is_staff = True
        self.retail_staff.save(update_fields=["is_staff"])
        self.client.force_login(self.retail_staff)
        for role in (self.role_employee, self.role_viewer):
            with self.subTest(role=role.name):
                WorkspaceMembership.objects.filter(
                    user=self.retail_staff, workspace=self.ws_retail,
                ).update(role=role)
                self.assertFalse(can_manage_bulletins(self.retail_staff, self.ws_retail))
                self.assertFalse(can_manage_bulletins(self.retail_staff, self.ws_service))
                for url in ("/noibo/bang-tin/tao/", "/api/v1/notifications/bulletins/"):
                    response = self.client.post(url, {
                        "title": "Forbidden staff publication", "content": "Not authorized",
                    })
                    self.assertEqual(response.status_code, 403)
        self.assertFalse(InternalBulletin.objects.filter(title="Forbidden staff publication").exists())

    def test_inactive_membership_cannot_publish(self):
        WorkspaceMembership.objects.filter(
            user=self.retail_admin, workspace=self.ws_retail,
        ).update(is_active=False)
        self.assertFalse(can_manage_bulletins(self.retail_admin, self.ws_retail))

    # -------------------------------------------------------------------------
    # Team Chat Tests
    # -------------------------------------------------------------------------

    def test_team_chat_isolation(self):
        """
        Messages sent within WS Retail must not leak to WS Service.
        """
        msg_retail = send_team_message(
            workspace=self.ws_retail,
            sender=self.retail_admin,
            message="Xin chào team bán lẻ!",
        )

        msg_service = send_team_message(
            workspace=self.ws_service,
            sender=self.service_mgr,
            message="Xin chào đội ngũ kỹ thuật!",
        )

        # Verify Retail messages
        retail_msgs = list(get_recent_team_messages(self.ws_retail))
        self.assertIn(msg_retail, retail_msgs)
        self.assertNotIn(msg_service, retail_msgs)

        # Verify Service messages
        service_msgs = list(get_recent_team_messages(self.ws_service))
        self.assertIn(msg_service, service_msgs)
        self.assertNotIn(msg_retail, service_msgs)

    def test_team_chat_incremental_polling(self):
        """
        Polling with since_id must return only messages strictly greater than since_id.
        """
        msg1 = send_team_message(self.ws_retail, self.retail_admin, "Tin nhắn 1")
        msg2 = send_team_message(self.ws_retail, self.retail_staff, "Tin nhắn 2")
        msg3 = send_team_message(self.ws_retail, self.retail_admin, "Tin nhắn 3")

        # Poll since msg2
        polled = list(get_recent_team_messages(self.ws_retail, since_id=msg2.id))
        self.assertEqual(len(polled), 1)
        self.assertEqual(polled[0].id, msg3.id)

    def test_team_chat_api_flow(self):
        """
        Test sending and polling chat messages via REST API.
        """
        self.client.force_login(self.retail_staff)

        # Send via API
        send_resp = self.client.post("/api/v1/notifications/chat/send/", {
            "message": "Tôi đang kiểm tra hàng mới về kho.",
        }, content_type="application/json")
        self.assertEqual(send_resp.status_code, 201)
        data = send_resp.json()
        self.assertTrue(data.get("ok"))
        created_msg_id = data["message"]["id"]

        # Fetch messages via API
        get_resp = self.client.get("/api/v1/notifications/chat/messages/")
        self.assertEqual(get_resp.status_code, 200)
        messages_data = get_resp.json().get("messages", [])
        self.assertTrue(any(m["id"] == created_msg_id for m in messages_data))

    def test_team_chat_colleagues_roster(self):
        """
        Roster must return only colleagues in the active workspace.
        """
        colleagues = get_workspace_colleagues(self.ws_retail)
        colleague_users = [c["user"] for c in colleagues]
        self.assertIn(self.retail_admin, colleague_users)
        self.assertIn(self.retail_staff, colleague_users)
        self.assertNotIn(self.service_mgr, colleague_users)
        self.assertNotIn(self.service_staff, colleague_users)

    # -------------------------------------------------------------------------
    # Public Customer and Unauthenticated Security Boundaries
    # -------------------------------------------------------------------------

    def test_unauthenticated_access_redirects(self):
        """
        Unauthenticated visitors must be redirected to login.
        """
        resp_bulletin = self.client.get("/noibo/bang-tin/")
        self.assertEqual(resp_bulletin.status_code, 302)
        self.assertIn("/accounts/login/", resp_bulletin["Location"])

        resp_chat = self.client.get("/noibo/trao-doi/")
        self.assertEqual(resp_chat.status_code, 302)
        self.assertIn("/accounts/login/", resp_chat["Location"])

    def test_customer_account_denied_access(self):
        """
        Public customers (with CustomerAccount) must be rejected with 403 Forbidden
        or redirected away from internal management routes.
        """
        self.client.force_login(self.customer_user)

        resp_bulletin = self.client.get("/noibo/bang-tin/")
        self.assertIn(resp_bulletin.status_code, [403, 302])

        resp_chat = self.client.get("/noibo/trao-doi/")
        self.assertIn(resp_chat.status_code, [403, 302])

        api_send = self.client.post("/api/v1/notifications/chat/send/", {
            "message": "Customer trying to chat with staff",
        }, content_type="application/json")
        self.assertEqual(api_send.status_code, 403)
