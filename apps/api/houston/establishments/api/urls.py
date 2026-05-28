from django.urls import path

from houston.establishments.api.views import (
    MembershipDeactivateView,
    MembershipDetailView,
    MembershipListView,
    ScopedUserSearchView,
)

urlpatterns = [
    path(
        "establishments/<uuid:establishment_id>/memberships/",
        MembershipListView.as_view(),
        name="establishment-membership-list",
    ),
    path(
        "establishments/<uuid:establishment_id>/memberships/<uuid:membership_id>/",
        MembershipDetailView.as_view(),
        name="establishment-membership-detail",
    ),
    path(
        "establishments/<uuid:establishment_id>/memberships/<uuid:membership_id>/deactivate/",
        MembershipDeactivateView.as_view(),
        name="establishment-membership-deactivate",
    ),
    path(
        "establishments/<uuid:establishment_id>/users/search/",
        ScopedUserSearchView.as_view(),
        name="establishment-user-search",
    ),
]
