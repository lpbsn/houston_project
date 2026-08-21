from django.urls import path

from houston.action_plans.api.cross_views import (
    CrossActionPlanExecutionDetailView,
    CrossActionPlanExecutionFeedView,
)
from houston.signals.api.cross_views import CrossSignalDetailView, CrossSignalFeedView

urlpatterns = [
    path("signal-feed/", CrossSignalFeedView.as_view(), name="cross-signal-feed"),
    path("signals/<uuid:signal_id>/", CrossSignalDetailView.as_view(), name="cross-signal-detail"),
    path(
        "action-plan-execution-feed/",
        CrossActionPlanExecutionFeedView.as_view(),
        name="cross-action-plan-execution-feed",
    ),
    path(
        "action-plan-executions/<uuid:execution_id>/",
        CrossActionPlanExecutionDetailView.as_view(),
        name="cross-action-plan-execution-detail",
    ),
]
