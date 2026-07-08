from __future__ import annotations

import uuid

from houston.action_plans.permissions import action_plan_execution_visible_to_membership
from houston.action_plans.selectors import get_action_plan_execution_for_detail
from houston.chat.permissions import can_access_chat
from houston.chat.selectors import get_conversation_for_participant
from houston.comments.models import Comment
from houston.comments.selectors import (
    get_action_plan_execution_for_comments,
    get_signal_for_comments,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import is_valid_membership
from houston.notifications.models import Notification


def notification_visible_to_membership(
    notification: Notification,
    membership: EstablishmentMembership | None,
) -> bool:
    if not is_valid_membership(membership):
        return False
    if notification.establishment_id != membership.establishment_id:
        return False
    return notification.recipient_membership_id == membership.id


def recipient_can_view_notification_subject(
    *,
    recipient: EstablishmentMembership,
    establishment_id: uuid.UUID,
    subject_type: str,
    subject_id: uuid.UUID,
) -> bool:
    if not is_valid_membership(recipient):
        return False
    if recipient.establishment_id != establishment_id:
        return False

    if subject_type == Notification.SubjectType.ACTION_PLAN_EXECUTION:
        execution = get_action_plan_execution_for_detail(
            membership=recipient,
            execution_id=subject_id,
        )
        if execution is None:
            return False
        return action_plan_execution_visible_to_membership(recipient, execution)

    if subject_type == Notification.SubjectType.COMMENT:
        comment = Comment.objects.filter(
            id=subject_id,
            establishment_id=establishment_id,
        ).first()
        if comment is None:
            return False
        if comment.signal_id is not None:
            return (
                get_signal_for_comments(
                    membership=recipient,
                    signal_id=comment.signal_id,
                )
                is not None
            )
        if comment.action_plan_execution_id is not None:
            return (
                get_action_plan_execution_for_comments(
                    membership=recipient,
                    execution_id=comment.action_plan_execution_id,
                )
                is not None
            )
        return False

    if subject_type == Notification.SubjectType.SIGNAL:
        from houston.signals.selectors import get_signal_for_detail

        return get_signal_for_detail(membership=recipient, signal_id=subject_id) is not None

    if subject_type == Notification.SubjectType.CHAT_CONVERSATION:
        if not can_access_chat(recipient):
            return False
        return (
            get_conversation_for_participant(
                establishment_id=establishment_id,
                conversation_id=subject_id,
                membership_id=recipient.id,
            )
            is not None
        )

    return False
