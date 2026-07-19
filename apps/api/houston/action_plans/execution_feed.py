from __future__ import annotations

from datetime import datetime

from django.utils import timezone

from houston.action_plans.constants import ExecutionFeedViewMode
from houston.action_plans.feed_cursor import (
    ActionPlanExecutionFeedCursor,
    apply_action_plan_execution_feed_cursor,
    encode_action_plan_execution_feed_cursor,
)
from houston.action_plans.lifecycle_promotion import ensure_execution_lifecycle_for_read
from houston.action_plans.materialization import (
    ensure_visible_action_plan_executions_materialized,
)
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import (
    action_plan_execution_feed_queryset,
    apply_action_plan_execution_feed_sorting,
    scheduled_executions_base_queryset,
    scheduled_executions_visible_preview_queryset,
)
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES


def _membership_for_action_plan_execution_feed(
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


def build_action_plan_execution_feed_page(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
    page_size: int,
    cursor: ActionPlanExecutionFeedCursor | None = None,
) -> tuple[
    list[ActionPlanExecution],
    bool,
    str | None,
    datetime,
    list[ActionPlanExecution],
    int,
]:
    membership = _membership_for_action_plan_execution_feed(membership)
    ensure_visible_action_plan_executions_materialized(
        membership=membership,
        view_mode=view_mode,
    )
    ensure_execution_lifecycle_for_read(establishment_id=membership.establishment_id)

    queryset = action_plan_execution_feed_queryset(
        membership=membership,
        view_mode=view_mode,
    )
    if cursor is not None:
        as_of = cursor.as_of
        sorted_qs = apply_action_plan_execution_feed_cursor(
            queryset,
            cursor,
            membership=membership,
        )
    else:
        as_of = timezone.now()
        sorted_qs = apply_action_plan_execution_feed_sorting(
            queryset,
            membership=membership,
            as_of=as_of,
        )

    candidates = list(sorted_qs[: page_size + 1])
    has_more = len(candidates) > page_size
    served = candidates[:page_size]
    next_cursor = None
    if has_more and served:
        next_cursor = encode_action_plan_execution_feed_cursor(served[-1], as_of=as_of)

    scheduled_count = scheduled_executions_base_queryset(
        membership=membership,
        view_mode=view_mode,
    ).count()
    if scheduled_count == 0:
        scheduled_items: list[ActionPlanExecution] = []
    else:
        scheduled_items = list(
            scheduled_executions_visible_preview_queryset(
                membership=membership,
                view_mode=view_mode,
            )
        )
    return served, has_more, next_cursor, as_of, scheduled_items, scheduled_count
