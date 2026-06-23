from __future__ import annotations

from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone

from houston.actions.models import Action
from houston.actions.services import (
    accept_action,
    cancel_action,
    create_action,
    mark_action_done,
    reassign_action,
    reopen_action,
)
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
)
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.testing.taxonomy import hotel_maintenance_setup

pytestmark = pytest.mark.django_db(transaction=True)

SENSITIVE_MARKERS = (
    "Sensitive task title",
    "Sensitive task instruction",
    "Do not leak",
)


def _notifications_for_action(*, action_id) -> list[Notification]:
    return list(
        Notification.objects.filter(
            subject_type=Notification.SubjectType.ACTION,
            subject_id=action_id,
        ).order_by("recipient_membership_id")
    )


def _recipient_ids(notifications: list[Notification]) -> set:
    return {item.recipient_membership_id for item in notifications}


def _assert_generic_copy(notification: Notification) -> None:
    for marker in SENSITIVE_MARKERS:
        assert marker not in notification.title
        assert marker not in notification.body


def test_action_created_notifies_assignees_excludes_creator_self_assign():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id, owner.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )

    notifications = _notifications_for_action(action_id=action.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.ACTION_CREATED
    assert notifications[0].priority == Notification.Priority.ACTION_REQUIRED
    _assert_generic_copy(notifications[0])


def test_staff_self_assigned_free_action_creates_zero_notifications():
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(staff.establishment)
    assign_business_unit_scope(staff, maintenance)

    action = create_action(
        establishment_id=staff.establishment_id,
        created_by=staff,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )

    assert _notifications_for_action(action_id=action.id) == []


def test_action_reassigned_notifies_new_and_removed_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    Notification.objects.filter(subject_id=action.id).delete()

    reassign_action(
        action_id=action.id,
        assignee_ids=[other_staff.id],
        actor=owner,
    )

    notifications = _notifications_for_action(action_id=action.id)
    assert _recipient_ids(notifications) == {staff.id, other_staff.id}
    assert all(
        item.event_key == Notification.EventKey.ACTION_REASSIGNED for item in notifications
    )
    for notification in notifications:
        _assert_generic_copy(notification)


def test_action_pending_validation_notifies_in_scope_validators_only():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager_in_scope = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    manager_out_of_scope = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager_in_scope, maintenance)
    assign_business_unit_scope(manager_out_of_scope, hotel)

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    accept_action(action_id=action.id, accepted_by=staff)
    mark_action_done(action_id=action.id)

    notifications = [
        item
        for item in _notifications_for_action(action_id=action.id)
        if item.event_key == Notification.EventKey.ACTION_PENDING_VALIDATION
    ]
    recipient_ids = _recipient_ids(notifications)
    assert owner.id in recipient_ids
    assert manager_in_scope.id in recipient_ids
    assert manager_out_of_scope.id not in recipient_ids
    assert staff.id not in recipient_ids
    assert all(
        item.event_key == Notification.EventKey.ACTION_PENDING_VALIDATION
        for item in notifications
    )


def test_pending_validation_notifies_validators_when_accepted_by_inactive():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager_in_scope = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager_in_scope, maintenance)

    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )

    with transaction.atomic():
        accept_action(action_id=action.id, accepted_by=staff)
        mark_action_done(action_id=action.id)
        staff.status = EstablishmentMembership.Status.DEACTIVATED
        staff.save(update_fields=["status", "updated_at"])

    notifications = [
        item
        for item in _notifications_for_action(action_id=action.id)
        if item.event_key == Notification.EventKey.ACTION_PENDING_VALIDATION
    ]
    recipient_ids = _recipient_ids(notifications)
    assert owner.id in recipient_ids
    assert manager_in_scope.id in recipient_ids
    assert staff.id not in recipient_ids


def test_action_reassigned_notifies_on_second_reassignment_within_dedupe_window():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    other_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    third_staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    Notification.objects.filter(subject_id=action.id).delete()

    reassign_action(
        action_id=action.id,
        assignee_ids=[other_staff.id],
        actor=owner,
    )
    reassign_action(
        action_id=action.id,
        assignee_ids=[third_staff.id],
        actor=owner,
    )

    other_staff_notifications = [
        item
        for item in _notifications_for_action(action_id=action.id)
        if item.recipient_membership_id == other_staff.id
        and item.event_key == Notification.EventKey.ACTION_REASSIGNED
    ]
    assert len(other_staff_notifications) == 2
    dedupe_keys = {item.dedupe_key for item in other_staff_notifications}
    assert len(dedupe_keys) == 2
    assert all(item.dedupe_key for item in other_staff_notifications)


def test_action_reopened_notifies_assignees_and_creator_deduped_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[owner.id, staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    accept_action(action_id=action.id, accepted_by=owner)
    mark_action_done(action_id=action.id)
    Notification.objects.filter(subject_id=action.id).delete()

    reopen_action(action_id=action.id, actor=owner)

    notifications = _notifications_for_action(action_id=action.id)
    assert _recipient_ids(notifications) == {staff.id}
    assert notifications[0].event_key == Notification.EventKey.ACTION_REOPENED


def test_action_canceled_notifies_assignees_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    Notification.objects.filter(subject_id=action.id).delete()

    cancel_action(action_id=action.id, actor=owner)

    notifications = _notifications_for_action(action_id=action.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.ACTION_CANCELED
    assert notifications[0].priority == Notification.Priority.INFO


def test_action_canceled_creator_assignee_overlap_single_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    manager = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.MANAGER,
    )
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    assign_business_unit_scope(manager, maintenance)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=manager,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[manager.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    Notification.objects.filter(subject_id=action.id).delete()

    cancel_action(action_id=action.id, actor=owner)

    notifications = _notifications_for_action(action_id=action.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == manager.id


def test_business_rollback_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)

    with pytest.raises(RuntimeError, match="force rollback"):
        with transaction.atomic():
            create_action(
                establishment_id=owner.establishment_id,
                created_by=owner,
                title="Sensitive task title",
                instruction="Sensitive task instruction",
                assignee_ids=[staff.id],
                due_at=timezone.now() + timezone.timedelta(days=1),
                responsible_business_unit_id=maintenance.id,
            )
            raise RuntimeError("force rollback")

    assert Notification.objects.count() == 0


def test_accept_action_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timezone.timedelta(days=1),
        responsible_business_unit_id=maintenance.id,
    )
    Notification.objects.filter(subject_id=action.id).delete()

    accept_action(action_id=action.id, accepted_by=staff)

    assert _notifications_for_action(action_id=action.id) == []


def test_notification_delivery_failure_does_not_break_action_create():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = hotel_maintenance_setup(owner.establishment)

    with patch(
        "houston.notifications.scheduling.create_in_app_notifications_for_recipients",
        side_effect=RuntimeError("notification delivery failed"),
    ):
        action = create_action(
            establishment_id=owner.establishment_id,
            created_by=owner,
            title="Sensitive task title",
            instruction="Sensitive task instruction",
            assignee_ids=[staff.id],
            due_at=timezone.now() + timezone.timedelta(days=1),
            responsible_business_unit_id=maintenance.id,
        )

    action.refresh_from_db()
    assert action.status == Action.Status.OPEN
    assert Notification.objects.filter(subject_id=action.id).count() == 0
