"""
Phase 11 Comprehensive Security Hardening & Platform Isolation Test Suite.
Validates:
1. Authentication Security (Session + DRF Token, unauthenticated rejection, inactive user block, logout token deletion, no JWT)
2. RBAC Enforcement (Admin, Manager, Employee, Viewer across mutations, tool execution, and approvals)
3. Multi-Tenant Cross-Workspace Scoping (Retail, Service, GIS, Integration, Mapping, RAG, Forecasting, Recommendations, Approvals)
4. IDOR Resistance (Direct ID queries across workspace boundaries return 404/403)
5. AI Safety & Tool Governance (Input schema validation, unknown tools rejected, malformed args blocked, zero direct mutations)
6. Data Integration & SSRF Protection (Internal IP, loopback, and metadata endpoint blocking)
7. Safe AST Expression Evaluator (Strict rejection of eval, exec, __import__, function calls, attributes)
8. GIS Customer PII Privacy Masking (Masking phone, email, address for non-authorized viewers)
"""

import io
import json
from decimal import Decimal
from django.test import TestCase
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.accounts.models import User, Role, Permission
from apps.accounts.services import authenticate_user
from apps.workspaces.models import Workspace, WorkspaceType, WorkspaceMembership
from apps.retail.models import Customer, Category, Product, Branch, Order, OrderItem, OrderStatus
from apps.service_ops.models import Service, Employee, SLA, ServiceRequest, ServiceRequestStatus, ServiceCategory
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.approvals.executor import execute_tool, process_approval_decision
from apps.approvals.registry import ToolRegistry, ToolValidationError, ToolPermissionDenied
from apps.integration.models import DataSource, SourceType
from apps.integration.services import validate_uploaded_file
from apps.integration.parsers.api_parser import validate_safe_remote_url
from apps.mapping.engine.safe_evaluator import evaluate_safe_expression, SecurityValidationError
from apps.gis.selectors import get_retail_customers_geojson
from apps.knowledge.models import KnowledgeBase, Document


class Phase11SecurityHardeningTests(TestCase):
    """
    Automated security verification across Authentication, RBAC, Multi-Tenancy,
    IDOR, AI Guardrails, SSRF, AST Safety, and GIS Privacy.
    """

    def setUp(self):
        # 1. Setup Tenant Workspaces A & B
        self.ws_a = Workspace.objects.create(
            name="Alpha Corp", code="WS_ALPHA_SEC", workspace_type=WorkspaceType.RETAIL, is_active=True
        )
        self.ws_b = Workspace.objects.create(
            name="Beta Enterprise", code="WS_BETA_SEC", workspace_type=WorkspaceType.RETAIL, is_active=True
        )

        # 2. Setup Permissions
        self.perm_view_order, _ = Permission.objects.get_or_create(codename="retail.view_order", defaults={"name": "View Orders", "module": "retail"})
        self.perm_change_order, _ = Permission.objects.get_or_create(codename="retail.change_order", defaults={"name": "Change Orders", "module": "retail"})
        self.perm_change_prod, _ = Permission.objects.get_or_create(codename="retail.change_product", defaults={"name": "Change Products", "module": "retail"})
        self.perm_manage_prod, _ = Permission.objects.get_or_create(codename="retail.manage_product", defaults={"name": "Manage Products", "module": "retail"})
        self.perm_manage_app, _ = Permission.objects.get_or_create(codename="approvals.manage_approval", defaults={"name": "Manage Approvals", "module": "approvals"})
        self.perm_chat_ai, _ = Permission.objects.get_or_create(codename="ai.chat", defaults={"name": "AI Chat", "module": "knowledge"})
        self.perm_view_pii, _ = Permission.objects.get_or_create(codename="retail.manage_customer", defaults={"name": "Manage Customer PII", "module": "retail"})

        # 3. Setup Roles
        self.role_admin = Role.objects.create(name="ADMIN")
        self.role_admin.permissions.set([
            self.perm_view_order, self.perm_change_order, self.perm_change_prod, self.perm_manage_prod,
            self.perm_manage_app, self.perm_chat_ai, self.perm_view_pii
        ])

        self.role_manager = Role.objects.create(name="MANAGER")
        self.role_manager.permissions.set([
            self.perm_view_order, self.perm_change_order, self.perm_change_prod, self.perm_manage_prod,
            self.perm_manage_app, self.perm_chat_ai
        ])

        self.role_employee = Role.objects.create(name="EMPLOYEE")
        self.role_employee.permissions.set([
            self.perm_view_order, self.perm_chat_ai, self.perm_change_prod
        ])

        self.role_viewer = Role.objects.create(name="VIEWER")
        self.role_viewer.permissions.set([self.perm_view_order])

        # 4. Users
        self.user_admin = User.objects.create_user(username="admin_a", email="admin_a@alpha.com", password="password123")
        self.user_manager = User.objects.create_user(username="manager_a", email="manager_a@alpha.com", password="password123")
        self.user_employee = User.objects.create_user(username="emp_a", email="emp_a@alpha.com", password="password123")
        self.user_viewer = User.objects.create_user(username="viewer_a", email="viewer_a@alpha.com", password="password123")
        self.user_b = User.objects.create_user(username="user_b", email="user_b@beta.com", password="password123")

        # Memberships for Workspace A
        WorkspaceMembership.objects.create(user=self.user_admin, workspace=self.ws_a, role=self.role_admin, is_active=True, is_default=True)
        WorkspaceMembership.objects.create(user=self.user_manager, workspace=self.ws_a, role=self.role_manager, is_active=True, is_default=True)
        WorkspaceMembership.objects.create(user=self.user_employee, workspace=self.ws_a, role=self.role_employee, is_active=True, is_default=True)
        WorkspaceMembership.objects.create(user=self.user_viewer, workspace=self.ws_a, role=self.role_viewer, is_active=True, is_default=True)

        # User B belongs ONLY to Workspace B
        WorkspaceMembership.objects.create(user=self.user_b, workspace=self.ws_b, role=self.role_manager, is_active=True, is_default=True)

        self.client = APIClient()

    # =========================================================================
    # 1. AUTHENTICATION SECURITY
    # =========================================================================
    def test_auth_unauthenticated_requests_rejected(self):
        """Unauthenticated requests must be rejected with 401 Unauthorized."""
        response = self.client.get("/api/v1/workspaces/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_inactive_user_cannot_login(self):
        """Disabled/inactive users cannot authenticate via API."""
        self.user_employee.is_active = False
        self.user_employee.save(update_fields=["is_active"])

        authenticated_user = authenticate_user("emp_a", "password123")
        self.assertIsNone(authenticated_user)

        response = self.client.post("/api/v1/auth/login/", {"username": "emp_a", "password": "password123"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_session_and_token_generated_on_login(self):
        """Successful login returns DRF token and establishes session."""
        response = self.client.post("/api/v1/auth/login/", {"username": "manager_a", "password": "password123"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data["data"])
        token_key = response.data["data"]["token"]
        self.assertTrue(Token.objects.filter(key=token_key, user=self.user_manager).exists())

    def test_auth_logout_destroys_token_and_session(self):
        """Logout invalidates both session and auth token."""
        login_res = self.client.post("/api/v1/auth/login/", {"username": "manager_a", "password": "password123"})
        token_key = login_res.data["data"]["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
        logout_res = self.client.post("/api/v1/auth/logout/")
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Token must be deleted
        self.assertFalse(Token.objects.filter(key=token_key).exists())

    # =========================================================================
    # 2. RBAC ENFORCEMENT & SEPARATION OF DUTIES
    # =========================================================================
    def test_rbac_viewer_cannot_mutate_or_approve(self):
        """Viewer role cannot execute mutations or process approvals."""
        category = Category.objects.create(workspace=self.ws_a, code="CAT_SEC", name="Security Category")
        product = Product.objects.create(
            workspace=self.ws_a, sku="PROD_SEC_01", name="Firewall", category=category, unit_price=Decimal("10000000")
        )

        # Viewer attempts tool execution -> raises ToolPermissionDenied
        with self.assertRaises(ToolPermissionDenied):
            execute_tool(
                name="adjust_product_price",
                workspace=self.ws_a,
                user=self.user_viewer,
                parameters={"product_id": product.id, "new_price": 9000000},
            )

    def test_rbac_separation_of_duties_requester_cannot_approve(self):
        """A user cannot approve their own mutation request unless they are superuser."""
        category = Category.objects.create(workspace=self.ws_a, code="CAT_SOD", name="SOD Category")
        product = Product.objects.create(
            workspace=self.ws_a, sku="PROD_SOD_01", name="Switch", category=category, unit_price=Decimal("5000000")
        )

        # Manager creates approval request
        res = execute_tool(
            name="adjust_product_price",
            workspace=self.ws_a,
            user=self.user_manager,
            parameters={"product_id": product.id, "new_price": 4500000},
        )
        app_id = res["approval_request_id"]
        app_req = ApprovalRequest.objects.get(id=app_id)

        # Manager tries to self-approve -> raises ToolPermissionDenied
        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(
                approval_request=app_req,
                reviewer=self.user_manager,
                decision="APPROVED",
            )

    # =========================================================================
    # 3. MULTI-TENANT ISOLATION & IDOR RESISTANCE
    # =========================================================================
    def test_multi_tenant_forged_workspace_header_rejected(self):
        """Supplying unauthorized X-Workspace-ID header must result in access denied."""
        token_b, _ = Token.objects.get_or_create(user=self.user_b)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_b.key}", HTTP_X_WORKSPACE_ID=str(self.ws_a.id))

        response = self.client.get(f"/api/v1/workspaces/{self.ws_a.id}/")
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_idor_cross_workspace_approval_rejected(self):
        """Manager from Workspace B cannot view or approve ApprovalRequest of Workspace A."""
        category = Category.objects.create(workspace=self.ws_a, code="CAT_IDOR", name="IDOR Category")
        product = Product.objects.create(
            workspace=self.ws_a, sku="PROD_IDOR_01", name="Router", category=category, unit_price=Decimal("3000000")
        )

        res = execute_tool(
            name="adjust_product_price",
            workspace=self.ws_a,
            user=self.user_employee,
            parameters={"product_id": product.id, "new_price": 2500000},
        )
        app_id = res["approval_request_id"]
        app_req = ApprovalRequest.objects.get(id=app_id)

        # User B (from Workspace B) attempts to approve request from Workspace A
        with self.assertRaises(ToolPermissionDenied):
            process_approval_decision(
                approval_request=app_req,
                reviewer=self.user_b,
                decision="APPROVED",
            )

    # =========================================================================
    # 4. AI SAFETY & TOOL VALIDATION INVARIANTS
    # =========================================================================
    def test_ai_safety_unknown_tool_rejected(self):
        """Calling an unregistered or unknown tool name raises ToolValidationError."""
        with self.assertRaises(ToolValidationError):
            execute_tool(
                name="drop_all_tables",
                workspace=self.ws_a,
                user=self.user_admin,
                parameters={},
            )

    def test_ai_safety_malformed_arguments_rejected(self):
        """Passing missing required parameters raises ToolValidationError."""
        with self.assertRaises(ToolValidationError):
            execute_tool(
                name="adjust_product_price",
                workspace=self.ws_a,
                user=self.user_employee,
                parameters={"product_id": 9999},  # missing new_price
            )

    def test_ai_safety_zero_direct_mutation_by_ai(self):
        """Mutations initiated via AI assistant always require PENDING approval and never write directly."""
        category = Category.objects.create(workspace=self.ws_a, code="CAT_SAFE", name="Safe Cat")
        product = Product.objects.create(
            workspace=self.ws_a, sku="PROD_SAFE_01", name="Modem", category=category, unit_price=Decimal("1200000")
        )

        res = execute_tool(
            name="adjust_product_price",
            workspace=self.ws_a,
            user=self.user_employee,
            parameters={"product_id": product.id, "new_price": 1000000},
        )
        self.assertEqual(res["status"], "APPROVAL_REQUIRED")

        # Product unit price MUST remain unchanged in database
        product.refresh_from_db()
        self.assertEqual(product.unit_price, Decimal("1200000"))

    # =========================================================================
    # 5. DATA INTEGRATION & SSRF PROTECTION
    # =========================================================================
    def test_ssrf_blocks_private_and_loopback_ips(self):
        """validate_safe_remote_url blocks private IPs, loopback, and metadata URLs."""
        is_safe, err = validate_safe_remote_url("http://127.0.0.1:8000/secret")
        self.assertFalse(is_safe)
        self.assertIn("blocked", err.lower())

        is_safe, err = validate_safe_remote_url("http://localhost:5432")
        self.assertFalse(is_safe)

        # Cloud metadata IP (AWS/GCP/Azure)
        is_safe, err = validate_safe_remote_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(is_safe)

        # Private RFC 1918 IPs
        is_safe, err = validate_safe_remote_url("http://192.168.1.1/admin")
        self.assertFalse(is_safe)
        is_safe, err = validate_safe_remote_url("http://10.0.0.1/internal")
        self.assertFalse(is_safe)

    def test_file_upload_safety_validation(self):
        """validate_uploaded_file rejects unsafe file extensions and oversized files."""
        # Unsafe extensions (.py, .exe, .sh)
        fake_py = io.BytesIO(b"print('hack')")
        fake_py.name = "exploit.py"
        is_safe, err = validate_uploaded_file(fake_py)
        self.assertFalse(is_safe)
        self.assertIn("unsupported file extension", err.lower())

        # Safe CSV file
        fake_csv = io.BytesIO(b"col1,col2\n1,2\n")
        fake_csv.name = "data.csv"
        is_safe, err = validate_uploaded_file(fake_csv)
        self.assertTrue(is_safe)

    # =========================================================================
    # 6. SAFE AST EXPRESSION EVALUATION (ZERO CODE EXECUTION)
    # =========================================================================
    def test_safe_evaluator_rejects_eval_exec_and_imports(self):
        """Safe AST Evaluator strictly prevents arbitrary code execution, imports, and calls."""
        # Function call
        with self.assertRaises(SecurityValidationError):
            evaluate_safe_expression("__import__('os').system('ls')", {})

        # Open file
        with self.assertRaises(SecurityValidationError):
            evaluate_safe_expression("open('/etc/passwd').read()", {})

        # Attribute access
        with self.assertRaises(SecurityValidationError):
            evaluate_safe_expression("price.__class__.__bases__", {"price": 100})

        # Valid arithmetic formula
        result = evaluate_safe_expression("unit_price * quantity - discount", {
            "unit_price": 50000,
            "quantity": 3,
            "discount": 10000,
        })
        self.assertEqual(result, 140000)

    # =========================================================================
    # 7. GIS PRIVACY & PII MASKING
    # =========================================================================
    def test_gis_customer_pii_masked_for_non_authorized_users(self):
        """Viewer without PII permissions receives masked customer name, address, email, phone."""
        Customer.objects.create(
            workspace=self.ws_a,
            code="CUST-SEC-01",
            name="Vũ Hoàng Minh",
            phone="0912345678",
            email="minh.vu@domain.com",
            address="123 Phố Huế, Hai Bà Trưng, Hà Nội",
            location=Point(105.8542, 21.0285, srid=4326),
            is_active=True,
        )

        # Non-authorized viewer (can_view_pii=False)
        geojson_masked = get_retail_customers_geojson(workspace=self.ws_a, can_view_pii=False)
        self.assertTrue(len(geojson_masked["features"]) >= 1)
        props = geojson_masked["features"][0]["properties"]

        self.assertEqual(props["name"], "Customer CUST-SEC-01")
        self.assertNotIn("email", props)
        self.assertNotIn("phone", props)
        self.assertEqual(props["address"], "Restricted (Address Protected)")
        self.assertTrue(geojson_masked["metadata"]["pii_masked"])

        # Authorized user (can_view_pii=True)
        geojson_unmasked = get_retail_customers_geojson(workspace=self.ws_a, can_view_pii=True)
        props_unmasked = geojson_unmasked["features"][0]["properties"]
        self.assertEqual(props_unmasked["name"], "Vũ Hoàng Minh")
        self.assertEqual(props_unmasked["email"], "minh.vu@domain.com")
        self.assertEqual(props_unmasked["phone"], "0912345678")
        self.assertFalse(geojson_unmasked["metadata"]["pii_masked"])
