from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone

from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.services import (
    NOTIFICATION_BULK_UPDATED_REASON,
    NOTIFICATION_CREATED_REASON,
    NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
    NOTIFICATION_UPDATED_REASON,
    archive_notification,
    create_in_app_notification,
    mark_all_notifications_read,
    mark_notification_read,
)
from houston.notifications.tests.conftest import create_test_notification
from houston.testing.auth import build_api_membership
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db(transaction=True)

FORBIDDEN_PAYLOAD_KEYS = frozenset(
    {
        "title",
        "body",
        "event_key",
        "actor",
        "actor_membership_id",
        "recipient_membership_id",
        "instruction",
        "subject_id",
        "priority",
        "status",
    }
)

ALLOWED_PAYLOAD_KEYS = frozenset(
    {
        "type",
        "subject_type",
        "reason",
        "establishment_id",
        "entity_id",
        "occurred_at",
    }
)


def _create_notification_without_action(*, owner, staff):
    return create_in_app_notification(
        establishment_id=owner.establishment_id,
        recipient_membership=staff,
        event_key=Notification.EventKey.ACTION_CREATED,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=uuid.uuid4(),
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=owner,
        skip_subject_visibility_recheck=True,
    )


def _open_action(*, owner, staff, maintenance):
    return create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive action title",
        instruction="Sensitive action instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )


def _create_notification(*, owner, staff, maintenance):
    del maintenance
    return _create_notification_without_action(owner=owner, staff=staff)


def test_create_emits_notification_created_after_commit():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        notification = _create_notification_without_action(owner=owner, staff=staff)

        assert notification is not None
        mock_notify.assert_called_once_with(
            establishment_id=owner.establishment_id,
            membership_id=staff.id,
            subject_type=NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
            reason=NOTIFICATION_CREATED_REASON,
            entity_id=notification.id,
        )


def test_actor_exclusion_does_not_emit_invalidation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = _open_action(owner=owner, staff=owner, maintenance=maintenance)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        notification = create_in_app_notification(
            establishment_id=owner.establishment_id,
            recipient_membership=owner,
            event_key=Notification.EventKey.ACTION_CREATED,
            subject_type=Notification.SubjectType.ACTION,
            subject_id=action.id,
            priority=Notification.Priority.ACTION_REQUIRED,
            actor_membership=owner,
        )

        assert notification is None
        mock_notify.assert_not_called()


def test_dedupe_does_not_emit_invalidation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    subject_id = uuid.uuid4()

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        first = create_in_app_notification(
            establishment_id=owner.establishment_id,
            recipient_membership=staff,
            event_key=Notification.EventKey.ACTION_CREATED,
            subject_type=Notification.SubjectType.ACTION,
            subject_id=subject_id,
            priority=Notification.Priority.ACTION_REQUIRED,
            actor_membership=owner,
            skip_subject_visibility_recheck=True,
        )
        second = create_in_app_notification(
            establishment_id=owner.establishment_id,
            recipient_membership=staff,
            event_key=Notification.EventKey.ACTION_CREATED,
            subject_type=Notification.SubjectType.ACTION,
            subject_id=subject_id,
            priority=Notification.Priority.ACTION_REQUIRED,
            actor_membership=owner,
            skip_subject_visibility_recheck=True,
        )

        assert first is not None
        assert second is None
        mock_notify.assert_called_once()


def test_create_not_emitted_on_transaction_rollback():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                _create_notification_without_action(owner=owner, staff=staff)
                raise RuntimeError("force rollback")

        mock_notify.assert_not_called()


def test_mark_read_emits_notification_updated_after_commit():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(recipient=owner, status=Notification.Status.UNREAD)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        mark_notification_read(membership=owner, notification_id=notification.id)

        mock_notify.assert_called_once_with(
            establishment_id=owner.establishment_id,
            membership_id=owner.id,
            subject_type=NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
            reason=NOTIFICATION_UPDATED_REASON,
            entity_id=notification.id,
        )


def test_mark_read_idempotent_does_not_emit_invalidation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(recipient=owner, status=Notification.Status.READ)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        mark_notification_read(membership=owner, notification_id=notification.id)

        mock_notify.assert_not_called()


def test_archive_emits_notification_updated_after_commit():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(recipient=owner, status=Notification.Status.UNREAD)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        archive_notification(membership=owner, notification_id=notification.id)

        mock_notify.assert_called_once_with(
            establishment_id=owner.establishment_id,
            membership_id=owner.id,
            subject_type=NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
            reason=NOTIFICATION_UPDATED_REASON,
            entity_id=notification.id,
        )


def test_mark_all_read_emits_bulk_updated_with_membership_entity_id():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=owner, status=Notification.Status.UNREAD)
    create_test_notification(recipient=owner, status=Notification.Status.UNREAD)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        updated = mark_all_notifications_read(
            membership=owner,
            establishment_id=owner.establishment_id,
        )

        assert updated == 2
        mock_notify.assert_called_once_with(
            establishment_id=owner.establishment_id,
            membership_id=owner.id,
            subject_type=NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
            reason=NOTIFICATION_BULK_UPDATED_REASON,
            entity_id=owner.id,
        )


def test_mark_all_read_zero_updates_does_not_emit_invalidation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)

    with patch("houston.realtime.broadcast.notify_membership_invalidation") as mock_notify:
        updated = mark_all_notifications_read(
            membership=owner,
            establishment_id=owner.establishment_id,
        )

        assert updated == 0
        mock_notify.assert_not_called()


def test_notification_invalidate_payload_allowlist():
    from houston.realtime.ws_payloads import build_invalidate_payload

    payload = build_invalidate_payload(
        subject_type=NOTIFICATION_INVALIDATION_SUBJECT_TYPE,
        reason=NOTIFICATION_CREATED_REASON,
        establishment_id=uuid.uuid4(),
        entity_id=uuid.uuid4(),
    )

    assert set(payload.keys()) == ALLOWED_PAYLOAD_KEYS
    assert FORBIDDEN_PAYLOAD_KEYS.isdisjoint(payload.keys())
    assert payload["type"] == "invalidate"
    assert payload["subject_type"] == NOTIFICATION_INVALIDATION_SUBJECT_TYPE
