from __future__ import annotations

import pytest

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.tests.conftest import (
    add_task_template,
    checklist_flash_todo_url,
    checklist_template_url,
)
from houston.establishments.tests.taxonomy_helpers import create_business_unit

pytestmark = pytest.mark.django_db


def _flash_payload(*, business_unit_id, assigned_to_id, title="Flash task"):
    return {
        "title": title,
        "business_unit_id": str(business_unit_id),
        "assigned_to": str(assigned_to_id),
        "tasks": [{"title": "Do the thing"}],
    }


def test_staff_can_create_flash_todo_in_scope(api_client, staff_membership, business_unit):
    template_count_before = ChecklistTemplate.objects.count()
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        checklist_flash_todo_url(staff_membership.establishment_id),
        _flash_payload(
            business_unit_id=business_unit.id,
            assigned_to_id=staff_membership.id,
        ),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["execution_source"] == "flash_todo"
    assert payload["checklist_template_id"] is None
    assert ChecklistTemplate.objects.count() == template_count_before
    execution = ChecklistExecution.objects.get(id=payload["id"])
    assert execution.execution_source == "flash_todo"
    assert execution.checklist_template_id is None
    assert execution.task_executions.count() == 1


def test_staff_denied_flash_todo_out_of_scope(
    api_client,
    staff_membership,
    establishment,
):
    other_bu = create_business_unit(establishment=establishment, key="spa")
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        checklist_flash_todo_url(staff_membership.establishment_id),
        _flash_payload(
            business_unit_id=other_bu.id,
            assigned_to_id=staff_membership.id,
        ),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_template_execution_endpoint_launches_from_model(
    api_client,
    owner_membership,
    staff_membership,
    registered_template,
):
    add_task_template(template=registered_template, task="Step 1")

    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        checklist_template_url(
            staff_membership.establishment_id,
            registered_template.id,
            "executions/",
        ),
        {"assigned_to": str(staff_membership.id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["execution_source"] == "template"
    assert payload["checklist_template_id"] == str(registered_template.id)
