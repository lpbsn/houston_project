from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from houston.actions.selectors import (
    ExecutionFeedViewMode,
    apply_execution_feed_sorting,
    execution_feed_queryset,
)
from houston.checklists.materialization import ensure_visible_executions_materialized
from houston.checklists.models import ChecklistExecution
from houston.checklists.selectors import (
    apply_checklist_feed_sorting,
    checklist_execution_feed_queryset,
)
from houston.establishments.membership_scope import membership_scope_prefetch
from houston.establishments.models import EstablishmentMembership
from houston.establishments.role_constants import _ADMIN_ROLES


@dataclass(frozen=True)
class ExecutionFeedPageItem:
    item_type: Literal["action", "checklist"]
    action: object | None = None
    checklist: ChecklistExecution | None = None


def _membership_for_execution_feed(
    membership: EstablishmentMembership,
) -> EstablishmentMembership:
    if membership.role in _ADMIN_ROLES:
        return membership
    return (
        EstablishmentMembership.objects.filter(pk=membership.pk)
        .select_related("establishment")
        .prefetch_related(membership_scope_prefetch())
        .get()
    )


def build_execution_feed_page(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
    page_size: int,
) -> tuple[list[ExecutionFeedPageItem], bool]:
    membership = _membership_for_execution_feed(membership)
    ensure_visible_executions_materialized(
        membership=membership,
        view_mode=view_mode,
    )

    action_qs = execution_feed_queryset(membership=membership, view_mode=view_mode)
    checklist_qs = checklist_execution_feed_queryset(
        membership=membership,
        view_mode=view_mode,
    )

    checklist_candidates = list(apply_checklist_feed_sorting(checklist_qs)[: page_size + 1])
    checklist_count = len(checklist_candidates)

    if checklist_count == 0:
        action_candidates = list(
            apply_execution_feed_sorting(action_qs, membership=membership)[: page_size + 1],
        )
        has_more = len(action_candidates) > page_size
        return (
            [
                ExecutionFeedPageItem(item_type="action", action=action)
                for action in action_candidates[:page_size]
            ],
            has_more,
        )

    if checklist_count > page_size:
        has_more = checklist_count > page_size or action_qs.exists()
        return (
            [
                ExecutionFeedPageItem(item_type="checklist", checklist=checklist)
                for checklist in checklist_candidates[:page_size]
            ],
            has_more,
        )

    checklists = checklist_candidates
    action_slots = page_size - len(checklists)
    action_candidates = list(
        apply_execution_feed_sorting(action_qs, membership=membership)[: action_slots + 1],
    )
    has_more = len(action_candidates) > action_slots

    items: list[ExecutionFeedPageItem] = [
        ExecutionFeedPageItem(item_type="checklist", checklist=checklist)
        for checklist in checklists
    ]
    items.extend(
        ExecutionFeedPageItem(item_type="action", action=action)
        for action in action_candidates[:action_slots]
    )
    return items, has_more
