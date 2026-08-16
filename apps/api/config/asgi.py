import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

# ruff: noqa: E402
from django.conf import settings
from houston.chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from houston.realtime.routing import websocket_urlpatterns as realtime_websocket_urlpatterns


class ClientOriginsValidator:
    """Rejects WebSocket handshakes whose Origin is not in HOUSTON_CLIENT_ORIGINS."""

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):
        inner = OriginValidator(self.application, list(settings.HOUSTON_CLIENT_ORIGINS))
        return await inner(scope, receive, send)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": ClientOriginsValidator(
            URLRouter(chat_websocket_urlpatterns + realtime_websocket_urlpatterns),
        ),
    }
)
