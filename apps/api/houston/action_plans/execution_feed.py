from __future__ import annotations

from houston.action_plans.constants import ExecutionFeedViewMode
from houston.action_plans.feed_cursor import (
    ActionPlanExecutionFeedCursor,
    apply_action_plan_execution_feed_cursor,
    encode_action_plan_execution_feed_cursor,
)
from houston.action_plans.materialization import (
    ensure_visible_action_plan_executions_materialized,
)
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import (
    action_plan_execution_feed_queryset,
    apply_action_plan_execution_feed_sorting,
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
) -> tuple[list[ActionPlanExecution], bool, str | None]:
    membership = _membership_for_action_plan_execution_feed(membership)
    ensure_visible_action_plan_executions_materialized(
        membership=membership,
        view_mode=view_mode,
    )
    queryset = action_plan_execution_feed_queryset(
        membership=membership,
        view_mode=view_mode,
    )
    if cursor is not None:
        sorted_qs = apply_action_plan_execution_feed_cursor(queryset, cursor)
    else:
        sorted_qs = apply_action_plan_execution_feed_sorting(queryset)

    candidates = list(sorted_qs[: page_size + 1])
    has_more = len(candidates) > page_size
    served = candidates[:page_size]
    next_cursor = None
    if has_more and served:
        next_cursor = encode_action_plan_execution_feed_cursor(served[-1])
    return served, has_more, next_cursor
