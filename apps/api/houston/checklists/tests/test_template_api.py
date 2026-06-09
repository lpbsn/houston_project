from __future__ import annotations

import pytest

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistExecution, ChecklistTemplate
from houston.checklists.tests.conftest import (
    checklist_execution_url,
    checklist_task_execution_url,
    checklist_task_template_url,
    checklist_template_url,
    checklist_templates_url,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import create_business_unit

pytestmark = pytest.mark.django_db


def _created_by_me_query() -> str:
    return "?created_by_me=true"


_PERSONAL_DELETE_ACTIVE_MESSAGE = (
    "Cette checklist est en cours d'exécution. "
    "Terminez ou annulez l'exécution avant de la supprimer."
)


def _staff_owned_template_with_tasks(api_client, staff, business_unit, *, task_count: int = 1):
    token = login(api_client, user=staff.user)
    template = api_client.post(
        checklist_templates_url(staff.establishment_id),
        {"title": "Mine", "business_unit_id": str(business_unit.id)},
        format="json",
        **auth_headers(token),
    )
    assert template.status_code == 201
    template_id = template.json()["id"]
    for index in range(task_count):
        task = api_client.post(
            checklist_template_url(staff.establishment_id, template_id, "tasks/"),
            {"task": f"Task {index + 1}"},
            format="json",
            **auth_headers(token),
        )
        assert task.status_code == 201
    activate = api_client.post(
        checklist_template_url(staff.establishment_id, template_id, "activate/"),
        **auth_headers(token),
    )
    assert activate.status_code == 200
    return template.json(), token


def _start_template_execution(api_client, staff, template_id, token):
    response = api_client.post(
        checklist_template_url(staff.establishment_id, template_id, "executions/"),
        {},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    return response.json()


def _create_registered_template_via_api(api_client, owner, business_unit, *, title="Shared"):
    token = login(api_client, user=owner.user)
    response = api_client.post(
        checklist_templates_url(owner.establishment_id),
        {
            "title": title,
            "business_unit_id": str(business_unit.id),
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    return response.json(), token


def test_registered_template_list_owner_sees_templates(api_client, owner_membership, business_unit):
    _create_registered_template_via_api(api_client, owner_membership, business_unit)
    token = login(api_client, user=owner_membership.user)
    response = api_client.get(
        checklist_templates_url(owner_membership.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_registered_template_list_staff_returns_empty(api_client, owner_membership, business_unit):
    _create_registered_template_via_api(api_client, owner_membership, business_unit)
    from houston.actions.tests.conftest import build_api_membership_on_establishment

    staff = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff.user)
    response = api_client.get(
        checklist_templates_url(staff.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json() == []


def test_manager_registered_template_list_is_scoped(
    api_client,
    owner_membership,
    manager_membership,
    business_unit,
    establishment,
):
    _create_registered_template_via_api(
        api_client, owner_membership, business_unit, title="In scope"
    )
    other_bu = create_business_unit(establishment=establishment, key="spa")
    _create_registered_template_via_api(api_client, owner_membership, other_bu, title="Out scope")

    token = login(api_client, user=manager_membership.user)
    response = api_client.get(
        checklist_templates_url(manager_membership.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert titles == {"In scope"}


def test_staff_owned_template_list_is_own_only(
    api_client,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    create = api_client.post(
        checklist_templates_url(staff_membership.establishment_id),
        {"title": "Mine", "business_unit_id": str(business_unit.id)},
        format="json",
        **auth_headers(token),
    )
    assert create.status_code == 201

    own_list = api_client.get(
        checklist_templates_url(staff_membership.establishment_id) + _created_by_me_query(),
        **auth_headers(token),
    )
    assert len(own_list.json()) == 1

    other_token = login(api_client, user=other_staff_membership.user)
    other_list = api_client.get(
        checklist_templates_url(other_staff_membership.establishment_id) + _created_by_me_query(),
        **auth_headers(other_token),
    )
    assert other_list.json() == []


def test_create_template_denied_for_unscoped_staff(api_client, owner_membership, business_unit):
    from houston.actions.tests.conftest import build_api_membership_on_establishment

    staff = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff.user)
    response = api_client.post(
        checklist_templates_url(staff.establishment_id),
        {
            "title": "Denied",
            "business_unit_id": str(business_unit.id),
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_create_registered_template_allowed_for_scoped_staff(
    api_client,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        checklist_templates_url(staff_membership.establishment_id),
        {"title": "Staff checklist", "business_unit_id": str(business_unit.id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201


def test_activate_template_requires_task(api_client, owner_membership, business_unit):
    payload, token = _create_registered_template_via_api(
        api_client, owner_membership, business_unit
    )
    response = api_client.post(
        checklist_template_url(owner_membership.establishment_id, payload["id"], "activate/"),
        **auth_headers(token),
    )
    assert response.status_code == 400


def test_delete_last_task_auto_deactivates_template(api_client, owner_membership, business_unit):
    payload, token = _create_registered_template_via_api(
        api_client, owner_membership, business_unit
    )
    task = api_client.post(
        checklist_template_url(owner_membership.establishment_id, payload["id"], "tasks/"),
        {"task": "Only task"},
        format="json",
        **auth_headers(token),
    )
    assert task.status_code == 201
    activate = api_client.post(
        checklist_template_url(owner_membership.establishment_id, payload["id"], "activate/"),
        **auth_headers(token),
    )
    assert activate.status_code == 200
    delete = api_client.delete(
        checklist_task_template_url(owner_membership.establishment_id, task.json()["id"]),
        **auth_headers(token),
    )
    assert delete.status_code == 204
    detail = api_client.get(
        checklist_template_url(owner_membership.establishment_id, payload["id"]),
        **auth_headers(token),
    )
    assert detail.json()["status"] == ChecklistTemplate.Status.INACTIVE


def test_delete_registered_template_succeeds_without_history(
    api_client,
    owner_membership,
    business_unit,
):
    payload, token = _create_registered_template_via_api(
        api_client, owner_membership, business_unit
    )
    response = api_client.delete(
        checklist_template_url(owner_membership.establishment_id, payload["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=payload["id"]).exists()


def test_delete_registered_template_denied_for_staff(
    api_client,
    owner_membership,
    business_unit,
):
    from houston.actions.tests.conftest import build_api_membership_on_establishment

    payload, owner_token = _create_registered_template_via_api(
        api_client,
        owner_membership,
        business_unit,
    )
    staff = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.STAFF,
    )
    staff_token = login(api_client, user=staff.user)
    response = api_client.delete(
        checklist_template_url(staff.establishment_id, payload["id"]),
        **auth_headers(staff_token),
    )
    assert response.status_code == 404
    assert ChecklistTemplate.objects.filter(id=payload["id"]).exists()


def test_delete_staff_owned_template_allowed_for_creator(
    api_client,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    create = api_client.post(
        checklist_templates_url(staff_membership.establishment_id),
        {"title": "Mine", "business_unit_id": str(business_unit.id)},
        format="json",
        **auth_headers(token),
    )
    assert create.status_code == 201
    template_id = create.json()["id"]

    response = api_client.delete(
        checklist_template_url(staff_membership.establishment_id, template_id),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=template_id).exists()


def test_delete_staff_owned_template_denied_for_other_member(
    api_client,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    create = api_client.post(
        checklist_templates_url(staff_membership.establishment_id),
        {"title": "Mine", "business_unit_id": str(business_unit.id)},
        format="json",
        **auth_headers(token),
    )
    assert create.status_code == 201
    template_id = create.json()["id"]

    other_token = login(api_client, user=other_staff_membership.user)
    response = api_client.delete(
        checklist_template_url(other_staff_membership.establishment_id, template_id),
        **auth_headers(other_token),
    )
    assert response.status_code == 403
    assert ChecklistTemplate.objects.filter(id=template_id).exists()


def test_delete_registered_template_allowed_for_manager_in_scope(
    api_client,
    owner_membership,
    manager_membership,
    business_unit,
):
    payload, _owner_token = _create_registered_template_via_api(
        api_client,
        owner_membership,
        business_unit,
    )
    manager_token = login(api_client, user=manager_membership.user)
    response = api_client.delete(
        checklist_template_url(manager_membership.establishment_id, payload["id"]),
        **auth_headers(manager_token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=payload["id"]).exists()


def test_delete_registered_template_allowed_for_director(
    api_client,
    owner_membership,
    director_membership,
    business_unit,
):
    payload, _owner_token = _create_registered_template_via_api(
        api_client,
        owner_membership,
        business_unit,
    )
    director_token = login(api_client, user=director_membership.user)
    response = api_client.delete(
        checklist_template_url(director_membership.establishment_id, payload["id"]),
        **auth_headers(director_token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=payload["id"]).exists()


def test_delete_template_with_assignment_no_active_execution_succeeds(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):

    from houston.checklists.models import ChecklistAssignment

    template, token = _create_registered_template_via_api(
        api_client, owner_membership, business_unit
    )
    task = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "tasks/"),
        {"task": "Task"},
        format="json",
        **auth_headers(token),
    )
    assert task.status_code == 201
    activate = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "activate/"),
        **auth_headers(token),
    )
    assert activate.status_code == 200
    from houston.checklists.tests.conftest import default_assignment_schedule

    schedule = default_assignment_schedule()
    ChecklistAssignment.objects.create(
        checklist_template_id=template["id"],
        establishment_id=owner_membership.establishment_id,
        assigned_to=staff_membership,
        assigned_by=owner_membership,
        business_unit_id=business_unit.id,
        start_date=schedule["start_date"],
        end_date=schedule["end_date"],
        start_at=schedule["start_at"],
        end_at=schedule["end_at"],
        recurrence_days=[],
        status=ChecklistAssignment.Status.ACTIVE,
    )

    response = api_client.delete(
        checklist_template_url(owner_membership.establishment_id, template["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=template["id"]).exists()


def test_delete_staff_owned_template_with_active_execution_returns_conflict(
    api_client,
    staff_membership,
    business_unit,
):
    template, token = _staff_owned_template_with_tasks(
        api_client,
        staff_membership,
        business_unit,
    )
    execution = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        token,
    )

    response = api_client.delete(
        checklist_template_url(staff_membership.establishment_id, template["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "conflict"
    assert payload["detail"] == _PERSONAL_DELETE_ACTIVE_MESSAGE
    assert payload["active_execution_id"] == execution["id"]
    assert ChecklistTemplate.objects.filter(id=template["id"]).exists()


def test_delete_staff_owned_template_with_in_progress_execution_returns_conflict(
    api_client,
    staff_membership,
    business_unit,
):
    template, token = _staff_owned_template_with_tasks(
        api_client,
        staff_membership,
        business_unit,
        task_count=2,
    )
    execution_payload = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        token,
    )
    execution = ChecklistExecution.objects.get(id=execution_payload["id"])
    first_task = execution.task_executions.order_by("position").first()
    mark_done = api_client.post(
        checklist_task_execution_url(
            staff_membership.establishment_id,
            first_task.id,
            "mark-done/",
        ),
        **auth_headers(token),
    )
    assert mark_done.status_code == 200
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.IN_PROGRESS

    response = api_client.delete(
        checklist_template_url(staff_membership.establishment_id, template["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "conflict"
    assert payload["detail"] == _PERSONAL_DELETE_ACTIVE_MESSAGE
    assert payload["active_execution_id"] == str(execution.id)
    assert ChecklistTemplate.objects.filter(id=template["id"]).exists()


def test_delete_staff_owned_template_with_done_execution_succeeds(
    api_client,
    staff_membership,
    business_unit,
):
    template, token = _staff_owned_template_with_tasks(
        api_client,
        staff_membership,
        business_unit,
    )
    execution_payload = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        token,
    )
    execution = ChecklistExecution.objects.get(id=execution_payload["id"])
    task = execution.task_executions.order_by("position").first()
    mark_done = api_client.post(
        checklist_task_execution_url(
            staff_membership.establishment_id,
            task.id,
            "mark-done/",
        ),
        **auth_headers(token),
    )
    assert mark_done.status_code == 200
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE

    response = api_client.delete(
        checklist_template_url(staff_membership.establishment_id, template["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=template["id"]).exists()
    execution.refresh_from_db()
    assert execution.checklist_template_id is None
    assert execution.template_title == template["title"]


def test_delete_staff_owned_template_with_canceled_execution_succeeds(
    api_client,
    staff_membership,
    business_unit,
):
    template, token = _staff_owned_template_with_tasks(
        api_client,
        staff_membership,
        business_unit,
    )
    execution_payload = _start_template_execution(
        api_client,
        staff_membership,
        template["id"],
        token,
    )
    cancel = api_client.post(
        checklist_execution_url(
            staff_membership.establishment_id,
            execution_payload["id"],
            "cancel/",
        ),
        **auth_headers(token),
    )
    assert cancel.status_code == 200

    response = api_client.delete(
        checklist_template_url(staff_membership.establishment_id, template["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=template["id"]).exists()
    execution = ChecklistExecution.objects.get(id=execution_payload["id"])
    assert execution.checklist_template_id is None
    assert execution.status == ChecklistExecution.Status.CANCELED


def test_delete_registered_template_with_historical_execution_succeeds(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):

    from houston.checklists.tests.test_assignment_api import _active_registered_template

    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    from houston.checklists.tests.conftest import assignment_api_payload

    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id, recurrence_days=[]),
        format="json",
        **auth_headers(owner_token),
    )
    assert assignment.status_code == 201
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])
    staff_token = login(api_client, user=staff_membership.user)
    for task in execution.task_executions.order_by("position"):
        mark_done = api_client.post(
            checklist_task_execution_url(
                staff_membership.establishment_id,
                task.id,
                "mark-done/",
            ),
            **auth_headers(staff_token),
        )
        assert mark_done.status_code == 200
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE

    response = api_client.delete(
        checklist_template_url(owner_membership.establishment_id, template["id"]),
        **auth_headers(owner_token),
    )
    assert response.status_code == 204
    assert not ChecklistTemplate.objects.filter(id=template["id"]).exists()
    execution.refresh_from_db()
    assert execution.checklist_template_id is None
    assert execution.template_title == template["title"]


def test_delete_registered_template_with_active_execution_returns_conflict(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):

    from houston.checklists.tests.test_assignment_api import _active_registered_template

    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    from houston.checklists.tests.conftest import assignment_api_payload

    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id, recurrence_days=[]),
        format="json",
        **auth_headers(owner_token),
    )
    assert assignment.status_code == 201
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])
    assert execution.status == ChecklistExecution.Status.ASSIGNED

    response = api_client.delete(
        checklist_template_url(owner_membership.establishment_id, template["id"]),
        **auth_headers(owner_token),
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "conflict"
    assert payload["detail"] == _PERSONAL_DELETE_ACTIVE_MESSAGE
    assert payload["active_execution_id"] == str(execution.id)
    assert ChecklistTemplate.objects.filter(id=template["id"]).exists()


def test_delete_registered_template_with_in_progress_execution_returns_conflict(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):

    from houston.checklists.tests.test_assignment_api import _active_registered_template

    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    second_task = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "tasks/"),
        {"task": "Task 2"},
        format="json",
        **auth_headers(owner_token),
    )
    assert second_task.status_code == 201
    from houston.checklists.tests.conftest import assignment_api_payload

    assignment = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id, recurrence_days=[]),
        format="json",
        **auth_headers(owner_token),
    )
    assert assignment.status_code == 201
    execution = ChecklistExecution.objects.get(checklist_assignment_id=assignment.json()["id"])
    staff_token = login(api_client, user=staff_membership.user)
    first_task = execution.task_executions.order_by("position").first()
    mark_done = api_client.post(
        checklist_task_execution_url(
            staff_membership.establishment_id,
            first_task.id,
            "mark-done/",
        ),
        **auth_headers(staff_token),
    )
    assert mark_done.status_code == 200
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.IN_PROGRESS

    response = api_client.delete(
        checklist_template_url(owner_membership.establishment_id, template["id"]),
        **auth_headers(owner_token),
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["code"] == "conflict"
    assert payload["detail"] == _PERSONAL_DELETE_ACTIVE_MESSAGE
    assert payload["active_execution_id"] == str(execution.id)
    assert ChecklistTemplate.objects.filter(id=template["id"]).exists()


def test_no_start_endpoint_in_checklist_urls():
    from houston.checklists.api import urls as checklist_urls

    joined = " ".join(str(pattern.pattern) for pattern in checklist_urls.urlpatterns)
    assert "start" not in joined


def test_openapi_contains_checklist_endpoints_and_polymorphic_feed_item():
    from pathlib import Path

    schema = Path(__file__).resolve().parents[3] / "schema.yml"
    content = schema.read_text()
    assert "/checklist-templates/" in content
    assert "/checklist-task-executions/" in content
    assert "ChecklistFeedItem" in content
    assert "ExecutionFeedItem" in content
