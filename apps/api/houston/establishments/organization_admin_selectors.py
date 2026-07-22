"""Read selectors for organization-scoped admin APIs (Lot C).

No session / selected_establishment dependency. Callers must authorize via
``resolve_manageable_organization`` before invoking these helpers.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from django.db.models import Count, Q

from houston.accounts.models import User
from houston.establishments.membership_scope import (
    membership_scope_prefetch,
    membership_scope_rows_for_membership,
)
from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentInvitation,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.organizations.models import Organization

_DRAFT_ACTIVE = (
    Establishment.Status.DRAFT,
    Establishment.Status.ACTIVE,
)

_OWNER_ROSTER_STATUSES = (
    EstablishmentMembership.Status.ACTIVE,
    EstablishmentMembership.Status.INVITED,
)

_DIRECTOR_LIST_STATUSES = (
    EstablishmentMembership.Status.ACTIVE,
    EstablishmentMembership.Status.INVITED,
)

ORGANIZATION_ADMIN_MEMBER_ROLES = [
    EstablishmentMembership.Role.OWNER,
    EstablishmentMembership.Role.DIRECTOR,
    EstablishmentMembership.Role.MANAGER,
    EstablishmentMembership.Role.STAFF,
]

ORGANIZATION_ADMIN_MEMBER_STATUSES = [
    EstablishmentMembership.Status.INVITED,
    EstablishmentMembership.Status.ACTIVE,
    EstablishmentMembership.Status.DEACTIVATED,
]


def get_organization_admin_overview(*, organization: Organization) -> dict[str, Any]:
    establishments = Establishment.objects.filter(
        organization_id=organization.id,
        status__in=_DRAFT_ACTIVE,
    )
    active_count = establishments.filter(status=Establishment.Status.ACTIVE).count()
    draft_count = establishments.filter(status=Establishment.Status.DRAFT).count()
    return {
        "id": organization.id,
        "name": organization.name,
        "status": organization.status,
        "active_establishment_count": active_count,
        "draft_establishment_count": draft_count,
    }


def list_organization_admin_establishments(
    *,
    organization: Organization,
    actor: User,
) -> list[dict[str, Any]]:
    establishments = list(
        Establishment.objects.filter(
            organization_id=organization.id,
            status__in=_DRAFT_ACTIVE,
        ).order_by("name", "id")
    )
    if not establishments:
        return []

    establishment_ids = [row.id for row in establishments]

    directors_by_establishment: dict[Any, list[EstablishmentMembership]] = defaultdict(list)
    director_qs = (
        EstablishmentMembership.objects.filter(
            establishment_id__in=establishment_ids,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=_DIRECTOR_LIST_STATUSES,
        )
        .select_related("user")
        .order_by("establishment_id", "created_at", "id")
    )
    for membership in director_qs:
        directors_by_establishment[membership.establishment_id].append(membership)

    active_counts = {
        row["establishment_id"]: row["count"]
        for row in (
            EstablishmentMembership.objects.filter(
                establishment_id__in=establishment_ids,
                status=EstablishmentMembership.Status.ACTIVE,
            )
            .values("establishment_id")
            .annotate(count=Count("id"))
        )
    }

    bu_counts = {
        row["establishment_id"]: row["count"]
        for row in (
            BusinessUnit.objects.filter(
                establishment_id__in=establishment_ids,
                active=True,
            )
            .values("establishment_id")
            .annotate(count=Count("id"))
        )
    }

    sessions_by_establishment = _latest_non_terminal_onboarding_sessions(establishment_ids)

    actor_owner_establishment_ids = set(
        EstablishmentMembership.objects.filter(
            user_id=actor.id,
            establishment_id__in=establishment_ids,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        ).values_list("establishment_id", flat=True)
    )

    results: list[dict[str, Any]] = []
    for establishment in establishments:
        item: dict[str, Any] = {
            "id": establishment.id,
            "name": establishment.name,
            "status": establishment.status,
            "directors": [
                _serialize_director(membership)
                for membership in directors_by_establishment.get(establishment.id, [])
            ],
            "active_member_count": active_counts.get(establishment.id, 0),
            "business_unit_count": bu_counts.get(establishment.id, 0),
            "onboarding_session_id": None,
            "onboarding_current_step": "",
            "can_continue_onboarding": False,
        }
        if establishment.status == Establishment.Status.DRAFT:
            session = sessions_by_establishment.get(establishment.id)
            item["onboarding_session_id"] = None if session is None else session.id
            item["onboarding_current_step"] = (
                "" if session is None else (session.current_step or "")
            )
            item["can_continue_onboarding"] = (
                establishment.id in actor_owner_establishment_ids
            )
        results.append(item)
    return results


def list_organization_admin_members(
    *,
    organization: Organization,
    q: str | None = None,
    establishment_id: UUID | None = None,
    business_unit_id: UUID | None = None,
    role: str | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    memberships_qs = (
        EstablishmentMembership.objects.filter(
            establishment__organization_id=organization.id,
            establishment__status__in=_DRAFT_ACTIVE,
        )
        .select_related("user", "establishment")
        .prefetch_related(membership_scope_prefetch())
        .order_by(
            "user__last_name",
            "user__first_name",
            "user__email",
            "user_id",
            "establishment__name",
            "establishment_id",
            "id",
        )
    )

    if establishment_id is not None:
        memberships_qs = memberships_qs.filter(establishment_id=establishment_id)
    if role is not None:
        memberships_qs = memberships_qs.filter(role=role)
    if status is not None:
        memberships_qs = memberships_qs.filter(status=status)
    if business_unit_id is not None:
        memberships_qs = memberships_qs.filter(
            scope_links__business_unit_id=business_unit_id,
        ).distinct()
    if q:
        normalized = q.strip()
        if normalized:
            memberships_qs = memberships_qs.filter(
                Q(user__first_name__icontains=normalized)
                | Q(user__last_name__icontains=normalized)
                | Q(user__email__icontains=normalized)
                | Q(user__username__icontains=normalized)
            )

    # When filtering by role/status/establishment/BU/q, still return the user's
    # full membership set within the org ACTIVE|DRAFT perimeter (deduped users
    # who match the filter on at least one membership).
    matching_user_ids = list(
        memberships_qs.values_list("user_id", flat=True).distinct()
    )
    if not matching_user_ids:
        return []

    all_memberships = (
        EstablishmentMembership.objects.filter(
            user_id__in=matching_user_ids,
            establishment__organization_id=organization.id,
            establishment__status__in=_DRAFT_ACTIVE,
        )
        .select_related("user", "establishment")
        .prefetch_related(membership_scope_prefetch())
        .order_by(
            "user__last_name",
            "user__first_name",
            "user__email",
            "user_id",
            "establishment__name",
            "establishment_id",
            "id",
        )
    )

    by_user: dict[Any, dict[str, Any]] = {}
    for membership in all_memberships:
        user = membership.user
        entry = by_user.get(user.id)
        if entry is None:
            entry = {
                "user_id": user.id,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "email": user.email,
                "memberships": [],
            }
            by_user[user.id] = entry
        entry["memberships"].append(_serialize_member_membership(membership))

    return list(by_user.values())


def get_organization_admin_member_filter_options(
    *,
    organization: Organization,
) -> dict[str, Any]:
    establishments = list(
        Establishment.objects.filter(
            organization_id=organization.id,
            status__in=_DRAFT_ACTIVE,
        )
        .order_by("name", "id")
        .values("id", "name", "status")
    )
    establishment_ids = [row["id"] for row in establishments]
    business_units = list(
        BusinessUnit.objects.filter(
            establishment_id__in=establishment_ids,
            active=True,
        )
        .order_by("establishment_id", "specific_name", "id")
        .values("id", "specific_name", "establishment_id")
    )
    return {
        "establishments": [
            {
                "id": row["id"],
                "name": row["name"],
                "status": row["status"],
            }
            for row in establishments
        ],
        "business_units": [
            {
                "id": row["id"],
                "label": row["specific_name"],
                "establishment_id": row["establishment_id"],
            }
            for row in business_units
        ],
        "roles": list(ORGANIZATION_ADMIN_MEMBER_ROLES),
        "statuses": list(ORGANIZATION_ADMIN_MEMBER_STATUSES),
    }


def list_organization_admin_owners(
    *,
    organization: Organization,
) -> list[dict[str, Any]]:
    memberships = list(
        EstablishmentMembership.objects.filter(
            establishment__organization_id=organization.id,
            establishment__status__in=_DRAFT_ACTIVE,
            role=EstablishmentMembership.Role.OWNER,
            status__in=_OWNER_ROSTER_STATUSES,
        )
        .select_related("user")
        .order_by("user__last_name", "user__first_name", "user__email", "user_id", "id")
    )
    if not memberships:
        return []

    by_user: dict[Any, list[EstablishmentMembership]] = defaultdict(list)
    for membership in memberships:
        by_user[membership.user_id].append(membership)

    user_ids = list(by_user.keys())
    invited_membership_ids = [
        membership.id
        for rows in by_user.values()
        for membership in rows
        if membership.status == EstablishmentMembership.Status.INVITED
    ]
    live_invitations: dict[Any, EstablishmentInvitation] = {}
    for invitation in EstablishmentInvitation.objects.filter(
        membership_id__in=invited_membership_ids,
        accepted_at__isnull=True,
        revoked_at__isnull=True,
    ).order_by("membership_id", "-created_at"):
        if invitation.membership_id not in live_invitations:
            live_invitations[invitation.membership_id] = invitation

    results: list[dict[str, Any]] = []
    for user_id in user_ids:
        rows = by_user[user_id]
        user = rows[0].user
        has_active = any(
            membership.status == EstablishmentMembership.Status.ACTIVE for membership in rows
        )
        status = (
            EstablishmentMembership.Status.ACTIVE
            if has_active
            else EstablishmentMembership.Status.INVITED
        )
        invited_at = None
        if status == EstablishmentMembership.Status.INVITED:
            # Deterministic: earliest live invitation among invited memberships.
            invitation_dates = []
            for membership in rows:
                invitation = live_invitations.get(membership.id)
                if invitation is not None:
                    invitation_dates.append(invitation.created_at)
            if invitation_dates:
                invited_at = min(invitation_dates)

        can_resend = (
            status == EstablishmentMembership.Status.INVITED
            and user.status == User.Status.PENDING
        )
        results.append(
            {
                "user_id": user.id,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "email": user.email,
                "status": status,
                "invited_at": invited_at,
                "can_resend_invitation": can_resend,
            }
        )

    results.sort(
        key=lambda row: (
            row["last_name"].lower(),
            row["first_name"].lower(),
            row["email"].lower(),
            str(row["user_id"]),
        )
    )
    return results


def _latest_non_terminal_onboarding_sessions(
    establishment_ids: list,
) -> dict[Any, OnboardingSession]:
    if not establishment_ids:
        return {}

    sessions = OnboardingSession.objects.filter(
        establishment_id__in=establishment_ids,
        status__in=OnboardingSession.NON_TERMINAL_STATUSES,
    ).order_by("establishment_id", "-created_at")

    sessions_by_establishment: dict[Any, OnboardingSession] = {}
    for session in sessions:
        if session.establishment_id not in sessions_by_establishment:
            sessions_by_establishment[session.establishment_id] = session
    return sessions_by_establishment


def _serialize_director(membership: EstablishmentMembership) -> dict[str, Any]:
    user = membership.user
    display_name = user.get_full_name().strip() or user.username or user.email
    return {
        "membership_id": membership.id,
        "display_name": display_name,
        "email": user.email,
        "status": membership.status,
    }


def _serialize_member_membership(membership: EstablishmentMembership) -> dict[str, Any]:
    scopes_payload, _ = membership_scope_rows_for_membership(membership)
    business_units = [
        {"id": row["scope_id"], "label": row["scope_label"]}
        for row in scopes_payload
    ]

    return {
        "membership_id": membership.id,
        "establishment_id": membership.establishment_id,
        "establishment_name": membership.establishment.name,
        "establishment_status": membership.establishment.status,
        "role": membership.role,
        "status": membership.status,
        "business_units": business_units,
    }
