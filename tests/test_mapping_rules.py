"""
Unit tests for Data Mapping Rule Types & Transformation Engine.
Covers:
- FIELD_MAPPING (Direct alias / rename)
- TYPE_CONVERSION (Decimal, Date, DateTime, Boolean, Integer, Float)
- VALUE_MAPPING (Dictionary enumeration lookup with default fallback)
- BUSINESS_FORMULA (Safe AST expression evaluation)
- Unsafe formula rejection (eval, exec, __import__, function calls)
"""

from decimal import Decimal
from datetime import date, datetime
from django.test import TestCase

from apps.mapping.models import MappingRule, RuleType, AIConfirmationStatus
from apps.mapping.engine.converters import (
    to_decimal,
    to_date,
    to_datetime,
    to_boolean,
    to_integer,
    to_float,
    to_list,
)
from apps.mapping.engine.value_mappers import apply_value_mapping
from apps.mapping.engine.safe_evaluator import (
    evaluate_safe_expression,
    SecurityValidationError,
    FormulaEvaluationError,
)
from apps.mapping.engine.transformer import transform_single_record


class MappingRulesEngineTestCase(TestCase):
    def test_field_mapping_direct(self):
        """Tests direct field alias extraction."""
        raw = {"ma_khach_hang": "CUST-001", "ten": "Nguyen Van A"}
        rule = MappingRule(
            source_field="ma_khach_hang",
            target_field="customer_id",
            rule_type=RuleType.FIELD_MAPPING,
        )
        canonical, errors = transform_single_record(raw, [rule], target_entity="Customer")
        self.assertEqual(len(errors), 0)
        self.assertEqual(canonical.get("customer_id"), "CUST-001")

    def test_type_conversion_decimal(self):
        """Tests decimal conversion with currency symbols and thousand separators."""
        self.assertEqual(to_decimal("1.500.000 đ"), Decimal("1500000.00"))
        self.assertEqual(to_decimal("1,250,000.50 VND"), Decimal("1250000.50"))
        self.assertEqual(to_decimal("$ 450.00"), Decimal("450.00"))
        self.assertEqual(to_decimal("(250.00)"), Decimal("-250.00"))
        self.assertEqual(to_decimal(15000), Decimal("15000"))

    def test_type_conversion_date(self):
        """Tests parsing multi-format date strings into datetime.date."""
        self.assertEqual(to_date("25/08/2026"), date(2026, 8, 25))
        self.assertEqual(to_date("2026-08-25"), date(2026, 8, 25))
        self.assertEqual(to_date("25-08-2026"), date(2026, 8, 25))
        self.assertEqual(to_date("2026/08/25"), date(2026, 8, 25))

    def test_type_conversion_boolean(self):
        """Tests truthy/falsy normalization."""
        self.assertTrue(to_boolean("true"))
        self.assertTrue(to_boolean("1"))
        self.assertTrue(to_boolean("có"))
        self.assertTrue(to_boolean("active"))
        self.assertFalse(to_boolean("false"))
        self.assertFalse(to_boolean("0"))
        self.assertFalse(to_boolean("không"))
        self.assertFalse(to_boolean("inactive"))

    def test_type_conversion_integer_and_float(self):
        """Tests integer and float parsing."""
        self.assertEqual(to_integer("150"), 150)
        self.assertEqual(to_integer("15.0"), 15)
        self.assertEqual(to_float("106.6821"), 106.6821)

    def test_value_mapping(self):
        """Tests categorical enumeration dictionary translation with default fallback."""
        v_map = {
            "da_thanh_toan": "COMPLETED",
            "1": "COMPLETED",
            "cho_xu_ly": "PENDING",
            "da_huy": "CANCELLED",
        }
        self.assertEqual(apply_value_mapping("da_thanh_toan", v_map, default_val="PENDING"), "COMPLETED")
        self.assertEqual(apply_value_mapping("1", v_map, default_val="PENDING"), "COMPLETED")
        self.assertEqual(apply_value_mapping("CHO_XU_LY", v_map, default_val="PENDING"), "PENDING")
        self.assertEqual(apply_value_mapping("unknown_code", v_map, default_val="PENDING"), "PENDING")

    def test_business_formula_arithmetic(self):
        """Tests safe AST-evaluated arithmetic formula."""
        record = {
            "unit_price": "200000",
            "quantity": 5,
            "discount": "50000",
        }
        # (unit_price * quantity) - discount = (200000 * 5) - 50000 = 950000
        result = evaluate_safe_expression("unit_price * quantity - discount", record)
        self.assertEqual(result, Decimal("950000"))

    def test_business_formula_string_concatenation(self):
        """Tests safe AST-evaluated string concatenation."""
        record = {
            "last_name": "Nguyen",
            "first_name": "Van A",
        }
        result = evaluate_safe_expression("last_name + ' ' + first_name", record)
        self.assertEqual(result, "Nguyen Van A")

    def test_unsafe_formula_rejection_eval_and_exec(self):
        """Verifies that arbitrary execution attempts (eval, exec, __import__) are strictly blocked."""
        record = {"x": 10}

        with self.assertRaises(SecurityValidationError):
            evaluate_safe_expression("__import__('os').system('echo pwned')", record)

        with self.assertRaises(SecurityValidationError):
            evaluate_safe_expression("eval('1 + 1')", record)

        with self.assertRaises(SecurityValidationError):
            evaluate_safe_expression("open('/etc/passwd')", record)

        with self.assertRaises(SecurityValidationError):
            evaluate_safe_expression("x.__class__.__bases__", record)

    def test_business_formula_division_by_zero(self):
        """Verifies graceful handling of division by zero in formulas."""
        record = {"a": 100, "b": 0}
        with self.assertRaises(FormulaEvaluationError):
            evaluate_safe_expression("a / b", record)
