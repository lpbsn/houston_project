from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import transaction

from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    reopen_action_plan_execution,
)
from houston.action_plans.tests.helpers import (
    build_assignee_payload,
    build_task_payload,
    create_open_signal,
)
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.testing.factories import create_membership
from houston.testing.taxonomy import create_membership_with_business_unit_scope

pytestmark = pytest.mark.django_db(transaction=True)

SENSITIVE_MARKERS = (
    "Sensitive plan title",
    "Sensitive task",
    "Sensitive signal title",
    "Sensitive observation summary",
    "Do not leak",
)


def _notifications_for_execution(*, execution_id) -> list[Notification]:
    return list(
        Notification.objects.filter(
            subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
            subject_id=execution_id,
        ).order_by("recipient_membership_id")
    )


def _assert_generic_copy(notification: Notification) -> None:
    for marker in SENSITIVE_MARKERS:
        assert marker not in notification.title
        assert marker not in notification.body


def _maintenance_staff(establishment, maintenance_business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=maintenance_business_unit,
    )
    return membership


def _creation_notifications(*, execution_id) -> list[Notification]:
    return [
        item
        for item in _notifications_for_execution(execution_id=execution_id)
        if item.event_key
        in {
            Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
            Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED_FROM_SIGNAL,
        }
    ]


def test_execution_created_from_signal_when_source_signal_set(
    owner_membership,
    establishment,
):
    signal = create_open_signal(
        owner_membership=owner_membership,
        title="Sensitive signal title",
    )
    maintenance_business_unit = signal.responsible_business_unit
    assert maintenance_business_unit is not None
    staff_membership = _maintenance_staff(establishment, maintenance_business_unit)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Sensitive plan title",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Sensitive task", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=staff_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    notifications = _creation_notifications(execution_id=execution.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff_membership.id
    assert (
        notifications[0].event_key
        == Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED_FROM_SIGNAL
    )


def test_execution_created_unchanged_when_source_signal_null(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Sensitive plan title",
        tasks=[build_task_payload(task="Sensitive task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    notifications = _creation_notifications(execution_id=execution.id)
    assert len(notifications) == 1
    assert notifications[0].event_key == Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED


def test_execution_created_exclusive_no_double_event(
    owner_membership,
    establishment,
):
    signal = create_open_signal(owner_membership=owner_membership)
    maintenance_business_unit = signal.responsible_business_unit
    assert maintenance_business_unit is not None
    staff_membership = _maintenance_staff(establishment, maintenance_business_unit)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Exclusive plan",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Task", business_unit=maintenance_business_unit)],
        assignees=[
            build_assignee_payload(
                membership=staff_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    creation_event_keys = {
        item.event_key for item in _creation_notifications(execution_id=execution.id)
    }
    assert creation_event_keys == {
        Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED_FROM_SIGNAL,
    }


def test_execution_created_from_signal_excludes_actor_self_assign(
    owner_membership,
    establishment,
):
    signal = create_open_signal(owner_membership=owner_membership)
    maintenance_business_unit = signal.responsible_business_unit
    assert maintenance_business_unit is not None

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Self-assign signal plan",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Task", business_unit=maintenance_business_unit)],
        assignees=[
            build_assignee_payload(
                membership=owner_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    notifications = _creation_notifications(execution_id=execution.id)
    assert notifications == []


def test_execution_created_from_signal_copy_safe(
    owner_membership,
    establishment,
):
    signal = create_open_signal(
        owner_membership=owner_membership,
        title="Sensitive signal title",
    )
    maintenance_business_unit = signal.responsible_business_unit
    assert maintenance_business_unit is not None
    staff_membership = _maintenance_staff(establishment, maintenance_business_unit)

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=maintenance_business_unit.id,
        title="Sensitive plan title",
        source_signal_id=signal.id,
        tasks=[
            build_task_payload(task="Sensitive task", business_unit=maintenance_business_unit)
        ],
        assignees=[
            build_assignee_payload(
                membership=staff_membership,
                business_unit=maintenance_business_unit,
            )
        ],
    )

    notifications = _creation_notifications(execution_id=execution.id)
    assert len(notifications) == 1
    _assert_generic_copy(notifications[0])
    assert notifications[0].title == "Plan d'action lié à une observation"
    assert (
        notifications[0].body
        == "Une exécution de plan d'action a été créée à partir d'une observation."
    )


def test_execution_created_notifies_assignees_excludes_creator_self_assign(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Sensitive plan title",
        tasks=[build_task_payload(task="Sensitive task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    notifications = _notifications_for_execution(execution_id=execution.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff_membership.id
    assert notifications[0].event_key == Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED
    _assert_generic_copy(notifications[0])


def test_pending_validation_notifies_validators(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Validation plan",
        requires_validation=True,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )

    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=staff_membership,
    )

    notifications = _notifications_for_execution(execution_id=execution.id)
    event_keys = {item.event_key for item in notifications}
    assert Notification.EventKey.ACTION_PLAN_EXECUTION_PENDING_VALIDATION in event_keys
    for notification in notifications:
        if notification.event_key == Notification.EventKey.ACTION_PLAN_EXECUTION_PENDING_VALIDATION:
            _assert_generic_copy(notification)


def test_canceled_notifies_assignees_excludes_actor(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Cancel plan",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    Notification.objects.filter(subject_id=execution.id).delete()

    cancel_action_plan_execution(
        execution_id=execution.id,
        actor=owner_membership,
    )

    notifications = [
        item
        for item in _notifications_for_execution(execution_id=execution.id)
        if item.event_key == Notification.EventKey.ACTION_PLAN_EXECUTION_CANCELED
    ]
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff_membership.id
    for notification in notifications:
        _assert_generic_copy(notification)


def test_reopened_notifies_assignees(
    owner_membership,
    business_unit,
    staff_membership,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Reopen plan",
        requires_validation=True,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=staff_membership,
    )

    reopen_action_plan_execution(
        execution_id=execution.id,
        actor=owner_membership,
    )

    notifications = [
        item
        for item in _notifications_for_execution(execution_id=execution.id)
        if item.event_key == Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED
    ]
    assert len(notifications) >= 1
    assert staff_membership.id in {item.recipient_membership_id for item in notifications}
    for notification in notifications:
        _assert_generic_copy(notification)


def test_notification_not_created_on_rollback(
    owner_membership,
    business_unit,
    staff_membership,
):
    from houston.action_plans.exceptions import ActionPlanStateError
    from houston.action_plans.services import cancel_action_plan_execution as cancel

    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title="Rollback plan",
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[
            build_assignee_payload(membership=staff_membership, business_unit=business_unit)
        ],
    )
    Notification.objects.filter(subject_id=execution.id).delete()

    with patch(
        "houston.notifications.scheduling.create_in_app_notifications_for_recipients",
    ) as mock_create:
        with pytest.raises(ActionPlanStateError):
            with transaction.atomic():
                cancel(
                    execution_id=execution.id,
                    actor=owner_membership,
                )
                raise ActionPlanStateError("force rollback")
        transaction.on_commit(lambda: None)

    mock_create.assert_not_called()
