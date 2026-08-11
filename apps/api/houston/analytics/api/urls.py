from __future__ import annotations

from django.urls import path

from houston.analytics.api.views import (
    AnalyticsDashboardView,
    AnalyticsPatternDetailView,
    AnalyticsPatternListView,
    AnalyticsPatternSignalsView,
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
]

