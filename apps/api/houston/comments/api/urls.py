from django.urls import path

from houston.comments.api.views import (
    ActionPlanExecutionCommentResolveView,
    ActionPlanExecutionCommentsView,
    ActionPlanExecutionCommentUnresolveView,
    SignalCommentsView,
)

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/signals/<uuid:signal_id>/comments/",
        SignalCommentsView.as_view(),
        name="signal-comments",
    ),
    path(
        (
            "establishments/<uuid:establishment_id>/action-plan-executions/"
            "<uuid:execution_id>/comments/"
        ),
        ActionPlanExecutionCommentsView.as_view(),
        name="action-plan-execution-comments",
    ),
    path(
        (
            "establishments/<uuid:establishment_id>/action-plan-executions/"
            "<uuid:execution_id>/comments/<uuid:comment_id>/resolve/"
        ),
        ActionPlanExecutionCommentResolveView.as_view(),
        name="action-plan-execution-comment-resolve",
    ),
    path(
        (
            "establishments/<uuid:establishment_id>/action-plan-executions/"
            "<uuid:execution_id>/comments/<uuid:comment_id>/unresolve/"
        ),
        ActionPlanExecutionCommentUnresolveView.as_view(),
        name="action-plan-execution-comment-unresolve",
    ),
]
