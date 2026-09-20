from __future__ import annotations

import uuid

from houston.chat.constants import (
    CHAT_GROUP_TITLE_MAX_LENGTH,
    CHAT_MESSAGE_BODY_MAX_LENGTH,
    CHAT_REPLY_EXCERPT_MAX_LENGTH,
)
from houston.chat.models import ChatConversation, ChatMessage, ChatParticipant
from houston.establishments.models import EstablishmentMembership
from rest_framework import serializers


class ChatWsTicketResponseSerializer(serializers.Serializer):
    ticket = serializers.CharField()
    expires_in = serializers.IntegerField()


class ChatStatusSerializer(serializers.Serializer):
    chat_enabled = serializers.BooleanField()
    can_access = serializers.BooleanField()
    can_create_dm = serializers.BooleanField()
    can_create_group = serializers.BooleanField()
    can_manage_settings = serializers.BooleanField()


class ChatMembershipSummarySerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    display_name = serializers.CharField()
    role = serializers.CharField()


class ChatParticipantSummarySerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    display_name = serializers.CharField()
    role = serializers.CharField()
    participant_role = serializers.CharField()


class ChatMessageMentionSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()
    start = serializers.IntegerField(min_value=0)
    end = serializers.IntegerField(min_value=1)
    display_name = serializers.CharField(required=False)


class ChatAttachmentSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField()
    original_filename = serializers.CharField()
    preview_url = serializers.CharField()
    thumbnail_url = serializers.CharField(allow_null=True)
    message_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    author_display_name = serializers.CharField()


class ChatReplyToSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    unavailable = serializers.BooleanField()
    author_display_name = serializers.CharField(required=False, allow_null=True)
    excerpt = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class ChatMessagePreviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    author_membership_id = serializers.UUIDField()
    author_display_name = serializers.CharField()
    body = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    is_reply = serializers.BooleanField(required=False)
    reply_to = ChatReplyToSerializer(allow_null=True, required=False)
    mentions = ChatMessageMentionSerializer(many=True, required=False)
    attachments = ChatAttachmentSerializer(many=True, required=False)


class ChatConversationListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    unread = serializers.BooleanField()
    unread_count = serializers.IntegerField(min_value=0)
    last_message_at = serializers.DateTimeField(allow_null=True)
    last_message_preview = ChatMessagePreviewSerializer(allow_null=True)
    participants = ChatParticipantSummarySerializer(many=True)
    pinned = serializers.BooleanField()
    can_delete = serializers.BooleanField()


class ChatConversationListResponseSerializer(serializers.Serializer):
    items = ChatConversationListItemSerializer(many=True)


class ChatConversationDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    created_at = serializers.DateTimeField()
    last_message_at = serializers.DateTimeField(allow_null=True)
    unread = serializers.BooleanField()
    participants = ChatParticipantSummarySerializer(many=True)
    can_manage = serializers.BooleanField()
    can_delete = serializers.BooleanField()
    pinned = serializers.BooleanField()


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    author_membership_id = serializers.UUIDField()
    author_display_name = serializers.CharField()
    body = serializers.CharField(allow_blank=True)
    client_message_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    is_reply = serializers.BooleanField()
    reply_to = ChatReplyToSerializer(allow_null=True)
    mentions = ChatMessageMentionSerializer(many=True)
    attachments = ChatAttachmentSerializer(many=True)


class ChatSendMessageRequestSerializer(serializers.Serializer):
    client_message_id = serializers.UUIDField()
    body = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=CHAT_MESSAGE_BODY_MAX_LENGTH,
        default="",
    )
    reply_to_id = serializers.UUIDField(required=False, allow_null=True)
    mentions = ChatMessageMentionSerializer(many=True, required=False)
    attachment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
    )

    def validate_mentions(self, value):
        for item in value:
            if item["start"] >= item["end"]:
                raise serializers.ValidationError("Mention start must be less than end.")
        return value


class ChatReserveUploadRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    filename = serializers.CharField(max_length=255)
    content_type = serializers.CharField(max_length=120)
    size_bytes = serializers.IntegerField(min_value=1)


class ChatReserveUploadResponseSerializer(serializers.Serializer):
    upload_id = serializers.UUIDField()
    put_url = serializers.CharField(allow_blank=True)
    expires_at = serializers.DateTimeField()


class ChatUploadCompleteResponseSerializer(serializers.Serializer):
    upload_id = serializers.UUIDField()
    status = serializers.CharField()
    kind = serializers.CharField()
    content_type = serializers.CharField()
    size_bytes = serializers.IntegerField(allow_null=True)


class ChatSharedMediaResponseSerializer(serializers.Serializer):
    items = ChatAttachmentSerializer(many=True)
    has_more = serializers.BooleanField()
    cursor = serializers.CharField(allow_null=True)


class ChatSendMessageResponseSerializer(serializers.Serializer):
    message = ChatMessageSerializer()
    created = serializers.BooleanField()


class ChatMessageListResponseSerializer(serializers.Serializer):
    items = ChatMessageSerializer(many=True)
    has_more = serializers.BooleanField()


class ChatCreateDmRequestSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()


class ChatCreateGroupRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=CHAT_GROUP_TITLE_MAX_LENGTH)
    membership_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )


class ChatRenameGroupRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=CHAT_GROUP_TITLE_MAX_LENGTH)


class ChatAddParticipantRequestSerializer(serializers.Serializer):
    membership_id = serializers.UUIDField()


class ChatSettingsPatchRequestSerializer(serializers.Serializer):
    chat_enabled = serializers.BooleanField()


class ChatCreateConversationResponseSerializer(serializers.Serializer):
    conversation = ChatConversationDetailSerializer()
    created = serializers.BooleanField(required=False)


class ChatEligibleMembershipsResponseSerializer(serializers.Serializer):
    items = ChatMembershipSummarySerializer(many=True)


def membership_display_name(membership: EstablishmentMembership) -> str:
    from houston.accounts.display import DELETED_ACCOUNT_DISPLAY_NAME
    from houston.accounts.models import User

    user = membership.user
    if user.status == User.Status.ANONYMIZED:
        return DELETED_ACCOUNT_DISPLAY_NAME
    full_name = f"{user.first_name} {user.last_name}".strip()
    if full_name:
        return full_name
    if user.username:
        return user.username
    return user.email or str(user.id)


def serialize_membership_summary(membership: EstablishmentMembership) -> dict:
    return {
        "membership_id": membership.id,
        "user_id": membership.user_id,
        "display_name": membership_display_name(membership),
        "role": membership.role,
    }


def serialize_participant_summary(participant: ChatParticipant) -> dict:
    membership = participant.membership
    return {
        "membership_id": membership.id,
        "user_id": membership.user_id,
        "display_name": membership_display_name(membership),
        "role": membership.role,
        "participant_role": participant.role,
    }


def _serialize_reply_to(message: ChatMessage, *, parent: ChatMessage | None) -> dict | None:
    reply_to_id = getattr(message, "reply_to_id", None)
    if reply_to_id is None:
        return None
    if parent is None:
        return {"id": reply_to_id, "unavailable": True}
    excerpt = parent.body[:CHAT_REPLY_EXCERPT_MAX_LENGTH]
    return {
        "id": parent.id,
        "unavailable": False,
        "author_display_name": membership_display_name(parent.author_membership),
        "excerpt": excerpt,
    }


def _serialize_mentions(message: ChatMessage) -> list[dict]:
    mentions = getattr(message, "_prefetched_objects_cache", {}).get("mentions")
    if mentions is None:
        mentions = list(message.mentions.select_related("membership__user").all())
    items = []
    for mention in mentions:
        items.append(
            {
                "membership_id": mention.membership_id,
                "start": mention.start,
                "end": mention.end,
                "display_name": membership_display_name(mention.membership),
            }
        )
    items.sort(key=lambda item: item["start"])
    return items


def serialize_attachment(attachment, *, message: ChatMessage | None = None) -> dict:
    resolved_message = message or attachment.message
    establishment_id = resolved_message.conversation.establishment_id
    thumbnail_key = getattr(attachment.upload, "thumbnail_storage_key", "")
    return {
        "id": attachment.id,
        "kind": attachment.kind,
        "content_type": attachment.content_type,
        "size_bytes": attachment.size_bytes,
        "original_filename": attachment.original_filename,
        "preview_url": (
            f"/api/v1/establishments/{establishment_id}"
            f"/chat/attachments/{attachment.id}/preview/"
        ),
        "thumbnail_url": (
            f"/api/v1/establishments/{establishment_id}"
            f"/chat/attachments/{attachment.id}/preview/?variant=thumbnail"
            if thumbnail_key
            else None
        ),
        "message_id": resolved_message.id,
        "created_at": attachment.created_at,
        "author_display_name": membership_display_name(resolved_message.author_membership),
    }


def _serialize_attachments(message: ChatMessage) -> list[dict]:
    attachments = getattr(message, "_prefetched_objects_cache", {}).get("attachments")
    if attachments is None:
        attachments = list(message.attachments.select_related("upload").all())
    return [
        serialize_attachment(attachment, message=message)
        for attachment in sorted(attachments, key=lambda item: (item.position, item.id))
    ]


def serialize_message(
    message: ChatMessage,
    *,
    parent: ChatMessage | None = None,
    parents_by_id: dict | None = None,
) -> dict:
    reply_to_id = getattr(message, "reply_to_id", None)
    resolved_parent = parent
    if resolved_parent is None and parents_by_id is not None and reply_to_id is not None:
        resolved_parent = parents_by_id.get(reply_to_id)
    elif resolved_parent is None and reply_to_id is not None:
        resolved_parent = (
            ChatMessage.objects.select_related("author_membership", "author_membership__user")
            .filter(id=reply_to_id, conversation_id=message.conversation_id)
            .first()
        )
    return {
        "id": message.id,
        "author_membership_id": message.author_membership_id,
        "author_display_name": membership_display_name(message.author_membership),
        "body": message.body,
        "client_message_id": message.client_message_id,
        "created_at": message.created_at,
        "is_reply": reply_to_id is not None,
        "reply_to": _serialize_reply_to(message, parent=resolved_parent),
        "mentions": _serialize_mentions(message),
        "attachments": _serialize_attachments(message),
    }


def serialize_messages(messages: list[ChatMessage]) -> list[dict]:
    parent_ids = [
        message.reply_to_id for message in messages if getattr(message, "reply_to_id", None)
    ]
    parents_by_id = {}
    if parent_ids:
        parents_by_id = {
            parent.id: parent
            for parent in ChatMessage.objects.filter(id__in=parent_ids).select_related(
                "author_membership",
                "author_membership__user",
            )
        }
    return [serialize_message(message, parents_by_id=parents_by_id) for message in messages]


def conversation_title(
    *,
    conversation: ChatConversation,
    viewer_membership_id: uuid.UUID,
) -> str:
    if conversation.type == ChatConversation.Type.GROUP:
        return conversation.title
    for participant in conversation.participants.all():
        if participant.left_at is not None:
            continue
        if participant.membership_id != viewer_membership_id:
            return membership_display_name(participant.membership)
    return "Direct message"


def serialize_conversation_detail(
    *,
    conversation: ChatConversation,
    viewer_membership_id: uuid.UUID,
    unread: bool,
    can_manage: bool,
    can_delete: bool,
    pinned: bool = False,
    last_message_at=...,
) -> dict:
    active_participants = [
        participant
        for participant in conversation.participants.all()
        if participant.left_at is None
    ]
    resolved_last_message_at = (
        conversation.last_message_at if last_message_at is ... else last_message_at
    )
    return {
        "id": conversation.id,
        "type": conversation.type,
        "title": conversation_title(
            conversation=conversation,
            viewer_membership_id=viewer_membership_id,
        ),
        "created_at": conversation.created_at,
        "last_message_at": resolved_last_message_at,
        "unread": unread,
        "participants": [
            serialize_participant_summary(participant) for participant in active_participants
        ],
        "can_manage": can_manage,
        "can_delete": can_delete,
        "pinned": pinned,
    }
