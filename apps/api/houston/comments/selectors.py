from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

from django.db.models import Prefetch, Q, QuerySet

from houston.actions.models import Action
from houston.actions.permissions import action_visible_to_membership
from houston.actions.selectors import actions_for_establishment
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


def get_action_for_comments(
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


def list_signal_comments(
    *,
    signal: Signal,
) -> list[Comment]:
    return list(
        _comments_queryset(establishment_id=signal.establishment_id)
        .filter(signal_id=signal.id, parent_comment_id__isnull=True)
        .order_by("created_at", "id")
    )


def list_action_comments(
    *,
    action: Action,
) -> list[Comment]:
    queryset = _comments_queryset(establishment_id=action.establishment_id)
    if action.signal_id is None:
        filter_q = Q(action_id=action.id)
    else:
        filter_q = Q(action_id=action.id) | Q(signal_id=action.signal_id)
    return list(
        queryset.filter(filter_q, parent_comment_id__isnull=True).order_by("created_at", "id")
    )


@dataclass(frozen=True)
class InheritedSignalCommentEntry:
    kind: Literal["inherited_signal"]
    comment: Comment


@dataclass(frozen=True)
class ActionCommentThreadEntry:
    kind: Literal["action_thread"]
    root: Comment
    replies: list[Comment]


ActionCommentListEntry = InheritedSignalCommentEntry | ActionCommentThreadEntry


def list_action_comments_for_detail(
    *,
    action: Action,
) -> list[ActionCommentListEntry]:
    queryset = _comments_queryset(establishment_id=action.establishment_id)
    if action.signal_id is None:
        scope_q = Q(action_id=action.id)
    else:
        scope_q = Q(action_id=action.id) | Q(signal_id=action.signal_id)

    roots = list(
        queryset.filter(scope_q, parent_comment_id__isnull=True).order_by("created_at", "id")
    )

    entries: list[ActionCommentListEntry] = []
    for root in roots:
        if root.signal_id is not None:
            entries.append(InheritedSignalCommentEntry(kind="inherited_signal", comment=root))
            continue
        replies = list(root.replies.all())
        entries.append(
            ActionCommentThreadEntry(kind="action_thread", root=root, replies=replies)
        )

    return entries
