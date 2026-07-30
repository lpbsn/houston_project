from __future__ import annotations

import pytest

from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import (
    action_plan_execution_url,
    build_assignee_payload,
    build_task_payload,
)
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def _execution_with_assignee(owner, staff, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=business_unit.id,
        title="Lifecycle plan",
        requires_validation=True,
        tasks=[build_task_payload(task="Task 1", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=staff, business_unit=business_unit)],
    )
    return execution


def test_execution_detail_visible_to_assignee(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plan_execution_url(staff_membership.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(execution.id)
    assert len(body["task_executions"]) == 1
    assert len(body["involved_poles"]) >= 1


def test_execution_detail_exposes_audit_current_fields_without_journal(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.action_plans.services import mark_action_plan_execution_done

    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    mark_action_plan_execution_done(
        execution_id=execution.id,
        actor_membership=owner_membership,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        action_plan_execution_url(owner_membership.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["marked_done_by_membership_id"] == str(owner_membership.id)
    assert body["marked_done_by_display_name"]
    assert body["marked_done_at"]
    assert body["validated_by_membership_id"] is None
    assert body["canceled_by_membership_id"] is None
    assert body["cancel_origin"] is None
    assert body["reopened_by_membership_id"] is None
    assert body["reopened_at"] is None
    assert body["started_by_membership_id"] is None
    assert body["started_at"] is None
    assert body["reactivated_by_membership_id"] is None
    assert body["reactivated_at"] is None
    assert "lifecycle_events" not in body
    assert "lifecycle_event" not in body


def test_execution_lifecycle_mark_done_validate_rejects_reopen(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from unittest.mock import patch

    from houston.action_plans.constants import EXECUTION_LIFECYCLE_EVENT_REOPENED
    from houston.action_plans.models import ActionPlanExecutionLifecycleEvent
    from houston.notifications.models import Notification
    from houston.signals.models import Signal
    from houston.testing.taxonomy import create_minimal_v3_signal

    _ = business_unit, staff_membership
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Validated done reopen rejected",
        status=Signal.Status.IN_PROGRESS,
    )
    pilot_bu = signal.responsible_business_unit
    assert pilot_bu is not None
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=pilot_bu.id,
        title="Lifecycle plan validated",
        source_signal_id=signal.id,
        requires_validation=True,
        tasks=[build_task_payload(task="Task 1", business_unit=pilot_bu)],
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=pilot_bu)
        ],
        use_shared_chronology=True,
    )
    owner_token = login(api_client, user=owner_membership.user)
    detail_url = action_plan_execution_url(owner_membership.establishment_id, execution.id)

    mark_done = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "mark-done/"),
        **auth_headers(owner_token),
    )
    assert mark_done.status_code == 200
    assert mark_done.json()["status"] == ActionPlanExecution.Status.PENDING_VALIDATION

    before_validate = api_client.get(detail_url, **auth_headers(owner_token))
    assert before_validate.status_code == 200
    assert before_validate.json()["active_review"] is None

    validate = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "validate/"),
        {"stars": 4, "comment": "Bien fait"},
        format="json",
        **auth_headers(owner_token),
    )
    assert validate.status_code == 200
    assert validate.json()["status"] == ActionPlanExecution.Status.DONE
    validated_at = validate.json()["validated_at"]
    assert validated_at is not None

    after_validate = api_client.get(detail_url, **auth_headers(owner_token))
    assert after_validate.status_code == 200
    assert after_validate.json()["active_review"] == {
        "stars": 4,
        "comment": "Bien fait",
    }
    assert after_validate.json()["permission_hints"]["can_reopen"] is False

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    signal_status_before = signal.status
    signal_resolved_at = signal.resolved_at
    event_count_before = ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution_id=execution.id,
    ).count()
    notif_count_before = Notification.objects.filter(
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
    ).count()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        reopen = api_client.post(
            action_plan_execution_url(owner_membership.establishment_id, execution.id, "reopen/"),
            **auth_headers(owner_token),
        )
    assert reopen.status_code == 400
    assert reopen.json() == {
        "code": "invalid_action_plan_state",
        "detail": "Execution cannot be reopened in its current state.",
    }
    mock_notify.assert_not_called()

    after_reopen = api_client.get(detail_url, **auth_headers(owner_token))
    assert after_reopen.status_code == 200
    assert after_reopen.json()["status"] == ActionPlanExecution.Status.DONE
    assert after_reopen.json()["validated_at"] == validated_at
    assert after_reopen.json()["active_review"] == {
        "stars": 4,
        "comment": "Bien fait",
    }
    assert after_reopen.json()["reopened_at"] is None
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution_id=execution.id,
        ).count()
        == event_count_before
    )
    assert not ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution_id=execution.id,
        event_type=EXECUTION_LIFECYCLE_EVENT_REOPENED,
    ).exists()
    assert (
        Notification.objects.filter(
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
            subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
            subject_id=execution.id,
        ).count()
        == notif_count_before
    )
    signal.refresh_from_db()
    assert signal.status == signal_status_before
    assert signal.resolved_at == signal_resolved_at


def test_execution_lifecycle_done_without_validation_rejects_reopen(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from unittest.mock import patch

    from houston.action_plans.constants import EXECUTION_LIFECYCLE_EVENT_REOPENED
    from houston.action_plans.models import ActionPlanExecutionLifecycleEvent
    from houston.notifications.models import Notification
    from houston.signals.models import Signal
    from houston.testing.taxonomy import create_minimal_v3_signal

    _ = business_unit, staff_membership
    signal = create_minimal_v3_signal(
        owner_membership,
        title="Unvalidated done reopen rejected",
        status=Signal.Status.IN_PROGRESS,
    )
    pilot_bu = signal.responsible_business_unit
    assert pilot_bu is not None
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=pilot_bu.id,
        title="No validation lifecycle",
        source_signal_id=signal.id,
        requires_validation=False,
        assignees=[
            build_assignee_payload(membership=owner_membership, business_unit=pilot_bu)
        ],
        use_shared_chronology=True,
    )
    owner_token = login(api_client, user=owner_membership.user)
    detail_url = action_plan_execution_url(owner_membership.establishment_id, execution.id)

    mark_done = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "mark-done/"),
        **auth_headers(owner_token),
    )
    assert mark_done.status_code == 200
    assert mark_done.json()["status"] == ActionPlanExecution.Status.DONE
    assert mark_done.json()["validated_at"] is None
    assert mark_done.json()["permission_hints"]["can_reopen"] is False
    marked_done_at = mark_done.json()["marked_done_at"]

    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    signal_resolved_at = signal.resolved_at
    event_count_before = ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution_id=execution.id,
    ).count()
    notif_count_before = Notification.objects.filter(
        event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
    ).count()

    with patch("houston.realtime.broadcast.notify_establishment_invalidation") as mock_notify:
        reopen = api_client.post(
            action_plan_execution_url(owner_membership.establishment_id, execution.id, "reopen/"),
            **auth_headers(owner_token),
        )
    assert reopen.status_code == 400
    assert reopen.json() == {
        "code": "invalid_action_plan_state",
        "detail": "Execution cannot be reopened in its current state.",
    }
    mock_notify.assert_not_called()

    after_reopen = api_client.get(detail_url, **auth_headers(owner_token))
    assert after_reopen.status_code == 200
    assert after_reopen.json()["status"] == ActionPlanExecution.Status.DONE
    assert after_reopen.json()["validated_at"] is None
    assert after_reopen.json()["marked_done_at"] == marked_done_at
    assert after_reopen.json()["reopened_at"] is None
    assert after_reopen.json()["permission_hints"]["can_reopen"] is False
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution_id=execution.id,
        ).count()
        == event_count_before
    )
    assert not ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution_id=execution.id,
        event_type=EXECUTION_LIFECYCLE_EVENT_REOPENED,
    ).exists()
    assert (
        Notification.objects.filter(
            event_key=Notification.EventKey.ACTION_PLAN_EXECUTION_REOPENED,
            subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
            subject_id=execution.id,
        ).count()
        == notif_count_before
    )
    signal.refresh_from_db()
    assert signal.status == Signal.Status.RESOLVED
    assert signal.resolved_at == signal_resolved_at


def test_execution_lifecycle_reopen_from_pending_validation_then_cancel(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    owner_token = login(api_client, user=owner_membership.user)

    mark_done = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "mark-done/"),
        **auth_headers(owner_token),
    )
    assert mark_done.status_code == 200
    assert mark_done.json()["status"] == ActionPlanExecution.Status.PENDING_VALIDATION
    assert mark_done.json()["permission_hints"]["can_reopen"] is True

    reopen = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "reopen/"),
        **auth_headers(owner_token),
    )
    assert reopen.status_code == 200
    assert reopen.json()["status"] == ActionPlanExecution.Status.IN_PROGRESS

    cancel = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "cancel/"),
        **auth_headers(owner_token),
    )
    assert cancel.status_code == 200
    assert cancel.json()["status"] == ActionPlanExecution.Status.CANCELED


def test_validate_requires_explicit_stars(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    owner_token = login(api_client, user=owner_membership.user)
    api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "mark-done/"),
        **auth_headers(owner_token),
    )

    validate = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "validate/"),
        {},
        format="json",
        **auth_headers(owner_token),
    )

    assert validate.status_code == 400
    assert validate.json()["code"] == "invalid_input"


def test_validate_accepts_comment_at_max_length(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.action_plans.constants import ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH

    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    owner_token = login(api_client, user=owner_membership.user)
    api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "mark-done/"),
        **auth_headers(owner_token),
    )
    comment = "a" * ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH

    validate = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "validate/"),
        {"stars": 4, "comment": comment},
        format="json",
        **auth_headers(owner_token),
    )

    assert validate.status_code == 200
    assert validate.json()["active_review"] == {"stars": 4, "comment": comment}


def test_validate_rejects_comment_over_max_length(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.action_plans.constants import ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH

    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    owner_token = login(api_client, user=owner_membership.user)
    api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "mark-done/"),
        **auth_headers(owner_token),
    )

    validate = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "validate/"),
        {
            "stars": 4,
            "comment": "a" * (ACTION_PLAN_EXECUTION_REVIEW_COMMENT_MAX_LENGTH + 1),
        },
        format="json",
        **auth_headers(owner_token),
    )

    assert validate.status_code == 400
    assert validate.json()["code"] == "invalid_input"


def test_mentioned_out_of_scope_staff_can_read_execution_detail(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    out_of_scope_staff,
):
    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    from houston.comments.services import create_action_plan_execution_comment

    create_action_plan_execution_comment(
        author_membership=owner_membership,
        execution=execution,
        body="please review",
        mentioned_membership_ids=[out_of_scope_staff.id],
    )

    token = login(api_client, user=out_of_scope_staff.user)
    response = api_client.get(
        action_plan_execution_url(out_of_scope_staff.establishment_id, execution.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    hints = response.json()["permission_hints"]
    assert hints["can_validate"] is False
    assert hints["can_mark_done"] is False
    assert hints["can_cancel"] is False


def test_mentioned_out_of_scope_staff_cannot_run_execution_commands(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    out_of_scope_staff,
):
    execution = _execution_with_assignee(owner_membership, staff_membership, business_unit)
    from houston.comments.services import create_action_plan_execution_comment

    create_action_plan_execution_comment(
        author_membership=owner_membership,
        execution=execution,
        body="please review",
        mentioned_membership_ids=[out_of_scope_staff.id],
    )

    token = login(api_client, user=out_of_scope_staff.user)
    mark_done = api_client.post(
        action_plan_execution_url(out_of_scope_staff.establishment_id, execution.id, "mark-done/"),
        **auth_headers(token),
    )
    assert mark_done.status_code == 403

    cancel = api_client.post(
        action_plan_execution_url(out_of_scope_staff.establishment_id, execution.id, "cancel/"),
        **auth_headers(token),
    )
    assert cancel.status_code == 403
