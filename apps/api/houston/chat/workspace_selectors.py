"""Bounded communication reads; chat and execution discussion keep their owners."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import datetime

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Exists, OuterRef, Q, QuerySet, Subquery
from houston.accounts.display import membership_display_name
from houston.action_plans.selectors import action_plan_execution_feed_queryset
from houston.chat.selectors import visible_messages
from houston.comments.models import Comment, PlanDiscussionPreference
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import is_valid_membership

PAGE_SIZE = 30
# (establishment, action_plan_execution, created_at, id) — LIMIT 1 per execution.
PLAN_COMMENT_LATEST_INDEX = "comments_co_establi_44e023_idx"


@dataclass(frozen=True)
class CommunicationHit:
    id: uuid.UUID
    kind: str
    parent_id: uuid.UUID
    title: str
    body: str
    author: str
    created_at: datetime
    unresolved: bool
    unread: bool


def visible_plan_comments(*, membership: EstablishmentMembership) -> QuerySet[Comment]:
    if not is_valid_membership(membership):
        return Comment.objects.none()
    visible_executions = action_plan_execution_feed_queryset(
        membership=membership,
        view_mode="general",
    )
    return Comment.objects.filter(
        establishment_id=membership.establishment_id,
        action_plan_execution_id__in=visible_executions.values("id"),
    )


def _before(queryset, cursor):
    if not cursor:
        return queryset
    created_at, item_id = cursor
    return queryset.filter(Q(created_at__lt=created_at) | Q(created_at=created_at, id__lt=item_id))


def _page(rows: list[CommunicationHit]) -> dict:
    has_more = len(rows) > PAGE_SIZE
    page = rows[:PAGE_SIZE]
    last = page[-1] if page else None
    cursor = f"{last.created_at.isoformat()}|{last.id}" if has_more and last is not None else None
    return {"items": [asdict(row) for row in page], "cursor": cursor}


def _chat_hit(message) -> CommunicationHit:
    return CommunicationHit(
        id=message.id,
        kind="chat",
        parent_id=message.conversation_id,
        title=message.conversation.title or "Message direct",
        body=message.body,
        author=membership_display_name(message.author_membership),
        created_at=message.created_at,
        unresolved=False,
        unread=False,
    )


def _plan_hit(comment, *, unread: bool) -> CommunicationHit:
    return CommunicationHit(
        id=comment.id,
        kind="plan",
        parent_id=comment.action_plan_execution_id,
        title=comment.action_plan_execution.title,
        body=comment.body,
        author=membership_display_name(comment.author_membership),
        created_at=comment.created_at,
        unresolved=comment.parent_comment_id is None and comment.resolved_at is None,
        unread=unread,
    )


def _needs_distinct(*, mentions: bool, files_only: bool) -> bool:
    return mentions or files_only


def _bounded_page(queryset, cursor, *, distinct: bool):
    bounded = _before(queryset, cursor)
    if distinct:
        bounded = bounded.distinct()
    return bounded.order_by("-created_at", "-id")[: PAGE_SIZE + 1]


def communication_search(
    *,
    membership,
    query="",
    mentions=False,
    cursor=None,
    author_id=None,
    after=None,
    before=None,
    files_only=False,
    execution_id=None,
):
    chat = visible_messages(membership=membership)
    comments = visible_plan_comments(membership=membership)
    if execution_id:
        chat = chat.none()
        comments = comments.filter(action_plan_execution_id=execution_id)
    if mentions:
        chat = chat.filter(mentions__membership=membership)
        comments = comments.filter(mention_links__mentioned_membership=membership)
    if query:
        # Same expression as the GIN indexes chat_message_search_idx and comment_search_idx.
        search = SearchQuery(query, config="french", search_type="plain")
        chat = chat.annotate(search=SearchVector("body", config="french")).filter(search=search)
        comments = comments.annotate(search=SearchVector("body", config="french")).filter(
            search=search
        )
    if author_id:
        chat = chat.filter(author_membership_id=author_id)
        comments = comments.filter(author_membership_id=author_id)
    if after:
        chat = chat.filter(created_at__gte=after)
        comments = comments.filter(created_at__gte=after)
    if before:
        chat = chat.filter(created_at__lt=before)
        comments = comments.filter(created_at__lt=before)
    if files_only:
        chat = chat.filter(attachments__isnull=False)
        comments = comments.filter(plan_comment_attachments__isnull=False)
    distinct = _needs_distinct(mentions=mentions, files_only=files_only)
    chat_rows = _bounded_page(
        chat.select_related("conversation", "author_membership__user"),
        cursor,
        distinct=distinct,
    )
    comment_rows = _bounded_page(
        comments.select_related("action_plan_execution", "author_membership__user"),
        cursor,
        distinct=distinct,
    )
    hits = [_chat_hit(message) for message in chat_rows]
    hits.extend(_plan_hit(comment, unread=False) for comment in comment_rows)
    hits.sort(key=lambda hit: (hit.created_at, hit.id), reverse=True)
    return _page(hits)


def latest_plan_comment_queryset(*, membership: EstablishmentMembership, unresolved: bool = False):
    """Latest visible comment per execution.

    The correlated LIMIT 1 matches PLAN_COMMENT_LATEST_INDEX:
    establishment, execution, then created_at/id descending.
    """
    if not is_valid_membership(membership):
        return Comment.objects.none().values("id")
    visible_executions = action_plan_execution_feed_queryset(
        membership=membership,
        view_mode="general",
    )
    latest_comment = Comment.objects.filter(
        establishment_id=membership.establishment_id,
        action_plan_execution_id=OuterRef("pk"),
    )
    if unresolved:
        latest_comment = latest_comment.filter(
            parent_comment__isnull=True,
            resolved_at__isnull=True,
        )
    latest_comment = latest_comment.order_by("-created_at", "-id")
    return (
        visible_executions.annotate(latest_comment_id=Subquery(latest_comment.values("id")[:1]))
        .exclude(latest_comment_id__isnull=True)
        .values("latest_comment_id")
    )


def plan_discussions(*, membership, cursor=None, unresolved=False):
    if not is_valid_membership(membership):
        return _page([])
    seen = PlanDiscussionPreference.objects.filter(
        execution_id=OuterRef("action_plan_execution_id"),
        membership=membership,
        seen_at__gte=OuterRef("created_at"),
    )
    comments = (
        Comment.objects.filter(
            id__in=latest_plan_comment_queryset(membership=membership, unresolved=unresolved)
        )
        .annotate(was_seen=Exists(seen))
        .select_related("action_plan_execution", "author_membership__user")
    )
    comments = _before(comments, cursor).order_by("-created_at", "-id")[: PAGE_SIZE + 1]
    return _page(
        [
            _plan_hit(
                comment,
                unread=not comment.was_seen and comment.author_membership_id != membership.id,
            )
            for comment in comments
        ]
    )
