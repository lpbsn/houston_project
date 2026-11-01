"""Discussion notification modes, resolved once for a whole recipient set.

Silent blocks the discussion, including mentions. Missing chat participation
does not notify. A plan discussion without a saved preference stays on "all".
Signal comments are not plan discussions and stay allowed. Work notifications
never consult this module.
"""

from __future__ import annotations

import uuid

from houston.chat.models import ChatMessage, ChatParticipant
from houston.comments.models import Comment, PlanDiscussionPreference
from houston.establishments.models import EstablishmentMembership

MODE_ALL = "all"
MODE_MENTIONS = "mentions"
MODE_SILENT = "silent"


def _mode_allows(
    mode: str | None, *, membership_id: uuid.UUID, mentioned_ids: set[uuid.UUID]
) -> bool:
    if mode == MODE_ALL:
        return True
    if mode == MODE_MENTIONS:
        return membership_id in mentioned_ids
    return False


def _chat_modes(
    *,
    conversation_id: uuid.UUID,
    membership_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not membership_ids:
        return {}
    return dict(
        ChatParticipant.objects.filter(
            conversation_id=conversation_id,
            membership_id__in=membership_ids,
            left_at__isnull=True,
        ).values_list("membership_id", "notification_mode")
    )


def _chat_mentioned_ids(message: ChatMessage, membership_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not membership_ids:
        return set()
    wanted = set(membership_ids)
    cached = getattr(message, "_prefetched_objects_cache", {}).get("mentions")
    if cached is not None:
        return {mention.membership_id for mention in cached if mention.membership_id in wanted}
    return set(
        message.mentions.filter(membership_id__in=wanted).values_list("membership_id", flat=True)
    )


def filter_chat_message_recipients(
    *,
    message: ChatMessage,
    recipients: list[EstablishmentMembership],
) -> list[EstablishmentMembership]:
    if not recipients:
        return []
    recipient_ids = [recipient.id for recipient in recipients]
    modes = _chat_modes(conversation_id=message.conversation_id, membership_ids=recipient_ids)
    mentioned_ids = _chat_mentioned_ids(
        message,
        [
            membership_id
            for membership_id in recipient_ids
            if modes.get(membership_id) == MODE_MENTIONS
        ],
    )
    return [
        recipient
        for recipient in recipients
        if _mode_allows(
            modes.get(recipient.id), membership_id=recipient.id, mentioned_ids=mentioned_ids
        )
    ]


def chat_message_notification_allowed(*, message: ChatMessage, membership_id: uuid.UUID) -> bool:
    mode = _chat_modes(
        conversation_id=message.conversation_id,
        membership_ids=[membership_id],
    ).get(membership_id)
    if mode != MODE_MENTIONS:
        return _mode_allows(mode, membership_id=membership_id, mentioned_ids=set())
    mentioned_ids = _chat_mentioned_ids(message, [membership_id])
    return _mode_allows(mode, membership_id=membership_id, mentioned_ids=mentioned_ids)


def _comment_mentioned_ids(comment: Comment, membership_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    if not membership_ids:
        return set()
    wanted = set(membership_ids)
    cached = getattr(comment, "_prefetched_objects_cache", {}).get("mention_links")
    if cached is not None:
        return {
            link.mentioned_membership_id
            for link in cached
            if link.mentioned_membership_id in wanted
        }
    return set(
        comment.mention_links.filter(mentioned_membership_id__in=wanted).values_list(
            "mentioned_membership_id",
            flat=True,
        )
    )


def _plan_discussion_modes(
    *,
    execution_id: uuid.UUID,
    membership_ids: list[uuid.UUID],
) -> dict[uuid.UUID, str]:
    if not membership_ids:
        return {}
    return dict(
        PlanDiscussionPreference.objects.filter(
            execution_id=execution_id,
            membership_id__in=membership_ids,
        ).values_list("membership_id", "notification_mode")
    )


def filter_comment_notification_recipients(
    *,
    comment: Comment,
    recipients: list[EstablishmentMembership],
) -> list[EstablishmentMembership]:
    """Plan-discussion filter. Signal comments and unknown comments are not filtered here."""
    if not recipients or comment.action_plan_execution_id is None:
        return list(recipients)
    recipient_ids = [recipient.id for recipient in recipients]
    modes = _plan_discussion_modes(
        execution_id=comment.action_plan_execution_id,
        membership_ids=recipient_ids,
    )
    mentioned_ids = _comment_mentioned_ids(
        comment,
        [
            membership_id
            for membership_id in recipient_ids
            if modes.get(membership_id, MODE_ALL) == MODE_MENTIONS
        ],
    )
    return [
        recipient
        for recipient in recipients
        if _mode_allows(
            modes.get(recipient.id, MODE_ALL),
            membership_id=recipient.id,
            mentioned_ids=mentioned_ids,
        )
    ]


def comment_notification_allowed(*, comment_id: uuid.UUID, membership_id: uuid.UUID) -> bool:
    comment = Comment.objects.filter(id=comment_id).only("id", "action_plan_execution_id").first()
    if comment is None or comment.action_plan_execution_id is None:
        return True
    mode = _plan_discussion_modes(
        execution_id=comment.action_plan_execution_id,
        membership_ids=[membership_id],
    ).get(membership_id, MODE_ALL)
    if mode != MODE_MENTIONS:
        return _mode_allows(mode, membership_id=membership_id, mentioned_ids=set())
    mentioned_ids = _comment_mentioned_ids(comment, [membership_id])
    return _mode_allows(mode, membership_id=membership_id, mentioned_ids=mentioned_ids)
