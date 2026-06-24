from __future__ import annotations

from houston.chat.models import ChatConversation, ChatParticipant
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import is_valid_membership
from houston.establishments.role_constants import _ACTION_ROLES, ADMIN_ROLES


def can_access_chat(membership: EstablishmentMembership | None) -> bool:
    if not is_valid_membership(membership):
        return False
    return bool(membership.establishment.chat_enabled)


def can_create_dm(membership: EstablishmentMembership | None) -> bool:
    return can_access_chat(membership)


def can_create_group(membership: EstablishmentMembership | None) -> bool:
    if not can_access_chat(membership):
        return False
    return membership.role in _ACTION_ROLES


def can_manage_establishment_chat_settings(membership: EstablishmentMembership | None) -> bool:
    if not is_valid_membership(membership):
        return False
    return membership.role in ADMIN_ROLES


def _is_active_participant(
    membership: EstablishmentMembership | None,
    conversation: ChatConversation,
) -> ChatParticipant | None:
    if membership is None:
        return None
    return (
        ChatParticipant.objects.filter(
            conversation_id=conversation.id,
            membership_id=membership.id,
            left_at__isnull=True,
        )
        .select_related("membership")
        .first()
    )


def can_view_conversation(
    membership: EstablishmentMembership | None,
    conversation: ChatConversation,
) -> bool:
    return _is_active_participant(membership, conversation) is not None


def can_manage_group(
    membership: EstablishmentMembership | None,
    conversation: ChatConversation,
) -> bool:
    if conversation.type != ChatConversation.Type.GROUP:
        return False
    participant = _is_active_participant(membership, conversation)
    return participant is not None and participant.role == ChatParticipant.Role.ADMIN


def can_delete_group(
    membership: EstablishmentMembership | None,
    conversation: ChatConversation,
) -> bool:
    return can_manage_group(membership, conversation)


def can_send_message(
    membership: EstablishmentMembership | None,
    conversation: ChatConversation,
) -> bool:
    if not can_access_chat(membership):
        return False
    return can_view_conversation(membership, conversation)
