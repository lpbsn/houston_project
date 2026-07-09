from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification, PushDelivery, WebPushSubscription
from houston.notifications.push import constants as push_constants
from houston.notifications.push.services import run_push_for_notification
from houston.notifications.push.tasks import send_push_for_notification_task
from houston.notifications.tests.conftest import create_test_notification
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

ALLOWED_EVENT_KEY = Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED


def _create_subscription(*, user) -> WebPushSubscription:
    return WebPushSubscription.objects.create(
        user=user,
        endpoint=f"https://push.example.com/device/{uuid.uuid4()}",
        p256dh="p256dh-key",
        auth="auth-key",
    )


@override_settings(HOUSTON_PUSH_ENABLED=False)
def test_run_push_for_notification_skips_when_flag_off():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with patch.object(push_constants, "PUSH_V1_EVENT_KEYS", frozenset({ALLOWED_EVENT_KEY})):
        created_count = run_push_for_notification(notification.id)

    assert created_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_run_push_for_notification_skips_when_notification_missing():
    created_count = run_push_for_notification(uuid.uuid4())
    assert created_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_run_push_for_notification_skips_when_event_key_not_allowlisted():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    created_count = run_push_for_notification(notification.id)

    assert created_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(HOUSTON_PUSH_ENABLED=True)
@pytest.mark.parametrize(
    ("notifications_enabled", "push_enabled"),
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_run_push_for_notification_skips_when_preferences_disabled(
    notifications_enabled,
    push_enabled,
):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.notifications_enabled = notifications_enabled
    recipient.push_enabled = push_enabled
    recipient.save(
        update_fields=["notifications_enabled", "push_enabled", "updated_at"],
    )
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with patch.object(push_constants, "PUSH_V1_EVENT_KEYS", frozenset({ALLOWED_EVENT_KEY})):
        created_count = run_push_for_notification(notification.id)

    assert created_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_run_push_for_notification_skips_when_no_active_subscriptions():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)

    with patch.object(push_constants, "PUSH_V1_EVENT_KEYS", frozenset({ALLOWED_EVENT_KEY})):
        created_count = run_push_for_notification(notification.id)

    assert created_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_run_push_for_notification_skips_revoked_subscription():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)
    subscription.revoked_at = notification.created_at
    subscription.save(update_fields=["revoked_at", "updated_at"])

    with patch.object(push_constants, "PUSH_V1_EVENT_KEYS", frozenset({ALLOWED_EVENT_KEY})):
        created_count = run_push_for_notification(notification.id)

    assert created_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_run_push_for_notification_creates_delivery_when_guards_pass():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)

    with patch.object(push_constants, "PUSH_V1_EVENT_KEYS", frozenset({ALLOWED_EVENT_KEY})):
        created_count = run_push_for_notification(notification.id)

    assert created_count == 1
    delivery = PushDelivery.objects.get()
    assert delivery.notification_id == notification.id
    assert delivery.subscription_id == subscription.id
    assert delivery.status == PushDelivery.Status.QUEUED


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_run_push_for_notification_is_idempotent_per_subscription():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with patch.object(push_constants, "PUSH_V1_EVENT_KEYS", frozenset({ALLOWED_EVENT_KEY})):
        first_count = run_push_for_notification(notification.id)
        second_count = run_push_for_notification(notification.id)

    assert first_count == 1
    assert second_count == 0
    assert PushDelivery.objects.count() == 1


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_send_push_for_notification_task_delegates_to_service():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with patch.object(push_constants, "PUSH_V1_EVENT_KEYS", frozenset({ALLOWED_EVENT_KEY})):
        created_count = send_push_for_notification_task.run(str(notification.id))

    assert created_count == 1
    assert PushDelivery.objects.count() == 1
