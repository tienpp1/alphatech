from unittest.mock import patch
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from apps.accounts.models import User, Role
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.notifications.models import InternalBulletin, TeamChatMessage


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class CollaborationWorkspaceSelectionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='collab-manager', email='manager@example.test', password='test-only')
        self.role = Role.objects.create(name='MANAGER')
        self.ws = Workspace.objects.create(name='A', code='collab-a', workspace_type='RETAIL')
        self.other = Workspace.objects.create(name='B', code='collab-b', workspace_type='RETAIL')
        self.member = WorkspaceMembership.objects.create(user=self.user, workspace=self.ws, role=self.role, is_active=True)
        self.client.force_login(self.user)
        self.reads = ['/noibo/bang-tin/', '/noibo/trao-doi/',
                      '/api/v1/notifications/bulletins/', '/api/v1/notifications/chat/messages/']
        self.invalid = [str(self.other.pk), 'not-a-uuid', '', '00000000-0000-0000-0000-000000000000']

    def test_invalid_explicit_reads_never_fallback(self):
        for url in self.reads:
            for value in self.invalid:
                with self.subTest(url=url, selector=value):
                    self.assertEqual(self.client.get(url, {'workspace_id': value}).status_code, 403)

    def test_invalid_chat_ui_posts_cannot_write_into_default(self):
        for value in self.invalid:
            response = self.client.post('/noibo/trao-doi/?workspace_id=' + value, {'message': 'Should not send'})
            self.assertEqual(response.status_code, 403)
        self.assertFalse(TeamChatMessage.objects.exists())

    def test_invalid_api_and_bulletin_posts_never_write(self):
        for url in ['/api/v1/notifications/chat/send/', '/api/v1/notifications/bulletins/create/', '/noibo/bang-tin/create/']:
            for value in self.invalid:
                with self.subTest(url=url, selector=value):
                    response = self.client.post(url, {'workspace_id': value, 'message': 'No', 'title': 'No', 'content': 'No'})
                    self.assertEqual(response.status_code, 403)
        self.assertFalse(TeamChatMessage.objects.exists())
        self.assertFalse(InternalBulletin.objects.exists())

    def test_valid_selection_and_missing_selection_keep_compatibility(self):
        for url in self.reads:
            self.assertEqual(self.client.get(url, {'workspace_id': str(self.ws.pk)}).status_code, 200)
            self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post('/api/v1/notifications/chat/send/', {'workspace_id': str(self.ws.pk), 'message': 'Xin chào'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(TeamChatMessage.objects.get().workspace_id, self.ws.pk)

    def test_valid_session_selection_used_by_ui(self):
        WorkspaceMembership.objects.create(user=self.user, workspace=self.other, role=self.role, is_active=True)
        session = self.client.session
        session['active_workspace_id'] = str(self.other.pk)
        session.save()
        for url in self.reads[:2]:
            self.assertEqual(self.client.get(url).context['active_workspace'].pk, self.other.pk)

    def test_stale_malformed_session_does_not_crash(self):
        session = self.client.session
        session['active_workspace_id'] = 'invalid'
        session.save()
        self.assertEqual(self.client.get('/noibo/trao-doi/').context['active_workspace'].pk, self.ws.pk)

    def test_inactive_membership_and_workspace_denied(self):
        self.member.is_active = False
        self.member.save()
        self.assertEqual(self.client.get(self.reads[2], {'workspace_id': self.ws.pk}).status_code, 403)
        self.member.is_active = True
        self.member.save()
        self.ws.is_active = False
        self.ws.save()
        self.assertEqual(self.client.post('/api/v1/notifications/chat/send/', {'workspace_id': self.ws.pk, 'message': 'No'}).status_code, 403)
        self.assertFalse(TeamChatMessage.objects.exists())

    def test_header_denial_is_not_overridden_by_authorized_query(self):
        for value in [str(self.other.pk), 'invalid']:
            for url in self.reads:
                self.assertEqual(self.client.get(url, {'workspace_id': self.ws.pk}, HTTP_X_WORKSPACE_ID=value).status_code, 403)

    def test_conflicting_authorized_header_and_query_denied(self):
        WorkspaceMembership.objects.create(user=self.user, workspace=self.other, role=self.role, is_active=True)
        for url in self.reads:
            self.assertEqual(self.client.get(url, {'workspace_id': self.other.pk}, HTTP_X_WORKSPACE_ID=str(self.ws.pk)).status_code, 403)
            self.assertEqual(self.client.get(url, HTTP_X_WORKSPACE_ID=str(self.other.pk)).status_code, 200)

    def test_permission_denied_propagates_without_success_or_exception_text(self):
        with patch('apps.notifications.ui_views.send_team_message', side_effect=PermissionDenied('private detail')):
            response = self.client.post('/noibo/trao-doi/?workspace_id=' + str(self.ws.pk), {'message': 'No'})
        self.assertEqual(response.status_code, 403)
        with patch('apps.notifications.views.send_team_message', side_effect=PermissionDenied('private detail')):
            response = self.client.post('/api/v1/notifications/chat/send/', {'workspace_id': self.ws.pk, 'message': 'No'})
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, 'private detail', status_code=403)
        self.assertFalse(TeamChatMessage.objects.exists())

    def test_public_customer_has_no_internal_access(self):
        customer = User.objects.create_user(username='collab-customer', email='customer@example.test')
        self.client.force_login(customer)
        for url in self.reads[:2]:
            self.assertRedirects(self.client.get(url), '/tai-khoan/?notice=customer_only', fetch_redirect_response=False)
        for url in self.reads[2:]:
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_superuser_can_select_active_workspace_but_not_inactive(self):
        self.user.is_superuser = True
        self.user.save()
        self.assertEqual(self.client.get(self.reads[2], {'workspace_id': self.other.pk}).status_code, 200)
        self.other.is_active = False
        self.other.save()
        self.assertEqual(self.client.get(self.reads[2], {'workspace_id': self.other.pk}).status_code, 403)
