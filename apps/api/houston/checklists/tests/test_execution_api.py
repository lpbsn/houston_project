from __future__ import annotations

import pytest

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistExecution
from houston.checklists.tests.conftest import (
    assignment_api_payload,
    checklist_execution_url,
    checklist_template_url,
    checklist_templates_url,
)
from houston.establishments.models import EstablishmentMembership

pytestmark = pytest.mark.django_db


def _personal_template_with_task(api_client, staff):
    token = login(api_client, user=staff.user)
    template = api_client.post(
        checklist_templates_url(staff.establishment_id),
        {"checklist_type": "personal", "title": "Mine"},
        format="json",
        **auth_headers(token),
    )
    assert template.status_code == 201
    task = api_client.post(
        checklist_template_url(staff.establishment_id, template.json()["id"], "tasks/"),
        {"task": "Task"},
        format="json",
        **auth_headers(token),
    )
    assert task.status_code == 201
    activate = api_client.post(
        checklist_template_url(staff.establishment_id, template.json()["id"], "activate/"),
        **auth_headers(token),
    )
    assert activate.status_code == 200
    return template.json(), token


def test_personal_execution_create_and_one_active_max(api_client, staff_membership):
    template, token = _personal_template_with_task(api_client, staff_membership)
    first = api_client.post(
        checklist_template_url(
            staff_membership.establishment_id,
            template["id"],
            "personal-executions/",
        ),
        **auth_headers(token),
    )
    assert first.status_code == 201

    second = api_client.post(
        checklist_template_url(
            staff_membership.establishment_id,
            template["id"],
            "personal-executions/",
        ),
        **auth_headers(token),
    )
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"
    assert second.json()["active_execution_id"] == first.json()["id"]


def test_execution_detail_rbac(api_client, owner_membership, staff_membership, business_unit):
    from houston.checklists.tests.test_assignment_api import _active_shared_template

    template, owner_token = _active_shared_template(api_client, owner_membership, business_unit)
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


def test_cancel_shared_execution_owner_allowed_staff_denied(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.tests.test_assignment_api import _active_shared_template

    template, owner_token = _active_shared_template(api_client, owner_membership, business_unit)
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
    assert staff_cancel.status_code == 403

    owner_cancel = api_client.post(
        checklist_execution_url(owner_membership.establishment_id, execution.id, "cancel/"),
        **auth_headers(owner_token),
    )
    assert owner_cancel.status_code == 200
    assert owner_cancel.json()["status"] == ChecklistExecution.Status.CANCELED


def test_cancel_shared_execution_manager_in_scope(
    api_client,
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.tests.test_assignment_api import _active_shared_template

    template, owner_token = _active_shared_template(api_client, owner_membership, business_unit)
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
