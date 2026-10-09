"""Send, polling and initial HTML must agree on chat display time."""
from datetime import datetime, timezone as datetime_timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.workspaces.models import Workspace, WorkspaceMembership
from apps.notifications.models import TeamChatMessage
from apps.notifications.chat_service import get_recent_team_messages


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class TeamChatDisplayTimeTests(TestCase):
    def setUp(self):
        self.workspace = Workspace.objects.create(name='Time display test', code='chat-time', workspace_type='RETAIL')
        self.user = User.objects.create_user(username='chat-time-manager', password='test-only')
        role = Role.objects.create(name='MANAGER')
        WorkspaceMembership.objects.create(user=self.user, workspace=self.workspace, role=role, is_active=True)
        self.client.force_login(self.user)

    def assert_display_time(self, zone, expected):
        instant = datetime(2026, 10, 4, 23, 58, tzinfo=datetime_timezone.utc)
        with timezone.override(zone), patch('django.utils.timezone.now', return_value=instant):
            sent = self.client.post('/api/v1/notifications/chat/send/', {
                'workspace_id': str(self.workspace.pk), 'message': 'Timestamp regression',
            })
            self.assertEqual(sent.status_code, 201)
            self.assertEqual(sent.json()['created_at'], expected)
            polled = self.client.get('/api/v1/notifications/chat/messages/', {
                'workspace_id': str(self.workspace.pk), 'since_id': 0,
            })
            self.assertEqual(polled.status_code, 200)
            self.assertEqual(polled.json()['messages'][0]['id'], sent.json()['message_id'])
            self.assertEqual(polled.json()['messages'][0]['created_at'], expected)
            page = self.client.get('/noibo/trao-doi/', {'workspace_id': str(self.workspace.pk)})
            self.assertContains(page, expected)

    def test_vietnam_time_rolls_to_next_day_in_all_three_paths(self):
        self.assert_display_time('Asia/Ho_Chi_Minh', '06:58 05/10')

    def test_active_utc_timezone_matches_initial_template_not_hardcoded_vietnam(self):
        self.assert_display_time('UTC', '23:58 04/10')

    def test_cursor_pages_use_id_order_even_when_timestamps_are_reversed(self):
        items = [TeamChatMessage.objects.create(workspace=self.workspace, sender=self.user, message=str(i)) for i in range(55)]
        TeamChatMessage.objects.filter(pk=items[0].pk).update(created_at=timezone.now())
        TeamChatMessage.objects.filter(pk=items[-1].pk).update(created_at=datetime(2000, 1, 1, tzinfo=datetime_timezone.utc))
        first = get_recent_team_messages(self.workspace, self.user, limit=50, since_id=0)
        second = get_recent_team_messages(self.workspace, self.user, limit=50, since_id=first[-1].pk)
        self.assertEqual([m.pk for m in first + second], [m.pk for m in items])
        self.assertEqual(get_recent_team_messages(self.workspace, self.user, limit=1)[0].pk, items[-1].pk)

    def test_live_scripts_and_accessible_feedback_are_loaded(self):
        page = self.client.get('/noibo/trao-doi/', {'workspace_id': self.workspace.pk})
        self.assertContains(page, 'js/internal_team_chat.js')
        self.assertContains(page, 'id="chatSendStatus"')
        self.assertContains(page, 'for="chatInputMessage"')
        # The shared notification bell still has its unrelated timer.
        from pathlib import Path
        from django.conf import settings
        template = (Path(settings.BASE_DIR) / 'templates/notifications/team_chat.html').read_text(encoding='utf-8')
        self.assertNotIn('setInterval(', template)
