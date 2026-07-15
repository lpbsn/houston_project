from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient

from houston.chat.models import ChatParticipant
from houston.chat.services import create_message
from houston.chat.tests.helpers import create_dm, create_group
from houston.establishments.models import EstablishmentMembership
from houston.notifications.constants import (
    DEDUPE_WINDOW,
    build_chat_message_dedupe_key,
    render_notification_copy,
)
from houston.notifications.models import Notification
from houston.notifications.scheduling import _run_notification_after_commit
from houston.testing.auth import (
    build_api_membership,
    build_api_membership_on_establishment,
    login,
)

pytestmark = pytest.mark.django_db(transaction=True)

LOGGER_NAME = "houston.notifications.scheduling"
SENSITIVE_MESSAGE_BODY = "Secret chat body must never appear in notification copy"


def _enable_chat_for_membership(membership: EstablishmentMembership) -> None:
    establishment = membership.establishment
    if establishment.chat_enabled:
        return
    establishment.chat_enabled = True
    establishment.save(update_fields=["chat_enabled", "updated_at"])


def _notifications_for_conversation(*, conversation_id: uuid.UUID) -> list[Notification]:
    return list(
        Notification.objects.filter(
            event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
            subject_type=Notification.SubjectType.CHAT_CONVERSATION,
            subject_id=conversation_id,
        ).order_by("recipient_membership_id", "created_at", "id")
    )


def _recipient_ids(notifications: list[Notification]) -> set[uuid.UUID]:
    return {item.recipient_membership_id for item in notifications}


def _assert_generic_copy(notification: Notification) -> None:
    assert SENSITIVE_MESSAGE_BODY not in notification.title
    assert SENSITIVE_MESSAGE_BODY not in notification.body


def _create_dm_conversation(
    *,
    author_membership: EstablishmentMembership,
    target_membership: EstablishmentMembership,
) -> uuid.UUID:
    api_client = APIClient()
    token = login(api_client, user=author_membership.user)
    response = create_dm(
        api_client,
        token=token,
        establishment_id=author_membership.establishment_id,
        target_membership_id=target_membership.id,
    )
    assert response.status_code == 201
    return uuid.UUID(response.json()["conversation"]["id"])


def _send_message(
    *,
    author_membership: EstablishmentMembership,
    conversation_id: uuid.UUID,
    body: str = SENSITIVE_MESSAGE_BODY,
    client_message_id: uuid.UUID | None = None,
):
    return create_message(
        author_membership=author_membership,
        establishment_id=author_membership.establishment_id,
        conversation_id=conversation_id,
        client_message_id=client_message_id or uuid.uuid4(),
        body=body,
    )


def test_dm_message_notifies_other_participant_not_author():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    target_membership = build_api_membership_on_establishment(author_membership)
    _enable_chat_for_membership(author_membership)
    conversation_id = _create_dm_conversation(
        author_membership=author_membership,
        target_membership=target_membership,
    )

    result = _send_message(
        author_membership=author_membership,
        conversation_id=conversation_id,
    )
    assert result.created is True

    notifications = _notifications_for_conversation(conversation_id=conversation_id)
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.recipient_membership_id == target_membership.id
    assert notification.event_key == Notification.EventKey.CHAT_MESSAGE_RECEIVED
    assert notification.priority == Notification.Priority.INFO
    assert notification.subject_id == conversation_id
    assert notification.subject_id != result.message.id
    assert notification.dedupe_key == build_chat_message_dedupe_key(
        conversation_id=conversation_id,
        recipient_membership_id=target_membership.id,
        actor_membership_id=author_membership.id,
    )
    _assert_generic_copy(notification)
    assert (
        author_membership.user.get_full_name()
        or author_membership.user.email
        or author_membership.user.username
    ) in notification.title


def test_group_message_notifies_all_other_active_participants():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    peer_a_membership = build_api_membership_on_establishment(author_membership)
    peer_b_membership = build_api_membership_on_establishment(author_membership)
    _enable_chat_for_membership(author_membership)

    api_client = APIClient()
    token = login(api_client, user=author_membership.user)
    response = create_group(
        api_client,
        token=token,
        establishment_id=author_membership.establishment_id,
        title="Ops",
        membership_ids=[peer_a_membership.id, peer_b_membership.id],
    )
    assert response.status_code == 201
    conversation_id = uuid.UUID(response.json()["conversation"]["id"])

    _send_message(author_membership=author_membership, conversation_id=conversation_id)

    notifications = _notifications_for_conversation(conversation_id=conversation_id)
    assert len(notifications) == 2
    assert _recipient_ids(notifications) == {peer_a_membership.id, peer_b_membership.id}
    for notification in notifications:
        assert notification.subject_id == conversation_id
        _assert_generic_copy(notification)


def test_notifications_disabled_skips_chat_notification():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    target_membership = build_api_membership_on_establishment(author_membership)
    target_membership.notifications_enabled = False
    target_membership.save(update_fields=["notifications_enabled", "updated_at"])
    _enable_chat_for_membership(author_membership)
    conversation_id = _create_dm_conversation(
        author_membership=author_membership,
        target_membership=target_membership,
    )

    _send_message(author_membership=author_membership, conversation_id=conversation_id)

    assert _notifications_for_conversation(conversation_id=conversation_id) == []


def test_burst_messages_dedupe_within_window():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    target_membership = build_api_membership_on_establishment(author_membership)
    _enable_chat_for_membership(author_membership)
    conversation_id = _create_dm_conversation(
        author_membership=author_membership,
        target_membership=target_membership,
    )

    for index in range(5):
        _send_message(
            author_membership=author_membership,
            conversation_id=conversation_id,
            body=f"{SENSITIVE_MESSAGE_BODY} {index}",
            client_message_id=uuid.uuid4(),
        )

    notifications = _notifications_for_conversation(conversation_id=conversation_id)
    assert len(notifications) == 1
    _assert_generic_copy(notifications[0])


def test_expired_dedupe_window_allows_new_notification():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    target_membership = build_api_membership_on_establishment(author_membership)
    _enable_chat_for_membership(author_membership)
    conversation_id = _create_dm_conversation(
        author_membership=author_membership,
        target_membership=target_membership,
    )

    _send_message(author_membership=author_membership, conversation_id=conversation_id)
    notifications = _notifications_for_conversation(conversation_id=conversation_id)
    assert len(notifications) == 1

    Notification.objects.filter(id=notifications[0].id).update(
        created_at=timezone.now() - DEDUPE_WINDOW - timedelta(seconds=1),
    )

    _send_message(
        author_membership=author_membership,
        conversation_id=conversation_id,
        client_message_id=uuid.uuid4(),
    )

    assert len(_notifications_for_conversation(conversation_id=conversation_id)) == 2


def test_idempotent_client_message_id_creates_single_notification():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    target_membership = build_api_membership_on_establishment(author_membership)
    _enable_chat_for_membership(author_membership)
    conversation_id = _create_dm_conversation(
        author_membership=author_membership,
        target_membership=target_membership,
    )
    client_message_id = uuid.uuid4()

    first = _send_message(
        author_membership=author_membership,
        conversation_id=conversation_id,
        client_message_id=client_message_id,
    )
    second = _send_message(
        author_membership=author_membership,
        conversation_id=conversation_id,
        client_message_id=client_message_id,
    )

    assert first.created is True
    assert second.created is False
    assert len(_notifications_for_conversation(conversation_id=conversation_id)) == 1


def test_participant_left_before_delivery_creates_zero_notifications():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    target_membership = build_api_membership_on_establishment(author_membership)
    _enable_chat_for_membership(author_membership)
    conversation_id = _create_dm_conversation(
        author_membership=author_membership,
        target_membership=target_membership,
    )

    with transaction.atomic():
        result = _send_message(
            author_membership=author_membership,
            conversation_id=conversation_id,
        )
        ChatParticipant.objects.filter(
            conversation_id=conversation_id,
            membership_id=target_membership.id,
        ).update(left_at=timezone.now())

    assert result.created is True
    assert _notifications_for_conversation(conversation_id=conversation_id) == []


def test_notification_delivery_failure_does_not_break_message_create():
    author_membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    target_membership = build_api_membership_on_establishment(author_membership)
    _enable_chat_for_membership(author_membership)
    conversation_id = _create_dm_conversation(
        author_membership=author_membership,
        target_membership=target_membership,
    )

    with patch(
        "houston.notifications.scheduling.create_in_app_notification",
        side_effect=RuntimeError("notification delivery failed"),
    ):
        result = _send_message(
            author_membership=author_membership,
            conversation_id=conversation_id,
        )

    assert result.created is True
    assert _notifications_for_conversation(conversation_id=conversation_id) == []


def test_scheduling_failure_logs_without_message_body(caplog: pytest.LogCaptureFixture):
    conversation_id = uuid.uuid4()

    def deliver() -> None:
        raise RuntimeError("simulated deliver failure")

    with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
        with transaction.atomic():
            _run_notification_after_commit(
                deliver=deliver,
                event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
                subject_type=Notification.SubjectType.CHAT_CONVERSATION,
                subject_id=conversation_id,
            )

    failure_record = next(
        record
        for record in caplog.records
        if "Failed to create in-app notification after business commit" in record.getMessage()
    )
    assert failure_record.event_key == Notification.EventKey.CHAT_MESSAGE_RECEIVED
    assert failure_record.subject_type == Notification.SubjectType.CHAT_CONVERSATION
    assert failure_record.subject_id == str(conversation_id)
    assert SENSITIVE_MESSAGE_BODY not in str(failure_record.__dict__)


def test_render_notification_copy_keeps_existing_events_unchanged():
    title, body = render_notification_copy(Notification.EventKey.SIGNAL_CREATED)
    assert title == "Nouveau signal"
    assert body == "Un signal a été créé sur votre pôle."

    title, body = render_notification_copy(
        Notification.EventKey.COMMENT_MENTION_CREATED,
        actor_display_name="Alice",
    )
    assert title == "Mention"
    assert body == "Vous avez été mentionné dans un commentaire."


def test_render_notification_copy_interpolates_actor_in_chat_title():
    title, body = render_notification_copy(
        Notification.EventKey.CHAT_MESSAGE_RECEIVED,
        actor_display_name="Alice Martin",
    )
    assert title == "Message reçu de Alice Martin"
    assert body == "Ouvrez la conversation pour lire le message."
    assert SENSITIVE_MESSAGE_BODY not in title
    assert SENSITIVE_MESSAGE_BODY not in body
