from __future__ import annotations

import uuid
from urllib.parse import urlencode

from houston.comments.models import Comment
from houston.notifications.models import Notification

COMMENT_DEEP_LINK_TAB = "comments"
COMMENT_DEEP_LINK_COMMENT_ID_PARAM = "commentId"


def resolve_comment_notification_navigation(comment: Comment) -> dict | None:
    if comment.signal_id is not None:
        return {
            "parent_subject_type": Notification.SubjectType.SIGNAL,
            "parent_subject_id": comment.signal_id,
        }
    if comment.action_plan_execution_id is not None:
        return {
            "parent_subject_type": Notification.SubjectType.ACTION_PLAN_EXECUTION,
            "parent_subject_id": comment.action_plan_execution_id,
        }
    return None


def build_comment_navigation_index(
    *,
    establishment_id: uuid.UUID,
    notifications: list[Notification],
) -> dict[uuid.UUID, dict]:
    comment_ids = [
        notification.subject_id
        for notification in notifications
        if notification.subject_type == Notification.SubjectType.COMMENT
    ]
    if not comment_ids:
        return {}

    comments = Comment.objects.filter(
        id__in=comment_ids,
        establishment_id=establishment_id,
    ).only("id", "signal_id", "action_plan_execution_id")

    index: dict[uuid.UUID, dict] = {}
    for comment in comments:
        navigation = resolve_comment_notification_navigation(comment)
        if navigation is not None:
            index[comment.id] = navigation
    return index


def _build_comment_deep_link_path(parent_path: str, comment_id: uuid.UUID) -> str:
    query = urlencode(
        {
            "tab": COMMENT_DEEP_LINK_TAB,
            COMMENT_DEEP_LINK_COMMENT_ID_PARAM: str(comment_id),
        }
    )
    return f"{parent_path}?{query}"


def _resolve_comment_notification_url(
    *,
    establishment_id: uuid.UUID,
    comment_id: uuid.UUID,
) -> str | None:
    comment = (
        Comment.objects.filter(
            id=comment_id,
            establishment_id=establishment_id,
        )
        .only("id", "signal_id", "action_plan_execution_id")
        .first()
    )
    if comment is None:
        return None

    navigation = resolve_comment_notification_navigation(comment)
    if navigation is None:
        return None

    parent_subject_type = navigation["parent_subject_type"]
    parent_subject_id = navigation["parent_subject_id"]
    if parent_subject_type == Notification.SubjectType.SIGNAL:
        parent_path = f"/signals/{parent_subject_id}"
    elif parent_subject_type == Notification.SubjectType.ACTION_PLAN_EXECUTION:
        parent_path = f"/action-plans/executions/{parent_subject_id}"
    else:
        return None

    return _build_comment_deep_link_path(parent_path, comment_id)


def resolve_notification_url(notification: Notification) -> str | None:
    subject_type = notification.subject_type
    subject_id = notification.subject_id

    if subject_type == Notification.SubjectType.ACTION_PLAN_EXECUTION:
        return f"/action-plans/executions/{subject_id}"

    if subject_type == Notification.SubjectType.SIGNAL:
        return f"/signals/{subject_id}"

    if subject_type == Notification.SubjectType.COMMENT:
        return _resolve_comment_notification_url(
            establishment_id=notification.establishment_id,
            comment_id=subject_id,
        )

    return None
