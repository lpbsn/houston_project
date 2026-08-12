from __future__ import annotations

from django.urls import path

from houston.analytics.api.views import (
    AnalyticsDashboardView,
    AnalyticsPatternDetailView,
    AnalyticsPatternListView,
    AnalyticsPatternMergeView,
    AnalyticsPatternMoveSignalsView,
    AnalyticsPatternRenameView,
    AnalyticsPatternSignalsView,
    AnalyticsPatternSplitToExistingView,
    AnalyticsPatternSplitToNewView,
)

urlpatterns = [
    path("analytics/dashboard/", AnalyticsDashboardView.as_view(), name="analytics-dashboard"),
    path("analytics/patterns/", AnalyticsPatternListView.as_view(), name="analytics-pattern-list"),
    path(
        "analytics/patterns/<uuid:pattern_id>/",
        AnalyticsPatternDetailView.as_view(),
        name="analytics-pattern-detail",
    ),
    path(
        "analytics/patterns/<uuid:pattern_id>/signals/",
        AnalyticsPatternSignalsView.as_view(),
        name="analytics-pattern-signals",
    ),
    path(
        "analytics/patterns/<uuid:pattern_id>/rename/",
        AnalyticsPatternRenameView.as_view(),
        name="analytics-pattern-rename",
    ),
    path(
        "analytics/patterns/<uuid:pattern_id>/merge/",
        AnalyticsPatternMergeView.as_view(),
        name="analytics-pattern-merge",
    ),
    path(
        "analytics/patterns/<uuid:pattern_id>/move-signals/",
        AnalyticsPatternMoveSignalsView.as_view(),
        name="analytics-pattern-move-signals",
    ),
    path(
        "analytics/patterns/<uuid:pattern_id>/split-to-existing/",
        AnalyticsPatternSplitToExistingView.as_view(),
        name="analytics-pattern-split-to-existing",
    ),
    path(
        "analytics/patterns/<uuid:pattern_id>/split-to-new/",
        AnalyticsPatternSplitToNewView.as_view(),
        name="analytics-pattern-split-to-new",
    ),
]
