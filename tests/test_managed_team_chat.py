"""Manager provisioning and invitations never expand the public/internal boundary."""
from importlib.util import find_spec
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import Client, RequestFactory, TestCase, TransactionTestCase, override_settings
from django.views.debug import SafeExceptionReporterFilter
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import translation
from django.conf import settings

from apps.accounts.models import Permission, Role, User
from apps.public_web.models import SocialIdentity
from apps.audit.models import AuditLog
from apps.notifications.chat_service import (
    get_recent_team_messages, get_workspace_colleagues, send_team_message, verify_chat_access,
)
from apps.notifications.models import TeamChatMessage
from apps.workspaces.models import Workspace, WorkspaceMembership


class ManagedTeamChatTests(TestCase):
    create_url = '/noibo/trao-doi/nhan-vien/tao/'
    add_url = '/noibo/trao-doi/thanh-vien/them/'

    def setUp(self):
        self.ws = Workspace.objects.create(name='Managed A', code='managed-a', workspace_type='RETAIL')
        self.other = Workspace.objects.create(name='Managed B', code='managed-b', workspace_type='SERVICE')
        self.roles = {name: Role.objects.get_or_create(name=name)[0]
                      for name in ('ADMIN', 'MANAGER', 'EMPLOYEE', 'VIEWER', 'CUSTOM')}
        self.manager, self.manager_member = self.member('manager', 'MANAGER')
        self.employee, self.employee_member = self.member('pending', 'EMPLOYEE')
        self.client.force_login(self.manager)
        self.payload = dict(workspace_id=str(self.ws.pk), full_name='Nguyễn Minh An',
                            email='new-worker@example.test', username='new-worker',
                            password1='A-new-strong-secret-724!', password2='A-new-strong-secret-724!')

    def member(self, name, role, workspace=None, **flags):
        user = User.objects.create_user(username=name, email=f'{name}@example.test', **flags)
        member = WorkspaceMembership.objects.create(user=user, workspace=workspace or self.ws,
                                                   role=self.roles[role], is_active=True)
        return user, member

    def services(self):
        self.assertIsNotNone(find_spec('apps.notifications.chat_members'),
                             'Scoped employee provisioning services must exist')
        from apps.notifications import chat_members
        return chat_members

    def enable(self, member):
        self.assertIn('team_chat_enabled', [f.name for f in WorkspaceMembership._meta.fields])
        WorkspaceMembership.objects.filter(pk=member.pk).update(team_chat_enabled=True)
        member.refresh_from_db()

    def test_new_employee_is_denied_until_explicit_invitation(self):
        self.assertFalse(verify_chat_access(self.employee, self.ws))
        with self.assertRaises(PermissionDenied):
            send_team_message(self.ws, self.employee, 'not invited')
        with self.assertRaises(PermissionDenied):
            get_recent_team_messages(self.ws, self.employee)
        self.enable(self.employee_member)
        self.assertTrue(verify_chat_access(self.employee, self.ws))

    def test_admin_superuser_viewer_custom_and_google_are_not_chat_members(self):
        for name, role, flags in [('admin', 'ADMIN', {}), ('super', 'MANAGER', {'is_superuser': True}),
                                  ('viewer', 'VIEWER', {}), ('custom', 'CUSTOM', {}),
                                  ('inactive', 'EMPLOYEE', {'is_active': False})]:
            user, member = self.member(name, role, **flags)
            with self.subTest(name=name):
                self.assertFalse(verify_chat_access(user, self.ws))
                self.client.force_login(user)
                # Django does not restore an inactive identity from a session;
                # its ordinary login redirect is also a fail-closed denial.
                expected = 403 if user.is_active else 302
                self.assertEqual(self.client.get('/noibo/trao-doi/', {'workspace_id': self.ws.pk}).status_code, expected)
                self.assertEqual(self.client.get('/api/v1/notifications/chat/messages/', {'workspace_id': self.ws.pk}).status_code, expected)
        SocialIdentity.objects.create(user=self.manager, provider='GOOGLE', subject='managed-google',
                                      provider_email='manager@example.test')
        self.assertFalse(verify_chat_access(self.manager, self.ws))

    def test_roster_excludes_pending_admin_and_superuser_even_with_manager_role(self):
        self.member('admin', 'ADMIN')
        self.member('super', 'MANAGER', is_superuser=True)
        invited, membership = self.member('invited', 'EMPLOYEE')
        self.enable(membership)
        self.assertEqual({row['user_id'] for row in get_workspace_colleagues(self.ws, self.manager)},
                         {self.manager.pk, invited.pk})

    def test_direct_history_without_actor_fails_closed(self):
        TeamChatMessage.objects.create(workspace=self.ws, sender=self.manager, message='private')
        with self.assertRaises(PermissionDenied):
            get_recent_team_messages(self.ws)
        with self.assertRaises(PermissionDenied):
            get_workspace_colleagues(self.ws)

    def test_pending_and_revoked_employee_denied_on_html_api_history_and_send(self):
        self.client.force_login(self.employee)
        for invited in (False, True, False):
            if invited:
                self.enable(self.employee_member)
            elif 'team_chat_enabled' in [f.name for f in WorkspaceMembership._meta.fields]:
                WorkspaceMembership.objects.filter(pk=self.employee_member.pk).update(team_chat_enabled=False)
            expected = 200 if invited else 403
            for path, extra in [('/noibo/trao-doi/', {}),
                                ('/api/v1/notifications/chat/messages/', {'since_id': 0}),
                                ('/api/v1/notifications/chat/messages/', {'before_id': 999999})]:
                self.assertEqual(self.client.get(path, {'workspace_id': self.ws.pk, **extra}).status_code, expected)
            sent = self.client.post('/api/v1/notifications/chat/send/', {'workspace_id': self.ws.pk, 'message': 'hello'})
            self.assertEqual(sent.status_code, 201 if invited else 403)
            fallback = self.client.post('/noibo/trao-doi/?workspace_id=' + str(self.ws.pk), {'message': 'fallback'})
            self.assertEqual(fallback.status_code, 302 if invited else 403)

    def test_manager_creates_fixed_employee_without_enabling_chat_or_broad_permissions(self):
        broad = Permission.objects.get_or_create(codename='accounts.manage_user', defaults={'name': 'Manage', 'module': 'accounts'})[0]
        response = self.client.post(self.create_url, {**self.payload, 'role': 'ADMIN', 'is_staff': '1', 'is_superuser': '1', 'team_chat_enabled': '1'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/noibo/trao-doi/?workspace_id=' + str(self.ws.pk))
        created = User.objects.get(username='new-worker')
        member = WorkspaceMembership.objects.get(user=created)
        self.assertEqual(created.get_full_name(), 'Nguyễn Minh An')
        self.assertTrue(created.check_password(self.payload['password1']))
        self.assertTrue(created.is_active and member.is_active)
        self.assertFalse(created.is_staff or created.is_superuser or member.team_chat_enabled)
        self.assertEqual(member.workspace_id, self.ws.pk)
        self.assertEqual(member.role.name, 'EMPLOYEE')
        self.assertFalse(created.user_permissions.exists() or created.groups.exists())
        self.assertFalse(self.roles['MANAGER'].permissions.filter(pk=broad.pk).exists())
        audit = AuditLog.objects.get(action='CHAT_EMPLOYEE_CREATED')
        self.assertEqual(audit.workspace_id, self.ws.pk)
        self.assertEqual(audit.actor_user_id, self.manager.pk)
        self.assertEqual(audit.changes, {'user_id': created.pk, 'role': 'EMPLOYEE', 'team_chat_enabled': False})
        self.assertNotIn(self.payload['password1'], str(audit.changes))
        self.assertNotIn(self.payload['email'], str(audit.changes))

    def test_creation_is_atomic_with_audit(self):
        services = self.services()
        with patch('apps.notifications.chat_members.log_action', side_effect=RuntimeError('audit failure')):
            with self.assertRaises(RuntimeError):
                services.create_chat_employee(workspace=self.ws, actor=self.manager,
                                              **{k: v for k, v in self.payload.items() if k != 'workspace_id'})
        self.assertFalse(User.objects.filter(username='new-worker').exists())
        self.assertEqual(WorkspaceMembership.objects.count(), 2)

    def test_existing_customer_email_and_username_are_never_promoted_or_reset(self):
        customer = User.objects.create_user(username='customer-existing', email='customer@example.test', password='unchanged-secret')
        for collision in ({'email': 'CUSTOMER@example.test'}, {'username': 'CUSTOMER-EXISTING'}):
            self.assertEqual(self.client.post(self.create_url, {**self.payload, **collision}).status_code, 400)
        customer.refresh_from_db()
        self.assertTrue(customer.check_password('unchanged-secret'))
        self.assertFalse(customer.workspace_memberships.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_form_validation_rejects_bad_lengths_passwords_and_preserves_nonsecret_fields(self):
        changes = [{'full_name': 'x' * 151}, {'username': 'x' * 151}, {'email': 'x' * 255 + '@example.test'},
                   {'username': 'invalid username'}, {'password2': 'different'},
                   {'password1': '123', 'password2': '123'}, {'email': 'invalid'}]
        for change in changes:
            with self.subTest(change=next(iter(change))):
                response = self.client.post(self.create_url, {**self.payload, **change})
                self.assertEqual(response.status_code, 400)
                self.assertTrue(response.context['employee_form'].errors)
                self.assertEqual(response.context['chat_management_panel'], 'create')
                self.assertEqual(response.context['employee_form']['username'].value(), change.get('username', 'new-worker'))
                self.assertNotIn(self.payload['password1'].encode(), response.content)
        self.assertFalse(User.objects.filter(username='new-worker').exists())

    def assert_management_error_in_vietnamese(self, path, payload, vietnamese, english):
        with translation.override('en-us'):
            response = self.client.post(path, payload)
            self.assertContains(response, vietnamese, status_code=400)
            self.assertNotContains(response, english, status_code=400)
            # A local management translation must not leak into other requests
            # or replace the application's existing global English locale.
            self.assertEqual(translation.get_language(), 'en-us')
            self.assertEqual(translation.gettext('This field is required.'), 'This field is required.')
            self.assertEqual(settings.LANGUAGE_CODE, 'en-us')

    def test_empty_employee_form_renders_vietnamese_required_errors_only_locally(self):
        self.assert_management_error_in_vietnamese(
            self.create_url, {'workspace_id': self.ws.pk},
            'Trường này là bắt buộc.', 'This field is required.')

    def test_invalid_employee_email_renders_vietnamese_validation_only_locally(self):
        self.assert_management_error_in_vietnamese(
            self.create_url, {**self.payload, 'email': 'invalid-email'},
            'Nhập một địa chỉ email hợp lệ.', 'Enter a valid email address.')

    def test_weak_employee_password_renders_vietnamese_validation_only_locally(self):
        self.assert_management_error_in_vietnamese(
            self.create_url, {**self.payload, 'password1': '123', 'password2': '123'},
            'Mật khẩu quá ngắn.', 'This password is too short.')

    def test_empty_invitation_renders_vietnamese_required_error_only_locally(self):
        self.assert_management_error_in_vietnamese(
            self.add_url, {'workspace_id': self.ws.pk},
            'Trường này là bắt buộc.', 'This field is required.')

    def test_username_length_is_checked_after_unicode_normalization(self):
        form = self.services().CreateEmployeeForm({**self.payload, 'username': '\ufb00' * 76})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)

    @override_settings(DEBUG=False)
    def test_creation_exception_report_redacts_password_and_identity_post_fields(self):
        from apps.notifications.chat_member_views import chat_employee_create_view
        request = RequestFactory().post(self.create_url, self.payload)
        request.user = self.manager
        with patch('apps.notifications.chat_member_views.create_chat_employee', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                chat_employee_create_view(request)
        filtered = SafeExceptionReporterFilter().get_post_parameters(request)
        for field in ('password1', 'password2', 'email', 'full_name', 'username'):
            self.assertEqual(filtered[field], '********************')

    def test_integrity_collision_is_a_clean_validation_error_and_no_partial_account(self):
        self.services()
        with patch('apps.notifications.chat_members.User.save', side_effect=IntegrityError('private database detail')):
            response = self.client.post(self.create_url, self.payload)
        self.assertEqual(response.status_code, 400)
        self.assertNotContains(response, 'private database detail', status_code=400)
        self.assertFalse(User.objects.filter(username='new-worker').exists())

    def test_invitation_is_scoped_idempotent_and_audited_only_on_transition(self):
        for _ in range(2):
            response = self.client.post(self.add_url, {'workspace_id': self.ws.pk, 'membership': self.employee_member.pk})
            self.assertEqual(response.status_code, 302)
        self.employee_member.refresh_from_db()
        self.assertTrue(self.employee_member.team_chat_enabled)
        self.assertEqual(AuditLog.objects.filter(action='CHAT_EMPLOYEE_INVITED').count(), 1)
        self.assertTrue(verify_chat_access(self.employee, self.ws))

    def test_invitation_choices_are_only_pending_eligible_same_workspace_employees(self):
        services = self.services()
        for name, role, flags in [('admin', 'ADMIN', {}), ('super', 'EMPLOYEE', {'is_superuser': True}),
                                 ('inactive', 'EMPLOYEE', {'is_active': False}), ('viewer', 'VIEWER', {})]:
            self.member(name, role, **flags)
        linked, _ = self.member('linked', 'EMPLOYEE')
        SocialIdentity.objects.create(user=linked, provider='GOOGLE', subject='linked', provider_email=linked.email)
        self.member('foreign', 'EMPLOYEE', workspace=self.other)
        _, invited = self.member('invited', 'EMPLOYEE')
        self.enable(invited)
        form = services.AddEmployeeForm(self.manager, self.ws)
        self.assertEqual(list(form.fields['membership'].queryset.values_list('pk', flat=True)), [self.employee_member.pk])

    def test_invitation_choice_shows_name_and_username_without_internal_model_repr(self):
        self.employee.first_name = 'Nhân viên thử'
        self.employee.save(update_fields=['first_name'])
        form = self.services().AddEmployeeForm(self.manager, self.ws)
        label = form.fields['membership'].label_from_instance(form.fields['membership'].queryset.get())
        self.assertEqual(label, 'Nhân viên thử (pending)')

    def test_forged_invitation_and_foreign_workspace_selectors_never_write(self):
        _, foreign = self.member('foreign', 'EMPLOYEE', workspace=self.other)
        _, admin = self.member('admin', 'ADMIN')
        for member in (foreign, admin):
            self.assertEqual(self.client.post(self.add_url, {'workspace_id': self.ws.pk, 'membership': member.pk}).status_code, 400)
        for selector in (str(self.other.pk), '', 'invalid'):
            self.assertEqual(self.client.post(self.create_url, {**self.payload, 'workspace_id': selector}).status_code, 403)
        self.assertEqual(self.client.post(self.create_url, self.payload, HTTP_X_WORKSPACE_ID=str(self.other.pk)).status_code, 403)
        self.assertFalse(User.objects.filter(username='new-worker').exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_nonmanagers_cannot_provision_or_invite_even_with_forged_post(self):
        admin, _ = self.member('admin', 'ADMIN')
        superuser, _ = self.member('super', 'MANAGER', is_superuser=True)
        public = User.objects.create_user(username='public', email='public@example.test')
        for user in (self.employee, admin, superuser, public):
            self.client.force_login(user)
            self.assertEqual(self.client.post(self.create_url, self.payload).status_code, 403)
            self.assertEqual(self.client.post(self.add_url, {'workspace_id': self.ws.pk, 'membership': self.employee_member.pk}).status_code, 403)
        self.assertFalse(User.objects.filter(username='new-worker').exists())

    def test_direct_services_recheck_revoked_manager_and_membership_eligibility(self):
        services = self.services()
        self.manager_member.is_active = False
        self.manager_member.save()
        with self.assertRaises(PermissionDenied):
            services.invite_chat_employee(workspace=self.ws, actor=self.manager, membership_id=self.employee_member.pk)
        with self.assertRaises(PermissionDenied):
            services.create_chat_employee(workspace=self.ws, actor=self.manager,
                                          **{k: v for k, v in self.payload.items() if k != 'workspace_id'})
        self.assertFalse(AuditLog.objects.exists())

    def test_manager_actions_require_post_and_csrf(self):
        for path in (self.create_url, self.add_url):
            self.assertEqual(self.client.get(path).status_code, 405)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.manager)
        self.assertEqual(csrf_client.post(self.create_url, self.payload).status_code, 403)

    def test_navigation_context_and_employee_page_never_expose_account_directory(self):
        self.enable(self.employee_member)
        self.client.force_login(self.employee)
        page = self.client.get('/noibo/trao-doi/', {'workspace_id': self.ws.pk})
        self.assertEqual(page.status_code, 200)
        self.assertTrue(page.context['can_use_team_chat'])
        self.assertFalse(page.context['can_manage_chat'])
        self.assertIsNone(page.context['employee_form'])
        self.assertIsNone(page.context['add_employee_form'])
        WorkspaceMembership.objects.filter(pk=self.employee_member.pk).update(team_chat_enabled=False)
        page = self.client.get('/noibo/')
        self.assertFalse(page.context['can_use_team_chat'])


class ManagedChatMigrationTests(TransactionTestCase):
    def test_legacy_code_can_insert_after_migration_with_fail_closed_database_default(self):
        old_apps = MigrationExecutor(connection).loader.project_state([('workspaces', '0001_initial')]).apps
        old_member = old_apps.get_model('workspaces', 'WorkspaceMembership')
        user = User.objects.create_user(username='rolling-release', email='rolling@example.test')
        role = Role.objects.create(name='EMPLOYEE')
        workspace = Workspace.objects.create(name='Rolling', code='rolling-chat', workspace_type='RETAIL')
        try:
            member = old_member.objects.create(user_id=user.pk, role_id=role.pk, workspace_id=workspace.pk)
        except IntegrityError:
            self.fail('Old code omitting the new column must insert safely during a rolling release')
        self.assertFalse(WorkspaceMembership.objects.get(pk=member.pk).team_chat_enabled)
        self.assertFalse(verify_chat_access(user, workspace))

    def test_legacy_memberships_keep_access_messages_survive_and_new_memberships_default_disabled(self):
        executor = MigrationExecutor(connection)
        old_target = [('workspaces', '0001_initial')]
        latest = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate(old_target)
            old_apps = executor.loader.project_state(old_target).apps
            old_member = old_apps.get_model('workspaces', 'WorkspaceMembership')
            user = User.objects.create_user(username='legacy-chat', email='legacy-chat@example.test')
            role = Role.objects.create(name='EMPLOYEE')
            workspace = Workspace.objects.create(name='Legacy', code='legacy-chat', workspace_type='RETAIL')
            member = old_member.objects.create(user_id=user.pk, role_id=role.pk, workspace_id=workspace.pk)
            message = TeamChatMessage.objects.create(workspace=workspace, sender=user, message='Legacy history is retained')
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            self.assertTrue(WorkspaceMembership.objects.get(pk=member.pk).team_chat_enabled)
            self.assertEqual(TeamChatMessage.objects.get(pk=message.pk).message, 'Legacy history is retained')
            newcomer = User.objects.create_user(username='new-membership', email='new-membership@example.test')
            fresh = WorkspaceMembership.objects.create(user=newcomer, workspace=workspace, role=role)
            self.assertFalse(fresh.team_chat_enabled)
            self.assertTrue(verify_chat_access(user, workspace))
            self.assertFalse(verify_chat_access(newcomer, workspace))
        finally:
            MigrationExecutor(connection).migrate(latest)
