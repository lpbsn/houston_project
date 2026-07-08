from __future__ import annotations

import uuid

from houston.comments.models import Comment
from houston.notifications.models import Notification


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
