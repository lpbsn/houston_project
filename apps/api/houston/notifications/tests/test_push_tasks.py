from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification, PushDelivery, PushDevice
from houston.notifications.push.services import run_push_for_notification
from houston.notifications.push.tasks import send_push_for_notification_task
from houston.notifications.tests.conftest import create_test_notification
from houston.notifications.tests.fcm_constants import FCM_PUSH_SETTINGS
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

VAPID_SETTINGS = FCM_PUSH_SETTINGS


def _create_subscription(*, user) -> PushDevice:
    return PushDevice.objects.create(
        user=user,
        token=f"fcm-token-{uuid.uuid4()}",
        platform="android",
    )


def _prepare_recipient():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    return recipient


@override_settings(HOUSTON_PUSH_ENABLED=False)
def test_run_push_for_notification_skips_when_flag_off():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_run_push_for_notification_skips_when_notification_missing():
    sent_count = run_push_for_notification(uuid.uuid4())
    assert sent_count == 0
    assert PushDelivery.objects.count() == 0


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_skips_when_event_key_not_allowlisted():
    recipient = _prepare_recipient()
    notification = create_test_notification(
        recipient=recipient,
        event_key="signal.future_event",
        subject_type=Notification.SubjectType.SIGNAL,
    )
    _create_subscription(user=recipient.user)

    with patch("houston.notifications.push.services.send_fcm") as send_fcm:
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_fcm.assert_not_called()


@override_settings(**VAPID_SETTINGS)
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
    recipient = _prepare_recipient()
    recipient.notifications_enabled = notifications_enabled
    recipient.push_enabled = push_enabled
    recipient.save(
        update_fields=["notifications_enabled", "push_enabled", "updated_at"],
    )
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with patch("houston.notifications.push.services.send_fcm") as send_fcm:
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_fcm.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_skips_when_no_active_devices():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)

    with patch("houston.notifications.push.services.send_fcm") as send_fcm:
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_fcm.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_skips_revoked_device():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)
    subscription.revoked_at = notification.created_at
    subscription.save(update_fields=["revoked_at", "updated_at"])

    with patch("houston.notifications.push.services.send_fcm") as send_fcm:
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_fcm.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_sends_delivery_when_guards_pass():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_fcm") as send_fcm,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 1
    send_fcm.assert_called_once()
    delivery = PushDelivery.objects.get()
    assert delivery.notification_id == notification.id
    assert delivery.device_id == subscription.id
    assert delivery.status == PushDelivery.Status.SENT


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_is_idempotent_per_device():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_fcm") as send_fcm,
    ):
        first_count = run_push_for_notification(notification.id)
        second_count = run_push_for_notification(notification.id)

    assert first_count == 1
    assert second_count == 0
    assert PushDelivery.objects.count() == 1
    assert send_fcm.call_count == 1


@override_settings(**VAPID_SETTINGS)
def test_send_push_for_notification_task_delegates_to_service():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_fcm"),
    ):
        sent_count = send_push_for_notification_task.run(str(notification.id))

    assert sent_count == 1
    assert PushDelivery.objects.count() == 1
    assert PushDelivery.objects.get().status == PushDelivery.Status.SENT
