from __future__ import annotations

import pytest

from houston.action_plans.constants import CATALOG_STATUS_ACTIVE, CATALOG_STATUS_INACTIVE
from houston.action_plans.models import ActionPlanExecution
from houston.action_plans.tests.conftest import (
    action_plan_url,
    action_plans_url,
    api_assignee_payload,
    api_task_payload,
    auth_headers,
    login,
)

pytestmark = pytest.mark.django_db


def _catalog_create_payload(*, business_unit, tasks=None, **overrides) -> dict:
    payload = {
        "title": "Catalog plan",
        "description": "Reusable",
        "pilot_business_unit_id": str(business_unit.id),
        "is_reusable": True,
        "tasks": tasks or [api_task_payload(task="Check inventory", business_unit=business_unit)],
    }
    payload.update(overrides)
    return payload


def _create_catalog_via_api(api_client, owner, business_unit, *, token=None):
    token = token or login(api_client, user=owner.user)
    response = api_client.post(
        action_plans_url(owner.establishment_id),
        _catalog_create_payload(business_unit=business_unit),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.json()
    return response.json(), token


def test_catalog_list_manager_sees_scoped_plans(
    api_client,
    owner_membership,
    manager_membership,
    business_unit,
):
    _create_catalog_via_api(api_client, owner_membership, business_unit)
    token = login(api_client, user=manager_membership.user)
    response = api_client.get(
        action_plans_url(manager_membership.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_catalog_list_staff_returns_404(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    _create_catalog_via_api(api_client, owner_membership, business_unit)
    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plans_url(staff_membership.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_catalog_create_returns_plan_detail(api_client, owner_membership, business_unit):
    body, _ = _create_catalog_via_api(api_client, owner_membership, business_unit)
    assert body["is_reusable"] is True
    assert body["catalog_status"] == CATALOG_STATUS_ACTIVE
    assert len(body["tasks"]) == 1
    assert "action_plan_id" not in body


def test_feed_create_returns_execution_detail(api_client, staff_membership, business_unit):
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plans_url(staff_membership.establishment_id),
        {
            "title": "Staff feed plan",
            "pilot_business_unit_id": str(business_unit.id),
            "requires_validation": False,
            "tasks": [api_task_payload(task="Self task", business_unit=business_unit)],
            "assignees": [
                api_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.json()
    body = response.json()
    assert body["status"] == ActionPlanExecution.Status.IN_PROGRESS
    assert body["action_plan_id"] is not None


def test_signal_create_returns_execution_detail(
    api_client,
    owner_membership,
    business_unit,
    signal,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plans_url(owner_membership.establishment_id),
        {
            "title": "Signal plan",
            "pilot_business_unit_id": str(business_unit.id),
            "source_signal_id": str(signal.id),
            "tasks": [api_task_payload(task="Fix leak", business_unit=business_unit)],
            "assignees": [
                api_assignee_payload(membership=owner_membership, business_unit=business_unit)
            ],
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.json()
    assert response.json()["signal_summary"]["id"] == str(signal.id)


def test_patch_updates_title_and_description(api_client, owner_membership, business_unit):
    plan, token = _create_catalog_via_api(api_client, owner_membership, business_unit)
    response = api_client.patch(
        action_plan_url(owner_membership.establishment_id, plan["id"]),
        {"title": "Updated title", "description": "Updated description"},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated title"
    assert body["description"] == "Updated description"


def test_activate_and_deactivate_catalog_plan(api_client, owner_membership, business_unit):
    token = login(api_client, user=owner_membership.user)
    create = api_client.post(
        action_plans_url(owner_membership.establishment_id),
        _catalog_create_payload(
            business_unit=business_unit,
            tasks=[api_task_payload(task="Task", business_unit=business_unit)],
        ),
        format="json",
        **auth_headers(token),
    )
    plan_id = create.json()["id"]
    deactivate = api_client.post(
        action_plan_url(owner_membership.establishment_id, plan_id, "deactivate/"),
        **auth_headers(token),
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["catalog_status"] == CATALOG_STATUS_INACTIVE

    activate = api_client.post(
        action_plan_url(owner_membership.establishment_id, plan_id, "activate/"),
        **auth_headers(token),
    )
    assert activate.status_code == 200
    assert activate.json()["catalog_status"] == CATALOG_STATUS_ACTIVE


def test_use_catalog_plan_creates_execution(
    api_client,
    owner_membership,
    staff_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id, "use/"),
        {
            "assignees": [
                api_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.json()
    assert response.json()["action_plan_id"] == str(catalog_action_plan.id)


def test_manager_cross_pole_use_allowed(
    api_client,
    owner_membership,
    manager_membership,
    cross_pole_catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=manager_membership.user)
    response = api_client.post(
        action_plan_url(
            manager_membership.establishment_id,
            cross_pole_catalog_action_plan.id,
            "use/",
        ),
        {
            "assignees": [
                api_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201


def test_out_of_scope_manager_use_returns_404(
    api_client,
    out_of_scope_manager,
    cross_pole_catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=out_of_scope_manager.user)
    response = api_client.post(
        action_plan_url(
            out_of_scope_manager.establishment_id,
            cross_pole_catalog_action_plan.id,
            "use/",
        ),
        {
            "assignees": [
                api_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_staff_catalog_detail_returns_404(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    plan, _ = _create_catalog_via_api(api_client, owner_membership, business_unit)
    token = login(api_client, user=staff_membership.user)
    response = api_client.get(
        action_plan_url(staff_membership.establishment_id, plan["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_list_and_detail_involved_pole_count_match(
    api_client,
    owner_membership,
    inactive_catalog_action_plan,
):
    token = login(api_client, user=owner_membership.user)
    list_response = api_client.get(
        action_plans_url(owner_membership.establishment_id),
        **auth_headers(token),
    )
    assert list_response.status_code == 200
    list_item = next(
        item for item in list_response.json() if item["id"] == str(inactive_catalog_action_plan.id)
    )

    detail_response = api_client.get(
        action_plan_url(owner_membership.establishment_id, inactive_catalog_action_plan.id),
        **auth_headers(token),
    )
    assert detail_response.status_code == 200
    detail_item = detail_response.json()

    assert list_item["involved_pole_count"] == detail_item["involved_pole_count"] == 1


def test_catalog_create_without_tasks_returns_400(
    api_client,
    owner_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    payload = _catalog_create_payload(business_unit=business_unit)
    payload["tasks"] = []
    response = api_client.post(
        action_plans_url(owner_membership.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_deactivate_non_reusable_plan_returns_400(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    staff_token = login(api_client, user=staff_membership.user)
    create = api_client.post(
        action_plans_url(staff_membership.establishment_id),
        {
            "title": "Staff feed plan",
            "pilot_business_unit_id": str(business_unit.id),
            "requires_validation": False,
            "tasks": [api_task_payload(task="Self task", business_unit=business_unit)],
            "assignees": [
                api_assignee_payload(membership=staff_membership, business_unit=business_unit)
            ],
        },
        format="json",
        **auth_headers(staff_token),
    )
    assert create.status_code == 201, create.json()
    plan_id = create.json()["action_plan_id"]

    owner_token = login(api_client, user=owner_membership.user)
    deactivate = api_client.post(
        action_plan_url(owner_membership.establishment_id, plan_id, "deactivate/"),
        **auth_headers(owner_token),
    )
    assert deactivate.status_code == 400
    assert deactivate.json()["code"] == "validation_error"


def test_openapi_post_action_plans_create_documents_dual_201_response():
    from pathlib import Path

    schema = Path(__file__).resolve().parents[3] / "schema.yml"
    content = schema.read_text()
    marker = "/api/v1/establishments/{establishment_id}/action-plans/:"
    start = content.index(marker)
    post_block = content[start : start + 2500]
    assert "post:" in post_block
    assert "ActionPlanCreate201Response" in post_block
    component_start = content.index("ActionPlanCreate201Response:")
    component_block = content[component_start : component_start + 300]
    assert "oneOf:" in component_block
    assert "ActionPlanDetail" in component_block
    assert "ActionPlanExecutionDetail" in component_block
