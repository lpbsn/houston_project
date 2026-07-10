from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.db import transaction
from django.test import override_settings

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.services import (
    create_action_plan_execution_comment,
    create_signal_comment,
)
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.recipients import resolve_comment_reply_created_recipients
from houston.signals.models import SignalSourceObservation
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
)
from houston.testing.pipeline import create_observation
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db(transaction=True)

SENSITIVE_COMMENT_BODY = "Secret comment body should never appear in notification copy"


def _signal(owner):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return (
        create_signal_v3_for_membership(
            owner,
            affected_business_unit=hotel,
            responsible_business_unit=maintenance,
            activity_subject=electricite,
        ),
        hotel,
        maintenance,
    )


def _notifications_for_comment(
    *,
    comment_id: uuid.UUID,
    event_key: str | None = None,
) -> list[Notification]:
    queryset = Notification.objects.filter(
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment_id,
    )
    if event_key is not None:
        queryset = queryset.filter(event_key=event_key)
    return list(queryset.order_by("recipient_membership_id", "event_key"))


def _recipient_ids(notifications: list[Notification]) -> set[uuid.UUID]:
    return {item.recipient_membership_id for item in notifications}


def _assert_generic_copy(notification: Notification) -> None:
    assert SENSITIVE_COMMENT_BODY not in notification.title
    assert SENSITIVE_COMMENT_BODY not in notification.body


def _linked_execution(*, owner, staff, signal, maintenance):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked execution",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    return execution


def _execution_without_signal(*, owner, staff, maintenance):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Standalone execution",
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    return execution


def test_signal_comment_notifies_linked_execution_assignee_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _linked_execution(owner=owner, staff=staff, signal=signal, maintenance=maintenance)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body=SENSITIVE_COMMENT_BODY,
    )

    notifications = _notifications_for_comment(
        comment_id=comment.id,
        event_key=Notification.EventKey.COMMENT_SIGNAL_CREATED,
    )
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    _assert_generic_copy(notifications[0])


def test_signal_comment_notifies_observation_reporter():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    reporter = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(reporter, maintenance)
    observation = create_observation(membership=reporter, text="A" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body=SENSITIVE_COMMENT_BODY,
    )

    notifications = _notifications_for_comment(
        comment_id=comment.id,
        event_key=Notification.EventKey.COMMENT_SIGNAL_CREATED,
    )
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == reporter.id


def test_signal_comment_mention_and_assignee_same_person_only_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _linked_execution(owner=owner, staff=staff, signal=signal, maintenance=maintenance)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff.id],
    )

    notifications = _notifications_for_comment(comment_id=comment.id)
    assert len(notifications) == 1
    assert notifications[0].event_key == Notification.EventKey.COMMENT_MENTION_CREATED
    assert notifications[0].recipient_membership_id == staff.id


def test_signal_comment_recipient_inactive_before_delivery_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _linked_execution(owner=owner, staff=staff, signal=signal, maintenance=maintenance)

    with transaction.atomic():
        comment = create_signal_comment(
            author_membership=owner,
            signal=signal,
            body=SENSITIVE_COMMENT_BODY,
        )
        staff.status = EstablishmentMembership.Status.DEACTIVATED
        staff.save(update_fields=["status", "updated_at"])

    assert (
        _notifications_for_comment(
            comment_id=comment.id,
            event_key=Notification.EventKey.COMMENT_SIGNAL_CREATED,
        )
        == []
    )


def test_signal_comment_rollback_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _linked_execution(owner=owner, staff=staff, signal=signal, maintenance=maintenance)

    with pytest.raises(RuntimeError, match="force rollback"):
        with transaction.atomic():
            create_signal_comment(
                author_membership=owner,
                signal=signal,
                body=SENSITIVE_COMMENT_BODY,
            )
            raise RuntimeError("force rollback")

    assert (
        Notification.objects.filter(
            event_key=Notification.EventKey.COMMENT_SIGNAL_CREATED,
        ).count()
        == 0
    )


def test_root_execution_comment_notifies_assignee_and_creator_excludes_actor():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)

    comment = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
    )

    notifications = _notifications_for_comment(
        comment_id=comment.id,
        event_key=Notification.EventKey.COMMENT_ACTION_PLAN_EXECUTION_CREATED,
    )
    assert _recipient_ids(notifications) == {staff.id}
    _assert_generic_copy(notifications[0])


def test_root_execution_comment_creator_self_assign_creates_single_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Self assign",
        tasks=[build_task_payload(task="Task", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=owner, business_unit=maintenance)],
    )

    comment = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
    )

    notifications = _notifications_for_comment(
        comment_id=comment.id,
        event_key=Notification.EventKey.COMMENT_ACTION_PLAN_EXECUTION_CREATED,
    )
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == owner.id


def test_root_execution_comment_mentioned_assignee_only_gets_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)

    comment = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff.id],
    )

    notifications = _notifications_for_comment(comment_id=comment.id)
    assert len(notifications) == 1
    assert notifications[0].event_key == Notification.EventKey.COMMENT_MENTION_CREATED
    assert notifications[0].recipient_membership_id == staff.id


def test_reply_does_not_emit_execution_created_event():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
    )

    reply = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        parent_comment_id=root.id,
    )

    assert (
        _notifications_for_comment(
            comment_id=reply.id,
            event_key=Notification.EventKey.COMMENT_ACTION_PLAN_EXECUTION_CREATED,
        )
        == []
    )


def test_reply_notifies_root_author():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
    )

    reply = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        parent_comment_id=root.id,
    )

    notifications = _notifications_for_comment(
        comment_id=reply.id,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
    )
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == owner.id
    _assert_generic_copy(notifications[0])


def test_second_reply_notifies_root_author_and_first_replier():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    third = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    assign_business_unit_scope(third, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
    )
    create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body="first reply",
        parent_comment_id=root.id,
    )

    second_reply = create_action_plan_execution_comment(
        author_membership=third,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        parent_comment_id=root.id,
    )

    notifications = _notifications_for_comment(
        comment_id=second_reply.id,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
    )
    assert _recipient_ids(notifications) == {owner.id, staff.id}


def test_reply_notifies_root_mention_on_subsequent_reply():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    mentioned = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    assign_business_unit_scope(mentioned, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
        mentioned_membership_ids=[mentioned.id],
    )

    reply = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        parent_comment_id=root.id,
    )

    notifications = _notifications_for_comment(
        comment_id=reply.id,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
    )
    assert mentioned.id in _recipient_ids(notifications)


def test_reply_mention_only_for_reply_mentionee():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    mentioned = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    assign_business_unit_scope(mentioned, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
    )

    reply = create_action_plan_execution_comment(
        author_membership=staff,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        parent_comment_id=root.id,
        mentioned_membership_ids=[mentioned.id],
    )

    reply_notifications = _notifications_for_comment(
        comment_id=reply.id,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
    )
    assert mentioned.id not in _recipient_ids(reply_notifications)

    mention_notifications = _notifications_for_comment(
        comment_id=reply.id,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
    )
    assert len(mention_notifications) == 1
    assert mention_notifications[0].recipient_membership_id == mentioned.id


def test_assignee_not_notified_on_reply_when_not_in_thread():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    third = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    _, maintenance, _ = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    assign_business_unit_scope(third, maintenance)
    execution = _execution_without_signal(owner=owner, staff=staff, maintenance=maintenance)
    root = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="root",
    )

    reply = create_action_plan_execution_comment(
        author_membership=third,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        parent_comment_id=root.id,
    )

    notifications = _notifications_for_comment(
        comment_id=reply.id,
        event_key=Notification.EventKey.COMMENT_REPLY_CREATED,
    )
    assert staff.id not in _recipient_ids(notifications)


def test_resolve_comment_reply_recipients_requires_execution_parent():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal, _, _ = _signal(owner)
    signal_comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="signal only",
    )

    assert resolve_comment_reply_created_recipients(reply_comment=signal_comment) == []


@override_settings(HOUSTON_PUSH_ENABLED=True)
def test_signal_comment_creation_enqueues_push_for_eligible_recipient():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _linked_execution(owner=owner, staff=staff, signal=signal, maintenance=maintenance)

    with patch("houston.notifications.push.tasks.send_push_for_notification_task.delay") as delay:
        create_signal_comment(
            author_membership=owner,
            signal=signal,
            body=SENSITIVE_COMMENT_BODY,
        )

    assert delay.call_count == 1
