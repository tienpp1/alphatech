"""Older chat pages and independent authenticated sessions use the real endpoints."""
from django.test import Client, TestCase, override_settings

from apps.accounts.models import Role, User
from apps.notifications.chat_service import get_recent_team_messages
from apps.notifications.models import TeamChatMessage
from apps.workspaces.models import Workspace, WorkspaceMembership


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TeamChatHistoryTests(TestCase):
    def setUp(self):
        self.ws = Workspace.objects.create(code='history-a', name='A', workspace_type='RETAIL')
        self.other = Workspace.objects.create(code='history-b', name='B', workspace_type='SERVICE')
        self.manager = User.objects.create_user(username='history-manager', email='manager@history.example', password='test-only')
        self.employee = User.objects.create_user(username='history-employee', email='employee@history.example', password='test-only')
        for user, role in ((self.manager, 'MANAGER'), (self.employee, 'EMPLOYEE')):
            WorkspaceMembership.objects.create(user=user, workspace=self.ws, role=Role.objects.get_or_create(name=role)[0])
        self.manager_client, self.employee_client = Client(), Client()
        self.manager_client.force_login(self.manager)
        self.employee_client.force_login(self.employee)
        self.url = '/api/v1/notifications/chat/messages/'
        self.items = TeamChatMessage.objects.bulk_create([
            TeamChatMessage(workspace=self.ws, sender=self.manager, message=f'History {i}') for i in range(123)
        ])
        self.foreign = TeamChatMessage.objects.create(workspace=self.other, sender=self.manager, message='FOREIGN SECRET')

    def page(self, client=None, **cursors):
        return (client or self.employee_client).get(self.url, {'workspace_id': str(self.ws.pk), **cursors})

    def test_backward_pages_recover_all_123_messages_without_gaps_or_duplicates(self):
        initial = self.page().json()
        self.assertEqual([x['id'] for x in initial['messages']], [m.pk for m in self.items[73:]])
        self.assertEqual(initial['oldest_id'], self.items[73].pk)
        self.assertTrue(initial['has_older'])
        middle = self.page(before_id=initial['oldest_id']).json()
        oldest = self.page(before_id=middle['oldest_id']).json()
        self.assertEqual([x['id'] for x in middle['messages']], [m.pk for m in self.items[23:73]])
        self.assertEqual([x['id'] for x in oldest['messages']], [m.pk for m in self.items[:23]])
        self.assertFalse(oldest['has_older'])
        exhausted = self.page(before_id=oldest['oldest_id']).json()
        self.assertEqual(exhausted['messages'], [])
        self.assertFalse(exhausted['has_older'])
        self.assertEqual(exhausted['oldest_id'], 0)
        reloaded = self.employee_client.get('/noibo/trao-doi/', {'workspace_id': self.ws.pk})
        self.assertContains(reloaded, 'id="chatLoadOlder"')
        self.assertEqual(reloaded.context['oldest_message_id'], self.items[73].pk)
        self.assertTrue(reloaded.context['has_older_messages'])

    def test_invalid_and_conflicting_cursors_are_400_not_silent_latest_page(self):
        for cursor in ('', '0', '-1', '1.5', 'bad', '9223372036854775808', '１２'):
            with self.subTest(cursor=cursor):
                self.assertEqual(self.page(before_id=cursor).status_code, 400)
        self.assertEqual(self.page(before_id=self.items[50].pk, since_id=0).status_code, 400)
        self.assertEqual(self.page(before_id=self.items[50].pk, since_id='').status_code, 400)
        self.assertEqual(self.page(since_id='bad').status_code, 400)

    def test_service_enforces_exclusive_cursors_and_page_bound(self):
        page = get_recent_team_messages(self.ws, self.employee, limit=500, before_id=self.items[-1].pk)
        self.assertEqual([m.pk for m in page], [m.pk for m in self.items[72:122]])
        with self.assertRaises(ValueError):
            get_recent_team_messages(self.ws, self.employee, since_id=0, before_id=self.items[-1].pk)
        with self.assertRaises(ValueError):
            get_recent_team_messages(self.ws, self.employee, before_id=0)

    def test_two_independent_sessions_exchange_reload_and_keep_forward_cursor_after_history(self):
        employee_cursor = self.page().json()['latest_id']
        sent = self.manager_client.post('/api/v1/notifications/chat/send/', {'workspace_id': self.ws.pk, 'message': 'Manager to employee'})
        self.assertEqual(sent.status_code, 201)
        manager_id = sent.json()['message_id']
        self.page(before_id=self.items[73].pk)
        received = self.page(since_id=employee_cursor).json()['messages']
        self.assertEqual([(m['id'], m['message'], m['is_me']) for m in received], [(manager_id, 'Manager to employee', False)])
        reply = self.employee_client.post('/api/v1/notifications/chat/send/', {'workspace_id': self.ws.pk, 'message': 'Employee to manager'})
        self.assertEqual(reply.status_code, 201)
        received = self.page(self.manager_client, since_id=manager_id).json()['messages']
        self.assertEqual([(m['id'], m['message'], m['is_me']) for m in received], [(reply.json()['message_id'], 'Employee to manager', False)])
        for client in (self.employee_client, self.manager_client):
            page = client.get('/noibo/trao-doi/', {'workspace_id': self.ws.pk})
            self.assertContains(page, 'Manager to employee')
            self.assertContains(page, 'Employee to manager')
            self.assertNotContains(page, 'FOREIGN SECRET')

    def test_older_history_cannot_select_foreign_workspace_or_survive_membership_withdrawal(self):
        foreign = self.employee_client.get(self.url, {'workspace_id': self.other.pk, 'before_id': self.foreign.pk + 1})
        self.assertEqual(foreign.status_code, 403)
        self.assertNotContains(foreign, 'FOREIGN SECRET', status_code=403)
        # A foreign row ID is just a numeric bound; it never selects its tenant.
        own = self.page(before_id=self.foreign.pk + 1).json()['messages']
        self.assertEqual(len(own), 50)
        self.assertNotIn(self.foreign.pk, [m['id'] for m in own])
        WorkspaceMembership.objects.filter(user=self.employee, workspace=self.ws).update(is_active=False)
        self.assertEqual(self.page(before_id=self.items[-1].pk).status_code, 403)
        self.assertEqual(self.page(since_id=0).status_code, 403)
        self.assertEqual(self.employee_client.post('/api/v1/notifications/chat/send/', {'workspace_id': self.ws.pk, 'message': 'Forbidden'}).status_code, 403)
