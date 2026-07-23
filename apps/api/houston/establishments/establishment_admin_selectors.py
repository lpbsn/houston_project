"""Read selectors for ACTIVE establishment admin APIs (Lot D).

Path-scoped via ``EstablishmentAdminActor``. No session / selected_establishment
dependency. Callers must authorize and enforce ACTIVE before invoking.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from django.db.models import Count, Q
from django.utils import timezone

from houston.action_plans.constants import (
    ACTIVE_EXECUTION_STATUSES,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.models import ActionPlanExecution
from houston.establishments.admin_serialization import serialize_admin_director
from houston.establishments.membership_scope import (
    membership_scope_prefetch,
    membership_scope_rows_for_membership,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.establishments.permission_hints import build_membership_permission_hints
from houston.establishments.permissions import EstablishmentAdminActor
from houston.observations.models import Observation
from houston.signals.models import Signal

_DIRECTOR_LIST_STATUSES = (
    EstablishmentMembership.Status.ACTIVE,
    EstablishmentMembership.Status.INVITED,
)

ESTABLISHMENT_ADMIN_MEMBER_ROLES = [
    EstablishmentMembership.Role.DIRECTOR,
    EstablishmentMembership.Role.MANAGER,
    EstablishmentMembership.Role.STAFF,
]

ESTABLISHMENT_ADMIN_MEMBER_STATUSES = [
    EstablishmentMembership.Status.INVITED,
    EstablishmentMembership.Status.ACTIVE,
    EstablishmentMembership.Status.DEACTIVATED,
]

OPERATIONAL_CONFIG_STATUS_CONFIGURED = "configured"
OPERATIONAL_CONFIG_STATUS_NEEDS_ATTENTION = "needs_attention"

OBSERVATION_WEEKLY_AVERAGE_WEEKS = 8


def _utc_week_start(moment=None):
    """Monday 00:00:00 UTC of the calendar week containing ``moment``."""
    now = moment or timezone.now()
    now_utc = now.astimezone(dt_timezone.utc)
    monday = now_utc.date() - timedelta(days=now_utc.weekday())
    return datetime(
        monday.year,
        monday.month,
        monday.day,
        tzinfo=dt_timezone.utc,
    )


def observation_weekly_average_window(*, moment=None) -> tuple[Any, Any]:
    """Eight complete UTC calendar weeks preceding the current week."""
    window_end = _utc_week_start(moment)
    window_start = window_end - timedelta(weeks=OBSERVATION_WEEKLY_AVERAGE_WEEKS)
    return window_start, window_end


def _round_one_decimal(value: float) -> float:
    return float(
        Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    )


def _operational_config_counts(*, establishment_id) -> dict[str, int]:
    active_business_unit_count = BusinessUnit.objects.filter(
        establishment_id=establishment_id,
        active=True,
    ).count()
    active_activity_subject_count = ActivitySubject.objects.filter(
        establishment_id=establishment_id,
        active=True,
    ).count()
    active_business_units_without_subjects_count = (
        BusinessUnit.objects.filter(
            establishment_id=establishment_id,
            active=True,
        )
        .annotate(
            active_subject_count=Count(
                "activity_subjects",
                filter=Q(activity_subjects__active=True),
            )
        )
        .filter(active_subject_count=0)
        .count()
    )
    return {
        "active_business_unit_count": active_business_unit_count,
        "active_activity_subject_count": active_activity_subject_count,
        "active_business_units_without_subjects_count": (
            active_business_units_without_subjects_count
        ),
    }


def derive_operational_config_status(*, counts: dict[str, int]) -> str:
    if (
        counts["active_business_unit_count"] >= 1
        and counts["active_business_units_without_subjects_count"] == 0
    ):
        return OPERATIONAL_CONFIG_STATUS_CONFIGURED
    return OPERATIONAL_CONFIG_STATUS_NEEDS_ATTENTION


def _establishment_admin_metrics(*, establishment_id, moment=None) -> dict[str, Any]:
    signal_counts = Signal.objects.filter(establishment_id=establishment_id).aggregate(
        signals_open=Count("id", filter=Q(status=Signal.Status.OPEN)),
        signals_in_progress=Count("id", filter=Q(status=Signal.Status.IN_PROGRESS)),
    )
    execution_counts = ActionPlanExecution.objects.filter(
        establishment_id=establishment_id,
    ).aggregate(
        action_plans_in_progress=Count(
            "id",
            filter=Q(status__in=ACTIVE_EXECUTION_STATUSES),
        ),
        action_plans_scheduled=Count(
            "id",
            filter=Q(status=EXECUTION_STATUS_SCHEDULED),
        ),
    )
    window_start, window_end = observation_weekly_average_window(moment=moment)
    observation_count = Observation.objects.filter(
        establishment_id=establishment_id,
        origin=Observation.Origin.DIRECT_REPORT,
        submitted_at__gte=window_start,
        submitted_at__lt=window_end,
    ).count()
    return {
        "signals_open": signal_counts["signals_open"] or 0,
        "signals_in_progress": signal_counts["signals_in_progress"] or 0,
        "action_plans_in_progress": execution_counts["action_plans_in_progress"] or 0,
        "action_plans_scheduled": execution_counts["action_plans_scheduled"] or 0,
        "observations_weekly_average": _round_one_decimal(
            observation_count / OBSERVATION_WEEKLY_AVERAGE_WEEKS
        ),
    }


def get_establishment_admin_overview(
    *,
    establishment: Establishment,
    moment=None,
) -> dict[str, Any]:
    directors = list(
        EstablishmentMembership.objects.filter(
            establishment_id=establishment.id,
            role=EstablishmentMembership.Role.DIRECTOR,
            status__in=_DIRECTOR_LIST_STATUSES,
        )
        .select_related("user")
        .order_by("created_at", "id")
    )
    active_member_count = EstablishmentMembership.objects.filter(
        establishment_id=establishment.id,
        status=EstablishmentMembership.Status.ACTIVE,
    ).count()
    config_counts = _operational_config_counts(establishment_id=establishment.id)
    return {
        "id": establishment.id,
        "name": establishment.name,
        "status": establishment.status,
        "organization_id": establishment.organization_id,
        "organization_name": establishment.organization.name,
        "directors": [serialize_admin_director(membership) for membership in directors],
        "active_member_count": active_member_count,
        "business_unit_count": config_counts["active_business_unit_count"],
        "metrics": _establishment_admin_metrics(
            establishment_id=establishment.id,
            moment=moment,
        ),
        "operational_config": {
            "status": derive_operational_config_status(counts=config_counts),
            **config_counts,
        },
    }


def list_establishment_admin_memberships(
    *,
    actor: EstablishmentAdminActor,
    q: str | None = None,
    role: str | None = None,
    status: str | None = None,
    business_unit_id: UUID | None = None,
) -> list[dict[str, Any]]:
    establishment_id = actor.establishment.id
    queryset = (
        EstablishmentMembership.objects.filter(establishment_id=establishment_id)
        .exclude(role=EstablishmentMembership.Role.OWNER)
        .select_related("user", "establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch(), "invitations")
        .order_by("user__last_name", "user__first_name", "user__email", "id")
    )

    if q:
        query = q.strip()
        if query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__email__icontains=query)
            )

    if role is not None:
        queryset = queryset.filter(role=role)
    if status is not None:
        queryset = queryset.filter(status=status)
    if business_unit_id is not None:
        queryset = queryset.filter(
            scope_links__business_unit_id=business_unit_id,
        ).distinct()

    management_membership = _management_actor_membership(actor)
    return [
        _serialize_admin_membership(
            membership,
            actor_membership=management_membership,
            path_admin_same_org_owner=actor.via_organization_owner
            and management_membership.establishment_id != establishment_id,
        )
        for membership in queryset
    ]


def get_establishment_admin_membership(
    *,
    actor: EstablishmentAdminActor,
    membership_id,
) -> dict[str, Any] | None:
    membership = (
        EstablishmentMembership.objects.filter(
            id=membership_id,
            establishment_id=actor.establishment.id,
        )
        .exclude(role=EstablishmentMembership.Role.OWNER)
        .select_related("user", "establishment", "establishment__organization")
        .prefetch_related(membership_scope_prefetch(), "invitations")
        .first()
    )
    if membership is None:
        return None

    management_membership = _management_actor_membership(actor)
    return _serialize_admin_membership(
        membership,
        actor_membership=management_membership,
        path_admin_same_org_owner=actor.via_organization_owner
        and management_membership.establishment_id != actor.establishment.id,
    )


def get_establishment_admin_member_filter_options(
    *,
    establishment: Establishment,
) -> dict[str, Any]:
    business_units = list(
        BusinessUnit.objects.filter(
            establishment_id=establishment.id,
            active=True,
        )
        .order_by("specific_name", "id")
        .values("id", "specific_name")
    )
    return {
        "roles": list(ESTABLISHMENT_ADMIN_MEMBER_ROLES),
        "statuses": list(ESTABLISHMENT_ADMIN_MEMBER_STATUSES),
        "business_units": [
            {"id": row["id"], "label": row["specific_name"]} for row in business_units
        ],
    }


def resolve_management_membership_for_admin(
    actor: EstablishmentAdminActor,
) -> EstablishmentMembership:
    # Org-owner path is authoritative: never downgrade to a local Director row.
    if actor.via_organization_owner:
        if (
            actor.membership.role == EstablishmentMembership.Role.OWNER
            and actor.membership.establishment_id == actor.establishment.id
        ):
            return actor.membership
        local_owner = (
            EstablishmentMembership.objects.filter(
                user_id=actor.user.id,
                establishment_id=actor.establishment.id,
                status=EstablishmentMembership.Status.ACTIVE,
                role=EstablishmentMembership.Role.OWNER,
            )
            .order_by("created_at", "id")
            .first()
        )
        if local_owner is not None:
            return local_owner
        return actor.membership

    return actor.membership


def _management_actor_membership(actor: EstablishmentAdminActor) -> EstablishmentMembership:
    return resolve_management_membership_for_admin(actor)


def _invitation_dates(membership: EstablishmentMembership) -> tuple[Any, Any]:
    invited_at = None
    activated_at = None
    invitations = list(membership.invitations.all())
    live = [
        invitation
        for invitation in invitations
        if invitation.accepted_at is None and invitation.revoked_at is None
    ]
    accepted = [invitation for invitation in invitations if invitation.accepted_at is not None]

    if membership.status == EstablishmentMembership.Status.INVITED and live:
        invited_at = min(invitation.created_at for invitation in live)
    if membership.status == EstablishmentMembership.Status.ACTIVE:
        if accepted:
            activated_at = max(invitation.accepted_at for invitation in accepted)
        else:
            activated_at = membership.created_at
    return invited_at, activated_at


def _serialize_admin_membership(
    membership: EstablishmentMembership,
    *,
    actor_membership: EstablishmentMembership,
    path_admin_same_org_owner: bool,
) -> dict[str, Any]:
    scopes_payload, _ = membership_scope_rows_for_membership(membership)
    business_units = [
        {"id": row["scope_id"], "label": row["scope_label"]} for row in scopes_payload
    ]
    invited_at, activated_at = _invitation_dates(membership)
    user = membership.user

    if path_admin_same_org_owner:
        from houston.establishments.services import can_actor_manage_target_membership

        can_manage = can_actor_manage_target_membership(
            actor_membership=actor_membership,
            target_membership=membership,
            path_admin_same_org_owner=True,
        )
        permission_hints = {
            "can_edit_role": can_manage,
            "can_edit_scopes": can_manage
            and membership.role
            in {
                EstablishmentMembership.Role.STAFF,
                EstablishmentMembership.Role.MANAGER,
            },
            "can_edit_status": can_manage
            and membership.status != EstablishmentMembership.Status.INVITED,
            "can_edit_personal_info": actor_membership.user_id == membership.user_id,
        }
    else:
        permission_hints = build_membership_permission_hints(
            actor_membership=actor_membership,
            target_membership=membership,
        )

    return {
        "id": membership.id,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "email": user.email,
        "role": membership.role,
        "status": membership.status,
        "business_units": business_units,
        "invited_at": invited_at,
        "activated_at": activated_at,
        "permission_hints": permission_hints,
    }
