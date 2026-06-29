from __future__ import annotations

import pytest

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.conftest import (
    action_plan_execution_url,
    action_plan_task_url,
    action_plan_url,
    action_plans_url,
    auth_headers,
    build_assignee_payload,
    build_task_payload,
    login,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db


def _foreign_context(owner, staff, business_unit):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=business_unit.id,
        title="Tenant isolation",
        requires_validation=False,
        tasks=[build_task_payload(task="Task", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=staff, business_unit=business_unit)],
    )
    task = execution.task_executions.first()
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    return {
        "execution": execution,
        "task": task,
        "foreign": foreign,
    }


def test_plan_detail_cross_establishment_returns_404(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.get(
        action_plan_url(foreign.establishment_id, catalog_action_plan.id),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_execution_detail_cross_establishment_returns_404(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    ctx = _foreign_context(owner_membership, staff_membership, business_unit)
    token = login(api_client, user=ctx["foreign"].user)
    response = api_client.get(
        action_plan_execution_url(ctx["foreign"].establishment_id, ctx["execution"].id),
        **auth_headers(token),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "suffix",
    [
        "mark-done/",
        "validate/",
        "reopen/",
        "cancel/",
    ],
)
def test_execution_command_cross_establishment_returns_404(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    suffix,
):
    ctx = _foreign_context(owner_membership, staff_membership, business_unit)
    token = login(api_client, user=ctx["foreign"].user)
    response = api_client.post(
        action_plan_execution_url(ctx["foreign"].establishment_id, ctx["execution"].id, suffix),
        **auth_headers(token),
    )
    assert response.status_code == 404


@pytest.mark.parametrize(
    "suffix",
    [
        "mark-done/",
        "skip/",
        "create-observation/",
    ],
)
def test_task_command_cross_establishment_returns_404(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    suffix,
):
    ctx = _foreign_context(owner_membership, staff_membership, business_unit)
    token = login(api_client, user=ctx["foreign"].user)
    payload = (
        {"text": "Broken equipment in kitchen area today"}
        if suffix == "create-observation/"
        else None
    )
    response = api_client.post(
        action_plan_task_url(ctx["foreign"].establishment_id, ctx["task"].id, suffix),
        payload or {},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_use_cross_establishment_returns_404(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.post(
        action_plan_url(foreign.establishment_id, catalog_action_plan.id, "use/"),
        {},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_list_cross_establishment_is_empty_not_leak(
    api_client,
    owner_membership,
    catalog_action_plan,
):
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=foreign.user)
    response = api_client.get(
        action_plans_url(foreign.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json() == []
