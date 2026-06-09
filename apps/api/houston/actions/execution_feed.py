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
from houston.establishments.models import EstablishmentMembership


@dataclass(frozen=True)
class ExecutionFeedPageItem:
    item_type: Literal["action", "checklist"]
    action: object | None = None
    checklist: ChecklistExecution | None = None


def build_execution_feed_page(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
    page_size: int,
) -> tuple[list[ExecutionFeedPageItem], int, bool]:
    ensure_visible_executions_materialized(membership=membership)

    action_qs = execution_feed_queryset(membership=membership, view_mode=view_mode)
    checklist_qs = checklist_execution_feed_queryset(
        membership=membership,
        view_mode=view_mode,
    )

    action_count = action_qs.count()
    checklist_count = checklist_qs.count()
    total_count = action_count + checklist_count

    if checklist_count == 0:
        actions = list(
            apply_execution_feed_sorting(action_qs, membership=membership)[:page_size],
        )
        return (
            [ExecutionFeedPageItem(item_type="action", action=action) for action in actions],
            total_count,
            total_count > page_size,
        )

    checklists = list(apply_checklist_feed_sorting(checklist_qs)[:page_size])
    action_slots = max(0, page_size - len(checklists))
    actions = (
        list(apply_execution_feed_sorting(action_qs, membership=membership)[:action_slots])
        if action_slots
        else []
    )

    items: list[ExecutionFeedPageItem] = [
        ExecutionFeedPageItem(item_type="checklist", checklist=checklist)
        for checklist in checklists
    ]
    items.extend(ExecutionFeedPageItem(item_type="action", action=action) for action in actions)
    return items, total_count, total_count > page_size
