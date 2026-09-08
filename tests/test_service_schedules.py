"""
Automated tests for Schedule model, time range validation, and schedule overlap rejection.
"""

from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership, WorkspaceType
from apps.retail.models import Customer
from apps.service_ops.models import Service, Employee, ServiceRequest, Task, Schedule, ScheduleStatus
from apps.service_ops.services import create_schedule


class ServiceScheduleTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(
            name="Service WS",
            code="svc-ws",
            workspace_type=WorkspaceType.SERVICE,
        )
        self.user = User.objects.create_user(
            username="sch_tester",
            email="sch_tester@example.com",
            password="Password123!",
        )

        self.customer = Customer.objects.create(workspace=self.workspace, code="CUST-01", name="Alpha Building")
        self.service = Service.objects.create(workspace=self.workspace, code="HVAC-01", name="HVAC Maintenance")
        self.tech = Employee.objects.create(workspace=self.workspace, code="TECH-01", full_name="Bao Pham", phone="0901222333")
        self.req = ServiceRequest.objects.create(
            workspace=self.workspace,
            request_number="SR-TEST-SCH",
            customer=self.customer,
            service=self.service,
            title="Chiller inspection",
            description="Inspect chiller",
        )
        self.task1 = Task.objects.create(service_request=self.req, assigned_to=self.tech, title="Task 1")
        self.task2 = Task.objects.create(service_request=self.req, assigned_to=self.tech, title="Task 2")

    def test_schedule_end_time_before_start_time_rejected(self):
        now = timezone.now()
        with self.assertRaises(ValidationError):
            create_schedule(
                self.task1,
                self.tech,
                self.user,
                {
                    "start_time": now + timedelta(hours=2),
                    "end_time": now + timedelta(hours=1),  # Invalid end before start
                },
            )

    def test_schedule_overlap_for_same_employee_rejected(self):
        now = timezone.now()
        # Schedule 1: 10:00 -> 12:00
        start1 = now + timedelta(hours=2)
        end1 = now + timedelta(hours=4)
        create_schedule(
            self.task1,
            self.tech,
            self.user,
            {"start_time": start1, "end_time": end1, "notes": "First slot"},
        )

        # Schedule 2: 11:00 -> 13:00 (Overlaps 10:00-12:00) -> MUST be rejected
        start2 = now + timedelta(hours=3)
        end2 = now + timedelta(hours=5)
        with self.assertRaises(ValidationError):
            create_schedule(
                self.task2,
                self.tech,
                self.user,
                {"start_time": start2, "end_time": end2, "notes": "Overlapping slot"},
            )
