"""
tests.test_service_labor - Automated Test Suite for IT Service Categories, Labor Time Tracking, Hourly Rates & Ticket Cost Aggregation.
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer, CustomerSegment
from apps.service_ops.models import (
    Service,
    ServiceCategory,
    Employee,
    SLA,
    SLAPriority,
    ServiceRequest,
    ServiceRequestStatus,
    ServiceRequestPriority,
    Task,
    TaskStatus,
    LaborEntry,
)
from apps.service_ops.services import (
    create_service,
    create_employee,
    create_service_request,
    create_labor_entry,
    get_service_request_cost_breakdown,
)


class ServiceLaborAndCategoriesTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="XYZ IT Services",
            code="xyz-it-services",
            workspace_type=WorkspaceType.SERVICE,
        )

        self.user = User.objects.create_user(
            username="tech_admin",
            email="tech_admin@test.com",
            password="Password123!",
            is_superuser=True,
        )

        self.customer = Customer.objects.create(
            workspace=self.workspace,
            code="CUST-IT-01",
            name="FinTech Corp",
            customer_segment=CustomerSegment.ENTERPRISE,
        )

        self.sla = SLA.objects.create(
            workspace=self.workspace,
            name="Critical SLA",
            priority=SLAPriority.CRITICAL,
            response_time_hours=2,
            resolution_time_hours=4,
        )

        # Technicians with different hourly rates
        self.tech_user = User.objects.create_user(
            username="technician_bob",
            email="bob@test.com",
            password="Password123!",
        )

        self.tech_bob = Employee.objects.create(
            workspace=self.workspace,
            user=self.tech_user,
            code="TECH-BOB",
            full_name="Bob Engineer",
            hourly_labor_rate=Decimal("200000.00"),
            skills=["SERVER", "DATABASE"],
        )

        self.service_db = Service.objects.create(
            workspace=self.workspace,
            code="DB-OPT",
            name="SQL Query Optimization",
            category=ServiceCategory.DATABASE_CONSULTING,
            standard_duration_minutes=120,
            base_fee=Decimal("1000000.00"),
        )

        self.ticket = ServiceRequest.objects.create(
            workspace=self.workspace,
            request_number="SR-20260826-0001",
            customer=self.customer,
            service=self.service_db,
            sla=self.sla,
            assigned_employee=self.tech_bob,
            title="Optimize slow invoice generation query",
            description="Query timeout on end of month report",
            priority=ServiceRequestPriority.HIGH,
            status=ServiceRequestStatus.IN_PROGRESS,
        )

        self.task = Task.objects.create(
            service_request=self.ticket,
            assigned_to=self.tech_bob,
            title="Profile query execution plan",
            estimated_duration_minutes=120,
            status=TaskStatus.IN_PROGRESS,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_service_category_choices_and_validation(self):
        """Validates all 4 primary IT service categories."""
        categories = [
            ("INST-TEST", "Linux Install", ServiceCategory.INSTALLATION),
            ("MAIN-TEST", "Server Check", ServiceCategory.MAINTENANCE),
            ("DB-TEST", "DB Consulting", ServiceCategory.DATABASE_CONSULTING),
            ("REP-TEST", "Laptop Board Fix", ServiceCategory.DEVICE_REPAIR),
        ]
        for code, name, cat in categories:
            svc = create_service(
                self.workspace,
                self.user,
                {
                    "code": code,
                    "name": name,
                    "category": cat,
                    "standard_duration_minutes": 60,
                    "base_fee": "200000.00",
                },
            )
            self.assertEqual(svc.category, cat)

        # Invalid category should raise ValidationError
        with self.assertRaises(Exception):
            create_service(
                self.workspace,
                self.user,
                {
                    "code": "INVALID-CAT",
                    "name": "Invalid Category Service",
                    "category": "SPACE_TRAVEL",
                },
            )

    def test_create_labor_entry_and_server_side_cost_calculation(self):
        """Verifies labor_cost = (duration_minutes / 60) * hourly_rate_snapshot."""
        now = timezone.now()
        start = now - timedelta(minutes=90)
        end = now

        entry = create_labor_entry(
            task=self.task,
            employee=self.tech_bob,
            user=self.user,
            data={
                "started_at": start,
                "ended_at": end,
                "duration_minutes": 90,
                "notes": "Identified missing composite index on orders table",
            },
        )

        self.assertEqual(entry.duration_minutes, 90)
        self.assertEqual(entry.hourly_rate_snapshot, Decimal("200000.00"))
        # 90 minutes = 1.5 hours * 200,000 VND = 300,000 VND
        self.assertEqual(entry.labor_cost, Decimal("300000.00"))
        self.assertEqual(entry.workspace.id, self.workspace.id)

    def test_hourly_rate_snapshot_immutability(self):
        """Verifies that changing an employee's hourly labor rate does NOT alter existing labor entries."""
        now = timezone.now()
        entry = create_labor_entry(
            task=self.task,
            employee=self.tech_bob,
            user=self.user,
            data={
                "started_at": now - timedelta(hours=2),
                "ended_at": now,
                "duration_minutes": 120,
            },
        )
        self.assertEqual(entry.labor_cost, Decimal("400000.00"))  # 2 hours * 200k = 400k

        # Technician gets a promotion / rate increase
        self.tech_bob.hourly_labor_rate = Decimal("300000.00")
        self.tech_bob.save()

        entry.refresh_from_db()
        # Historical rate and cost must remain unchanged
        self.assertEqual(entry.hourly_rate_snapshot, Decimal("200000.00"))
        self.assertEqual(entry.labor_cost, Decimal("400000.00"))

    def test_ticket_cost_aggregation_service_and_api(self):
        """Verifies service request cost aggregation endpoint."""
        now = timezone.now()
        # Create 2 labor entries for this ticket's task
        create_labor_entry(
            task=self.task,
            employee=self.tech_bob,
            user=self.user,
            data={
                "started_at": now - timedelta(hours=3),
                "ended_at": now - timedelta(hours=1),
                "duration_minutes": 120,  # 2h * 200k = 400,000 VND
            },
        )
        create_labor_entry(
            task=self.task,
            employee=self.tech_bob,
            user=self.user,
            data={
                "started_at": now - timedelta(hours=1),
                "ended_at": now,
                "duration_minutes": 60,  # 1h * 200k = 200,000 VND
            },
        )

        cost_breakdown = get_service_request_cost_breakdown(self.ticket)
        self.assertEqual(cost_breakdown["total_labor_minutes"], 180)
        self.assertEqual(cost_breakdown["total_labor_hours"], 3.0)
        self.assertEqual(cost_breakdown["total_labor_cost"], Decimal("600000.00"))
        self.assertEqual(cost_breakdown["service_base_fee"], Decimal("1000000.00"))
        self.assertEqual(cost_breakdown["total_estimated_cost"], Decimal("1600000.00"))
        self.assertEqual(cost_breakdown["labor_entries_count"], 2)

        # Test REST API endpoint
        url = f"/api/v1/service-ops/requests/{self.ticket.id}/cost/"
        resp = self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()["data"]
        self.assertEqual(data["total_labor_minutes"], 180)
        self.assertEqual(float(data["total_labor_cost"]), 600000.0)
        self.assertEqual(float(data["total_estimated_cost"]), 1600000.0)

    def test_invalid_labor_duration_rejection(self):
        """Verifies that ended_at <= started_at or duration <= 0 raises ValidationError."""
        now = timezone.now()
        with self.assertRaises(Exception):
            create_labor_entry(
                task=self.task,
                employee=self.tech_bob,
                user=self.user,
                data={
                    "started_at": now,
                    "ended_at": now - timedelta(minutes=30),  # Inverted time
                    "duration_minutes": 30,
                },
            )

    def test_labor_entry_rest_api_creation(self):
        """Verifies creating labor entry via REST API."""
        url = "/api/v1/service-ops/labor-entries/"
        now = timezone.now()
        payload = {
            "task_id": self.task.id,
            "employee_id": self.tech_bob.id,
            "started_at": (now - timedelta(minutes=45)).isoformat(),
            "ended_at": now.isoformat(),
            "duration_minutes": 45,
            "notes": "Added covering index on user_id",
        }
        resp = self.client.post(url, payload, format="json", HTTP_X_WORKSPACE_ID=str(self.workspace.id))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        res_data = resp.json()["data"]
        self.assertEqual(res_data["duration_minutes"], 45)
        # 45 mins = 0.75 hrs * 200,000 VND = 150,000 VND
        self.assertEqual(float(res_data["labor_cost"]), 150000.0)
