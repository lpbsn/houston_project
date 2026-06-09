from __future__ import annotations

import uuid

from django.db.models import Q, QuerySet
from houston.accounts.models import User
from houston.chat.models import ChatConversation, ChatMessage, ChatParticipant
from houston.establishments.models import (
    Establishment,
    EstablishmentMembership,
)
from houston.organizations.models import Organization


def canonical_dm_membership_pair(
    first: EstablishmentMembership,
    second: EstablishmentMembership,
) -> tuple[EstablishmentMembership, EstablishmentMembership]:
    if first.id < second.id:
        return first, second
    return second, first


def get_eligible_chat_memberships_queryset(
    *,
    establishment_id: uuid.UUID,
    query: str | None = None,
) -> QuerySet[EstablishmentMembership]:
    queryset = (
        EstablishmentMembership.objects.filter(
            establishment_id=establishment_id,
            status=EstablishmentMembership.Status.ACTIVE,
            user__status=User.Status.ACTIVE,
            establishment__status=Establishment.Status.ACTIVE,
            establishment__organization__status=Organization.Status.ACTIVE,
        )
        .select_related("user", "establishment", "establishment__organization")
        .order_by("user__first_name", "user__last_name", "user__username", "id")
    )
    if not query:
        return queryset

    normalized = query.strip()
    if not normalized:
        return queryset

    return queryset.filter(
        Q(user__first_name__icontains=normalized)
        | Q(user__last_name__icontains=normalized)
        | Q(user__username__icontains=normalized)
        | Q(user__email__icontains=normalized)
    )


def active_participant_queryset(
    *,
    conversation_id: uuid.UUID,
) -> QuerySet[ChatParticipant]:
    return ChatParticipant.objects.filter(
        conversation_id=conversation_id,
        left_at__isnull=True,
    ).select_related("membership", "membership__user")


def get_active_participant(
    *,
    conversation_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> ChatParticipant | None:
    return (
        active_participant_queryset(conversation_id=conversation_id)
        .filter(membership_id=membership_id)
        .first()
    )


def get_conversation_for_participant(
    *,
    establishment_id: uuid.UUID,
    conversation_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> ChatConversation | None:
    return (
        ChatConversation.objects.filter(
            id=conversation_id,
            establishment_id=establishment_id,
            deleted_at__isnull=True,
            participants__membership_id=membership_id,
            participants__left_at__isnull=True,
        )
        .select_related("establishment", "created_by_membership", "created_by_membership__user")
        .prefetch_related(
            "participants__membership__user",
        )
        .distinct()
        .first()
    )


def list_conversations_for_membership(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> QuerySet[ChatConversation]:
    return (
        ChatConversation.objects.filter(
            establishment_id=establishment_id,
            deleted_at__isnull=True,
            participants__membership_id=membership_id,
            participants__left_at__isnull=True,
        )
        .select_related("created_by_membership", "created_by_membership__user")
        .prefetch_related("participants__membership__user")
        .distinct()
        .order_by("-last_message_at", "-created_at")
    )


def get_latest_message(conversation_id: uuid.UUID) -> ChatMessage | None:
    return (
        ChatMessage.objects.filter(conversation_id=conversation_id)
        .select_related("author_membership", "author_membership__user")
        .order_by("-created_at", "-id")
        .first()
    )


def list_messages_for_conversation(
    *,
    conversation_id: uuid.UUID,
    limit: int,
    before_created_at=None,
    before_id: uuid.UUID | None = None,
) -> list[ChatMessage]:
    queryset = ChatMessage.objects.filter(conversation_id=conversation_id).select_related(
        "author_membership",
        "author_membership__user",
    )
    if before_created_at is not None and before_id is not None:
        queryset = queryset.filter(
            Q(created_at__lt=before_created_at) | Q(created_at=before_created_at, id__lt=before_id)
        )
    return list(queryset.order_by("-created_at", "-id")[:limit])


def is_conversation_unread(
    *,
    participant: ChatParticipant,
    latest_message: ChatMessage | None,
) -> bool:
    if latest_message is None:
        return False
    if latest_message.author_membership_id == participant.membership_id:
        return False
    if participant.last_seen_message_id is None or participant.last_seen_message_created_at is None:
        return True
    if latest_message.created_at > participant.last_seen_message_created_at:
        return True
    if latest_message.created_at < participant.last_seen_message_created_at:
        return False
    return str(latest_message.id) > str(participant.last_seen_message_id)


def find_existing_dm_conversation(
    *,
    establishment_id: uuid.UUID,
    membership_a_id: uuid.UUID,
    membership_b_id: uuid.UUID,
) -> ChatConversation | None:
    first_id, second_id = sorted((membership_a_id, membership_b_id))
    return ChatConversation.objects.filter(
        establishment_id=establishment_id,
        type=ChatConversation.Type.DM,
        deleted_at__isnull=True,
        dm_membership_a_id=first_id,
        dm_membership_b_id=second_id,
    ).first()
