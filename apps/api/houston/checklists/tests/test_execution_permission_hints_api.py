from __future__ import annotations

import pytest

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistExecution
from houston.checklists.permission_hints import build_checklist_execution_permission_hints
from houston.checklists.tests.conftest import checklist_execution_url
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _execution_hints(api_client, membership, execution_id) -> dict:
    token = login(api_client, user=membership.user)
    response = api_client.get(
        checklist_execution_url(membership.establishment_id, execution_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()["permission_hints"]


def test_staff_assignee_shared_can_execute_not_cancel(
    api_client,
    staff_membership,
    shared_execution,
):
    hints = _execution_hints(api_client, staff_membership, shared_execution.id)
    assert hints["can_execute_tasks"] is True
    assert hints["can_cancel"] is False


def test_staff_assignee_personal_can_execute_and_cancel(
    api_client,
    staff_membership,
    personal_execution,
):
    hints = _execution_hints(api_client, staff_membership, personal_execution.id)
    assert hints["can_execute_tasks"] is True
    assert hints["can_cancel"] is True


def test_staff_non_assignee_cannot_view_execution_detail(
    api_client,
    other_staff_membership,
    shared_execution,
):
    token = login(api_client, user=other_staff_membership.user)
    response = api_client.get(
        checklist_execution_url(other_staff_membership.establishment_id, shared_execution.id),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_owner_viewer_non_assignee_can_cancel_shared_not_execute(
    api_client,
    owner_membership,
    shared_execution,
):
    hints = _execution_hints(api_client, owner_membership, shared_execution.id)
    assert hints["can_execute_tasks"] is False
    assert hints["can_cancel"] is True


def test_manager_in_bu_viewer_non_assignee_can_cancel_shared_not_execute(
    api_client,
    manager_membership,
    shared_execution,
):
    hints = _execution_hints(api_client, manager_membership, shared_execution.id)
    assert hints["can_execute_tasks"] is False
    assert hints["can_cancel"] is True


def test_manager_out_of_bu_cannot_view_execution_detail(
    api_client,
    establishment,
    owner_membership,
    shared_execution,
    business_unit,
):
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
        checklist_execution_url(out_manager.establishment_id, shared_execution.id),
        **auth_headers(token),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    ("status",),
    [
        (ChecklistExecution.Status.DONE,),
        (ChecklistExecution.Status.CANCELED,),
    ],
)
def test_terminal_execution_hints_disable_actions(
    api_client,
    staff_membership,
    shared_execution,
    status,
):
    shared_execution.status = status
    shared_execution.save(update_fields=["status", "updated_at"])

    hints = _execution_hints(api_client, staff_membership, shared_execution.id)
    assert hints["can_execute_tasks"] is False
    assert hints["can_cancel"] is False


def test_build_checklist_execution_permission_hints_unit(shared_execution, staff_membership):
    hints = build_checklist_execution_permission_hints(
        membership=staff_membership,
        execution=shared_execution,
    )
    assert hints == {"can_execute_tasks": True, "can_cancel": False}
