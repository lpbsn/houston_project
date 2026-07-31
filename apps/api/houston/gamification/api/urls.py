from django.urls import path

from houston.gamification.api.views import (
    GamificationOverviewView,
    GamificationTransactionListView,
)

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/gamification/me/",
        GamificationOverviewView.as_view(),
        name="gamification-overview",
    ),
    path(
        "establishments/<uuid:establishment_id>/gamification/me/transactions/",
        GamificationTransactionListView.as_view(),
        name="gamification-transactions",
    ),
]
