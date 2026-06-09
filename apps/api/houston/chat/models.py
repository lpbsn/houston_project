from __future__ import annotations

from django.db import models
from django.db.models import Q
from houston.chat.constants import CHAT_GROUP_TITLE_MAX_LENGTH, CHAT_MESSAGE_BODY_MAX_LENGTH
from houston.core.models import BaseModel


class ChatConversation(BaseModel):
    class Type(models.TextChoices):
        DM = "dm", "Direct message"
        GROUP = "group", "Group"

    establishment = models.ForeignKey(
        "establishments.Establishment",
        on_delete=models.CASCADE,
        related_name="chat_conversations",
    )
    type = models.CharField(max_length=16, choices=Type.choices)
    title = models.CharField(max_length=CHAT_GROUP_TITLE_MAX_LENGTH, blank=True, default="")
    dm_membership_a = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.CASCADE,
        related_name="chat_dm_conversations_a",
        null=True,
        blank=True,
    )
    dm_membership_b = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.CASCADE,
        related_name="chat_dm_conversations_b",
        null=True,
        blank=True,
    )
    created_by_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="chat_conversations_created",
    )
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["establishment", "-last_message_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(type="dm", dm_membership_a__isnull=False, dm_membership_b__isnull=False)
                    | Q(
                        type="group",
                        dm_membership_a__isnull=True,
                        dm_membership_b__isnull=True,
                    )
                ),
                name="chat_conversation_type_membership_shape",
            ),
            models.UniqueConstraint(
                fields=["establishment", "dm_membership_a", "dm_membership_b"],
                condition=Q(type="dm"),
                name="uniq_chat_dm_membership_pair",
            ),
        ]


class ChatParticipant(BaseModel):
    class Role(models.TextChoices):
        MEMBER = "member", "Member"
        ADMIN = "admin", "Admin"

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="participants",
    )
    membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.CASCADE,
        related_name="chat_participants",
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    last_seen_message_id = models.UUIDField(null=True, blank=True)
    last_seen_message_created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["membership", "left_at"]),
            models.Index(fields=["conversation", "left_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "membership"],
                name="uniq_chat_participant_membership",
            ),
        ]


class ChatMessage(BaseModel):
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author_membership = models.ForeignKey(
        "establishments.EstablishmentMembership",
        on_delete=models.PROTECT,
        related_name="chat_messages_authored",
    )
    body = models.TextField(max_length=CHAT_MESSAGE_BODY_MAX_LENGTH)
    client_message_id = models.UUIDField()

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [
            models.Index(fields=["conversation", "created_at", "id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "author_membership", "client_message_id"],
                name="uniq_chat_message_client_id",
            ),
        ]
