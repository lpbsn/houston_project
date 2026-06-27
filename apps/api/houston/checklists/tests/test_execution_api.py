from __future__ import annotations

import pytest

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistExecution
from houston.checklists.tests.conftest import (
    assignment_api_payload,
    checklist_execution_url,
    checklist_template_url,
)
from houston.establishments.models import EstablishmentMembership

pytestmark = pytest.mark.django_db


def _active_template_for_staff(api_client, owner, staff, business_unit):
    from houston.checklists.tests.test_assignment_api import _active_registered_template

    template, owner_token = _active_registered_template(api_client, owner, business_unit)
    staff_token = login(api_client, user=staff.user)
    return template, staff_token


def test_template_execution_create_allows_multiple_active(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, staff_token = _active_template_for_staff(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    first = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
    )
    assert first.status_code == 201

    second = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
    )
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def _start_template_execution(api_client, membership, template_id, token, *, assigned_to_id=None):
    payload = {}
    if assigned_to_id is not None:
        payload["assigned_to"] = str(assigned_to_id)
    return api_client.post(
        checklist_template_url(membership.establishment_id, template_id, "executions/"),
        payload,
        format="json",
        **auth_headers(token),
    )


def test_staff_launch_for_self_succeeds(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, staff_token = _active_template_for_staff(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    response = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
    )
    assert response.status_code == 201
    assert response.json()["assigned_to_id"] == str(staff_membership.id)


def test_staff_launch_for_other_assignee_denied(
    api_client,
    owner_membership,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    template, staff_token = _active_template_for_staff(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    response = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
        assigned_to_id=other_staff_membership.id,
    )
    assert response.status_code == 403


def test_execution_detail_rbac(api_client, owner_membership, staff_membership, business_unit):
    from houston.checklists.tests.test_assignment_api import _active_registered_template

    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(owner_token),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])

    staff_token = login(api_client, user=staff_membership.user)
    allowed = api_client.get(
        checklist_execution_url(staff_membership.establishment_id, execution.id),
        **auth_headers(staff_token),
    )
    assert allowed.status_code == 200
    assert "raw_text" not in allowed.json()

    from houston.actions.tests.conftest import build_api_membership_on_establishment

    other_staff = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.STAFF,
    )
    other_token = login(api_client, user=other_staff.user)
    denied = api_client.get(
        checklist_execution_url(other_staff.establishment_id, execution.id),
        **auth_headers(other_token),
    )
    assert denied.status_code == 404


def test_execution_detail_query_count_and_task_order(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.tests.test_template_api import _active_template_with_tasks
    from houston.testing.query_baseline import capture_queries

    template, owner_token = _active_template_with_tasks(
        api_client,
        owner_membership,
        business_unit,
        task_count=5,
    )
    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(owner_token),
    )
    assert assignment.status_code == 201
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])

    staff_token = login(api_client, user=staff_membership.user)

    # Measured post-fix on PostgreSQL test DB (ORM-QW-01 / DB-06).
    max_queries = 9

    with capture_queries() as context:
        response = api_client.get(
            checklist_execution_url(staff_membership.establishment_id, execution.id),
            **auth_headers(staff_token),
        )

    assert response.status_code == 200
    assert len(context.captured_queries) <= max_queries
    positions = [task["position"] for task in response.json()["task_executions"]]
    assert positions == sorted(positions)


def test_cancel_assignment_execution_assignee_and_owner_allowed(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.tests.test_assignment_api import _active_registered_template

    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(owner_token),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])

    staff_token = login(api_client, user=staff_membership.user)
    staff_cancel = api_client.post(
        checklist_execution_url(staff_membership.establishment_id, execution.id, "cancel/"),
        **auth_headers(staff_token),
    )
    assert staff_cancel.status_code == 200
    assert staff_cancel.json()["status"] == ChecklistExecution.Status.CANCELED


def test_cancel_assignment_execution_manager_in_scope(
    api_client,
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.tests.test_assignment_api import _active_registered_template

    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(owner_token),
    )
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])
    manager_token = login(api_client, user=manager_membership.user)
    response = api_client.post(
        checklist_execution_url(manager_membership.establishment_id, execution.id, "cancel/"),
        **auth_headers(manager_token),
    )
    assert response.status_code == 200
