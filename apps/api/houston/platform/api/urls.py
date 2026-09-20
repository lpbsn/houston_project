from django.urls import path

from houston.platform.api.views import (
    PlatformEstablishmentDeleteView,
    PlatformEstablishmentDetailView,
    PlatformEstablishmentListView,
    PlatformMembershipListView,
    PlatformOnboardingCompleteView,
    PlatformOnboardingDetailView,
    PlatformOnboardingDirectorInviteView,
    PlatformOnboardingDraftView,
    PlatformOnboardingListCreateView,
    PlatformOnboardingOwnerInviteView,
    PlatformOnboardingSummaryView,
    PlatformOrganizationDeleteView,
    PlatformOrganizationDetailView,
    PlatformOrganizationListView,
    PlatformSessionView,
    PlatformUserDetailView,
    PlatformUserListView,
)

urlpatterns = [
    path("session/", PlatformSessionView.as_view(), name="platform-session"),
    path("organizations/", PlatformOrganizationListView.as_view(), name="platform-organizations"),
    path(
        "organizations/<uuid:organization_id>/",
        PlatformOrganizationDetailView.as_view(),
        name="platform-organization-detail",
    ),
    path(
        "organizations/<uuid:organization_id>/delete/",
        PlatformOrganizationDeleteView.as_view(),
        name="platform-organization-delete",
    ),
    path(
        "establishments/",
        PlatformEstablishmentListView.as_view(),
        name="platform-establishments",
    ),
    path(
        "establishments/<uuid:establishment_id>/",
        PlatformEstablishmentDetailView.as_view(),
        name="platform-establishment-detail",
    ),
    path(
        "establishments/<uuid:establishment_id>/delete/",
        PlatformEstablishmentDeleteView.as_view(),
        name="platform-establishment-delete",
    ),
    path("users/", PlatformUserListView.as_view(), name="platform-users"),
    path("users/<uuid:user_id>/", PlatformUserDetailView.as_view(), name="platform-user-detail"),
    path("memberships/", PlatformMembershipListView.as_view(), name="platform-memberships"),
    path("onboardings/", PlatformOnboardingListCreateView.as_view(), name="platform-onboardings"),
    path(
        "onboardings/<uuid:session_id>/",
        PlatformOnboardingDetailView.as_view(),
        name="platform-onboarding-detail",
    ),
    path(
        "onboardings/<uuid:session_id>/draft/",
        PlatformOnboardingDraftView.as_view(),
        name="platform-onboarding-draft",
    ),
    path(
        "onboardings/<uuid:session_id>/complete/",
        PlatformOnboardingCompleteView.as_view(),
        name="platform-onboarding-complete",
    ),
    path(
        "onboardings/<uuid:session_id>/summary/",
        PlatformOnboardingSummaryView.as_view(),
        name="platform-onboarding-summary",
    ),
    path(
        "onboardings/<uuid:session_id>/director-invitations/",
        PlatformOnboardingDirectorInviteView.as_view(),
        name="platform-onboarding-director-invite",
    ),
    path(
        "onboardings/<uuid:session_id>/owner-invitations/",
        PlatformOnboardingOwnerInviteView.as_view(),
        name="platform-onboarding-owner-invite",
    ),
]
