"""
Management command to idempotently seed student administrator accounts:
minhtien147896325@gmail.com and 1250080194@sv.hcmunre.edu.vn.
Grants full superuser, staff, and ADMIN workspace memberships across all workspaces.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership


class Command(BaseCommand):
    help = "Seeds student administrator accounts with full superuser and workspace ADMIN roles."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("==> Ensuring Student Administrator Accounts...")

        admin_role = Role.objects.filter(name="ADMIN").first()
        if not admin_role:
            self.stdout.write(self.style.WARNING("Role 'ADMIN' does not exist yet. Please run seed_demo first."))

        workspaces = list(Workspace.objects.all())

        student_accounts = [
            {
                "username": "minhtien",
                "email": "minhtien147896325@gmail.com",
                "first_name": "Minh",
                "last_name": "Tiến",
                "password": "AdminPass123!",
            },
            {
                "username": "1250080194",
                "email": "1250080194@sv.hcmunre.edu.vn",
                "first_name": "Sinh",
                "last_name": "Viên",
                "password": "AdminPass123!",
            },
        ]

        for acc in student_accounts:
            user = User.objects.filter(email=acc["email"]).first()
            if not user:
                user = User.objects.filter(username=acc["username"]).first()

            if user:
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.first_name = acc["first_name"]
                user.last_name = acc["last_name"]
                user.save()
            else:
                user = User.objects.create_user(
                    username=acc["username"],
                    email=acc["email"],
                    password=acc["password"],
                    first_name=acc["first_name"],
                    last_name=acc["last_name"],
                    is_staff=True,
                    is_superuser=True,
                    is_active=True,
                )

            # Ensure password is set if needed
            user.set_password(acc["password"])
            user.save()

            Token.objects.get_or_create(user=user)

            # Ensure memberships in all workspaces with ADMIN role
            if admin_role:
                for idx, ws in enumerate(workspaces):
                    WorkspaceMembership.objects.update_or_create(
                        user=user,
                        workspace=ws,
                        defaults={
                            "role": admin_role,
                            "is_default": (idx == 0),
                            "is_active": True,
                        },
                    )

            self.stdout.write(
                self.style.SUCCESS(
                    f"    [OK] Student Admin: {user.email} (Username: {user.username}) - Superuser & ADMIN"
                )
            )

        self.stdout.write(self.style.SUCCESS("==> Student Administrator Accounts successfully verified."))
