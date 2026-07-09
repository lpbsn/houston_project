from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from django.test import override_settings

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.services import create_in_app_notification
from houston.testing.auth import build_api_membership, build_api_membership_on_establishment

pytestmark = pytest.mark.django_db(transaction=True)


def _create_notification(*, recipient, actor):
    return create_in_app_notification(
        establishment_id=recipient.establishment_id,
        recipient_membership=recipient,
        event_key=Notification.EventKey.SIGNAL_CREATED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=uuid.uuid4(),
        priority=Notification.Priority.ACTION_REQUIRED,
        actor_membership=actor,
        skip_subject_visibility_recheck=True,
    )


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_create_in_app_notification_enqueues_push_task_on_commit():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)

    with patch("houston.notifications.push.tasks.send_push_for_notification_task.delay") as delay:
        notification = _create_notification(recipient=staff, actor=owner)
        delay.assert_called_once_with(str(notification.id))


@override_settings(HOUSTON_PUSH_ENABLED=False)
def test_create_in_app_notification_does_not_enqueue_when_push_disabled():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)

    with patch("houston.notifications.push.tasks.send_push_for_notification_task.delay") as delay:
        _create_notification(recipient=staff, actor=owner)
        delay.assert_not_called()


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_create_in_app_notification_does_not_enqueue_on_transaction_rollback():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)

    with patch("houston.notifications.push.tasks.send_push_for_notification_task.delay") as delay:
        with pytest.raises(RuntimeError, match="force rollback"):
            with transaction.atomic():
                _create_notification(recipient=staff, actor=owner)
                raise RuntimeError("force rollback")

        delay.assert_not_called()


def test_create_in_app_notification_does_not_enqueue_when_notification_not_created():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    staff.notifications_enabled = False
    staff.save(update_fields=["notifications_enabled", "updated_at"])

    with patch("houston.notifications.push.tasks.send_push_for_notification_task.delay") as delay:
        notification = _create_notification(recipient=staff, actor=owner)
        assert notification is None
        delay.assert_not_called()
