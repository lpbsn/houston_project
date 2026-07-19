from __future__ import annotations

from datetime import datetime
from uuid import UUID

from django.db.models import Q

from houston.action_plans.constants import ExecutionFeedViewMode
from houston.action_plans.lifecycle_promotion import ensure_execution_lifecycle_for_read
from houston.action_plans.materialization import (
    ensure_visible_action_plan_executions_materialized,
)
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import scheduled_executions_upcoming_queryset
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES


def _membership_for_upcoming_feed(
    membership: EstablishmentMembership,
) -> EstablishmentMembership:
    if membership.role in ADMIN_ROLES:
        return membership
    return (
        EstablishmentMembership.objects.filter(pk=membership.pk)
        .select_related("establishment")
        .prefetch_related(membership_scope_prefetch())
        .get()
    )


def build_action_plan_execution_upcoming_page(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
    page_size: int,
    cursor_start_at: datetime | None = None,
    cursor_id: UUID | None = None,
) -> tuple[list[ActionPlanExecution], bool, datetime | None, UUID | None]:
    membership = _membership_for_upcoming_feed(membership)
    ensure_visible_action_plan_executions_materialized(
        membership=membership,
        view_mode=view_mode,
    )
    ensure_execution_lifecycle_for_read(establishment_id=membership.establishment_id)

    queryset = scheduled_executions_upcoming_queryset(
        membership=membership,
        view_mode=view_mode,
    )
    if cursor_start_at is not None and cursor_id is not None:
        queryset = queryset.filter(
            Q(start_at__gt=cursor_start_at) | Q(start_at=cursor_start_at, id__gt=cursor_id),
        )

    candidates = list(queryset[: page_size + 1])
    has_more = len(candidates) > page_size
    served = candidates[:page_size]
    next_start_at = None
    next_id = None
    if has_more and served:
        next_start_at = served[-1].start_at
        next_id = served[-1].id
    return served, has_more, next_start_at, next_id
