"""
Unit tests for Canonical Model Consistency & Post-Phase-7 Verification.
Covers:
- Retail Product canonical model (commercial catalog focus, stock_quantity as optional non-core data)
- Service category consistency (strictly INSTALLATION, MAINTENANCE, DATABASE_CONSULTING, DEVICE_REPAIR; rejection of stale INSPECTION)
- Order money semantics (Order.total_amount as discrete transaction amount, Revenue as derived analytics metric)
- RAG readiness (predictable canonical field names)
"""

from decimal import Decimal
from django.test import TestCase

from apps.workspaces.models import Workspace, WorkspaceType
from apps.accounts.models import User, Role
from apps.retail.models import Customer, Product, Category, Order, OrderStatus
from apps.retail.selectors import get_revenue_summary
from apps.service_ops.models import Service, ServiceCategory
from apps.integration.models import DataSource, SourceType, ImportJob, RawImportRecord
from apps.mapping.canonical import get_canonical_model
from apps.mapping.validators import validate_canonical_record
from apps.mapping.models import MappingProfile, MappingRule, RuleType
from apps.mapping.services import create_mapping_profile, add_mapping_rule, apply_mapping_to_domain


class CanonicalConsistencyTestCase(TestCase):
    def setUp(self):
        self.retail_ws = Workspace.objects.create(
            name="Retail Workspace",
            code="retail-ws",
            workspace_type=WorkspaceType.RETAIL,
        )
        self.service_ws = Workspace.objects.create(
            name="Service Workspace",
            code="service-ws",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.user = User.objects.create_user(username="consistency_user", email="consistency@example.com")
        self.category = Category.objects.create(workspace=self.retail_ws, code="ELEC", name="Electronics")

    def test_product_canonical_model_non_warehouse(self):
        """Verifies Product does not require stock_quantity and treats it as optional non-core data."""
        prod_model = get_canonical_model("Product")
        self.assertIsNotNone(prod_model)
        self.assertFalse(prod_model.get_field("stock_quantity").required)

        # Valid payload without stock_quantity
        valid_payload = {
            "sku": "PROD-001",
            "name": "Wireless Mouse",
            "unit_price": "250000",
            "category_code": "ELEC",
        }
        errors = validate_canonical_record(valid_payload, "Product", self.retail_ws)
        self.assertEqual(len(errors), 0)

        # Valid payload with optional non-core stock_quantity
        payload_with_stock = {
            "sku": "PROD-002",
            "name": "Mechanical Keyboard",
            "unit_price": "1250000",
            "category_code": "ELEC",
            "stock_quantity": 45,
        }
        errors_stock = validate_canonical_record(payload_with_stock, "Product", self.retail_ws)
        self.assertEqual(len(errors_stock), 0)

    def test_service_category_consistency_rejects_stale_inspection(self):
        """Verifies Service category strictly enforces approved categories and rejects stale INSPECTION."""
        svc_model = get_canonical_model("Service")
        self.assertIsNotNone(svc_model)
        approved_categories = ["INSTALLATION", "MAINTENANCE", "DATABASE_CONSULTING", "DEVICE_REPAIR"]
        self.assertEqual(svc_model.get_field("category").choices, approved_categories)

        # Approved categories pass validation
        for cat in approved_categories:
            payload = {"code": f"SVC-{cat[:4]}", "name": f"Service {cat}", "category": cat}
            errs = validate_canonical_record(payload, "Service", self.service_ws)
            self.assertEqual(len(errs), 0, msg=f"Category {cat} should be valid")

        # Stale INSPECTION category is strictly rejected with INVALID_CHOICE
        stale_payload = {
            "code": "SVC-INSP-01",
            "name": "Annual HVAC Inspection",
            "category": "INSPECTION",
        }
        errs_stale = validate_canonical_record(stale_payload, "Service", self.service_ws)
        self.assertTrue(any(e["code"] == "INVALID_CHOICE" for e in errs_stale))

    def test_order_money_semantics_total_amount_and_revenue(self):
        """
        Verifies Order monetary semantics:
        - total_amount is the physical transaction field stored on Order.
        - revenue is the derived analytics metric and accepted canonical alias.
        - get_revenue_summary aggregates valid orders (excluding CANCELLED).
        """
        cust = Customer.objects.create(workspace=self.retail_ws, code="CUST-MONEY-01", name="Client A")

        # Test A: Mapping directly via total_amount
        ds = DataSource.objects.create(workspace=self.retail_ws, name="Order Feed 1", source_type=SourceType.CSV)
        prof1 = create_mapping_profile(self.retail_ws, self.user, "Order Total Map", "Order", data_source=ds)
        add_mapping_rule(prof1, self.user, "so_hd", "order_number", RuleType.FIELD_MAPPING)
        add_mapping_rule(prof1, self.user, "ma_kh", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(prof1, self.user, "ngay", "order_date", RuleType.TYPE_CONVERSION, {"target_type": "DATE"})
        add_mapping_rule(prof1, self.user, "tong_tien", "total_amount", RuleType.TYPE_CONVERSION, {"target_type": "DECIMAL"})

        job1 = ImportJob.objects.create(workspace=self.retail_ws, data_source=ds, total_rows=1)
        RawImportRecord.objects.create(
            workspace=self.retail_ws,
            import_job=job1,
            row_number=1,
            raw_data={"so_hd": "ORD-MONEY-01", "ma_kh": "CUST-MONEY-01", "ngay": "2026-08-27", "tong_tien": "1.800.000 đ"},
        )

        res1 = apply_mapping_to_domain(self.retail_ws, self.user, prof1, job1, strict=True)
        self.assertEqual(res1["status"], "COMPLETED")

        order1 = Order.objects.for_workspace(self.retail_ws).get(order_number="ORD-MONEY-01")
        self.assertEqual(order1.total_amount, Decimal("1800000.00"))

        # Test B: Mapping via revenue canonical alias
        prof2 = create_mapping_profile(self.retail_ws, self.user, "Order Rev Map", "Order", data_source=ds)
        add_mapping_rule(prof2, self.user, "so_hd", "order_number", RuleType.FIELD_MAPPING)
        add_mapping_rule(prof2, self.user, "ma_kh", "customer_id", RuleType.FIELD_MAPPING)
        add_mapping_rule(prof2, self.user, "ngay", "order_date", RuleType.TYPE_CONVERSION, {"target_type": "DATE"})
        add_mapping_rule(prof2, self.user, "doanh_thu", "revenue", RuleType.TYPE_CONVERSION, {"target_type": "DECIMAL"})

        job2 = ImportJob.objects.create(workspace=self.retail_ws, data_source=ds, total_rows=1)
        RawImportRecord.objects.create(
            workspace=self.retail_ws,
            import_job=job2,
            row_number=1,
            raw_data={"so_hd": "ORD-MONEY-02", "ma_kh": "CUST-MONEY-01", "ngay": "2026-08-27", "doanh_thu": "2.200.000 đ"},
        )

        res2 = apply_mapping_to_domain(self.retail_ws, self.user, prof2, job2, strict=True)
        self.assertEqual(res2["status"], "COMPLETED")

        order2 = Order.objects.for_workspace(self.retail_ws).get(order_number="ORD-MONEY-02")
        self.assertEqual(order2.total_amount, Decimal("2200000.00"))

        # Verify realized revenue analytics aggregation (1.8M + 2.2M = 4.0M)
        rev_summary = get_revenue_summary(self.retail_ws)
        self.assertEqual(rev_summary["total_revenue"], Decimal("4000000.00"))
        self.assertEqual(rev_summary["order_count"], 2)

    def test_order_missing_both_monetary_fields_fails_validation(self):
        """Verifies that an Order without total_amount or revenue fails canonical validation."""
        cust = Customer.objects.create(workspace=self.retail_ws, code="CUST-NO-MONEY", name="Client B")
        payload = {
            "order_number": "ORD-NOMONEY-01",
            "customer_id": "CUST-NO-MONEY",
            "order_date": "2026-08-27",
        }
        errs = validate_canonical_record(payload, "Order", self.retail_ws)
        self.assertTrue(any(e["field"] == "total_amount" and e["code"] == "REQUIRED_FIELD_MISSING" for e in errs))

    def test_rag_readiness_canonical_naming(self):
        """Verifies canonical entity schemas provide clean, predictable field names suitable for RAG context generation."""
        for entity_name in ["Customer", "Product", "Order", "OrderItem", "Branch", "Service", "Employee", "ServiceRequest", "Task", "LaborEntry"]:
            model_def = get_canonical_model(entity_name)
            self.assertIsNotNone(model_def)
            self.assertGreater(len(model_def.fields), 0)
            for fname, fdef in model_def.fields.items():
                self.assertTrue(fname.islower(), f"Field '{fname}' on '{entity_name}' should be snake_case")
                self.assertFalse(" " in fname, f"Field '{fname}' on '{entity_name}' should not have spaces")
                self.assertIsNotNone(fdef.description, f"Field '{fname}' on '{entity_name}' must have a description")
