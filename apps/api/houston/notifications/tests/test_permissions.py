from __future__ import annotations

import uuid

import pytest

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.permissions import (
    notification_visible_to_membership,
    recipient_can_view_notification_subject,
)
from houston.notifications.tests.conftest import create_test_notification
from houston.signals.models import Signal
from houston.signals.tests.conftest import create_minimal_v3_signal
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
)
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


def test_recipient_can_view_action_plan_execution_subject():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Sensitive plan execution",
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )

    assert recipient_can_view_notification_subject(
        recipient=staff,
        establishment_id=owner.establishment_id,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
    )


def test_recipient_cannot_view_action_plan_execution_subject_out_of_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership()
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Sensitive plan execution",
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=owner, business_unit=maintenance)],
    )

    assert (
        recipient_can_view_notification_subject(
            recipient=outsider,
            establishment_id=outsider.establishment_id,
            subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
            subject_id=execution.id,
        )
        is False
    )


def test_recipient_can_view_signal_subject_open_resolved_canceled_scoped():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(staff, maintenance)

    open_signal = create_minimal_v3_signal(owner, status=Signal.Status.OPEN)
    resolved_signal = create_minimal_v3_signal(owner, status=Signal.Status.RESOLVED)
    canceled_signal = create_minimal_v3_signal(owner, status=Signal.Status.CANCELED)

    for subject_id in (open_signal.id, resolved_signal.id, canceled_signal.id):
        assert recipient_can_view_notification_subject(
            recipient=staff,
            establishment_id=owner.establishment_id,
            subject_type=Notification.SubjectType.SIGNAL,
            subject_id=subject_id,
        )


def test_recipient_can_view_canceled_signal_admin_without_pole_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    canceled_signal = create_minimal_v3_signal(owner, status=Signal.Status.CANCELED)

    assert recipient_can_view_notification_subject(
        recipient=owner,
        establishment_id=owner.establishment_id,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=canceled_signal.id,
    )


def test_recipient_can_view_canceled_signal_director_without_pole_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    canceled_signal = create_minimal_v3_signal(owner, status=Signal.Status.CANCELED)

    assert recipient_can_view_notification_subject(
        recipient=director,
        establishment_id=owner.establishment_id,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=canceled_signal.id,
    )


def test_signal_subject_unknown_id_returns_false():
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
