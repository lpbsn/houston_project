from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.db import transaction
from django.utils import timezone

from houston.actions.services import create_action
from houston.actions.tests.conftest import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
)
from houston.comments.models import Comment
from houston.comments.services import create_action_comment, create_signal_comment
from houston.establishments.models import EstablishmentMembership
from houston.notifications.constants import build_mention_dedupe_key
from houston.notifications.models import Notification
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


def _linked_action(owner):
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Sensitive task title",
        instruction="Sensitive task instruction",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        signal_id=signal.id,
    )
    return staff, signal, action


def _notifications_for_comment(*, comment_id) -> list[Notification]:
    return list(
        Notification.objects.filter(
            subject_type=Notification.SubjectType.COMMENT,
            subject_id=comment_id,
        ).order_by("recipient_membership_id")
    )


def _recipient_ids(notifications: list[Notification]) -> set:
    return {item.recipient_membership_id for item in notifications}


def _assert_generic_copy(notification: Notification) -> None:
    assert SENSITIVE_COMMENT_BODY not in notification.title
    assert SENSITIVE_COMMENT_BODY not in notification.body


def test_signal_comment_mention_notifies_in_scope_recipient():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff.id],
    )

    notifications = _notifications_for_comment(comment_id=comment.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.COMMENT_MENTION_CREATED
    assert notifications[0].priority == Notification.Priority.INFO
    assert notifications[0].dedupe_key == build_mention_dedupe_key(
        comment_id=comment.id,
        mentioned_membership_id=staff.id,
    )
    _assert_generic_copy(notifications[0])


def test_action_comment_mention_notifies_in_scope_recipient():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff, _, action = _linked_action(owner)

    comment = create_action_comment(
        author_membership=owner,
        action=action,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff.id],
    )

    notifications = _notifications_for_comment(comment_id=comment.id)
    assert len(notifications) == 1
    assert notifications[0].recipient_membership_id == staff.id
    assert notifications[0].event_key == Notification.EventKey.COMMENT_MENTION_CREATED
    _assert_generic_copy(notifications[0])


def test_action_comment_mention_skips_out_of_scope_recipient():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff_in_scope, _, action = _linked_action(owner)
    staff_out_of_scope = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )

    comment = create_action_comment(
        author_membership=owner,
        action=action,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff_out_of_scope.id],
    )

    assert staff_in_scope.id != staff_out_of_scope.id
    assert _notifications_for_comment(comment_id=comment.id) == []


def test_self_mention_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal, _, _ = _signal(owner)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="note",
        mentioned_membership_ids=[owner.id],
    )

    assert comment.mention_links.filter(mentioned_membership_id=owner.id).exists()
    assert _notifications_for_comment(comment_id=comment.id) == []


def test_mentioned_recipient_inactive_before_delivery_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)

    with transaction.atomic():
        comment = create_signal_comment(
            author_membership=owner,
            signal=signal,
            body=SENSITIVE_COMMENT_BODY,
            mentioned_membership_ids=[staff.id],
        )
        staff.status = EstablishmentMembership.Status.DEACTIVATED
        staff.save(update_fields=["status", "updated_at"])

    assert _notifications_for_comment(comment_id=comment.id) == []


def test_mention_notification_excludes_comment_body():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff.id],
    )

    notifications = _notifications_for_comment(comment_id=comment.id)
    assert len(notifications) == 1
    _assert_generic_copy(notifications[0])


def test_duplicate_mention_ids_create_single_notification():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="hello",
        mentioned_membership_ids=[staff.id, staff.id],
    )

    assert comment.mention_links.count() == 1
    notifications = _notifications_for_comment(comment_id=comment.id)
    assert len(notifications) == 1
    assert _recipient_ids(notifications) == {staff.id}


def test_business_rollback_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)

    with pytest.raises(RuntimeError, match="force rollback"):
        with transaction.atomic():
            create_signal_comment(
                author_membership=owner,
                signal=signal,
                body="hello",
                mentioned_membership_ids=[staff.id],
            )
            raise RuntimeError("force rollback")

    assert (
        Notification.objects.filter(
            event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        ).count()
        == 0
    )


def test_notification_delivery_failure_does_not_break_comment_create():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, _, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)

    with patch(
        "houston.notifications.scheduling.create_in_app_notification",
        side_effect=RuntimeError("notification delivery failed"),
    ):
        comment = create_signal_comment(
            author_membership=owner,
            signal=signal,
            body=SENSITIVE_COMMENT_BODY,
            mentioned_membership_ids=[staff.id],
        )

    comment.refresh_from_db()
    assert Comment.objects.filter(id=comment.id).exists()
    assert _notifications_for_comment(comment_id=comment.id) == []


def test_comment_without_mentions_creates_zero_notifications():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal, _, _ = _signal(owner)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="hello",
    )

    assert comment.mention_links.count() == 0
    assert _notifications_for_comment(comment_id=comment.id) == []
