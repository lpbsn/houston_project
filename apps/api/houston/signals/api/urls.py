from django.urls import path

from houston.signals.api.views import (
    SignalDetailView,
    SignalFeedView,
    SignalPinView,
    SignalUnpinView,
    SignalUrgencyView,
)

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/signal-feed/",
        SignalFeedView.as_view(),
        name="signal-feed",
    ),
    path(
        "establishments/<uuid:establishment_id>/signals/<uuid:signal_id>/",
        SignalDetailView.as_view(),
        name="signal-detail",
    ),
    path(
        "establishments/<uuid:establishment_id>/signals/<uuid:signal_id>/pin/",
        SignalPinView.as_view(),
        name="signal-pin",
    ),
    path(
        "establishments/<uuid:establishment_id>/signals/<uuid:signal_id>/unpin/",
        SignalUnpinView.as_view(),
        name="signal-unpin",
    ),
    path(
        "establishments/<uuid:establishment_id>/signals/<uuid:signal_id>/urgency/",
        SignalUrgencyView.as_view(),
        name="signal-urgency",
    ),
]
