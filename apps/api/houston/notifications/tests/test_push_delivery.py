from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.test import override_settings
from django.utils import timezone
from pywebpush import WebPushException

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification, PushDelivery, WebPushSubscription
from houston.notifications.push.services import (
    _try_claim_push_delivery_for_send,
    run_push_for_notification,
)
from houston.notifications.tests.conftest import create_test_notification
from houston.notifications.tests.test_push_vapid_public_key_api import (
    TEST_PRIVATE_KEY,
    TEST_PUBLIC_KEY,
)
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

VAPID_SETTINGS = {
    "HOUSTON_PUSH_ENABLED": True,
    "HOUSTON_VAPID_PUBLIC_KEY": TEST_PUBLIC_KEY,
    "HOUSTON_VAPID_PRIVATE_KEY": TEST_PRIVATE_KEY,
    "HOUSTON_VAPID_SUBJECT": "mailto:push@houston.local",
}

EVENT_KEY_SUBJECT_TYPES = [
    (
        Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
        Notification.SubjectType.ACTION_PLAN_EXECUTION,
    ),
    (
        Notification.EventKey.ACTION_PLAN_EXECUTION_PENDING_VALIDATION,
        Notification.SubjectType.ACTION_PLAN_EXECUTION,
    ),
    (
        Notification.EventKey.ACTION_PLAN_EXECUTION_CANCELED,
        Notification.SubjectType.ACTION_PLAN_EXECUTION,
    ),
    (
        Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
        Notification.SubjectType.ACTION_PLAN_EXECUTION,
    ),
    (Notification.EventKey.SIGNAL_CREATED, Notification.SubjectType.SIGNAL),
    (Notification.EventKey.SIGNAL_URGENCY_CHANGED, Notification.SubjectType.SIGNAL),
    (Notification.EventKey.SIGNAL_PINNED, Notification.SubjectType.SIGNAL),
    (Notification.EventKey.SIGNAL_RESOLVED, Notification.SubjectType.SIGNAL),
    (Notification.EventKey.SIGNAL_CANCELED, Notification.SubjectType.SIGNAL),
]


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


@override_settings(**VAPID_SETTINGS)
@pytest.mark.parametrize(("event_key", "subject_type"), EVENT_KEY_SUBJECT_TYPES)
def test_run_push_for_notification_sends_for_allowlisted_event_keys(
    event_key,
    subject_type,
):
    recipient = _prepare_recipient()
    notification = create_test_notification(
        recipient=recipient,
        event_key=event_key,
        subject_type=subject_type,
    )
    subscription = _create_subscription(user=recipient.user)

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
    assert delivery.notification_id == notification.id
    assert delivery.subscription_id == subscription.id
    assert delivery.status == PushDelivery.Status.SENT
    assert delivery.sent_at is not None


@override_settings(**VAPID_SETTINGS)
@pytest.mark.django_db(transaction=True)
def test_run_push_for_notification_sends_for_comment_mention():
    from houston.comments.services import create_signal_comment
    from houston.establishments.models import EstablishmentMembership
    from houston.testing.auth import (
        assign_business_unit_scope,
        build_api_membership_on_establishment,
    )
    from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    staff.push_enabled = True
    staff.save(update_fields=["push_enabled", "updated_at"])
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
    )
    assign_business_unit_scope(staff, maintenance)
    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="mention body",
        mentioned_membership_ids=[staff.id],
    )
    notification = create_test_notification(
        recipient=staff,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment.id,
    )
    subscription = _create_subscription(user=staff.user)

    with patch("houston.notifications.push.services.send_web_push") as send_web_push:
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 1
    send_web_push.assert_called_once()
    delivery = PushDelivery.objects.get()
    assert delivery.notification_id == notification.id
    assert delivery.subscription_id == subscription.id
    assert delivery.status == PushDelivery.Status.SENT


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_skips_chat_when_presence_active():
    recipient = _prepare_recipient()
    notification = create_test_notification(
        recipient=recipient,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
        subject_type=Notification.SubjectType.CHAT_CONVERSATION,
    )
    _create_subscription(user=recipient.user)

    with (
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
def test_run_push_for_notification_skips_when_actor_is_recipient():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    notification.actor_membership = recipient
    notification.save(update_fields=["actor_membership", "updated_at"])
    _create_subscription(user=recipient.user)

    with patch("houston.notifications.push.services.send_web_push") as send_web_push:
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_web_push.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_skips_when_subject_not_visible():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=False,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_web_push.assert_not_called()


@override_settings(
    HOUSTON_PUSH_ENABLED=True,
    HOUSTON_VAPID_PUBLIC_KEY="",
    HOUSTON_VAPID_PRIVATE_KEY="",
)
def test_run_push_for_notification_skips_when_vapid_not_configured():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with patch("houston.notifications.push.services.send_web_push") as send_web_push:
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    assert PushDelivery.objects.count() == 0
    send_web_push.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_marks_missing_navigation_as_skipped():
    recipient = _prepare_recipient()
    notification = create_test_notification(
        recipient=recipient,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
    )
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    delivery = PushDelivery.objects.get()
    assert delivery.status == PushDelivery.Status.SKIPPED
    assert delivery.error_code == "missing_navigation"
    send_web_push.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_is_idempotent_after_sent():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        first_count = run_push_for_notification(notification.id)
        second_count = run_push_for_notification(notification.id)

    assert first_count == 1
    assert second_count == 0
    assert PushDelivery.objects.count() == 1
    assert PushDelivery.objects.get().status == PushDelivery.Status.SENT
    assert send_web_push.call_count == 1


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_does_not_retry_failed_delivery():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)
    PushDelivery.objects.create(
        notification_id=notification.id,
        subscription_id=subscription.id,
        status=PushDelivery.Status.FAILED,
        error_code="http_500",
    )

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    delivery = PushDelivery.objects.get()
    assert delivery.status == PushDelivery.Status.FAILED
    assert delivery.error_code == "http_500"
    send_web_push.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_revokes_subscription_on_410():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)
    response = type("Response", (), {"status_code": 410})()

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch(
            "houston.notifications.push.services.send_web_push",
            side_effect=WebPushException("gone", response=response),
        ),
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    delivery = PushDelivery.objects.get()
    assert delivery.status == PushDelivery.Status.FAILED
    assert delivery.error_code == "http_410"
    subscription.refresh_from_db()
    assert subscription.revoked_at is not None


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_marks_unknown_web_push_error():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
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
    assert delivery.error_code == "unknown"


@override_settings(**VAPID_SETTINGS)
def test_try_claim_push_delivery_for_send_is_exclusive():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)
    delivery = PushDelivery.objects.create(
        notification_id=notification.id,
        subscription_id=subscription.id,
        status=PushDelivery.Status.QUEUED,
    )
    now = timezone.now()

    assert _try_claim_push_delivery_for_send(delivery_id=delivery.id, now=now) is True
    delivery.refresh_from_db()
    assert delivery.status == PushDelivery.Status.PROCESSING
    assert _try_claim_push_delivery_for_send(delivery_id=delivery.id, now=now) is False


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_skips_processing_delivery():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)
    PushDelivery.objects.create(
        notification_id=notification.id,
        subscription_id=subscription.id,
        status=PushDelivery.Status.PROCESSING,
    )

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    send_web_push.assert_not_called()
    assert PushDelivery.objects.get().status == PushDelivery.Status.PROCESSING


@override_settings(**VAPID_SETTINGS)
def test_run_claim_lost_does_not_send():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    _create_subscription(user=recipient.user)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch(
            "houston.notifications.push.services._try_claim_push_delivery_for_send",
            return_value=False,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    send_web_push.assert_not_called()


@override_settings(**VAPID_SETTINGS)
def test_run_push_continues_after_unexpected_send_error():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    first_subscription = _create_subscription(user=recipient.user)
    second_subscription = _create_subscription(user=recipient.user)

    def send_side_effect(*, subscription, payload):
        if subscription.id == first_subscription.id:
            raise RuntimeError("boom")

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
    deliveries = {
        delivery.subscription_id: delivery
        for delivery in PushDelivery.objects.filter(notification_id=notification.id)
    }
    assert deliveries[first_subscription.id].status == PushDelivery.Status.FAILED
    assert deliveries[first_subscription.id].error_code == "unexpected_error"
    assert deliveries[second_subscription.id].status == PushDelivery.Status.SENT


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_does_not_retry_skipped_delivery():
    recipient = _prepare_recipient()
    notification = create_test_notification(recipient=recipient)
    subscription = _create_subscription(user=recipient.user)
    PushDelivery.objects.create(
        notification_id=notification.id,
        subscription_id=subscription.id,
        status=PushDelivery.Status.SKIPPED,
        error_code="missing_navigation",
    )

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        patch("houston.notifications.push.services.send_web_push") as send_web_push,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 0
    send_web_push.assert_not_called()
    delivery = PushDelivery.objects.get()
    assert delivery.status == PushDelivery.Status.SKIPPED
    assert delivery.error_code == "missing_navigation"
