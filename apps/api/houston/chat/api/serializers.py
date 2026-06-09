from __future__ import annotations

import uuid

from houston.chat.constants import (
    CHAT_GROUP_TITLE_MAX_LENGTH,
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


class ChatMessagePreviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    author_membership_id = serializers.UUIDField()
    author_display_name = serializers.CharField()
    body = serializers.CharField()
    created_at = serializers.DateTimeField()


class ChatConversationListItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    type = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    unread = serializers.BooleanField()
    last_message_at = serializers.DateTimeField(allow_null=True)
    last_message_preview = ChatMessagePreviewSerializer(allow_null=True)
    participants = ChatParticipantSummarySerializer(many=True)


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


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    author_membership_id = serializers.UUIDField()
    author_display_name = serializers.CharField()
    body = serializers.CharField()
    client_message_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()


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


class ChatSettingsResponseSerializer(serializers.Serializer):
    chat_enabled = serializers.BooleanField()


class ChatCreateConversationResponseSerializer(serializers.Serializer):
    conversation = ChatConversationDetailSerializer()
    created = serializers.BooleanField(required=False)


class ChatEligibleMembershipsResponseSerializer(serializers.Serializer):
    items = ChatMembershipSummarySerializer(many=True)


def membership_display_name(membership: EstablishmentMembership) -> str:
    user = membership.user
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


def serialize_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "author_membership_id": message.author_membership_id,
        "author_display_name": membership_display_name(message.author_membership),
        "body": message.body,
        "client_message_id": message.client_message_id,
        "created_at": message.created_at,
    }


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
) -> dict:
    active_participants = [
        participant
        for participant in conversation.participants.all()
        if participant.left_at is None
    ]
    return {
        "id": conversation.id,
        "type": conversation.type,
        "title": conversation_title(
            conversation=conversation,
            viewer_membership_id=viewer_membership_id,
        ),
        "created_at": conversation.created_at,
        "last_message_at": conversation.last_message_at,
        "unread": unread,
        "participants": [
            serialize_participant_summary(participant) for participant in active_participants
        ],
        "can_manage": can_manage,
        "can_delete": can_delete,
    }
