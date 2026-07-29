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


def test_execution_lifecycle_mark_done_validate_reopen_cancel(
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

    validate = api_client.post(
        action_plan_execution_url(owner_membership.establishment_id, execution.id, "validate/"),
        **auth_headers(owner_token),
    )
    assert validate.status_code == 200
    assert validate.json()["status"] == ActionPlanExecution.Status.DONE

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
