"""
Automated tests for Customer model, segments, and API operations.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer, CustomerSegment
from apps.retail.services import create_customer


class RetailCustomerTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.workspace1 = Workspace.objects.create(
            name="Retail WS 1",
            code="retail-1",
            workspace_type=WorkspaceType.RETAIL,
        )

        self.perm_view = Permission.objects.create(codename="retail.view_customer", name="View", module="retail")
        self.perm_manage = Permission.objects.create(codename="retail.manage_customer", name="Manage", module="retail")

        self.admin_role = Role.objects.create(name="ADMIN")
        self.admin_role.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(
            username="cust_admin",
            email="cust_admin@example.com",
            password="Password123!",
        )
        WorkspaceMembership.objects.create(
            user=self.user,
            workspace=self.workspace1,
            role=self.admin_role,
            is_default=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_customer_with_segment(self):
        cust = create_customer(
            workspace=self.workspace1,
            user=self.user,
            data={
                "code": "CUST-VIP-01",
                "name": "Nguyen Van A",
                "email": "vip_a@example.com",
                "phone": "0901234567",
                "customer_segment": CustomerSegment.VIP,
            },
        )
        self.assertEqual(cust.code, "CUST-VIP-01")
        self.assertEqual(cust.customer_segment, CustomerSegment.VIP)
        self.assertEqual(cust.workspace, self.workspace1)

    def test_customer_api_list_and_filter(self):
        create_customer(
            workspace=self.workspace1,
            user=self.user,
            data={"code": "CUST-01", "name": "Alice", "customer_segment": "STANDARD"},
        )
        create_customer(
            workspace=self.workspace1,
            user=self.user,
            data={"code": "CUST-02", "name": "Bob VIP", "customer_segment": "VIP"},
        )

        url = reverse("retail_api_customers")
        # Filter by VIP segment
        response = self.client.get(url, {"customer_segment": "VIP"}, HTTP_X_WORKSPACE_ID=str(self.workspace1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["data"][0]["code"], "CUST-02")
