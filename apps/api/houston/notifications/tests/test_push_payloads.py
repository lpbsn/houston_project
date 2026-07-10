from __future__ import annotations

import pytest

from houston.notifications.models import Notification
from houston.notifications.push import constants as push_constants
from houston.notifications.push.payloads import ALLOWED_PUSH_DATA_KEYS, build_push_payload
from houston.notifications.tests.conftest import create_test_notification
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

SENSITIVE_SNIPPET = "Secret observation text must never leak"


def test_push_v1_event_keys_includes_chat_and_has_fourteen_keys():
    assert Notification.EventKey.CHAT_MESSAGE_RECEIVED in push_constants.PUSH_V1_EVENT_KEYS
    assert len(push_constants.PUSH_V1_EVENT_KEYS) == 14


def test_build_push_payload_has_strict_shape():
    recipient = build_api_membership()
    notification = create_test_notification(
        recipient=recipient,
        title="Nouveau signal",
        body="Un signal a été créé sur votre pôle.",
        event_key=Notification.EventKey.SIGNAL_CREATED,
        subject_type=Notification.SubjectType.SIGNAL,
    )

    payload = build_push_payload(notification)

    assert set(payload.keys()) == {"title", "body", "data"}
    assert set(payload["data"].keys()) == ALLOWED_PUSH_DATA_KEYS
    assert payload["title"] == notification.title
    assert payload["body"] == notification.body
    assert payload["data"]["notification_id"] == str(notification.id)
    assert payload["data"]["event_key"] == notification.event_key
    assert payload["data"]["establishment_id"] == str(notification.establishment_id)
    assert payload["data"]["url"] == f"/signals/{notification.subject_id}"


def test_build_push_payload_data_never_includes_subject_fields():
    recipient = build_api_membership()
    notification = create_test_notification(
        recipient=recipient,
        title="Mention",
        body="Vous avez été mentionné dans un commentaire.",
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
    )

    payload = build_push_payload(notification)

    assert "subject_type" not in payload["data"]
    assert "subject_id" not in payload["data"]
    assert "actor" not in payload["data"]
    assert SENSITIVE_SNIPPET not in str(payload["data"])
