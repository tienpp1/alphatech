from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase

from apps.accounts.models import User, Role, Permission
from apps.workspaces.models import Workspace, WorkspaceMembership
from config.consumers import TelemetryConsumer


class CommandCenterPermissionsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cc-user", email="cc@example.com")
        self.workspace = Workspace.objects.create(code="cc", name="CC", workspace_type="RETAIL")
        self.role = Role.objects.create(name="CC_VIEWER")
        self.client.force_login(self.user)

    def test_public_customer_denied(self):
        self.assertEqual(self.client.get('/noibo/ai-command-center/').status_code, 403)

    def test_membership_without_required_permissions_denied(self):
        WorkspaceMembership.objects.create(user=self.user, workspace=self.workspace, role=self.role)
        self.assertEqual(self.client.get('/noibo/ai-command-center/').status_code, 403)

    def test_authorized_member_sees_explicit_demo_label(self):
        for code in ('gis.view_spatial_layers', 'forecasting.view_forecast',
                     'knowledge.view_knowledge', 'approvals.view_approval'):
            permission, _ = Permission.objects.get_or_create(codename=code, defaults={'name': code, 'module': code.split('.')[0]})
            self.role.permissions.add(permission)
        membership = WorkspaceMembership.objects.create(user=self.user, workspace=self.workspace, role=self.role)
        response = self.client.get('/noibo/ai-command-center/')
        self.assertContains(response, 'DỮ LIỆU MÔ PHỎNG')
        self.assertNotContains(response, 'Live AI Accuracy')
        self.assertEqual(self.client.get('/noibo/ai-command-center/', HTTP_X_WORKSPACE_ID='invalid').status_code, 403)
        membership.is_active = False
        membership.save(update_fields=['is_active'])
        self.assertEqual(self.client.get('/noibo/ai-command-center/').status_code, 403)


class CommandCenterSocketTests(SimpleTestCase):
    async def test_anonymous_socket_denied_before_accept(self):
        socket = WebsocketCommunicator(TelemetryConsumer.as_asgi(), '/ws/telemetry/')
        socket.scope['user'] = AnonymousUser()
        accepted, code = await socket.connect()
        self.assertFalse(accepted)
        self.assertEqual(code, 4403)
        await socket.disconnect()

    async def test_customer_socket_denied_before_accept(self):
        socket = WebsocketCommunicator(TelemetryConsumer.as_asgi(), '/ws/telemetry/')
        socket.scope['user'] = SimpleNamespace(pk=1, is_authenticated=True)
        with patch('config.consumers.may_view_telemetry', new=AsyncMock(return_value=False)):
            accepted, code = await socket.connect()
            self.assertFalse(accepted)
            self.assertEqual(code, 4403)
            await socket.disconnect()

    async def test_demo_payload_and_revocation(self):
        socket = WebsocketCommunicator(TelemetryConsumer.as_asgi(), '/ws/telemetry/')
        socket.scope['user'] = SimpleNamespace(pk=1, is_authenticated=True)
        with patch('config.consumers.may_view_telemetry', new=AsyncMock(side_effect=[True, True, False])):
            accepted, _ = await socket.connect()
            self.assertTrue(accepted)
            payload = await socket.receive_json_from()
            self.assertEqual(payload['mode'], 'DEMO')
            self.assertIn('minh họa', payload['log_message'])
            event = await socket.receive_output(timeout=4)
            self.assertEqual(event, {'type': 'websocket.close', 'code': 4403})
            await socket.disconnect()

    async def test_foreign_origin_denied(self):
        from config.asgi import application
        socket = WebsocketCommunicator(application, '/ws/telemetry/', headers=[(b'origin', b'https://evil.invalid')])
        accepted, _ = await socket.connect()
        self.assertFalse(accepted)
        await socket.disconnect()
