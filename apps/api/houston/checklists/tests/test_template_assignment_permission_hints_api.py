from __future__ import annotations

import pytest

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistAssignment
from houston.checklists.tests.conftest import (
    add_task_template,
    checklist_assignment_url,
    checklist_template_url,
    checklist_templates_url,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _template_detail_hints(api_client, membership, template_id) -> dict:
    token = login(api_client, user=membership.user)
    response = api_client.get(
        checklist_template_url(membership.establishment_id, template_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()["permission_hints"]


def test_manager_in_bu_can_manage_shared_template_not_delete(
    api_client,
    manager_membership,
    shared_template,
):
    add_task_template(template=shared_template)
    hints = _template_detail_hints(api_client, manager_membership, shared_template.id)
    assert hints["can_update"] is True
    assert hints["can_manage_tasks"] is True
    assert hints["can_create_assignment"] is True
    assert hints["can_delete"] is False


def test_owner_can_delete_shared_template(
    api_client,
    owner_membership,
    shared_template,
):
    add_task_template(template=shared_template)
    hints = _template_detail_hints(api_client, owner_membership, shared_template.id)
    assert hints["can_delete"] is True


def test_owner_detail_delete_hint_false_when_active_execution(
    api_client,
    owner_membership,
    shared_template,
    shared_execution,
):
    add_task_template(template=shared_template)
    hints = _template_detail_hints(api_client, owner_membership, shared_template.id)
    assert hints["can_delete"] is False


def test_owner_list_delete_hint_ignores_active_execution_conflict(
    api_client,
    owner_membership,
    shared_template,
    shared_execution,
):
    add_task_template(template=shared_template)
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        checklist_templates_url(owner_membership.establishment_id, "?type=shared"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = next(row for row in response.json() if row["id"] == str(shared_template.id))
    assert item["permission_hints"]["can_delete"] is True


def test_manager_out_of_bu_cannot_view_shared_template_detail(
    api_client,
    establishment,
    owner_membership,
    shared_template,
    business_unit,
):
    add_task_template(template=shared_template)
    other_bu = create_business_unit(establishment=establishment, key="spa")
    out_manager = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(
        membership=out_manager,
        business_unit=other_bu,
    )

    token = login(api_client, user=out_manager.user)
    response = api_client.get(
        checklist_template_url(out_manager.establishment_id, shared_template.id),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_personal_template_list_omits_dynamic_personal_execution_hint(
    api_client,
    staff_membership,
    personal_template,
):
    add_task_template(template=personal_template)
    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        checklist_templates_url(staff_membership.establishment_id, "?type=personal"),
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = next(row for row in response.json() if row["id"] == str(personal_template.id))
    assert item["permission_hints"]["can_create_personal_execution"] is False


def test_personal_template_detail_can_create_personal_execution_when_no_active(
    api_client,
    staff_membership,
    personal_template,
):
    add_task_template(template=personal_template)
    hints = _template_detail_hints(api_client, staff_membership, personal_template.id)
    assert hints["can_create_personal_execution"] is True


def test_assignment_deactivate_hint_false_when_in_progress_execution(
    api_client,
    owner_membership,
    checklist_assignment,
    shared_execution,
):
    from houston.checklists.models import ChecklistExecution

    shared_execution.status = ChecklistExecution.Status.IN_PROGRESS
    shared_execution.save(update_fields=["status", "updated_at"])

    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        checklist_assignment_url(
            owner_membership.establishment_id,
            checklist_assignment.id,
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["permission_hints"]["can_deactivate"] is False
    assert response.json()["permission_hints"]["can_update"] is True


def test_inactive_assignment_hints_disable_update_and_deactivate(
    api_client,
    owner_membership,
    checklist_assignment,
):
    checklist_assignment.status = ChecklistAssignment.Status.INACTIVE
    checklist_assignment.save(update_fields=["status", "updated_at"])

    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        checklist_assignment_url(
            owner_membership.establishment_id,
            checklist_assignment.id,
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200
    item = response.json()
    assert item["permission_hints"]["can_update"] is False
    assert item["permission_hints"]["can_deactivate"] is False
