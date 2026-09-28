from django.urls import path

from houston.action_plans.api.cross_views import (
    CrossActionPlanExecutionCalendarView,
    CrossActionPlanExecutionDetailView,
    CrossActionPlanExecutionFeedPinsView,
    CrossActionPlanExecutionFeedView,
    CrossActionPlanExecutionUpcomingView,
)
from houston.action_plans.api.history_views import CrossExecutionHistoryView
from houston.signals.api.cross_views import (
    CrossSignalDetailView,
    CrossSignalFeedPinsView,
    CrossSignalFeedView,
)
from houston.signals.api.history_views import CrossSignalHistoryView

urlpatterns = [
    path("signal-feed/", CrossSignalFeedView.as_view(), name="cross-signal-feed"),
    path("history/signals/", CrossSignalHistoryView.as_view(), name="cross-signal-history"),
    path(
        "history/executions/",
        CrossExecutionHistoryView.as_view(),
        name="cross-execution-history",
    ),
    path(
        "signal-feed-pins/",
        CrossSignalFeedPinsView.as_view(),
        name="cross-signal-feed-pins",
    ),
    path("signals/<uuid:signal_id>/", CrossSignalDetailView.as_view(), name="cross-signal-detail"),
    path(
        "action-plan-execution-feed/",
        CrossActionPlanExecutionFeedView.as_view(),
        name="cross-action-plan-execution-feed",
    ),
    path(
        "action-plan-execution-feed-pins/",
        CrossActionPlanExecutionFeedPinsView.as_view(),
        name="cross-action-plan-execution-feed-pins",
    ),
    path(
        "action-plan-execution-upcoming/",
        CrossActionPlanExecutionUpcomingView.as_view(),
        name="cross-action-plan-execution-upcoming",
    ),
    path(
        "action-plan-execution-calendar/",
        CrossActionPlanExecutionCalendarView.as_view(),
        name="cross-action-plan-execution-calendar",
    ),
    path(
        "action-plan-executions/<uuid:execution_id>/",
        CrossActionPlanExecutionDetailView.as_view(),
        name="cross-action-plan-execution-detail",
    ),
]
