from django.urls import re_path
from houston.chat.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/v1/establishments/(?P<establishment_id>[0-9a-f-]{36})/chat/$",
        ChatConsumer.as_asgi(),
    ),
]
