from __future__ import annotations

from django.db import models
from django.db.models import Q

from houston.accounts.models import User
from houston.establishments.membership_scope import (
    membership_covers_business_unit_including_admins,
    membership_is_assignable_by_actor,
    membership_scope_prefetch,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    EstablishmentMembership,
    MembershipScope,
    OnboardingProposal,
    OnboardingSession,
    OperationalUnit,
)
from houston.establishments.role_constants import ADMIN_ROLES
from houston.organizations.models import Organization

_ONBOARDING_MANAGEMENT_ROLES = (
    EstablishmentMembership.Role.OWNER,
    EstablishmentMembership.Role.DIRECTOR,
)
_ONBOARDING_ESTABLISHMENT_STATUSES = (
    Establishment.Status.DRAFT,
    Establishment.Status.ACTIVE,
)


_TEAM_MEMBERSHIP_ROLE_ORDER = models.Case(
    models.When(role=EstablishmentMembership.Role.OWNER, then=0),
    models.When(role=EstablishmentMembership.Role.DIRECTOR, then=1),
    models.When(role=EstablishmentMembership.Role.MANAGER, then=2),
    models.When(role=EstablishmentMembership.Role.STAFF, then=3),
    default=4,
)


def list_memberships_for_team(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> list[EstablishmentMembership] | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    return list(
        _management_membership_queryset(establishment_id=establishment_id).order_by(
            _TEAM_MEMBERSHIP_ROLE_ORDER,
            "user__first_name",
            "user__last_name",
            "user__username",
            "user__email",
            "id",
        )
    )


def list_memberships_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> list[EstablishmentMembership] | None:
    return list_memberships_for_team(
        current_membership=current_membership,
        establishment_id=establishment_id,
    )


def get_membership_for_team_detail(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
) -> EstablishmentMembership | None:
    return get_membership_for_management(
        current_membership=current_membership,
        establishment_id=establishment_id,
        membership_id=membership_id,
    )


def get_membership_for_management(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    membership_id,
) -> EstablishmentMembership | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    return (
        _management_membership_queryset(establishment_id=establishment_id)
        .filter(id=membership_id)
        .first()
    )


def get_workspace_summary_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
) -> dict | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    establishment = current_membership.establishment

    owner_membership = (
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        .select_related("user")
        .order_by("created_at", "id")
        .first()
    )

    director_membership = (
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=[
                EstablishmentMembership.Status.ACTIVE,
                EstablishmentMembership.Status.INVITED,
            ],
        )
        .select_related("user")
        .order_by(
            models.Case(
                models.When(status=EstablishmentMembership.Status.ACTIVE, then=0),
                default=1,
            ),
            "created_at",
            "id",
        )
        .first()
    )

    active_membership_count = EstablishmentMembership.objects.filter(
        establishment_id=establishment_id,
        status=EstablishmentMembership.Status.ACTIVE,
    ).count()

    return {
        "establishment": {
            "id": establishment.id,
            "name": establishment.name,
        },
        "owner": _serialize_workspace_person(owner_membership),
        "director": _serialize_workspace_director(director_membership),
        "active_membership_count": active_membership_count,
    }


def _serialize_workspace_person(membership: EstablishmentMembership | None) -> dict | None:
    if membership is None:
        return None

    return {"display_name": _membership_display_name(membership.user)}


def _serialize_workspace_director(membership: EstablishmentMembership | None) -> dict | None:
    if membership is None:
        return None

    return {
        "display_name": _membership_display_name(membership.user),
        "status": membership.status,
    }


def _membership_display_name(user: User) -> str:
    full_name = user.get_full_name().strip()
    if full_name:
        return full_name

    if user.username:
        return user.username

    if user.email:
        return user.email

    return str(user.id)


def search_users_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    query: str,
    business_unit: BusinessUnit | None = None,
    context: str = "assignee",
) -> list[EstablishmentMembership] | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None

    normalized_query = query.strip()
    if not normalized_query:
        return []

    memberships = list(
        _management_membership_queryset(establishment_id=establishment_id)
        .filter(
            user__status=User.Status.ACTIVE,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .filter(
            Q(user__first_name__icontains=normalized_query)
            | Q(user__last_name__icontains=normalized_query)
            | Q(user__username__icontains=normalized_query)
            | Q(user__email__icontains=normalized_query)
        )
    )

    if context == "mention":
        if business_unit is not None:
            return [
                membership
                for membership in memberships
                if membership_covers_business_unit_including_admins(membership, business_unit)
            ]
        return memberships

    if business_unit is None:
        if current_membership.role in ADMIN_ROLES:
            return memberships
        if current_membership.role == EstablishmentMembership.Role.MANAGER:
            return [
                membership
                for membership in memberships
                if membership_is_assignable_by_actor(
                    actor=current_membership,
                    target=membership,
                )
            ]
        return []

    return [
        membership
        for membership in memberships
        if membership_covers_business_unit_including_admins(membership, business_unit)
    ]


def get_onboarding_session_for_actor(
    *,
    actor: User,
    session_id,
) -> OnboardingSession | None:
    if actor.status != User.Status.ACTIVE:
        return None

    return _onboarding_session_queryset_for_actor(actor).filter(id=session_id).first()


def list_onboarding_sessions_for_actor(*, actor: User) -> list[OnboardingSession]:
    if actor.status != User.Status.ACTIVE:
        return []

    return list(_onboarding_session_queryset_for_actor(actor))


def get_active_onboarding_session_for_establishment(
    *,
    actor: User,
    establishment_id,
) -> OnboardingSession | None:
    if actor.status != User.Status.ACTIVE:
        return None

    return (
        _onboarding_session_queryset_for_actor(actor)
        .filter(
            establishment_id=establishment_id,
            status__in=OnboardingSession.NON_TERMINAL_STATUSES,
        )
        .first()
    )


def list_onboarding_proposals_for_actor(
    *,
    actor: User,
    session_id,
) -> list[OnboardingProposal] | None:
    session = get_onboarding_session_for_actor(actor=actor, session_id=session_id)
    if session is None:
        return None

    return list(_onboarding_proposal_queryset(session_id=session.id))


def get_onboarding_proposal_for_actor(
    *,
    actor: User,
    session_id,
    proposal_id,
) -> OnboardingProposal | None:
    session = get_onboarding_session_for_actor(actor=actor, session_id=session_id)
    if session is None:
        return None

    return _onboarding_proposal_queryset(session_id=session.id).filter(id=proposal_id).first()


def get_membership_for_invitation(
    *,
    user: User,
    establishment_id,
) -> EstablishmentMembership | None:
    return (
        EstablishmentMembership.objects.filter(
            user=user,
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
            establishment__status__in=(
                Establishment.Status.ACTIVE,
                Establishment.Status.DRAFT,
            ),
            role__in=EstablishmentMembership.Role.values,
        )
        .select_related("establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch())
        .first()
    )


def get_applied_onboarding_proposal_for_establishment(
    *,
    establishment_id,
) -> OnboardingProposal | None:
    return (
        OnboardingProposal.objects.filter(
            establishment_id=establishment_id,
            status=OnboardingProposal.Status.APPLIED,
        )
        .order_by("-applied_at", "-id")
        .first()
    )


def get_runtime_config_for_session(*, session: OnboardingSession) -> dict:
    establishment_id = session.establishment_id
    business_unit_tree = get_establishment_business_unit_tree(
        establishment_id=establishment_id,
        active_only=True,
    )

    return {
        "activity_description": _get_activity_description(establishment_id),
        "active_business_units": (
            business_unit_tree["business_units"] if business_unit_tree is not None else []
        ),
        "optional_units": list(
            OperationalUnit.objects.filter(
                establishment_id=establishment_id,
                active=True,
            ).order_by("key", "id")
        ),
    }


def _onboarding_session_queryset_for_actor(actor: User):
    accessible_establishment_ids = EstablishmentMembership.objects.filter(
        user=actor,
        status=EstablishmentMembership.Status.ACTIVE,
        role__in=_ONBOARDING_MANAGEMENT_ROLES,
        establishment__status__in=_ONBOARDING_ESTABLISHMENT_STATUSES,
        establishment__organization__status=Organization.Status.ACTIVE,
    ).values("establishment_id")

    return (
        OnboardingSession.objects.filter(
            establishment_id__in=accessible_establishment_ids,
            organization_id=models.F("establishment__organization_id"),
            establishment__status__in=_ONBOARDING_ESTABLISHMENT_STATUSES,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related(
            "organization",
            "establishment",
            "establishment__organization",
            "started_by",
        )
        .order_by("-updated_at", "-created_at", "id")
    )


def _onboarding_proposal_queryset(*, session_id):
    return (
        OnboardingProposal.objects.filter(onboarding_session_id=session_id)
        .select_related(
            "onboarding_session",
            "onboarding_session__organization",
            "onboarding_session__establishment",
            "establishment",
            "created_by",
            "validated_by",
            "applied_by",
        )
        .order_by("-updated_at", "-created_at", "id")
    )


def _get_activity_description(establishment_id):
    return (
        EstablishmentActivityDescription.objects.filter(establishment_id=establishment_id)
        .select_related("submitted_by")
        .first()
    )


def _management_membership_queryset(*, establishment_id):
    return (
        EstablishmentMembership.objects.filter(establishment_id=establishment_id)
        .select_related("user", "establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch())
        .order_by("user__username", "user__email", "id")
    )


def _serialize_activity_subject_public(*, activity_subject: ActivitySubject) -> dict | None:
    from houston.establishments.public_serialization import serialize_activity_subject_public

    return serialize_activity_subject_public(activity_subject=activity_subject)


def _serialize_business_unit_public(
    *,
    business_unit: BusinessUnit,
    activity_subjects: list[ActivitySubject] | None = None,
) -> dict | None:
    from houston.establishments.public_serialization import serialize_business_unit_public

    return serialize_business_unit_public(
        business_unit=business_unit,
        activity_subjects=activity_subjects,
        include_activity_subjects=True,
    )


def get_establishment_business_unit_tree(
    *,
    establishment_id,
    active_only: bool = True,
) -> dict | None:
    establishment = Establishment.objects.filter(pk=establishment_id).only("id", "name").first()
    if establishment is None:
        return None

    active_filter = {"active": True} if active_only else {}
    business_units = list(
        BusinessUnit.objects.filter(
            establishment_id=establishment_id,
            **active_filter,
        )
        .select_related("catalog_business_unit")
        .order_by("specific_name", "label", "key", "id")
    )
    subjects = list(
        ActivitySubject.objects.filter(
            establishment_id=establishment_id,
            **active_filter,
        )
        .select_related("catalog_activity_subject")
        .order_by("label", "normalized_name", "id")
    )
    subjects_by_bu: dict = {}
    for subject in subjects:
        subjects_by_bu.setdefault(subject.business_unit_id, []).append(subject)

    serialized_units = []
    for bu in business_units:
        item = _serialize_business_unit_public(
            business_unit=bu,
            activity_subjects=subjects_by_bu.get(bu.id, []),
        )
        if item is not None:
            serialized_units.append(item)

    return {
        "establishment_id": establishment.id,
        "establishment_name": establishment.name,
        "business_units": serialized_units,
    }


_SCOPE_FILTERED_ROLES = frozenset(
    {
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    }
)


def get_business_units_for_establishment(
    *,
    current_membership: EstablishmentMembership | None,
    establishment_id,
    include_inactive: bool = False,
) -> dict | None:
    if current_membership is None or current_membership.establishment_id != establishment_id:
        return None
    if current_membership.status != EstablishmentMembership.Status.ACTIVE:
        return None

    tree = get_establishment_business_unit_tree(
        establishment_id=establishment_id,
        active_only=not include_inactive,
    )
    if tree is None:
        return None

    if current_membership.role not in _SCOPE_FILTERED_ROLES:
        return tree

    business_unit_ids = [item["id"] for item in tree["business_units"]]
    business_units_by_id = BusinessUnit.objects.in_bulk(business_unit_ids)
    tree["business_units"] = [
        item
        for item in tree["business_units"]
        if membership_covers_business_unit_including_admins(
            current_membership,
            business_units_by_id.get(item["id"]),
        )
    ]
    return tree


def business_unit_has_active_membership_scopes(*, business_unit: BusinessUnit) -> bool:
    return MembershipScope.objects.filter(
        business_unit=business_unit,
        membership__status=EstablishmentMembership.Status.ACTIVE,
    ).exists()


def serialize_business_unit_tree_item(*, business_unit: BusinessUnit) -> dict:
    if (
        business_unit.catalog_business_unit_id is not None
        and getattr(business_unit, "catalog_business_unit", None) is None
    ):
        business_unit = (
            BusinessUnit.objects.select_related("catalog_business_unit")
            .filter(id=business_unit.id)
            .first()
            or business_unit
        )
    item = _serialize_business_unit_public(business_unit=business_unit)
    if item is None:
        raise ValueError("Business unit identity is incomplete.")
    return item


def serialize_activity_subject_tree_item(*, activity_subject: ActivitySubject) -> dict:
    if (
        activity_subject.catalog_activity_subject_id is not None
        and getattr(activity_subject, "catalog_activity_subject", None) is None
    ):
        activity_subject = (
            ActivitySubject.objects.select_related("catalog_activity_subject")
            .filter(id=activity_subject.id)
            .first()
            or activity_subject
        )
    item = _serialize_activity_subject_public(activity_subject=activity_subject)
    if item is None:
        raise ValueError("Activity subject identity is incomplete.")
    return item


def get_active_business_unit_for_establishment(
    *,
    establishment_id,
    business_unit_id,
) -> BusinessUnit | None:
    return (
        BusinessUnit.objects.filter(
            id=business_unit_id,
            establishment_id=establishment_id,
            active=True,
        )
        .select_related("establishment")
        .first()
    )


def get_active_activity_subject_for_establishment(
    *,
    establishment_id,
    activity_subject_id,
) -> ActivitySubject | None:
    return (
        ActivitySubject.objects.filter(
            id=activity_subject_id,
            establishment_id=establishment_id,
            active=True,
        )
        .select_related("business_unit", "establishment")
        .first()
    )
