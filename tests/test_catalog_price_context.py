"""Actual scoped catalog prices, never sampled KB or sales-derived prices."""
from decimal import Decimal

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import Permission, Role, User
from apps.knowledge.tools import ToolPermissionDenied, get_product_catalog_summary
from apps.retail.models import Category, Product
from apps.workspaces.models import Workspace, WorkspaceMembership


class CatalogPriceContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ws = Workspace.objects.create(code="catalog-price-a", name="Catalog A", workspace_type="RETAIL")
        cls.other_ws = Workspace.objects.create(code="catalog-price-b", name="Catalog B", workspace_type="RETAIL")
        cls.category = Category.objects.create(workspace=cls.ws, code="LAPTOP", name="Máy tính xách tay")
        cls.mouse_category = Category.objects.create(workspace=cls.ws, code="MOUSE", name="Chuột")
        cls.foreign_category = Category.objects.create(workspace=cls.other_ws, code="LAPTOP", name="Foreign laptops")
        cls.user = User.objects.create_user(username="catalog-reader", email="catalog-reader@example.test")
        cls.no_permission = User.objects.create_user(username="catalog-no-perm", email="catalog-no-perm@example.test")
        cls.customer = User.objects.create_user(username="catalog-customer", email="catalog-customer@example.test")
        permission, _ = Permission.objects.get_or_create(codename="retail.view_product", defaults={"name": "View catalog", "module": "retail"})
        cls.role = Role.objects.create(name="CATALOG_PRICE_READER")
        cls.role.permissions.add(permission)
        cls.membership = WorkspaceMembership.objects.create(user=cls.user, workspace=cls.ws, role=cls.role)
        WorkspaceMembership.objects.create(user=cls.no_permission, workspace=cls.ws)
        for number in range(1, 7):
            Product.objects.create(workspace=cls.ws, category=cls.category, sku=f"LAP-{number:02d}",
                name=f"A{number} Everyday laptop", unit_price=Decimal(f"100{number}.00"))
        cls.maximum = Product.objects.create(workspace=cls.ws, category=cls.category, sku="LAP-MAX",
            name="Z Maximum laptop", unit_price=Decimal("9999.99"), cost_price=Decimal("8000.00"),
            description="private supplier notes and description-only-marker")
        Product.objects.create(workspace=cls.ws, category=cls.category, sku="LAP-INACTIVE",
            name="Inactive laptop", unit_price=Decimal("100000.00"), is_active=False)
        Product.objects.create(workspace=cls.ws, category=cls.category, sku="LAP-DELETED",
            name="Deleted laptop", unit_price=Decimal("90000.00"), deleted_at=timezone.now())
        Product.objects.create(workspace=cls.ws, category=cls.foreign_category, sku="LAP-WRONG-CATEGORY",
            name="Wrong category workspace", unit_price=Decimal("80000.00"))
        Product.objects.create(workspace=cls.other_ws, category=cls.foreign_category, sku="LAP-FOREIGN",
            name="Foreign workspace product", unit_price=Decimal("70000.00"))
        Product.objects.create(workspace=cls.ws, category=cls.mouse_category, sku="MOUSE-HIGH",
            name="Premium mouse", unit_price=Decimal("60000.00"))

    def summary(self, **kwargs):
        params = {"sort_by": "unit_price", "category": "laptop"}
        params.update(kwargs)
        return get_product_catalog_summary(self.ws, self.user, **params)

    def test_extremum_queries_all_eligible_products_not_first_five(self):
        result = self.summary(limit=1)
        self.assertEqual(result.get("ranked_products"), [{"sku": "LAP-MAX", "name": "Z Maximum laptop",
            "unit_price": "9999.99", "unit_price_formatted": "9,999.99 VND"}])
        self.assertEqual(result.get("total_matching"), 7)
        self.assertEqual(result.get("displayed_count"), 1)
        self.assertEqual(result.get("limit"), 1)
        self.assertTrue(result.get("truncated"))
        self.assertEqual(result.get("tie_count"), 1)
        self.assertEqual(result.get("sort_order"), "DESC")
        self.assertIn("Product.unit_price", result.get("price_basis", ""))

    def test_lowest_price_is_current_catalog_not_order_data(self):
        result = self.summary(sort_order="ASC", limit=2)
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-01", "LAP-02"])
        self.assertEqual([row["unit_price"] for row in result.get("ranked_products", [])], ["1001.00", "1002.00"])

    def test_foreign_workspace_inactive_deleted_and_foreign_category_are_excluded(self):
        result = self.summary(limit=20)
        self.assertEqual(result.get("displayed_count"), 7)
        self.assertEqual({row["sku"] for row in result.get("ranked_products", [])},
            {"LAP-01", "LAP-02", "LAP-03", "LAP-04", "LAP-05", "LAP-06", "LAP-MAX"})
        self.assertFalse(result.get("truncated"))

    def test_category_matches_exact_normalized_name_code_or_scoped_id(self):
        for category in ("LAPTOP", "Máy tính xách tay", "may tinh xach tay", str(self.category.pk)):
            with self.subTest(category=category):
                self.assertEqual(self.summary(category=category).get("total_matching"), 7)
        for category in ("lap", "does-not-exist", str(self.foreign_category.pk)):
            with self.subTest(category=category):
                self.assertEqual(self.summary(category=category).get("ranked_products"), [])
                self.assertEqual(self.summary(category=category).get("total_matching"), 0)

    def test_ambiguous_category_does_not_select_first_match(self):
        Category.objects.create(workspace=self.ws, code="laptop-alternative", name="LAPTOP")
        self.assertEqual(self.summary().get("ranked_products"), [])

    def test_empty_match_is_explicit_and_has_no_extremum_ties(self):
        result = self.summary(search="not-a-real-product", limit=1)
        self.assertEqual(result.get("ranked_products"), [])
        self.assertEqual(result.get("total_matching"), 0)
        self.assertEqual(result.get("displayed_count"), 0)
        self.assertEqual(result.get("tie_count"), 0)
        self.assertFalse(result.get("truncated"))

    def test_tied_extremum_has_deterministic_sku_order_and_total_tie_count(self):
        Product.objects.create(workspace=self.ws, category=self.category, sku="LAP-MAX-2",
            name="Another maximum laptop", unit_price=Decimal("9999.99"))
        result = self.summary(limit=1)
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-MAX"])
        self.assertEqual(result.get("tie_count"), 2)
        result = self.summary(limit=2)
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-MAX", "LAP-MAX-2"])

    def test_decimal_precision_and_price_bounds_are_applied_before_sort(self):
        Product.objects.create(workspace=self.ws, category=self.category, sku="LAP-DECIMAL",
            name="Decimal laptop", unit_price=Decimal("9999.98"))
        result = self.summary(min_price="9999.98", max_price="9999.99", limit=2)
        self.assertEqual([row["unit_price"] for row in result.get("ranked_products", [])], ["9999.99", "9999.98"])
        result = self.summary(min_price="9999.98", min_price_inclusive=False, max_price="9999.99", limit=2)
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-MAX"])
        result = self.summary(min_price="9999.98", max_price="9999.99", max_price_inclusive=False, limit=2)
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-DECIMAL"])

    def test_multiple_conditions_intersect_category_name_and_price(self):
        result = self.summary(search="Everyday", min_price="1003.00", max_price="1005.00", sort_order="ASC", limit=20)
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-03", "LAP-04", "LAP-05"])
        self.assertEqual(result.get("total_matching"), 3)

    def test_search_mode_matches_name_or_sku_but_never_description(self):
        result = get_product_catalog_summary(self.ws, self.user, search="lap-03")
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-03"])
        self.assertEqual(self.summary(search="description-only-marker").get("ranked_products"), [])

    def test_price_bound_alone_enables_safe_mode(self):
        result = get_product_catalog_summary(self.ws, self.user, min_price="9999.99", max_price="9999.99")
        self.assertEqual([row["sku"] for row in result.get("ranked_products", [])], ["LAP-MAX"])

    def test_ranked_payload_omits_cost_description_and_unrelated_metadata(self):
        result = self.summary(limit=1)
        self.assertEqual(set(result.get("ranked_products", [{}])[0]),
            {"sku", "name", "unit_price", "unit_price_formatted"})
        self.assertNotIn("private supplier", str(result))
        self.assertNotIn("cost_price", str(result))

    def test_invalid_limits_are_rejected_not_silently_truncated_or_coerced(self):
        for limit in (True, False, 0, -1, 21, 1.5, "2", None, [], {}):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.summary(limit=limit)

    def test_invalid_price_bounds_are_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity", "-0.01", "not-price", "", True, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.summary(min_price=value)
        with self.assertRaises(ValueError):
            self.summary(min_price="2000.00", max_price="1000.00")
        for flag in ("false", 0, None):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                self.summary(min_price="0", min_price_inclusive=flag)

    def test_invalid_search_and_ordering_are_rejected(self):
        for search in ("x" * 121, [], {}, True):
            with self.subTest(search=search), self.assertRaises(ValueError):
                self.summary(search=search)
        for options in ({"sort_by": "cost_price"}, {"sort_order": "INVALID"}, {"sort_order": []}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.summary(**options)

    def test_permission_is_required_before_validating_or_reading_price_parameters(self):
        for user in (AnonymousUser(), self.customer, self.no_permission):
            with self.subTest(user=str(user)), self.assertRaises(ToolPermissionDenied):
                get_product_catalog_summary(self.ws, user, sort_by="unit_price", limit=-1)
        with self.assertRaises(ToolPermissionDenied):
            get_product_catalog_summary(self.other_ws, self.user, sort_by="unit_price")
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])
        with self.assertRaises(ToolPermissionDenied):
            self.summary()

    def test_inactive_regular_user_is_denied(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        with self.assertRaises(ToolPermissionDenied):
            self.summary()

    def test_legacy_default_summary_remains_compatible(self):
        result = get_product_catalog_summary(self.ws, self.user)
        self.assertEqual(result["total_products"], 11)
        self.assertEqual(result["active_products"], 10)
        self.assertEqual(len(result["sample_products"]), 5)
        self.assertNotIn("ranked_products", result)
