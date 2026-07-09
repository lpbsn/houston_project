from __future__ import annotations

import pytest

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.comments.services import (
    create_action_plan_execution_comment,
    create_signal_comment,
)
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.navigation import resolve_notification_url
from houston.notifications.tests.conftest import create_test_notification
from houston.testing.auth import (
    assign_business_unit_scope,
    build_api_membership,
    build_api_membership_on_establishment,
)
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db(transaction=True)


def _signal(owner):
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    return (
        create_signal_v3_for_membership(
            owner,
            affected_business_unit=hotel,
            responsible_business_unit=maintenance,
            activity_subject=electricite,
        ),
        maintenance,
    )


def test_resolve_notification_url_for_signal():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal, _maintenance = _signal(owner)
    notification = create_test_notification(
        recipient=owner,
        event_key=Notification.EventKey.SIGNAL_CREATED,
        subject_type=Notification.SubjectType.SIGNAL,
        subject_id=signal.id,
    )

    assert resolve_notification_url(notification) == f"/signals/{signal.id}"


def test_resolve_notification_url_for_action_plan_execution():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked execution",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    notification = create_test_notification(
        recipient=staff,
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
    )

    assert resolve_notification_url(notification) == f"/action-plans/executions/{execution.id}"


def test_resolve_notification_url_for_signal_comment_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body="mention body",
        mentioned_membership_ids=[staff.id],
    )
    notification = create_test_notification(
        recipient=staff,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment.id,
    )

    assert resolve_notification_url(notification) == (
        f"/signals/{signal.id}?tab=comments&commentId={comment.id}"
    )


def test_resolve_notification_url_for_execution_comment_mention():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked execution",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    comment = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body="mention body",
        mentioned_membership_ids=[staff.id],
    )
    notification = create_test_notification(
        recipient=staff,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment.id,
    )

    assert resolve_notification_url(notification) == (
        f"/action-plans/executions/{execution.id}?tab=comments&commentId={comment.id}"
    )


def test_resolve_notification_url_returns_none_for_chat_conversation():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(
        recipient=owner,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
        subject_type=Notification.SubjectType.CHAT_CONVERSATION,
    )

    assert resolve_notification_url(notification) is None


def test_resolve_notification_url_returns_none_for_orphan_comment():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(
        recipient=owner,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
    )

    assert resolve_notification_url(notification) is None
