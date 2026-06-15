from django.urls import path

from houston.comments.api.views import ActionCommentsView, SignalCommentsView

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/signals/<uuid:signal_id>/comments/",
        SignalCommentsView.as_view(),
        name="signal-comments",
    ),
    path(
        "establishments/<uuid:establishment_id>/actions/<uuid:action_id>/comments/",
        ActionCommentsView.as_view(),
        name="action-comments",
    ),
]
