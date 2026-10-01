from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path("ws/telemetry/", consumers.TelemetryConsumer.as_asgi()),
]
