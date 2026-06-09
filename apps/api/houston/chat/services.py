from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from houston.chat.exceptions import ChatNotFoundError, ChatPermissionError, ChatValidationError
from houston.chat.models import ChatConversation, ChatMessage, ChatParticipant
from houston.chat.permissions import (
    can_access_chat,
    can_create_dm,
    can_create_group,
    can_delete_group,
    can_manage_establishment_chat_settings,
    can_manage_group,
    can_send_message,
)
from houston.chat.selectors import (
    active_participant_queryset,
    canonical_dm_membership_pair,
    find_existing_dm_conversation,
    get_active_participant,
    get_conversation_for_participant,
    get_latest_message,
)
from houston.establishments.models import Establishment, EstablishmentMembership
from houston.establishments.permissions import _ADMIN_ROLES, _is_valid_membership

from .constants import CHAT_GROUP_TITLE_MAX_LENGTH, CHAT_MESSAGE_BODY_MAX_LENGTH
from .ws_notify import (
    schedule_conversation_access_revoked,
    schedule_conversation_access_revoked_for_memberships,
)


@dataclass(frozen=True)
class MessageSendResult:
    message: ChatMessage
    created: bool
    recipient_membership_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class ChatStatus:
    chat_enabled: bool
    can_access: bool
    can_create_dm: bool
    can_create_group: bool
    can_manage_settings: bool


def build_chat_status(*, membership: EstablishmentMembership | None) -> ChatStatus:
    from houston.chat.permissions import can_create_dm as perm_create_dm
    from houston.chat.permissions import can_create_group as perm_create_group

    chat_enabled = bool(membership and membership.establishment.chat_enabled)
    can_access = perm_create_dm(membership) if membership else False
    return ChatStatus(
        chat_enabled=chat_enabled,
        can_access=can_access,
        can_create_dm=perm_create_dm(membership) if membership else False,
        can_create_group=perm_create_group(membership) if membership else False,
        can_manage_settings=can_manage_establishment_chat_settings(membership),
    )


def _active_participant_membership_ids(*, conversation_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        active_participant_queryset(conversation_id=conversation_id).values_list(
            "membership_id",
            flat=True,
        )
    )


def _ensure_group_has_admin(*, conversation: ChatConversation) -> None:
    if conversation.type != ChatConversation.Type.GROUP:
        return

    active_participants = list(
        active_participant_queryset(conversation_id=conversation.id).select_related("membership")
    )
    if not active_participants:
        return
    if any(participant.role == ChatParticipant.Role.ADMIN for participant in active_participants):
        return

    for participant in active_participants:
        if participant.membership.role in _ADMIN_ROLES:
            participant.role = ChatParticipant.Role.ADMIN
            participant.save(update_fields=["role", "updated_at"])
            return

    oldest = min(active_participants, key=lambda item: item.joined_at)
    oldest.role = ChatParticipant.Role.ADMIN
    oldest.save(update_fields=["role", "updated_at"])


@transaction.atomic
def handle_membership_chat_deactivation(*, membership: EstablishmentMembership) -> None:
    establishment_id = membership.establishment_id
    membership_id = membership.id

    dm_conversations = list(
        ChatConversation.objects.filter(
            establishment_id=establishment_id,
            type=ChatConversation.Type.DM,
        ).filter(Q(dm_membership_a_id=membership_id) | Q(dm_membership_b_id=membership_id))
    )
    for conversation in dm_conversations:
        participant_membership_ids = _active_participant_membership_ids(
            conversation_id=conversation.id,
        )
        schedule_conversation_access_revoked_for_memberships(
            establishment_id=establishment_id,
            conversation_id=conversation.id,
            membership_ids=participant_membership_ids,
            reason="membership_deactivated",
        )
        conversation.delete()

    active_group_participants = list(
        ChatParticipant.objects.filter(
            membership_id=membership_id,
            left_at__isnull=True,
            conversation__establishment_id=establishment_id,
            conversation__type=ChatConversation.Type.GROUP,
            conversation__deleted_at__isnull=True,
        ).select_related("conversation")
    )
    now = timezone.now()
    for participant in active_group_participants:
        participant.left_at = now
        participant.save(update_fields=["left_at", "updated_at"])
        _ensure_group_has_admin(conversation=participant.conversation)
        schedule_conversation_access_revoked(
            establishment_id=establishment_id,
            membership_id=membership_id,
            conversation_id=participant.conversation_id,
            reason="membership_deactivated",
        )


def _require_chat_membership(
    membership: EstablishmentMembership,
    *,
    target_membership_id: uuid.UUID,
) -> EstablishmentMembership:
    target = (
        EstablishmentMembership.objects.select_related(
            "user",
            "establishment",
            "establishment__organization",
        )
        .filter(id=target_membership_id)
        .first()
    )
    if target is None or not _is_valid_membership(target):
        raise ChatValidationError("Target membership is not eligible for chat.")
    if target.establishment_id != membership.establishment_id:
        raise ChatValidationError("Target membership must belong to the same establishment.")
    if not target.establishment.chat_enabled:
        raise ChatValidationError("Chat is disabled for this establishment.")
    return target


def _normalize_group_title(title: str) -> str:
    normalized = title.strip()
    if not normalized:
        raise ChatValidationError("Group title is required.")
    if len(normalized) > CHAT_GROUP_TITLE_MAX_LENGTH:
        raise ChatValidationError(
            f"Group title must be at most {CHAT_GROUP_TITLE_MAX_LENGTH} characters."
        )
    return normalized


def _create_participant(
    *,
    conversation: ChatConversation,
    membership: EstablishmentMembership,
    role: str,
) -> ChatParticipant:
    return ChatParticipant.objects.create(
        conversation=conversation,
        membership=membership,
        role=role,
    )


@transaction.atomic
def create_or_get_dm_conversation(
    *,
    actor_membership: EstablishmentMembership,
    target_membership_id: uuid.UUID,
) -> tuple[ChatConversation, bool]:
    if not can_create_dm(actor_membership):
        raise ChatPermissionError()

    if actor_membership.id == target_membership_id:
        raise ChatValidationError("You cannot create a direct message with yourself.")

    target_membership = _require_chat_membership(
        actor_membership,
        target_membership_id=target_membership_id,
    )
    membership_a, membership_b = canonical_dm_membership_pair(
        actor_membership,
        target_membership,
    )

    existing = find_existing_dm_conversation(
        establishment_id=actor_membership.establishment_id,
        membership_a_id=membership_a.id,
        membership_b_id=membership_b.id,
    )
    if existing is not None:
        return existing, False

    conversation = ChatConversation.objects.create(
        establishment_id=actor_membership.establishment_id,
        type=ChatConversation.Type.DM,
        created_by_membership=actor_membership,
        dm_membership_a=membership_a,
        dm_membership_b=membership_b,
    )
    _create_participant(
        conversation=conversation,
        membership=membership_a,
        role=ChatParticipant.Role.MEMBER,
    )
    _create_participant(
        conversation=conversation,
        membership=membership_b,
        role=ChatParticipant.Role.MEMBER,
    )
    return conversation, True


@transaction.atomic
def create_group_conversation(
    *,
    actor_membership: EstablishmentMembership,
    title: str,
    membership_ids: list[uuid.UUID],
) -> ChatConversation:
    if not can_create_group(actor_membership):
        raise ChatPermissionError()

    normalized_title = _normalize_group_title(title)
    unique_membership_ids = list(dict.fromkeys(membership_ids))
    if actor_membership.id not in unique_membership_ids:
        unique_membership_ids.insert(0, actor_membership.id)
    if len(unique_membership_ids) < 2:
        raise ChatValidationError("A group requires at least two participants.")

    memberships = []
    for membership_id in unique_membership_ids:
        memberships.append(
            _require_chat_membership(actor_membership, target_membership_id=membership_id)
        )

    conversation = ChatConversation.objects.create(
        establishment_id=actor_membership.establishment_id,
        type=ChatConversation.Type.GROUP,
        title=normalized_title,
        created_by_membership=actor_membership,
    )
    for membership in memberships:
        role = (
            ChatParticipant.Role.ADMIN
            if membership.id == actor_membership.id
            else ChatParticipant.Role.MEMBER
        )
        _create_participant(
            conversation=conversation,
            membership=membership,
            role=role,
        )
    return conversation


@transaction.atomic
def rename_group_conversation(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
    title: str,
) -> ChatConversation:
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if conversation.type != ChatConversation.Type.GROUP:
        raise ChatValidationError("Only groups can be renamed.")
    if not can_manage_group(actor_membership, conversation):
        raise ChatPermissionError()

    conversation.title = _normalize_group_title(title)
    conversation.save(update_fields=["title", "updated_at"])
    return conversation


@transaction.atomic
def delete_group_conversation(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
) -> ChatConversation:
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if conversation.type != ChatConversation.Type.GROUP:
        raise ChatValidationError("Only groups can be deleted.")
    if not can_delete_group(actor_membership, conversation):
        raise ChatPermissionError()

    now = timezone.now()
    conversation.deleted_at = now
    conversation.save(update_fields=["deleted_at", "updated_at"])
    participant_membership_ids = _active_participant_membership_ids(conversation_id=conversation.id)
    ChatParticipant.objects.filter(conversation=conversation, left_at__isnull=True).update(
        left_at=now,
        updated_at=now,
    )
    schedule_conversation_access_revoked_for_memberships(
        establishment_id=conversation.establishment_id,
        conversation_id=conversation.id,
        membership_ids=participant_membership_ids,
        reason="group_deleted",
    )
    return conversation


@transaction.atomic
def add_group_participant(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
    target_membership_id: uuid.UUID,
) -> ChatParticipant:
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if conversation.type != ChatConversation.Type.GROUP:
        raise ChatValidationError("Participants can only be added to groups.")
    if not can_manage_group(actor_membership, conversation):
        raise ChatPermissionError()

    target_membership = _require_chat_membership(
        actor_membership,
        target_membership_id=target_membership_id,
    )
    existing = ChatParticipant.objects.filter(
        conversation=conversation,
        membership=target_membership,
    ).first()
    if existing is not None and existing.left_at is None:
        raise ChatValidationError("Membership is already an active participant.")
    if existing is not None:
        existing.left_at = None
        existing.role = ChatParticipant.Role.MEMBER
        existing.save(update_fields=["left_at", "role", "updated_at"])
        return existing

    return _create_participant(
        conversation=conversation,
        membership=target_membership,
        role=ChatParticipant.Role.MEMBER,
    )


@transaction.atomic
def remove_group_participant(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
    target_membership_id: uuid.UUID,
) -> ChatParticipant:
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if conversation.type != ChatConversation.Type.GROUP:
        raise ChatValidationError("Participants can only be removed from groups.")
    if not can_manage_group(actor_membership, conversation):
        raise ChatPermissionError()

    participant = get_active_participant(
        conversation_id=conversation.id,
        membership_id=target_membership_id,
    )
    if participant is None:
        raise ChatNotFoundError()
    if participant.membership_id == actor_membership.id:
        raise ChatValidationError("Use leave to remove yourself from a group.")

    now = timezone.now()
    participant.left_at = now
    participant.save(update_fields=["left_at", "updated_at"])
    _ensure_group_has_admin(conversation=conversation)
    schedule_conversation_access_revoked(
        establishment_id=conversation.establishment_id,
        membership_id=target_membership_id,
        conversation_id=conversation.id,
        reason="participant_removed",
    )
    return participant


@transaction.atomic
def promote_group_participant(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
    target_membership_id: uuid.UUID,
) -> ChatParticipant:
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if conversation.type != ChatConversation.Type.GROUP:
        raise ChatValidationError("Only group participants can be promoted.")
    if not can_manage_group(actor_membership, conversation):
        raise ChatPermissionError()

    participant = get_active_participant(
        conversation_id=conversation.id,
        membership_id=target_membership_id,
    )
    if participant is None:
        raise ChatNotFoundError()

    participant.role = ChatParticipant.Role.ADMIN
    participant.save(update_fields=["role", "updated_at"])
    return participant


@transaction.atomic
def leave_group_conversation(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
) -> ChatParticipant:
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if conversation.type != ChatConversation.Type.GROUP:
        raise ChatValidationError("Only groups can be left.")

    participant = get_active_participant(
        conversation_id=conversation.id,
        membership_id=actor_membership.id,
    )
    if participant is None:
        raise ChatNotFoundError()

    now = timezone.now()
    participant.left_at = now
    participant.save(update_fields=["left_at", "updated_at"])
    _ensure_group_has_admin(conversation=conversation)
    return participant


@transaction.atomic
def mark_conversation_seen(
    *,
    actor_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
) -> ChatParticipant:
    conversation = get_conversation_for_participant(
        establishment_id=actor_membership.establishment_id,
        conversation_id=conversation_id,
        membership_id=actor_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()

    participant = get_active_participant(
        conversation_id=conversation.id,
        membership_id=actor_membership.id,
    )
    if participant is None:
        raise ChatNotFoundError()

    latest_message = get_latest_message(conversation.id)
    if latest_message is None:
        return participant

    participant.last_seen_message_id = latest_message.id
    participant.last_seen_message_created_at = latest_message.created_at
    participant.save(
        update_fields=[
            "last_seen_message_id",
            "last_seen_message_created_at",
            "updated_at",
        ]
    )
    return participant


@transaction.atomic
def update_establishment_chat_enabled(
    *,
    actor_membership: EstablishmentMembership,
    chat_enabled: bool,
) -> Establishment:
    if not can_manage_establishment_chat_settings(actor_membership):
        raise ChatPermissionError()

    establishment = actor_membership.establishment
    establishment.chat_enabled = chat_enabled
    establishment.save(update_fields=["chat_enabled", "updated_at"])
    return establishment


def normalize_message_body(body: str) -> str:
    normalized = body.strip()
    if not normalized:
        raise ChatValidationError("Message body is required.")
    if len(normalized) > CHAT_MESSAGE_BODY_MAX_LENGTH:
        raise ChatValidationError(
            f"Message body must be at most {CHAT_MESSAGE_BODY_MAX_LENGTH} characters."
        )
    return normalized


def _active_recipient_membership_ids(*, conversation_id: uuid.UUID) -> tuple[uuid.UUID, ...]:
    return tuple(
        active_participant_queryset(conversation_id=conversation_id).values_list(
            "membership_id",
            flat=True,
        )
    )


@transaction.atomic
def create_message(
    *,
    author_membership: EstablishmentMembership,
    establishment_id: uuid.UUID,
    conversation_id: uuid.UUID,
    client_message_id: uuid.UUID,
    body: str,
) -> MessageSendResult:
    if not can_access_chat(author_membership):
        raise ChatPermissionError()
    if author_membership.establishment_id != establishment_id:
        raise ChatPermissionError()

    conversation = get_conversation_for_participant(
        establishment_id=establishment_id,
        conversation_id=conversation_id,
        membership_id=author_membership.id,
    )
    if conversation is None:
        raise ChatNotFoundError()
    if not can_send_message(author_membership, conversation):
        raise ChatPermissionError()

    normalized_body = normalize_message_body(body)
    recipient_membership_ids = _active_recipient_membership_ids(conversation_id=conversation.id)

    existing = (
        ChatMessage.objects.select_related("author_membership", "author_membership__user")
        .filter(
            conversation_id=conversation.id,
            author_membership_id=author_membership.id,
            client_message_id=client_message_id,
        )
        .first()
    )
    if existing is not None:
        return MessageSendResult(
            message=existing,
            created=False,
            recipient_membership_ids=recipient_membership_ids,
        )

    message = ChatMessage.objects.create(
        conversation=conversation,
        author_membership=author_membership,
        body=normalized_body,
        client_message_id=client_message_id,
    )
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])
    return MessageSendResult(
        message=message,
        created=True,
        recipient_membership_ids=recipient_membership_ids,
    )
