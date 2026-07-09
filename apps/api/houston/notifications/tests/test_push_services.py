from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.test import override_settings

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import PushDelivery, WebPushSubscription
from houston.notifications.push.exceptions import WebPushSubscriptionValidationError
from houston.notifications.push.services import (
    run_push_for_notification,
    upsert_web_push_subscription,
)
from houston.notifications.tests.conftest import create_test_notification
from houston.notifications.tests.test_push_vapid_public_key_api import (
    TEST_PRIVATE_KEY,
    TEST_PUBLIC_KEY,
)
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

ENDPOINT = "https://push.example.com/device/race-test"
P256DH = "updated-p256dh-key"
AUTH = "updated-auth-key"

VAPID_SETTINGS = {
    "HOUSTON_PUSH_ENABLED": True,
    "HOUSTON_VAPID_PUBLIC_KEY": TEST_PUBLIC_KEY,
    "HOUSTON_VAPID_PRIVATE_KEY": TEST_PRIVATE_KEY,
    "HOUSTON_VAPID_SUBJECT": "mailto:push@houston.local",
}


def _force_create_race_path(monkeypatch, *, endpoint: str) -> None:
    original_filter = WebPushSubscription.objects.filter

    def filter_with_miss_on_first(*args, **kwargs):
        queryset = original_filter(*args, **kwargs)
        if args and args[0] == endpoint:
            original_first = queryset.first
            calls = {"count": 0}

            def first_with_initial_miss():
                calls["count"] += 1
                if calls["count"] == 1:
                    return None
                return original_first()

            queryset.first = first_with_initial_miss  # type: ignore[method-assign]
        return queryset

    monkeypatch.setattr(WebPushSubscription.objects, "filter", filter_with_miss_on_first)
    monkeypatch.setattr(
        WebPushSubscription.objects,
        "create",
        lambda **_kwargs: (_ for _ in ()).throw(IntegrityError("duplicate endpoint")),
    )


def test_upsert_recovers_from_create_race_for_same_user(monkeypatch):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    WebPushSubscription.objects.create(
        user=recipient.user,
        endpoint=ENDPOINT,
        p256dh="stale-p256dh",
        auth="stale-auth",
    )
    _force_create_race_path(monkeypatch, endpoint=ENDPOINT)

    subscription = upsert_web_push_subscription(
        user=recipient.user,
        endpoint=ENDPOINT,
        p256dh=P256DH,
        auth=AUTH,
        user_agent="pytest",
    )

    assert WebPushSubscription.objects.filter(endpoint=ENDPOINT).count() == 1
    assert subscription.user_id == recipient.user_id
    assert subscription.p256dh == P256DH
    assert subscription.auth == AUTH
    assert subscription.revoked_at is None


def test_upsert_create_race_for_other_user_raises_validation_error(monkeypatch):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    WebPushSubscription.objects.create(
        user=owner.user,
        endpoint=ENDPOINT,
        p256dh="owner-p256dh",
        auth="owner-auth",
    )
    _force_create_race_path(monkeypatch, endpoint=ENDPOINT)

    with pytest.raises(
        WebPushSubscriptionValidationError,
        match="another user",
    ):
        upsert_web_push_subscription(
            user=outsider.user,
            endpoint=ENDPOINT,
            p256dh=P256DH,
            auth=AUTH,
        )


def test_upsert_reraises_integrity_error_when_row_missing_after_create_race(monkeypatch):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _force_create_race_path(monkeypatch, endpoint=ENDPOINT)

    with pytest.raises(IntegrityError, match="duplicate endpoint"):
        upsert_web_push_subscription(
            user=recipient.user,
            endpoint=ENDPOINT,
            p256dh=P256DH,
            auth=AUTH,
        )


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_treats_existing_delivery_as_idempotent(monkeypatch):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    subscription = WebPushSubscription.objects.create(
        user=recipient.user,
        endpoint=f"https://push.example.com/device/{uuid.uuid4()}",
        p256dh="p256dh-key",
        auth="auth-key",
    )
    PushDelivery.objects.create(
        notification_id=notification.id,
        subscription_id=subscription.id,
        status=PushDelivery.Status.QUEUED,
    )

    def raise_integrity_error(*_args, **_kwargs):
        raise IntegrityError("duplicate delivery")

    monkeypatch.setattr(PushDelivery.objects, "get_or_create", raise_integrity_error)

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
    assert PushDelivery.objects.filter(
        notification_id=notification.id,
        subscription_id=subscription.id,
    ).count() == 1
    assert PushDelivery.objects.get().status == PushDelivery.Status.SENT


@override_settings(**VAPID_SETTINGS)
def test_run_push_for_notification_reraises_integrity_error_when_delivery_missing(
    monkeypatch,
):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    WebPushSubscription.objects.create(
        user=recipient.user,
        endpoint=f"https://push.example.com/device/{uuid.uuid4()}",
        p256dh="p256dh-key",
        auth="auth-key",
    )

    def raise_integrity_error(*_args, **_kwargs):
        raise IntegrityError("unexpected delivery constraint")

    monkeypatch.setattr(PushDelivery.objects, "get_or_create", raise_integrity_error)

    with (
        patch(
            "houston.notifications.push.services.recipient_can_view_notification_subject",
            return_value=True,
        ),
        pytest.raises(IntegrityError, match="unexpected delivery constraint"),
    ):
        run_push_for_notification(notification.id)

    assert PushDelivery.objects.count() == 0
