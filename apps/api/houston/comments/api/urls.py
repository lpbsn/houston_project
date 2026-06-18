from django.urls import path

from houston.comments.api.views import (
    ActionCommentResolveView,
    ActionCommentsView,
    ActionCommentUnresolveView,
    SignalCommentsView,
)

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
    path(
        (
            "establishments/<uuid:establishment_id>/actions/<uuid:action_id>/comments/"
            "<uuid:comment_id>/resolve/"
        ),
        ActionCommentResolveView.as_view(),
        name="action-comment-resolve",
    ),
    path(
        (
            "establishments/<uuid:establishment_id>/actions/<uuid:action_id>/comments/"
            "<uuid:comment_id>/unresolve/"
        ),
        ActionCommentUnresolveView.as_view(),
        name="action-comment-unresolve",
    ),
]
