from __future__ import annotations

import pytest

from houston.notifications.models import Notification
from houston.notifications.push import constants as push_constants
from houston.notifications.push.payloads import (
    ALLOWED_PUSH_DATA_KEYS,
    build_push_payload,
    stringify_push_data,
)
from houston.notifications.push.sender import build_fcm_http_body
from houston.notifications.tests.conftest import create_test_notification
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

SENSITIVE_SNIPPET = "Secret observation text must never leak"


def test_push_v1_event_keys_includes_chat_and_has_twenty_keys():
    assert Notification.EventKey.CHAT_MESSAGE_RECEIVED in push_constants.PUSH_V1_EVENT_KEYS
    assert (
        Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED_FROM_SIGNAL
        in push_constants.PUSH_V1_EVENT_KEYS
    )
    assert (
        Notification.EventKey.ACTION_PLAN_EXECUTION_UPDATED
        in push_constants.PUSH_V1_EVENT_KEYS
    )
    assert (
        Notification.EventKey.SIGNAL_CREATED_UNASSIGNED_GLOBAL
        in push_constants.PUSH_V1_EVENT_KEYS
    )
    assert (
        Notification.EventKey.SIGNAL_RESOLUTION_REQUEST_CREATED
        in push_constants.PUSH_V1_EVENT_KEYS
    )
    assert (
        Notification.EventKey.SIGNAL_RESOLUTION_REQUEST_APPROVED
        in push_constants.PUSH_V1_EVENT_KEYS
    )
    assert (
        Notification.EventKey.SIGNAL_RESOLUTION_REQUEST_REJECTED
        in push_constants.PUSH_V1_EVENT_KEYS
    )
    assert (
        Notification.EventKey.SIGNAL_RESOLUTION_REQUEST_CANCELED
        in push_constants.PUSH_V1_EVENT_KEYS
    )
    assert len(push_constants.PUSH_V1_EVENT_KEYS) == 20


def test_build_push_payload_has_strict_shape():
    recipient = build_api_membership()
    notification = create_test_notification(
        recipient=recipient,
        title="Nouvelle observation",
        body="Une observation a été créée sur votre pôle.",
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


def test_stringify_push_data_converts_values_to_strings_without_extra_keys():
    data = stringify_push_data(
        {
            "notification_id": "nid",
            "event_key": "signal.created",
            "establishment_id": "est",
            "url": None,
        }
    )

    assert data == {
        "notification_id": "nid",
        "event_key": "signal.created",
        "establishment_id": "est",
        "url": "",
    }
    assert set(data.keys()) == ALLOWED_PUSH_DATA_KEYS


def test_build_fcm_http_body_uses_notification_and_string_data():
    recipient = build_api_membership()
    notification = create_test_notification(
        recipient=recipient,
        event_key=Notification.EventKey.SIGNAL_CREATED,
        subject_type=Notification.SubjectType.SIGNAL,
    )
    payload = build_push_payload(notification)
    body = build_fcm_http_body(token="fcm-token", payload=payload)

    assert set(body.keys()) == {"message"}
    message = body["message"]
    assert message["token"] == "fcm-token"
    assert message["notification"] == {"title": payload["title"], "body": payload["body"]}
    assert set(message["data"].keys()) == ALLOWED_PUSH_DATA_KEYS
    assert all(isinstance(value, str) for value in message["data"].values())
    assert "subject_type" not in message["data"]
