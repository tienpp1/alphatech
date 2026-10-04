"""Permission-protected illustrative stream; never represents business metrics."""
import asyncio
from contextlib import suppress
from datetime import datetime, timezone

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import PermissionDenied


@database_sync_to_async
def may_view_telemetry(user_id, session=None):
    from apps.accounts.models import User
    from config.views import _report_workspaces
    from apps.accounts.internal_access import has_internal_role, is_public_only_session

    if session is not None and getattr(session, "session_key", None):
        from importlib import import_module
        from django.conf import settings
        from django.contrib.auth import SESSION_KEY
        session = import_module(settings.SESSION_ENGINE).SessionStore(session.session_key)
        if str(session.get(SESSION_KEY)) != str(user_id):
            return False

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        return False
    if not has_internal_role(user) or is_public_only_session(user, session or {}):
        return False
    try:
        return _report_workspaces(user, "telemetry").exists()
    except PermissionDenied:
        return False


class TelemetryConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not await may_view_telemetry(user.pk, self.scope.get("session")):
            await self.close(code=4403)
            return
        self.user_id = user.pk
        await self.accept()
        self.stream_task = asyncio.create_task(self.stream_data())

    async def disconnect(self, close_code):
        task = getattr(self, "stream_task", None)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    async def stream_data(self):
        frame = 0
        while True:
            # Reload identity and membership so revocation applies to open sockets.
            if not await may_view_telemetry(self.user_id, self.scope.get("session")):
                await self.close(code=4403)
                return
            await self.send_json({
                "mode": "DEMO",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actual_revenue": [40, 55, 48, 62][frame % 4],
                "ai_forecast": [42, 51, 50, 60][frame % 4],
                "agent_count": 4,
                "system_load": [25, 30, 28, 32][frame % 4],
                "log_message": "Dữ liệu minh họa giao diện; chưa đo hiệu quả AI hay tải hệ thống.",
            })
            frame += 1
            await asyncio.sleep(2)
