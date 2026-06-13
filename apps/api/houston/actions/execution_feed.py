from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.db.models import QuerySet
from django.utils import timezone

from houston.actions.execution_feed_cursor import (
    ExecutionFeedCursor,
    apply_action_feed_cursor,
    apply_checklist_feed_cursor,
    encode_action_cursor,
    encode_action_phase_start,
    encode_checklist_cursor,
)
from houston.actions.models import Action
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


def _checklist_items(checklists: list[ChecklistExecution]) -> list[ExecutionFeedPageItem]:
    return [
        ExecutionFeedPageItem(item_type="checklist", checklist=checklist)
        for checklist in checklists
    ]


def _action_items(actions: list[Action]) -> list[ExecutionFeedPageItem]:
    return [ExecutionFeedPageItem(item_type="action", action=action) for action in actions]



def _build_mixed_page(
    *,
    checklists: list[ChecklistExecution],
    action_qs: QuerySet[Action],
    membership: EstablishmentMembership,
    page_size: int,
    as_of,
) -> tuple[list[ExecutionFeedPageItem], bool, str | None]:
    action_slots = page_size - len(checklists)
    action_candidates = list(
        apply_execution_feed_sorting(action_qs, membership=membership, as_of=as_of)[
            : action_slots + 1
        ],
    )
    has_more = len(action_candidates) > action_slots
    served_actions = action_candidates[:action_slots]
    items = _checklist_items(checklists) + _action_items(served_actions)
    next_cursor = None
    if has_more and served_actions:
        next_cursor = encode_action_cursor(
            served_actions[-1],
            membership=membership,
            as_of=as_of,
        )
    return items, has_more, next_cursor


def _build_action_only_page(
    *,
    action_qs: QuerySet[Action],
    membership: EstablishmentMembership,
    page_size: int,
    as_of,
    cursor: ExecutionFeedCursor | None = None,
) -> tuple[list[ExecutionFeedPageItem], bool, str | None]:
    if cursor is not None:
        sorted_qs = apply_action_feed_cursor(action_qs, cursor, membership=membership)
    else:
        sorted_qs = apply_execution_feed_sorting(
            action_qs,
            membership=membership,
            as_of=as_of,
        )
    action_candidates = list(sorted_qs[: page_size + 1])
    has_more = len(action_candidates) > page_size
    served_actions = action_candidates[:page_size]
    next_cursor = None
    if has_more and served_actions:
        next_cursor = encode_action_cursor(
            served_actions[-1],
            membership=membership,
            as_of=as_of,
        )
    return _action_items(served_actions), has_more, next_cursor


def _build_from_checklist_cursor(
    *,
    checklist_qs: QuerySet[ChecklistExecution],
    action_qs: QuerySet[Action],
    membership: EstablishmentMembership,
    page_size: int,
    cursor: ExecutionFeedCursor,
) -> tuple[list[ExecutionFeedPageItem], bool, str | None]:
    as_of = timezone.now()
    sorted_checklists = apply_checklist_feed_cursor(
        apply_checklist_feed_sorting(checklist_qs),
        cursor,
    )
    checklist_candidates = list(sorted_checklists[: page_size + 1])
    checklist_count = len(checklist_candidates)

    if checklist_count > page_size:
        served_checklists = checklist_candidates[:page_size]
        has_more = True
        next_cursor = encode_checklist_cursor(served_checklists[-1])
        return _checklist_items(served_checklists), has_more, next_cursor

    if checklist_count == page_size and action_qs.exists():
        served_checklists = checklist_candidates[:page_size]
        return (
            _checklist_items(served_checklists),
            True,
            encode_action_phase_start(as_of=as_of),
        )

    return _build_mixed_page(
        checklists=checklist_candidates,
        action_qs=action_qs,
        membership=membership,
        page_size=page_size,
        as_of=as_of,
    )


def _build_initial_page(
    *,
    checklist_qs: QuerySet[ChecklistExecution],
    action_qs: QuerySet[Action],
    membership: EstablishmentMembership,
    page_size: int,
) -> tuple[list[ExecutionFeedPageItem], bool, str | None]:
    as_of = timezone.now()
    checklist_candidates = list(
        apply_checklist_feed_sorting(checklist_qs)[: page_size + 1],
    )
    checklist_count = len(checklist_candidates)

    if checklist_count == 0:
        return _build_action_only_page(
            action_qs=action_qs,
            membership=membership,
            page_size=page_size,
            as_of=as_of,
        )

    if checklist_count > page_size:
        served_checklists = checklist_candidates[:page_size]
        has_more = checklist_count > page_size or action_qs.exists()
        next_cursor = encode_checklist_cursor(served_checklists[-1])
        return _checklist_items(served_checklists), has_more, next_cursor

    if checklist_count == page_size and action_qs.exists():
        served_checklists = checklist_candidates[:page_size]
        return (
            _checklist_items(served_checklists),
            True,
            encode_action_phase_start(as_of=as_of),
        )

    return _build_mixed_page(
        checklists=checklist_candidates,
        action_qs=action_qs,
        membership=membership,
        page_size=page_size,
        as_of=as_of,
    )


def build_execution_feed_page(
    *,
    membership: EstablishmentMembership,
    view_mode: ExecutionFeedViewMode,
    page_size: int,
    cursor: ExecutionFeedCursor | None = None,
) -> tuple[list[ExecutionFeedPageItem], bool, str | None]:
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

    if cursor is None:
        return _build_initial_page(
            checklist_qs=checklist_qs,
            action_qs=action_qs,
            membership=membership,
            page_size=page_size,
        )

    if cursor.phase == "checklist":
        return _build_from_checklist_cursor(
            checklist_qs=checklist_qs,
            action_qs=action_qs,
            membership=membership,
            page_size=page_size,
            cursor=cursor,
        )

    if cursor.as_of is None:
        return [], False, None

    return _build_action_only_page(
        action_qs=action_qs,
        membership=membership,
        page_size=page_size,
        as_of=cursor.as_of,
        cursor=cursor,
    )
