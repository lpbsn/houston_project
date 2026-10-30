"""Bounded communication reads; chat and execution discussion keep their owners."""

from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Exists, OuterRef, Q, Subquery
from houston.accounts.display import membership_display_name
from houston.action_plans.selectors import action_plan_execution_feed_queryset
from houston.chat.selectors import visible_messages
from houston.comments.models import Comment, PlanDiscussionPreference
from houston.establishments.permissions import is_valid_membership

PAGE_SIZE = 30


def visible_plan_comments(*, membership):
    if not is_valid_membership(membership):
        return Comment.objects.none()
    visible = action_plan_execution_feed_queryset(membership=membership, view_mode="general")
    return Comment.objects.filter(
        establishment_id=membership.establishment_id,
        action_plan_execution_id__in=visible.values("id"),
    )


def _before(qs, cursor):
    if cursor:
        at, key = cursor
        return qs.filter(Q(created_at__lt=at) | Q(created_at=at, id__lt=key))
    return qs


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
    chat = (
        _before(chat, cursor)
        .select_related("conversation", "author_membership__user")
        .distinct()
        .order_by("-created_at", "-id")[: PAGE_SIZE + 1]
    )
    comments = (
        _before(comments, cursor)
        .select_related("action_plan_execution", "author_membership__user")
        .distinct()
        .order_by("-created_at", "-id")[: PAGE_SIZE + 1]
    )
    rows = [
        dict(
            id=m.id,
            kind="chat",
            parent_id=m.conversation_id,
            title=m.conversation.title or "Message direct",
            body=m.body,
            author=membership_display_name(m.author_membership),
            created_at=m.created_at,
            unresolved=False,
            unread=False,
        )
        for m in chat
    ]
    rows += [
        dict(
            id=c.id,
            kind="plan",
            parent_id=c.action_plan_execution_id,
            title=c.action_plan_execution.title,
            body=c.body,
            author=membership_display_name(c.author_membership),
            created_at=c.created_at,
            unresolved=c.parent_comment_id is None and c.resolved_at is None,
            unread=False,
        )
        for c in comments
    ]
    rows.sort(key=lambda x: (x["created_at"], x["id"]), reverse=True)
    return _page(rows)


def _page(rows):
    has_more = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE]
    last = rows[-1] if rows else None
    return dict(
        items=rows, cursor=f"{last['created_at'].isoformat()}|{last['id']}" if has_more else None
    )


def plan_discussions(*, membership, cursor=None, unresolved=False):
    comments = visible_plan_comments(membership=membership)
    if unresolved:
        comments = comments.filter(parent_comment__isnull=True, resolved_at__isnull=True)
    # One last message per plan, restricted before pagination, not one query per plan.
    latest = Comment.objects.filter(
        action_plan_execution_id=OuterRef("action_plan_execution_id")
    ).order_by("-created_at", "-id")
    if unresolved:
        latest = latest.filter(parent_comment__isnull=True, resolved_at__isnull=True)
    seen = PlanDiscussionPreference.objects.filter(
        execution_id=OuterRef("action_plan_execution_id"),
        membership=membership,
        seen_at__gte=OuterRef("created_at"),
    )
    comments = comments.filter(id=Subquery(latest.values("id")[:1])).annotate(was_seen=Exists(seen))
    comments = (
        _before(comments, cursor)
        .select_related("action_plan_execution", "author_membership__user")
        .order_by("-created_at", "-id")[: PAGE_SIZE + 1]
    )
    return _page(
        [
            dict(
                id=c.id,
                kind="plan",
                parent_id=c.action_plan_execution_id,
                title=c.action_plan_execution.title,
                body=c.body,
                author=membership_display_name(c.author_membership),
                created_at=c.created_at,
                unresolved=c.parent_comment_id is None and c.resolved_at is None,
                unread=not c.was_seen and c.author_membership_id != membership.id,
            )
            for c in comments
        ]
    )
