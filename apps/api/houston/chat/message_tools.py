"""Explicit message handoff. No automatic mining of private conversations."""

import uuid

from django.db import transaction
from houston.chat.exceptions import ChatNotFoundError, ChatPermissionError
from houston.chat.models import (
    ChatMessage,
    ChatMessageAcknowledgement,
    ChatObservationSource,
    ChatParticipant,
)
from houston.chat.permissions import can_access_chat
from houston.establishments.permissions import can_create_observation
from houston.observations.services import submit_observation


def visible_messages(*, membership):
    from django.db.models import Exists, OuterRef, Q

    if not can_access_chat(membership):
        return ChatMessage.objects.none()
    participant = ChatParticipant.objects.filter(
        conversation_id=OuterRef("conversation_id"),
        membership_id=membership.id,
        left_at__isnull=True,
    ).filter(Q(history_cutoff_at__isnull=True) | Q(history_cutoff_at__lt=OuterRef("created_at")))
    return ChatMessage.objects.filter(
        conversation__establishment_id=membership.establishment_id,
        conversation__deleted_at__isnull=True,
    ).filter(Exists(participant))


def require_message(*, membership, message_id, lock=False):
    qs = visible_messages(membership=membership)
    if lock:
        qs = qs.select_for_update(of=("self",))
    message = qs.filter(id=message_id).first()
    if message is None:
        raise ChatNotFoundError()
    return message


@transaction.atomic
def acknowledge_message(*, membership, message_id, active):
    message = require_message(membership=membership, message_id=message_id, lock=True)
    if active:
        ChatMessageAcknowledgement.objects.get_or_create(message=message, membership=membership)
    else:
        ChatMessageAcknowledgement.objects.filter(message=message, membership=membership).delete()

    _notify_message_tools(message)


@transaction.atomic
def observation_from_message(*, membership, message_id, text):
    message = require_message(membership=membership, message_id=message_id, lock=True)
    if not can_create_observation(membership):
        raise ChatPermissionError()
    existing = ChatObservationSource.objects.filter(message=message).first()
    if existing:
        return existing
    observation = submit_observation(
        membership=membership,
        text=text,
        temporary_upload_ids=[],
        client_submission_id=uuid.uuid5(message.id, "observation"),
    )
    source = ChatObservationSource.objects.create(
        message=message,
        observation=observation,
        source_author=message.author_membership,
        source_created_at=message.created_at,
        source_message_id=message.id,
        source_conversation_id=message.conversation_id,
    )

    _notify_message_tools(message)
    return source


@transaction.atomic
def set_conversation_notifications(*, membership, conversation_id, mode):
    from houston.chat.selectors import get_conversation_for_participant

    if (
        not can_access_chat(membership)
        or get_conversation_for_participant(
            establishment_id=membership.establishment_id,
            membership_id=membership.id,
            conversation_id=conversation_id,
        )
        is None
    ):
        raise ChatNotFoundError()
    ChatParticipant.objects.filter(
        conversation_id=conversation_id, membership=membership, left_at__isnull=True
    ).update(notification_mode=mode)


def _notify_message_tools(message):
    from houston.chat.ws_notify import schedule_conversation_updated

    schedule_conversation_updated(
        establishment_id=message.conversation.establishment_id,
        conversation_id=message.conversation_id,
        membership_ids=list(
            ChatParticipant.objects.filter(
                conversation_id=message.conversation_id, left_at__isnull=True
            ).values_list("membership_id", flat=True)
        ),
    )
