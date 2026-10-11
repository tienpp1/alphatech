"""Conversation history privacy regressions, using only isolated test records."""
from rest_framework.test import APITestCase

from apps.accounts.models import Permission, Role, User
from apps.knowledge.models import ChatMessage, ConversationSession
from apps.workspaces.models import Workspace, WorkspaceMembership


class ConversationHistoryAuditTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ws = Workspace.objects.create(code="history-audit", name="History A", workspace_type="RETAIL")
        cls.other_ws = Workspace.objects.create(code="history-foreign", name="History B", workspace_type="SERVICE")
        cls.owner = User.objects.create_user(username="history-owner", email="history-owner@example.com")
        cls.other = User.objects.create_user(username="history-other", email="history-other@example.com")
        cls.no_permission = User.objects.create_user(username="history-no-permission", email="history-no-permission@example.com")
        cls.admin = User.objects.create_superuser(username="history-superuser", email="history-superuser@example.com")
        role, _ = Role.objects.get_or_create(name="MANAGER")
        permission, _ = Permission.objects.get_or_create(codename="ai.chat", defaults={"name": "AI Chat", "module": "ai"})
        role.permissions.add(permission)
        WorkspaceMembership.objects.create(user=cls.owner, workspace=cls.ws, role=role, is_default=True)
        WorkspaceMembership.objects.create(user=cls.owner, workspace=cls.other_ws, role=role)
        WorkspaceMembership.objects.create(user=cls.other, workspace=cls.ws, role=role, is_default=True)
        WorkspaceMembership.objects.create(user=cls.no_permission, workspace=cls.ws, role=None, is_default=True)
        cls.owned = ConversationSession.objects.create(workspace=cls.ws, user=cls.owner, title="Owned A")
        cls.other_owned = ConversationSession.objects.create(workspace=cls.ws, user=cls.other, title="Other user A")
        cls.other_workspace = ConversationSession.objects.create(workspace=cls.other_ws, user=cls.owner, title="Owned B")
        cls.sources = [{"document_title": "Approved guide", "chunk_id": 11, "similarity": .8}]
        cls.tools = [{"tool": "get_sales_summary", "status": "SUCCESS"}]
        ChatMessage.objects.create(workspace=cls.ws, session=cls.owned, role="USER", content="History question")
        ChatMessage.objects.create(workspace=cls.ws, session=cls.owned, role="ASSISTANT", content="History answer", sources=cls.sources, tools_used=cls.tools)
        ChatMessage.objects.create(workspace=cls.ws, session=cls.other_owned, role="ASSISTANT", content="Other-owner secret")
        ChatMessage.objects.create(workspace=cls.other_ws, session=cls.other_workspace, role="ASSISTANT", content="Other-workspace secret")

    def detail(self, session, workspace=None):
        return self.client.get(
            f"/api/v1/ai/sessions/{session.pk}/messages/",
            HTTP_X_WORKSPACE_ID=str((workspace or self.ws).pk),
        )

    def test_owner_history_preserves_roles_sources_and_tool_metadata(self):
        self.client.force_authenticate(self.owner)
        result = self.detail(self.owned)
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data["success"])
        self.assertEqual(result.data["data"]["session_id"], self.owned.pk)
        messages = result.data["data"]["messages"]
        self.assertEqual([message["role"] for message in messages], ["USER", "ASSISTANT"])
        self.assertEqual(messages[-1]["sources"], self.sources)
        self.assertEqual(messages[-1]["tools_used"], self.tools)

    def test_other_owner_same_workspace_cannot_read_history(self):
        self.client.force_authenticate(self.owner)
        result = self.detail(self.other_owned)
        self.assertEqual(result.status_code, 404)
        self.assertEqual(result.data["error"]["code"], "NOT_FOUND")
        self.assertNotIn("Other-owner secret", str(result.data))

    def test_owner_cannot_read_another_workspace_session_using_current_workspace(self):
        self.client.force_authenticate(self.owner)
        result = self.detail(self.other_workspace)
        self.assertEqual(result.status_code, 404)
        self.assertNotIn("Other-workspace secret", str(result.data))

    def test_history_list_only_contains_current_owner_and_workspace(self):
        self.client.force_authenticate(self.owner)
        result = self.client.get("/api/v1/ai/sessions/", HTTP_X_WORKSPACE_ID=str(self.ws.pk))
        self.assertEqual(result.status_code, 200)
        self.assertEqual([item["id"] for item in result.data["data"]], [self.owned.pk])

    def test_non_member_cannot_select_another_workspace(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.detail(self.other_workspace, self.other_ws).status_code, 403)

    def test_ai_chat_permission_required_for_history_list_and_detail(self):
        self.client.force_authenticate(self.no_permission)
        for path in ("/api/v1/ai/sessions/", f"/api/v1/ai/sessions/{self.owned.pk}/messages/"):
            with self.subTest(path=path):
                result = self.client.get(path, HTTP_X_WORKSPACE_ID=str(self.ws.pk))
                self.assertEqual(result.status_code, 403)
                self.assertEqual(result.data["error"]["code"], "PERMISSION_DENIED")

    def test_anonymous_cannot_read_history_list_or_detail(self):
        for path in ("/api/v1/ai/sessions/", f"/api/v1/ai/sessions/{self.owned.pk}/messages/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path, HTTP_X_WORKSPACE_ID=str(self.ws.pk)).status_code, 401)

    def test_superuser_does_not_bypass_conversation_ownership(self):
        self.client.force_authenticate(self.admin)
        result = self.detail(self.owned)
        self.assertEqual(result.status_code, 404)
        self.assertNotIn("History answer", str(result.data))

    def test_malformed_foreign_workspace_message_cannot_leak_through_owned_session(self):
        ChatMessage.objects.create(workspace=self.other_ws, session=self.owned, role="ASSISTANT", content="Foreign mismatched message")
        self.client.force_authenticate(self.owner)
        result = self.detail(self.owned)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.data["data"]["messages"]), 2)
        self.assertNotIn("Foreign mismatched message", str(result.data))
