from __future__ import annotations

import uuid

import pytest

from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.permissions import (
    notification_visible_to_membership,
    recipient_can_view_notification_subject,
)
from houston.notifications.tests.conftest import create_test_notification
from houston.testing.auth import build_api_membership
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def test_notification_visible_only_to_recipient():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other = build_api_membership()
    notification = create_test_notification(recipient=recipient)

    assert notification_visible_to_membership(notification, recipient) is True
    assert notification_visible_to_membership(notification, other) is False


def test_notification_not_visible_cross_establishment():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership()
    notification = create_test_notification(recipient=recipient)

    assert notification_visible_to_membership(notification, outsider) is False


def test_recipient_can_view_action_subject():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    from django.utils import timezone

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive action title",
        instruction="Sensitive instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )

    assert recipient_can_view_notification_subject(
        recipient=staff,
        establishment_id=owner.establishment_id,
        subject_type=Notification.SubjectType.ACTION,
        subject_id=action.id,
    )


def test_recipient_cannot_view_action_subject_out_of_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership()
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    from django.utils import timezone

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive action title",
        instruction="Sensitive instruction",
        assignee_ids=[owner.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )

    assert (
        recipient_can_view_notification_subject(
            recipient=outsider,
            establishment_id=outsider.establishment_id,
            subject_type=Notification.SubjectType.ACTION,
            subject_id=action.id,
        )
        is False
    )


def test_signal_subject_type_returns_false():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    assert (
        recipient_can_view_notification_subject(
            recipient=owner,
            establishment_id=owner.establishment_id,
            subject_type=Notification.SubjectType.SIGNAL,
            subject_id=uuid.uuid4(),
        )
        is False
    )


def test_unsupported_subject_type_returns_false():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    assert (
        recipient_can_view_notification_subject(
            recipient=owner,
            establishment_id=owner.establishment_id,
            subject_type="unknown_subject",
            subject_id=uuid.uuid4(),
        )
        is False
    )
