import json

from django.test import Client, TestCase, override_settings
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.notifications.models import InternalBulletin


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class BulletinUpdateTests(TestCase):
    def test_live_feed_preserves_editor_outside_replacement_region(self):
        response = self.client.get('/noibo/bang-tin/', {'workspace_id': self.ws.pk})
        self.assertContains(response, 'id="bulletinLiveFeed"')
        self.assertContains(response, 'js/internal_bulletins.js')
        self.assertContains(response, 'data-can-manage="true"')
        self.role.name = 'EMPLOYEE'
        self.role.save()
        employee_page = self.client.get('/noibo/bang-tin/', {'workspace_id': self.ws.pk})
        self.assertContains(employee_page, 'data-can-manage="false"')
        self.assertNotContains(employee_page, 'id="new-bulletin-modal"')

    def setUp(self):
        self.ws = Workspace.objects.create(code="edit-a", name="A", workspace_type="RETAIL")
        self.other = Workspace.objects.create(code="edit-b", name="B", workspace_type="RETAIL")
        self.user = User.objects.create_user(username="editor", password="test-password")
        self.role = Role.objects.create(name="MANAGER")
        self.membership = WorkspaceMembership.objects.create(user=self.user, workspace=self.ws, role=self.role, is_active=True)
        self.post = InternalBulletin.objects.create(workspace=self.ws, author=self.user, title="Original", content="Body")
        self.foreign = InternalBulletin.objects.create(workspace=self.other, author=self.user, title="Private", content="Secret")
        self.client.force_login(self.user)
        self.url = f"/api/v1/notifications/bulletins/{self.post.pk}/update/"
        self.ui = f"/noibo/bang-tin/{self.post.pk}/sua/"
        self.data = {"workspace_id": str(self.ws.pk), "title": "New", "content": "Updated", "priority": "URGENT"}

    def test_manager_api_updates_only_editorial_fields(self):
        response = self.client.post(self.url, {**self.data, "author": 999, "is_published": False})
        self.assertEqual(response.status_code, 200)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "New")
        self.assertEqual(self.post.workspace_id, self.ws.pk)
        self.assertEqual(self.post.author_id, self.user.pk)
        self.assertTrue(self.post.is_published)

    def test_cross_workspace_object_404(self):
        response = self.client.post(f"/api/v1/notifications/bulletins/{self.foreign.pk}/update/", self.data)
        self.assertEqual(response.status_code, 404)
        self.foreign.refresh_from_db()
        self.assertEqual(self.foreign.content, "Secret")

    def test_invalid_or_unauthorized_workspace_no_fallback(self):
        for value in (str(self.other.pk), "invalid", ""):
            with self.subTest(value=value):
                self.assertEqual(self.client.post(self.url, {**self.data, "workspace_id": value}).status_code, 403)

    def test_employee_staff_and_inactive_manager_denied(self):
        self.role.name = "EMPLOYEE"
        self.role.save()
        self.user.is_staff = True
        self.user.save()
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.role.name = "MANAGER"
        self.role.save()
        self.membership.is_active = False
        self.membership.save()
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)

    def test_ui_validation_preserves_input_and_does_not_save(self):
        response = self.client.post(self.ui, {**self.data, "content": "   "})
        self.assertContains(response, 'value="New"', status_code=400)
        self.assertContains(response, 'role="alert"', status_code=400)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Original")

    def test_ui_save_and_controls(self):
        self.assertContains(self.client.get(self.ui, {"workspace_id": self.ws.pk}), "Lưu thay đổi")
        self.assertEqual(self.client.post(self.ui, self.data).status_code, 302)
        board = f"/noibo/bang-tin/?workspace_id={self.ws.pk}"
        self.assertContains(self.client.get(board), "Sửa bản tin")
        self.role.name = "EMPLOYEE"
        self.role.save()
        self.assertNotContains(self.client.get(board), "Sửa bản tin")
        self.assertEqual(self.client.get(self.ui, {"workspace_id": self.ws.pk}).status_code, 403)
        self.role.name = "VIEWER"
        self.role.save()
        self.assertEqual(self.client.get(board).status_code, 403)

    def test_csrf_and_get_cannot_mutate(self):
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.user)
        self.assertEqual(secure.post(self.url, self.data).status_code, 403)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Original")

    def test_malformed_json_and_invalid_fields(self):
        for payload in ([], {**self.data, "title": "x" * 256}, {**self.data, "priority": "INVALID"}):
            self.assertEqual(self.client.post(self.url, json.dumps(payload), content_type="application/json").status_code, 400)

    def test_public_customer_cannot_edit(self):
        customer = User.objects.create_user(username="customer", email="customer@example.test")
        self.client.force_login(customer)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.assertEqual(self.client.get(self.ui, {"workspace_id": self.ws.pk}).status_code, 403)

    def test_service_enforces_permission_and_scope(self):
        from django.core.exceptions import PermissionDenied
        from django.http import Http404
        from apps.notifications.bulletin_service import update_bulletin
        fields = {key: self.data[key] for key in ("title", "content", "priority")}
        with self.assertRaises(Http404):
            update_bulletin(self.ws, self.user, self.foreign.pk, **fields)
        self.membership.is_active = False
        self.membership.save()
        with self.assertRaises(PermissionDenied):
            update_bulletin(self.ws, self.user, self.post.pk, **fields)
