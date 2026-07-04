from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from django.db.models import Prefetch, Q, QuerySet

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.selectors import get_action_plan_execution_for_detail
from houston.comments.models import Comment, CommentMention
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.selectors import get_signal_for_detail

_COMMENT_PREFETCH = (
    "author_membership__user",
    "resolved_by_membership__user",
    Prefetch(
        "mention_links",
        queryset=CommentMention.objects.select_related("mentioned_membership__user").order_by(
            "mentioned_membership__user__first_name",
            "mentioned_membership__user__last_name",
            "mentioned_membership__user__username",
            "mentioned_membership_id",
        ),
    ),
    Prefetch(
        "replies",
        queryset=Comment.objects.select_related("author_membership__user")
        .prefetch_related(
            Prefetch(
                "mention_links",
                queryset=CommentMention.objects.select_related(
                    "mentioned_membership__user"
                ).order_by(
                    "mentioned_membership__user__first_name",
                    "mentioned_membership__user__last_name",
                    "mentioned_membership__user__username",
                    "mentioned_membership_id",
                ),
            ),
        )
        .order_by("created_at", "id"),
    ),
)


def _comments_queryset(*, establishment_id: uuid.UUID) -> QuerySet[Comment]:
    return Comment.objects.filter(establishment_id=establishment_id).prefetch_related(
        *_COMMENT_PREFETCH
    )


def get_signal_for_comments(
    *,
    membership: EstablishmentMembership,
    signal_id: uuid.UUID,
) -> Signal | None:
    return get_signal_for_detail(membership=membership, signal_id=signal_id)


def get_action_plan_execution_for_comments(
    *,
    membership: EstablishmentMembership,
    execution_id: uuid.UUID,
) -> ActionPlanExecution | None:
    return get_action_plan_execution_for_detail(
        membership=membership,
        execution_id=execution_id,
    )


def list_signal_comments(
    *,
    signal: Signal,
) -> list[Comment]:
    return list(
        _comments_queryset(establishment_id=signal.establishment_id)
        .filter(signal_id=signal.id, parent_comment_id__isnull=True)
        .order_by("created_at", "id")
    )


@dataclass(frozen=True)
class InheritedSignalCommentEntry:
    kind: Literal["inherited_signal"]
    comment: Comment


@dataclass(frozen=True)
class ExecutionCommentThreadEntry:
    kind: Literal["execution_thread"]
    root: Comment
    replies: list[Comment]


ExecutionCommentListEntry = InheritedSignalCommentEntry | ExecutionCommentThreadEntry


def list_action_plan_execution_comments_for_detail(
    *,
    execution: ActionPlanExecution,
) -> list[ExecutionCommentListEntry]:
    queryset = _comments_queryset(establishment_id=execution.establishment_id)
    if execution.source_signal_id is None:
        scope_q = Q(action_plan_execution_id=execution.id)
    else:
        scope_q = Q(action_plan_execution_id=execution.id) | Q(signal_id=execution.source_signal_id)

    roots = list(
        queryset.filter(scope_q, parent_comment_id__isnull=True).order_by("created_at", "id")
    )

    entries: list[ExecutionCommentListEntry] = []
    for root in roots:
        if root.signal_id is not None:
            entries.append(InheritedSignalCommentEntry(kind="inherited_signal", comment=root))
            continue
        replies = list(root.replies.all())
        entries.append(
            ExecutionCommentThreadEntry(kind="execution_thread", root=root, replies=replies)
        )

    return entries
