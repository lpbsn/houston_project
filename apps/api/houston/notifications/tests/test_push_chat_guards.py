from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from pywebpush import WebPushException

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification, PushDelivery, WebPushSubscription
from houston.notifications.push import constants as push_constants
from houston.notifications.push.chat_guards import (
    claim_chat_push_throttle,
    release_chat_push_throttle,
)
from houston.notifications.push.services import run_push_for_notification
from houston.notifications.tests.conftest import create_test_notification
from houston.notifications.tests.vapid_constants import TEST_PRIVATE_KEY, TEST_PUBLIC_KEY
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

VAPID_SETTINGS = {
    "HOUSTON_PUSH_ENABLED": True,
    "HOUSTON_VAPID_PUBLIC_KEY": TEST_PUBLIC_KEY,
    "HOUSTON_VAPID_PRIVATE_KEY": TEST_PRIVATE_KEY,
    "HOUSTON_VAPID_SUBJECT": "mailto:push@houston.local",
}


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def _create_subscription(*, user) -> WebPushSubscription:
    return WebPushSubscription.objects.create(
        user=user,
        endpoint=f"https://push.example.com/device/{uuid.uuid4()}",
        p256dh="p256dh-key",
        auth="auth-key",
    )


def _prepare_recipient():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    return recipient


def _create_chat_notification(*, recipient, conversation_id: uuid.UUID | None = None):
    return create_test_notification(
        recipient=recipient,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
        subject_type=Notification.SubjectType.CHAT_CONVERSATION,
        subject_id=conversation_id or uuid.uuid4(),
        title="Message reçu",
        body="Vous avez reçu un nouveau message.",
    )


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_sends_chat_message_received():
    recipient = _prepare_recipient()
    notification = _create_chat_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 1
    send_web_push.assert_called_once()
    delivery = PushDelivery.objects.get()
    assert delivery.status == PushDelivery.Status.SENT


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_skips_chat_when_presence_active():
    recipient = _prepare_recipient()
    conversation_id = uuid.uuid4()
    notification = _create_chat_notification(
        recipient=recipient,
        conversation_id=conversation_id,
    )
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch(
            "houston.notifications.push.services.is_chat_presence_active",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_web_push.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_throttles_chat_push_to_one_per_window():
    recipient = _prepare_recipient()
    conversation_id = uuid.uuid4()
    _create_subscription(user=recipient.user)

    notifications = [
        _create_chat_notification(recipient=recipient, conversation_id=conversation_id)
        for _ in range(3)
    ]

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_counts = [run_push_for_notification(notification.id) for notification in notifications]

    assert sent_counts == [1, 0, 0]
    assert send_web_push.call_count == 1


@override_settings(**VAPID_SETTINGS)
def test_chat_push_throttle_not_consumed_without_active_subscription():
    recipient = _prepare_recipient()
    conversation_id = uuid.uuid4()
    notification = _create_chat_notification(
        recipient=recipient,
        conversation_id=conversation_id,
    )

    with patch(
        "houston.notifications.push.services.recipient_can_view_notification_subject",
        return_value=True,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    assert claim_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient.id,
        owner_token=str(uuid.uuid4()),
    )


@override_settings(**VAPID_SETTINGS)
def test_chat_push_throttle_not_consumed_when_navigation_missing():
    recipient = _prepare_recipient()
    conversation_id = uuid.uuid4()
    notification = _create_chat_notification(
        recipient=recipient,
        conversation_id=conversation_id,
    )
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch(
            "houston.notifications.push.payloads.resolve_notification_url",
            return_value=None,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_web_push.assert_not_called()
    assert claim_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient.id,
        owner_token=str(uuid.uuid4()),
    )


@override_settings(**VAPID_SETTINGS)
def test_chat_push_throttle_not_consumed_when_all_deliveries_fail():
    recipient = _prepare_recipient()
    conversation_id = uuid.uuid4()
    notification = _create_chat_notification(
        recipient=recipient,
        conversation_id=conversation_id,
    )
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch(
            "houston.notifications.push.services.send_web_push",
            side_effect=WebPushException("network error", response=None),
        ),
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    delivery = PushDelivery.objects.get()
    assert delivery.status == PushDelivery.Status.FAILED
    assert claim_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient.id,
        owner_token=str(uuid.uuid4()),
    )


@override_settings(**VAPID_SETTINGS)
def test_chat_push_throttle_consumed_after_successful_send():
    recipient = _prepare_recipient()
    conversation_id = uuid.uuid4()
    notification = _create_chat_notification(
        recipient=recipient,
        conversation_id=conversation_id,
    )
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push"),
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 1
    assert not claim_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient.id,
        owner_token=str(uuid.uuid4()),
    )


@override_settings(**VAPID_SETTINGS)
def test_chat_push_throttle_consumed_when_one_of_multiple_subscriptions_succeeds():
    recipient = _prepare_recipient()
    conversation_id = uuid.uuid4()
    notification = _create_chat_notification(
        recipient=recipient,
        conversation_id=conversation_id,
    )
    _create_subscription(user=recipient.user)
    _create_subscription(user=recipient.user)

    call_count = 0

    def send_side_effect(*, subscription, payload):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise WebPushException("gone", response=type("Response", (), {"status_code": 410})())

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch(
            "houston.notifications.push.services.send_web_push",
            side_effect=send_side_effect,
        ),
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 1
    assert not claim_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient.id,
        owner_token=str(uuid.uuid4()),
    )


def test_release_chat_push_throttle_does_not_clear_newer_owner():
    conversation_id = uuid.uuid4()
    recipient_membership_id = uuid.uuid4()
    owner_token_a = str(uuid.uuid4())
    owner_token_b = str(uuid.uuid4())

    assert claim_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient_membership_id,
        owner_token=owner_token_a,
    )
    assert not claim_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient_membership_id,
        owner_token=owner_token_b,
    )

    cache_key = f"push:chat:{conversation_id}:{recipient_membership_id}"
    cache.set(cache_key, owner_token_b, timeout=120)

    release_chat_push_throttle(
        conversation_id=conversation_id,
        recipient_membership_id=recipient_membership_id,
        owner_token=owner_token_a,
    )

    assert cache.get(cache_key) == owner_token_b


def test_push_v1_event_keys_includes_chat():
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
