"""
Automated tests for Grounded AI Assistant, Structured Business Tools,
Hybrid Questions, and No-Context Fallbacks.
"""

from decimal import Decimal
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, Permission, Role
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.retail.models import Order, OrderStatus, Customer
from apps.service_ops.models import ServiceRequest, ServiceRequestStatus, ServiceRequestPriority
from apps.knowledge.models import (
    KnowledgeBase,
    ConversationSession,
    ChatMessage,
    ChatRole,
)
from apps.knowledge.services import (
    create_knowledge_base,
    upload_and_ingest_document,
    answer_grounded_query,
    FALLBACK_NO_CONTEXT_MESSAGE,
)
from apps.knowledge.tools import (
    get_sales_summary,
    get_customer_summary,
    get_service_ticket_summary,
    ToolPermissionDenied,
)


class GroundingAssistantTests(TestCase):
    def setUp(self):
        # Create Superuser
        self.admin = User.objects.create_superuser(username="admin_user", email="admin@example.com", password="password")

        # Create Standard User
        self.user = User.objects.create_user(username="chat_user", email="user@example.com", password="password")

        # Retail Workspace
        self.retail_ws = Workspace.objects.create(
            code="retail-test",
            name="Retail Operations Test",
            workspace_type=WorkspaceType.RETAIL,
        )

        # Service Workspace
        self.service_ws = Workspace.objects.create(
            code="service-test",
            name="Service Operations Test",
            workspace_type=WorkspaceType.SERVICE,
        )

        # Permissions
        self.perm_ai_chat, _ = Permission.objects.get_or_create(codename="ai.chat", defaults={"name": "AI Chat", "module": "ai"})
        self.perm_view_order, _ = Permission.objects.get_or_create(codename="retail.view_order", defaults={"name": "View Order", "module": "retail"})
        self.perm_view_cust, _ = Permission.objects.get_or_create(codename="retail.view_customer", defaults={"name": "View Customer", "module": "retail"})
        self.perm_view_sr, _ = Permission.objects.get_or_create(codename="service.view_servicerequest", defaults={"name": "View SR", "module": "service_ops"})

        # Role & Membership
        self.role = Role.objects.create(name="OPERATOR_ROLE")
        self.role.permissions.add(self.perm_ai_chat, self.perm_view_order, self.perm_view_cust, self.perm_view_sr)

        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.retail_ws,
            role=self.role,
            is_default=True,
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.service_ws,
            role=self.role,
            is_default=False,
        )

        # Ingest document into Retail Workspace
        self.retail_kb = create_knowledge_base(self.retail_ws, self.admin, "Retail Docs")
        policy_text = b"Chinh sach bao hanh: May tinh xach tay laptop duoc bao hanh 24 thang. Khach duoc 1 doi 1 trong 30 ngay dau."
        file_obj = SimpleUploadedFile("laptop_warranty.txt", policy_text, content_type="text/plain")
        self.doc_retail = upload_and_ingest_document(
            workspace=self.retail_ws,
            user=self.admin,
            knowledge_base=self.retail_kb,
            file_obj=file_obj,
            title="Chinh Sach Bao Hanh Laptop",
            file_type="TXT",
        )

        # Create structured sample retail records
        from django.utils import timezone
        now = timezone.now()

        self.customer = Customer.objects.create(
            workspace=self.retail_ws,
            code="CUST-001",
            name="Nguyen Van A",
            phone="0901234567",
            customer_segment="VIP",
        )
        self.order = Order.objects.create(
            workspace=self.retail_ws,
            order_number="ORD-001",
            customer=self.customer,
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("15000000.00"),
            order_date=now.date(),
            order_timestamp=now,
        )

    def test_structured_tool_get_sales_summary(self):
        """Test get_sales_summary retrieves verified workspace sales metrics."""
        summary = get_sales_summary(self.retail_ws, self.user)
        self.assertEqual(summary["total_orders"], 1)
        self.assertEqual(summary["completed_orders"], 1)
        self.assertEqual(summary["total_revenue_raw"], 15000000.0)

    def test_grounded_query_with_citations(self):
        """Test query answering from ingested document includes source citations."""
        res = answer_grounded_query(
            workspace=self.retail_ws,
            user=self.user,
            message="Chinh sach bao hanh laptop quy dinh thoi han bao nhieu thang?",
        )

        self.assertIn("session_id", res)
        self.assertIn("24 thang", res["answer"])
        self.assertGreater(len(res["sources"]), 0)
        self.assertEqual(res["sources"][0]["document_title"], "Chinh Sach Bao Hanh Laptop")

    def test_hybrid_query_combines_tools_and_documents(self):
        """Test hybrid question accesses both structured tool facts and document chunks."""
        res = answer_grounded_query(
            workspace=self.retail_ws,
            user=self.user,
            message="Tong doanh thu ban hang va chinh sach bao hanh laptop la bao nhieu?",
        )

        # Verify tool was invoked
        tools_invoked = [t["tool"] for t in res["tools_used"]]
        self.assertIn("get_sales_summary", tools_invoked)

        # Verify document citation exists
        self.assertGreater(len(res["sources"]), 0)

        # Verify answer mentions sales data and warranty term
        self.assertTrue(
            "doanh thu" in res["answer"].lower() or "15,000,000" in res["answer"] or "15.000.000" in res["answer"]
        )
        self.assertIn("24 thang", res["answer"])

    def test_out_of_domain_query_returns_strict_fallback(self):
        """
        CRITICAL TEST: An unsupported query without match must return
        the exact controlled fallback message without hallucinating.
        """
        res = answer_grounded_query(
            workspace=self.retail_ws,
            user=self.user,
            message="Gia co phieu hang khong Boeing hom nay tren thi truong chung khoan la bao nhieu?",
        )

        self.assertEqual(res["answer"], FALLBACK_NO_CONTEXT_MESSAGE)
        self.assertEqual(len(res["sources"]), 0)

    def test_conversation_session_history_persisted(self):
        """Test conversation sessions and chat messages are saved in database."""
        res1 = answer_grounded_query(
            workspace=self.retail_ws,
            user=self.user,
            message="Cau hoi 1 ve chinh sach laptop",
        )
        sess_id = res1["session_id"]

        res2 = answer_grounded_query(
            workspace=self.retail_ws,
            user=self.user,
            message="Cau hoi 2 trong cung phien",
            session_id=sess_id,
        )
        self.assertEqual(res2["session_id"], sess_id)

        session = ConversationSession.objects.get(id=sess_id)
        self.assertEqual(session.messages.count(), 4)  # 2 user msgs + 2 assistant msgs
