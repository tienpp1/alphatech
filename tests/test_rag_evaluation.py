"""
Automated tests for AI RAG Benchmark Evaluation dataset and metrics.
"""

from decimal import Decimal
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.accounts.models import User, Permission
from apps.workspaces.models import Workspace, WorkspaceType
from apps.retail.models import Customer, Order, OrderStatus, Category, Product
from apps.service_ops.models import ServiceRequest, ServiceRequestStatus, ServiceRequestPriority
from apps.knowledge.services import (
    create_knowledge_base,
    upload_and_ingest_document,
)
from apps.knowledge.evaluation import run_benchmark_evaluation, BENCHMARK_QUESTIONS


class RAGEvaluationBenchmarkTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="eval_admin", email="eval@example.com", password="password")

        # Retail Workspace
        self.retail_ws = Workspace.objects.create(code="eval-retail", name="Eval Retail", workspace_type=WorkspaceType.RETAIL)

        # Ingest benchmark documents into Retail Workspace with accurate Vietnamese diacritics
        kb = create_knowledge_base(self.retail_ws, self.admin, "Eval Retail KB")

        docs = [
            (
                "Chính Sách Bảo Hành Thiết Bị",
                "Chính sách bảo hành: Thiết bị máy tính xách tay (Laptop) được bảo hành chính hãng 24 tháng. Đổi mới 1 đổi 1 trong 30 ngày đầu nếu phát sinh lỗi phần cứng do nhà sản xuất.".encode("utf-8")
            ),
            (
                "Chính Sách Bán Hàng Và Đổi Trả",
                "Chính sách bán hàng: Khách hàng mua sản phẩm được quyền đổi trả sản phẩm trong vòng 07 ngày kể từ ngày mua. Sản phẩm đổi trả phải còn nguyên tem mác và hộp đóng gói ban đầu.".encode("utf-8")
            ),
            (
                "Quy Chế Khách Hàng VIP",
                "Quy chế VIP: Khách hàng VIP được chiết khấu giảm giá 10% trên tổng mọi đơn hàng và miễn phí vận chuyển trong bán kính 15km.".encode("utf-8")
            ),
            (
                "Cẩm Nang Khuyến Mãi Flash Sale",
                "Quy định Flash Sale: Mỗi khách hàng chỉ được mua tối đa 02 sản phẩm giảm giá sâu trong chương trình Flash Sale hàng tuần.".encode("utf-8")
            ),
        ]

        for title, text in docs:
            f = SimpleUploadedFile(f"{title}.txt", text, content_type="text/plain")
            upload_and_ingest_document(
                workspace=self.retail_ws,
                user=self.admin,
                knowledge_base=kb,
                file_obj=f,
                title=title,
                file_type="TXT",
            )

        # Seed structured retail data
        from django.utils import timezone
        now = timezone.now()
        cat = Category.objects.create(workspace=self.retail_ws, code="CAT-EV", name="Thiết bị số")
        Product.objects.create(workspace=self.retail_ws, category=cat, sku="SKU-EV", name="Laptop Gaming Pro", unit_price=Decimal("25000000.00"), is_active=True)
        cust = Customer.objects.create(workspace=self.retail_ws, code="C-EV", name="Customer Eval", phone="0999888777")
        Order.objects.create(
            workspace=self.retail_ws,
            order_number="ORD-EV",
            customer=cust,
            status=OrderStatus.COMPLETED,
            total_amount=Decimal("20000000.00"),
            order_date=now.date(),
            order_timestamp=now,
        )

    def test_benchmark_evaluation_metrics_pass_threshold(self):
        """Run benchmark evaluation and assert minimum quality thresholds."""
        metrics = run_benchmark_evaluation(self.retail_ws, self.admin)

        self.assertGreaterEqual(metrics["total_evaluated"], 5)
        # Fallback precision must be 100% on out-of-domain questions
        self.assertEqual(metrics["fallback_precision"], 100.0)
        # Grounded correctness rate must be >= 80%
        self.assertGreaterEqual(metrics["grounded_correctness_rate"], 80.0)
