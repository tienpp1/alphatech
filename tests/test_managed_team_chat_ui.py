"""Rendered UI contracts; no account or business database writes."""
from html.parser import HTMLParser
from types import SimpleNamespace

from django import forms
from django.contrib.messages import constants as message_levels
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import SimpleTestCase


class EmployeeForm(forms.Form):
    full_name = forms.CharField(label="Họ và tên")
    email = forms.EmailField(label="Email công việc")
    username = forms.CharField(label="Tên đăng nhập")
    password1 = forms.CharField(label="Mật khẩu", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Xác nhận mật khẩu", widget=forms.PasswordInput)


class InviteForm(forms.Form):
    membership = forms.ChoiceField(label="Nhân viên", choices=[("42", "Nhân viên chờ mời")])


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def tagged(self, tag):
        return [attrs for element, attrs in self.elements if element == tag]

    def by_id(self, element_id):
        return next((attrs for _, attrs in self.elements if attrs.get("id") == element_id), {})


class ManagedTeamChatUITests(SimpleTestCase):
    def render_chat(self, **overrides):
        context = {
            "active_workspace": SimpleNamespace(id="workspace-1", name="Không gian thử", code="TEST"),
            "request": SimpleNamespace(user=SimpleNamespace(id=7, username="manager", is_authenticated=True)),
            "csrf_token": "test-csrf-token",
            "can_manage_chat": True,
            "can_use_team_chat": True,
            "employee_form": EmployeeForm(),
            "add_employee_form": InviteForm(),
            "chat_management_panel": "",
            "colleagues": [{"username": "employee", "full_name": "Nhân viên đã mời", "role": "EMPLOYEE"}],
            "messages_list": [],
            "latest_message_id": 19,
            "oldest_message_id": 3,
            "has_older_messages": True,
        }
        context.update(overrides)
        return render_to_string("notifications/team_chat.html", context)

    def test_manager_actions_submit_scoped_csrf_forms_above_chat(self):
        html = self.render_chat()
        dom = Elements(html)
        forms_by_action = {attrs.get("action"): attrs for attrs in dom.tagged("form")}
        for action in ("/noibo/trao-doi/nhan-vien/tao/", "/noibo/trao-doi/thanh-vien/them/"):
            self.assertEqual(forms_by_action.get(action, {}).get("method", "").lower(), "post")
        self.assertEqual(sum(a.get("name") == "workspace_id" and a.get("value") == "workspace-1" for a in dom.tagged("input")), 2)
        self.assertEqual(sum(a.get("name") == "csrfmiddlewaretoken" for a in dom.tagged("input")), 3)
        labels = {a.get("for") for a in dom.tagged("label")}
        self.assertTrue({"id_full_name", "id_email", "id_username", "id_password1", "id_password2", "id_membership"} <= labels)
        self.assertLess(html.index('id="chat-management"'), html.index('class="chat-page-layout"'))
        self.assertIn("Tạo tài khoản nhân viên", html)
        self.assertIn("Thêm nhân viên vào chat", html)
        self.assertIn("chưa có quyền trao đổi", html)
        self.assertIn("Nhân viên (EMPLOYEE)", html)

    def test_employee_never_sees_management_forms_or_pending_directory(self):
        html = self.render_chat(can_manage_chat=False)
        self.assertNotIn('/noibo/trao-doi/nhan-vien/tao/', html)
        self.assertNotIn('/noibo/trao-doi/thanh-vien/them/', html)
        self.assertNotIn("Nhân viên chờ mời", html)
        self.assertIn("Nhân viên đã mời", html)

    def test_create_errors_open_panel_link_fields_and_never_echo_password(self):
        form = EmployeeForm({"full_name": "Tên còn giữ", "email": "email-sai", "username": "retained", "password1": "private-password", "password2": "private-password"})
        self.assertFalse(form.is_valid())
        html = self.render_chat(employee_form=form, chat_management_panel="create")
        dom = Elements(html)
        self.assertIn("open", dom.by_id("chat-create-panel"))
        self.assertNotIn("open", dom.by_id("chat-add-panel"))
        self.assertEqual(dom.by_id("id_full_name")["value"], "Tên còn giữ")
        self.assertEqual(dom.by_id("id_email")["value"], "email-sai")
        self.assertEqual(dom.by_id("id_username")["value"], "retained")
        self.assertNotIn("private-password", html)
        self.assertEqual(dom.by_id("chat-create-errors")["tabindex"], "-1")
        self.assertIn("#id_email", [a.get("href") for a in dom.tagged("a")])
        self.assertEqual(dom.by_id("id_email")["aria-invalid"], "true")
        self.assertIn("id_email_error", dom.by_id("id_email")["aria-describedby"])

    def test_invite_error_opens_only_invite_panel_and_preserves_selection(self):
        form = InviteForm({"membership": "42"})
        self.assertTrue(form.is_valid())
        form.add_error(None, "Quyền đã thay đổi, hãy thử lại.")
        html = self.render_chat(add_employee_form=form, chat_management_panel="add")
        dom = Elements(html)
        self.assertIn("open", dom.by_id("chat-add-panel"))
        self.assertNotIn("open", dom.by_id("chat-create-panel"))
        self.assertEqual(dom.by_id("chat-add-errors")["tabindex"], "-1")
        self.assertIn("Quyền đã thay đổi, hãy thử lại.", html)
        self.assertInHTML('<option value="42" selected>Nhân viên chờ mời</option>', html)

    def test_navigation_requires_actual_chat_access(self):
        self.assertFalse(Elements(self.render_chat(can_use_team_chat=False, can_manage_chat=False)).by_id("nav-direct-chat"))
        self.assertIn('id="nav-direct-chat"', self.render_chat(can_use_team_chat=True))

    def test_operation_notices_display_success_and_error_with_appropriate_roles(self):
        html = self.render_chat(messages=[
            Message(message_levels.SUCCESS, "Đã tạo tài khoản; hãy thêm vào chat."),
            Message(message_levels.ERROR, "Chưa thể thêm nhân viên."),
        ])
        self.assertInHTML('<p class="chat-operation-notice" role="status">Đã tạo tài khoản; hãy thêm vào chat.</p>', html)
        self.assertInHTML('<p class="chat-operation-notice chat-operation-error" role="alert">Chưa thể thêm nhân viên.</p>', html)

    def test_chat_transport_controls_and_history_cursors_are_preserved(self):
        dom = Elements(self.render_chat())
        self.assertEqual(dom.by_id("chatMessagesStream")["data-latest-id"], "19")
        self.assertEqual(dom.by_id("chatMessagesStream")["data-oldest-id"], "3")
        for element_id in ("chatForm", "chatInputMessage", "btnSendChat", "chatLoadOlder", "chatHistoryStatus", "chatConnectionStatus", "chatSendStatus"):
            self.assertTrue(dom.by_id(element_id))
        self.assertTrue(any(a.get("src", "").endswith("js/internal_team_chat.js") for a in dom.tagged("script")))
