"""
Automated tests for RBAC, Tenant Security, Injection Immunity, and Audit Logging in Phase 8.
"""

from rest_framework.test import APITestCase
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, Permission, Role
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.audit.models import AuditLog
from apps.knowledge.models import KnowledgeBase, Document
from apps.knowledge.services import create_knowledge_base, upload_and_ingest_document


class RAGSecurityRBACTests(APITestCase):
    def setUp(self):
        # Workspaces
        self.ws_a = Workspace.objects.create(code="ws-alpha", name="Alpha Corp", workspace_type=WorkspaceType.RETAIL)
        self.ws_b = Workspace.objects.create(code="ws-beta", name="Beta Corp", workspace_type=WorkspaceType.SERVICE)

        # Users
        self.user_with_perm = User.objects.create_user(username="authorized_user", email="auth@example.com", password="password")
        self.user_no_perm = User.objects.create_user(username="unauthorized_user", email="unauth@example.com", password="password")

        # Permissions
        self.perm_view_kb, _ = Permission.objects.get_or_create(codename="knowledge.view_knowledge", defaults={"name": "View KB", "module": "knowledge"})
        self.perm_manage_kb, _ = Permission.objects.get_or_create(codename="knowledge.manage_knowledge", defaults={"name": "Manage KB", "module": "knowledge"})
        self.perm_chat, _ = Permission.objects.get_or_create(codename="ai.chat", defaults={"name": "AI Chat", "module": "ai"})

        # Roles
        self.role_admin = Role.objects.create(name="TEST_ADMIN")
        self.role_admin.permissions.add(self.perm_view_kb, self.perm_manage_kb, self.perm_chat)

        self.role_guest = Role.objects.create(name="TEST_GUEST")

        # Memberships
        WorkspaceMembership.objects.create(user=self.user_with_perm, workspace=self.ws_a, role=self.role_admin, is_default=True)
        WorkspaceMembership.objects.create(user=self.user_with_perm, workspace=self.ws_b, role=self.role_admin, is_default=False)
        WorkspaceMembership.objects.create(user=self.user_no_perm, workspace=self.ws_a, role=self.role_guest, is_default=True)

        # Pre-seed Knowledge Base and Document in Workspace A
        self.kb_a = create_knowledge_base(self.ws_a, self.user_with_perm, "Secret Alpha KB")
        file_obj = SimpleUploadedFile("secret.txt", b"Confidential financial strategies.", content_type="text/plain")
        self.doc_a = upload_and_ingest_document(
            workspace=self.ws_a,
            user=self.user_with_perm,
            knowledge_base=self.kb_a,
            file_obj=file_obj,
            title="Secret Alpha Strategy",
            file_type="TXT",
        )

    def test_unauthenticated_api_rejected(self):
        """Test unauthenticated request to chat API is rejected with 401."""
        resp = self.client.post("/api/v1/ai/chat/", {"message": "Hello"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_workspace_rejected(self):
        """An authenticated non-member is denied as an internal API caller."""
        orphan_user = User.objects.create_user(username="orphan_user", email="orphan@example.com", password="password")
        self.client.force_authenticate(user=orphan_user)
        resp = self.client.post("/api/v1/ai/chat/", {"message": "Hello"})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_denied_without_ai_chat_perm(self):
        """Test user lacking 'ai.chat' permission receives 403 Forbidden."""
        self.client.force_authenticate(user=self.user_no_perm)
        resp = self.client.post(
            "/api/v1/ai/chat/",
            {"message": "Hello"},
            HTTP_X_WORKSPACE=self.ws_a.code,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data["error"]["code"], "PERMISSION_DENIED")

    def test_permission_denied_for_kb_creation_without_manage_perm(self):
        """Test user without 'knowledge.manage_knowledge' cannot create knowledge base."""
        self.client.force_authenticate(user=self.user_no_perm)
        resp = self.client.post(
            "/api/v1/knowledge/bases/",
            {"name": "Unauthorized KB"},
            HTTP_X_WORKSPACE=self.ws_a.code,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_tenant_document_access_prevented(self):
        """Test accessing document belonging to Workspace A from Workspace B returns 404."""
        self.client.force_authenticate(user=self.user_with_perm)
        # Attempt to access doc_a while in workspace B
        resp = self.client.get(
            f"/api/v1/knowledge/documents/{self.doc_a.id}/",
            HTTP_X_WORKSPACE=self.ws_b.code,
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_sql_injection_immunity_in_chat(self):
        """Test chat input with SQL injection payload executes safely without database error."""
        self.client.force_authenticate(user=self.user_with_perm)
        sql_payload = "'; DROP TABLE knowledge_document; SELECT * FROM accounts_user WHERE '1'='1"
        resp = self.client.post(
            "/api/v1/ai/chat/",
            {"message": sql_payload},
            HTTP_X_WORKSPACE=self.ws_a.code,
        )
        # Should execute safely (status 200) and return controlled fallback
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(Document.objects.filter(id=self.doc_a.id).exists())

    def test_audit_log_generated_on_chat_query(self):
        """Test every chat query produces an audit record."""
        initial_count = AuditLog.objects.filter(action="AI_CHAT_QUERY").count()

        self.client.force_authenticate(user=self.user_with_perm)
        resp = self.client.post(
            "/api/v1/ai/chat/",
            {"message": "Test audit logging question"},
            HTTP_X_WORKSPACE=self.ws_a.code,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        new_count = AuditLog.objects.filter(action="AI_CHAT_QUERY").count()
        self.assertEqual(new_count, initial_count + 1)
