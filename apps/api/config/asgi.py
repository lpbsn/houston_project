import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

# ruff: noqa: E402
from houston.chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from houston.realtime.routing import websocket_urlpatterns as realtime_websocket_urlpatterns

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            URLRouter(chat_websocket_urlpatterns + realtime_websocket_urlpatterns),
        ),
    }
)
