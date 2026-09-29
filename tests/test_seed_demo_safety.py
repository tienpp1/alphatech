"""Safety tests use the isolated Django test database, never business data."""
from io import StringIO
from unittest.mock import patch
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from rest_framework.authtoken.models import Token
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace
from apps.retail.models import Product


@override_settings(DEBUG=True)
class SeedDemoSafetyTests(TestCase):
    def seed(self, **options):
        return call_command("seed_demo", stdout=StringIO(), **options)

    def test_requires_explicit_confirmation(self):
        with self.assertRaisesMessage(CommandError, "--confirm-empty-demo"):
            self.seed(identity_only=True)
        self.assertFalse(User.objects.exists())
        self.assertFalse(Role.objects.exists())

    @override_settings(DEBUG=False)
    def test_production_denied(self):
        with self.assertRaisesMessage(CommandError, "production seeding is forbidden"):
            self.seed(confirm_empty_demo=True)
        self.assertFalse(Workspace.objects.exists())

    def test_remote_database_denied_without_connecting_to_it(self):
        with patch("apps.accounts.management.commands.seed_demo.settings") as config:
            config.DEBUG = True
            config.DATABASES = {"default": {"HOST": "remote.example.com"}}
            with self.assertRaisesMessage(CommandError, "remote hosts are forbidden"):
                self.seed(confirm_empty_demo=True)
        self.assertFalse(User.objects.exists())

    def test_existing_account_password_and_flags_unchanged(self):
        user = User.objects.create_user(username="admin", email="admin@example.com", password="private-test")
        original = user.password
        with self.assertRaisesMessage(CommandError, "already contains"):
            self.seed(confirm_empty_demo=True)
        user.refresh_from_db()
        self.assertEqual(user.password, original)
        self.assertFalse(user.is_superuser)
        self.assertFalse(Workspace.objects.exists())

    def test_existing_workspace_denied(self):
        workspace = Workspace.objects.create(name="Existing", code="existing", workspace_type="RETAIL")
        with self.assertRaisesMessage(CommandError, "already contains"):
            self.seed(confirm_empty_demo=True)
        self.assertTrue(Workspace.objects.filter(pk=workspace.pk).exists())
        self.assertFalse(User.objects.exists())

    def test_existing_role_denied(self):
        Role.objects.create(name="CUSTOM")
        with self.assertRaisesMessage(CommandError, "already contains"):
            self.seed(confirm_empty_demo=True)
        self.assertFalse(User.objects.exists())

    def test_identity_only_and_no_credentials_in_output(self):
        output = StringIO()
        call_command("seed_demo", confirm_empty_demo=True, identity_only=True, stdout=output)
        self.assertEqual(User.objects.count(), 4)
        self.assertEqual(Workspace.objects.count(), 2)
        self.assertFalse(Product.objects.exists())
        for token in Token.objects.all():
            self.assertNotIn(token.key, output.getvalue())
        for password in ("AdminPass123!", "ManagerPass123!", "EmployeePass123!", "ViewerPass123!"):
            self.assertNotIn(password, output.getvalue())
        with self.assertRaisesMessage(CommandError, "already contains"):
            self.seed(confirm_empty_demo=True, identity_only=True)
