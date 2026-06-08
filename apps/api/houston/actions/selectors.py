from __future__ import annotations

import uuid
from typing import Literal

from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.utils import timezone

from houston.actions.constants import EXECUTION_FEED_STATUSES
from houston.actions.models import Action
from houston.actions.permissions import action_visible_to_membership
from houston.establishments.membership_scope import build_action_visibility_scope_q
from houston.establishments.models import EstablishmentMembership

ExecutionFeedViewMode = Literal["personal", "general"]

_ACTION_LIST_SELECT_RELATED = (
    "affected_business_unit",
    "responsible_business_unit",
    "activity_subject",
    "created_by__user",
    "assigned_to__user",
    "signal",
    "signal__affected_business_unit",
    "signal__responsible_business_unit",
    "signal__activity_subject",
)


def actions_for_establishment(*, establishment_id: uuid.UUID) -> QuerySet[Action]:
    return Action.objects.filter(establishment_id=establishment_id).select_related(
        *_ACTION_LIST_SELECT_RELATED
    )


def action_personal_feed_q(*, membership: EstablishmentMembership) -> Q:
    return (
        Q(created_by_id=membership.id) | Q(assigned_to_id=membership.id)
    ) & Q(establishment_id=membership.establishment_id)


def action_general_feed_visibility_q(*, membership: EstablishmentMembership) -> Q:
    if membership.role in {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }:
        return Q(establishment_id=membership.establishment_id)

    personal_q = Q(created_by_id=membership.id) | Q(assigned_to_id=membership.id)

    if membership.role == EstablishmentMembership.Role.STAFF:
        return personal_q & Q(establishment_id=membership.establishment_id)

    scope_q = build_action_visibility_scope_q(membership=membership)
    if scope_q is None:
        return personal_q & Q(establishment_id=membership.establishment_id)
    return (personal_q | scope_q) & Q(establishment_id=membership.establishment_id)


def execution_feed_queryset(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
) -> QuerySet[Action]:
    visibility_q = (
        action_personal_feed_q(membership=membership)
        if view_mode == "personal"
        else action_general_feed_visibility_q(membership=membership)
    )
    return actions_for_establishment(
        establishment_id=membership.establishment_id,
    ).filter(
        visibility_q,
        status__in=EXECUTION_FEED_STATUSES,
    )


def apply_execution_feed_sorting(
    queryset: QuerySet[Action],
    *,
    membership: EstablishmentMembership,
) -> QuerySet[Action]:
    now = timezone.now()
    is_overdue = Case(
        When(
            due_at__lt=now,
            status__in=[
                Action.Status.OPEN,
                Action.Status.IN_PROGRESS,
                Action.Status.PENDING_VALIDATION,
                Action.Status.REOPENED,
            ],
            then=Value(1),
        ),
        default=Value(0),
        output_field=IntegerField(),
    )
    requires_me_rank = Case(
        When(
            assigned_to_id=membership.id,
            status__in=[Action.Status.OPEN, Action.Status.REOPENED, Action.Status.IN_PROGRESS],
            then=Value(0),
        ),
        When(
            created_by_id=membership.id,
            status=Action.Status.PENDING_VALIDATION,
            then=Value(1),
        ),
        default=Value(2),
        output_field=IntegerField(),
    )
    status_rank = Case(
        When(status=Action.Status.OPEN, then=Value(0)),
        When(status=Action.Status.REOPENED, then=Value(1)),
        When(status=Action.Status.IN_PROGRESS, then=Value(2)),
        When(status=Action.Status.PENDING_VALIDATION, then=Value(3)),
        default=Value(4),
        output_field=IntegerField(),
    )
    return queryset.annotate(
        is_overdue_rank=is_overdue,
        requires_me_rank=requires_me_rank,
        status_rank=status_rank,
    ).order_by(
        "-is_overdue_rank",
        "requires_me_rank",
        "status_rank",
        "due_at",
        "-last_activity_at",
        "-created_at",
    )


def get_action_for_detail(
    *,
    membership: EstablishmentMembership,
    action_id: uuid.UUID,
) -> Action | None:
    action = (
        actions_for_establishment(establishment_id=membership.establishment_id)
        .filter(id=action_id)
        .first()
    )
    if action is None:
        return None
    if not action_visible_to_membership(membership, action):
        return None
    return action
