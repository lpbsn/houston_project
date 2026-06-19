from django.urls import path

from houston.realtime.api.views import RealtimeWsTicketView

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/realtime/ws-ticket/",
        RealtimeWsTicketView.as_view(),
        name="realtime-ws-ticket",
    ),
]
