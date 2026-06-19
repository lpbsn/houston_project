from django.urls import re_path

from houston.realtime.consumers import RealtimeConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/v1/establishments/(?P<establishment_id>[0-9a-f-]{36})/realtime/$",
        RealtimeConsumer.as_asgi(),
    ),
]
