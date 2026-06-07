from __future__ import annotations

from houston.accounts.models import User, UserSession
from houston.establishments.membership_scope import (
    membership_scope_prefetch,
    membership_scope_rows_for_membership,
)
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
    OnboardingSession,
)
from houston.organizations.models import Organization

_ONBOARDING_CONTINUE_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
    }
)


def list_active_memberships(user: User) -> list[EstablishmentMembership]:
    return list(_active_membership_queryset(user))


def list_bootstrap_memberships(user: User) -> list[dict]:
    memberships = list_active_memberships(user)
    return [_serialize_membership(membership) for membership in memberships]


def build_bootstrap_payload(
    user: User,
    *,
    session: UserSession,
    autoselect_single_membership: bool = False,
) -> dict:
    memberships, active_membership = resolve_active_membership(
        user=user,
        session=session,
        autoselect_single_membership=autoselect_single_membership,
    )

    pending_onboarding_memberships = list_pending_onboarding_memberships(user)

    return {
        "authenticated": True,
        "user": _serialize_user(user),
        "memberships": [_serialize_membership(membership) for membership in memberships],
        "active_membership": (
            None if active_membership is None else _serialize_membership(active_membership)
        ),
        "pending_onboarding_memberships": pending_onboarding_memberships,
    }


def resolve_active_membership(
    *,
    user: User,
    session: UserSession,
    autoselect_single_membership: bool = False,
) -> tuple[list[EstablishmentMembership], EstablishmentMembership | None]:
    memberships = list_active_memberships(user)
    memberships_by_establishment_id = {
        membership.establishment_id: membership for membership in memberships
    }

    selected_membership = None
    selected_establishment_id = session.selected_establishment_id

    if selected_establishment_id is not None:
        selected_membership = memberships_by_establishment_id.get(selected_establishment_id)

        if selected_membership is None:
            _update_selected_establishment(session=session, establishment=None)

    if (
        selected_membership is None
        and session.selected_establishment_id is None
        and autoselect_single_membership
        and len(memberships) == 1
    ):
        selected_membership = memberships[0]
        _update_selected_establishment(
            session=session,
            establishment=selected_membership.establishment,
        )

    return memberships, selected_membership


def list_pending_onboarding_memberships(user: User) -> list[dict]:
    if user.status != User.Status.ACTIVE:
        return []

    memberships = (
        EstablishmentMembership.objects.filter(
            user=user,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.DRAFT,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("establishment", "establishment__organization")
        .order_by("establishment__name", "establishment_id")
    )

    establishment_ids = [membership.establishment_id for membership in memberships]
    sessions_by_establishment_id = _latest_non_terminal_onboarding_sessions_by_establishment(
        establishment_ids,
    )

    return [
        _serialize_pending_onboarding_membership(
            membership,
            onboarding_session=sessions_by_establishment_id.get(membership.establishment_id),
        )
        for membership in memberships
    ]


def _latest_non_terminal_onboarding_sessions_by_establishment(
    establishment_ids: list,
) -> dict:
    if not establishment_ids:
        return {}

    sessions = (
        OnboardingSession.objects.filter(
            establishment_id__in=establishment_ids,
            status__in=OnboardingSession.NON_TERMINAL_STATUSES,
        )
        .order_by("establishment_id", "-created_at")
    )

    sessions_by_establishment_id: dict = {}
    for session in sessions:
        if session.establishment_id not in sessions_by_establishment_id:
            sessions_by_establishment_id[session.establishment_id] = session

    return sessions_by_establishment_id


def _serialize_pending_onboarding_membership(
    membership: EstablishmentMembership,
    *,
    onboarding_session: OnboardingSession | None,
) -> dict:
    establishment = membership.establishment
    return {
        "id": str(membership.id),
        "establishment_id": str(membership.establishment_id),
        "establishment_name": establishment.name,
        "establishment_status": establishment.status,
        "role": membership.role,
        "onboarding_session_id": (
            None if onboarding_session is None else str(onboarding_session.id)
        ),
        "can_continue_onboarding": membership.role in _ONBOARDING_CONTINUE_ROLES,
    }


def _active_membership_queryset(user: User):
    return (
        EstablishmentMembership.objects.filter(
            user=user,
            status=EstablishmentMembership.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch())
        .order_by("establishment__name", "establishment_id")
    )


def _serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "identity_type": user.identity_type,
    }


def _serialize_membership(membership: EstablishmentMembership) -> dict:
    return {
        "id": str(membership.id),
        "establishment_id": str(membership.establishment_id),
        "establishment_name": membership.establishment.name,
        "organization_id": str(membership.establishment.organization_id),
        "organization_name": membership.establishment.organization.name,
        "role": membership.role,
        "status": membership.status,
        **dict(
            zip(
                ("scopes", "scope_summary"),
                membership_scope_rows_for_membership(membership),
                strict=True,
            )
        ),
    }


def _update_selected_establishment(
    *,
    session: UserSession,
    establishment: Establishment | None,
) -> None:
    next_establishment_id = None if establishment is None else establishment.id

    if session.selected_establishment_id == next_establishment_id:
        return

    session.selected_establishment = establishment
    session.save(update_fields=["selected_establishment", "updated_at"])
