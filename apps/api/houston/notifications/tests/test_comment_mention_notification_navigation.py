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
from houston.notifications.tests.conftest import (
    NOTIFICATION_RESPONSE_ALLOWLIST,
    create_test_notification,
    notifications_url,
)
from houston.testing.auth import (
    assign_business_unit_scope,
    auth_headers,
    build_api_membership,
    build_api_membership_on_establishment,
    login,
)
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
        maintenance,
    )


def _execution(owner, staff, signal, maintenance):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Linked execution",
        source_signal_id=signal.id,
        tasks=[build_task_payload(task="Inspect", business_unit=maintenance, position=1)],
        assignees=[build_assignee_payload(membership=staff, business_unit=maintenance)],
    )
    return execution


def _mention_notification(*, recipient, comment, actor):
    return Notification.objects.filter(
        recipient_membership_id=recipient.id,
        subject_type=Notification.SubjectType.COMMENT,
        subject_id=comment.id,
    ).get()


def test_list_notifications_includes_signal_comment_navigation(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)

    comment = create_signal_comment(
        author_membership=owner,
        signal=signal,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff.id],
    )
    notification = _mention_notification(recipient=staff, comment=comment, actor=owner)

    token = login(api_client, user=staff.user)
    response = api_client.get(
        notifications_url(staff.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert set(item.keys()) == NOTIFICATION_RESPONSE_ALLOWLIST
    assert item["id"] == str(notification.id)
    assert item["navigation"] == {
        "parent_subject_type": "signal",
        "parent_subject_id": str(signal.id),
    }
    assert SENSITIVE_COMMENT_BODY not in item["title"]
    assert SENSITIVE_COMMENT_BODY not in item["body"]


def test_list_notifications_includes_execution_comment_navigation(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    signal, maintenance = _signal(owner)
    assign_business_unit_scope(staff, maintenance)
    execution = _execution(owner, staff, signal, maintenance)

    comment = create_action_plan_execution_comment(
        author_membership=owner,
        execution=execution,
        body=SENSITIVE_COMMENT_BODY,
        mentioned_membership_ids=[staff.id],
    )
    notification = _mention_notification(recipient=staff, comment=comment, actor=owner)

    token = login(api_client, user=staff.user)
    response = api_client.get(
        notifications_url(staff.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == str(notification.id)
    assert item["navigation"] == {
        "parent_subject_type": "action_plan_execution",
        "parent_subject_id": str(execution.id),
    }
    assert SENSITIVE_COMMENT_BODY not in item["title"]
    assert SENSITIVE_COMMENT_BODY not in item["body"]


def test_list_notifications_returns_null_navigation_when_comment_missing(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(
        recipient=recipient,
        event_key=Notification.EventKey.COMMENT_MENTION_CREATED,
        subject_type=Notification.SubjectType.COMMENT,
        title="Mention",
        body="Vous avez été mentionné dans un commentaire.",
    )

    token = login(api_client, user=recipient.user)
    response = api_client.get(
        notifications_url(recipient.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["id"] == str(notification.id)
    assert item["subject_type"] == "comment"
    assert item["navigation"] is None


def test_non_comment_notifications_have_null_navigation(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=recipient)

    token = login(api_client, user=recipient.user)
    response = api_client.get(
        notifications_url(recipient.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["navigation"] is None
