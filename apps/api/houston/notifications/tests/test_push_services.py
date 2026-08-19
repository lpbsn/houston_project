from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import IntegrityError
from django.test import override_settings

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import PushDelivery, PushDevice
from houston.notifications.push.services import (
    run_push_for_notification,
    upsert_push_device,
)
from houston.notifications.tests.conftest import create_test_notification
from houston.notifications.tests.fcm_constants import FCM_PUSH_SETTINGS
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db

TOKEN = "fcm-token-race-test"
PLATFORM = "android"


def _force_create_race_path(monkeypatch, *, token: str) -> None:
    original_filter = PushDevice.objects.filter
    calls = {"count": 0}

    def filter_with_miss_on_first(*args, **kwargs):
        queryset = original_filter(*args, **kwargs)
        if kwargs.get("token") != token:
            return queryset
        original_first = queryset.first

        def first_with_initial_miss():
            calls["count"] += 1
            if calls["count"] == 1:
                return None
            return original_first()

        queryset.first = first_with_initial_miss  # type: ignore[method-assign]
        return queryset

    monkeypatch.setattr(PushDevice.objects, "filter", filter_with_miss_on_first)
    monkeypatch.setattr(
        PushDevice.objects,
        "create",
        lambda **_kwargs: (_ for _ in ()).throw(IntegrityError("duplicate token")),
    )


def test_upsert_recovers_from_create_race_for_same_user(monkeypatch):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    PushDevice.objects.create(
        user=recipient.user,
        token=TOKEN,
        platform="ios",
    )
    _force_create_race_path(monkeypatch, token=TOKEN)

    device = upsert_push_device(
        user=recipient.user,
        token=TOKEN,
        platform=PLATFORM,
    )

    assert PushDevice.objects.filter(token=TOKEN, revoked_at__isnull=True).count() == 1
    assert device.user_id == recipient.user_id
    assert device.platform == PLATFORM
    assert device.revoked_at is None


def test_upsert_create_race_for_other_user_transfers_ownership(monkeypatch):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    PushDevice.objects.create(
        user=owner.user,
        token=TOKEN,
        platform="ios",
    )
    _force_create_race_path(monkeypatch, token=TOKEN)

    device = upsert_push_device(
        user=outsider.user,
        token=TOKEN,
        platform=PLATFORM,
    )

    assert device.user_id == outsider.user_id
    assert PushDevice.objects.filter(token=TOKEN, revoked_at__isnull=True).count() == 1


def test_upsert_reraises_integrity_error_when_row_missing_after_create_race(monkeypatch):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _force_create_race_path(monkeypatch, token=TOKEN)

    with pytest.raises(IntegrityError, match="duplicate token"):
        upsert_push_device(
            user=recipient.user,
            token=TOKEN,
            platform=PLATFORM,
        )


@override_settings(**FCM_PUSH_SETTINGS)
def test_run_push_for_notification_treats_existing_delivery_as_idempotent(monkeypatch):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    device = PushDevice.objects.create(
        user=recipient.user,
        token=f"fcm-token-{uuid.uuid4()}",
        platform="android",
    )
    PushDelivery.objects.create(
        notification_id=notification.id,
        device_id=device.id,
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
        patch("houston.notifications.push.services.send_fcm") as send_fcm,
    ):
        sent_count = run_push_for_notification(notification.id)

    assert sent_count == 1
    send_fcm.assert_called_once()
    assert PushDelivery.objects.filter(
        notification_id=notification.id,
        device_id=device.id,
    ).count() == 1
    assert PushDelivery.objects.get().status == PushDelivery.Status.SENT


@override_settings(**FCM_PUSH_SETTINGS)
def test_run_push_for_notification_reraises_integrity_error_when_delivery_missing(
    monkeypatch,
):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    recipient.push_enabled = True
    recipient.save(update_fields=["push_enabled", "updated_at"])
    notification = create_test_notification(recipient=recipient)
    PushDevice.objects.create(
        user=recipient.user,
        token=f"fcm-token-{uuid.uuid4()}",
        platform="android",
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
