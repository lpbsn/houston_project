from houston.chat.models import ChatParticipant
from houston.comments.models import Comment, PlanDiscussionPreference


def chat_message_notification_allowed(*, message, membership_id):
    mode = (
        ChatParticipant.objects.filter(
            conversation_id=message.conversation_id,
            membership_id=membership_id,
            left_at__isnull=True,
        )
        .values_list("notification_mode", flat=True)
        .first()
    )
    return mode == "all" or (
        mode == "mentions" and message.mentions.filter(membership_id=membership_id).exists()
    )


def comment_notification_allowed(*, comment_id, membership_id):
    comment = Comment.objects.filter(id=comment_id).first()
    if comment is None or comment.action_plan_execution_id is None:
        return True
    mode = (
        PlanDiscussionPreference.objects.filter(
            execution_id=comment.action_plan_execution_id, membership_id=membership_id
        )
        .values_list("notification_mode", flat=True)
        .first()
        or "all"
    )
    return mode == "all" or (
        mode == "mentions"
        and comment.mention_links.filter(mentioned_membership_id=membership_id).exists()
    )
