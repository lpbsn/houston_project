from __future__ import annotations

import pytest
from django.utils import timezone

from houston.actions.tests.conftest import auth_headers, login
from houston.checklists.models import ChecklistAssignment, ChecklistExecution
from houston.checklists.services import (
    _ASSIGNMENT_INACTIVE_PATCH_MESSAGE,
    _REMOVE_ASSIGNMENT_IN_PROGRESS_MESSAGE,
)
from houston.checklists.tests.conftest import (
    assignment_api_payload,
    checklist_assignment_url,
    checklist_assignments_url,
    checklist_task_execution_url,
    checklist_template_url,
    checklist_templates_url,
    default_assignment_schedule,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import create_business_unit

pytestmark = pytest.mark.django_db


def _active_registered_template(api_client, owner, business_unit):
    token = login(api_client, user=owner.user)
    template = api_client.post(
        checklist_templates_url(owner.establishment_id),
        {
            "title": "Routine",
            "business_unit_id": str(business_unit.id),
        },
        format="json",
        **auth_headers(token),
    )
    assert template.status_code == 201
    task = api_client.post(
        checklist_template_url(owner.establishment_id, template.json()["id"], "tasks/"),
        {"task": "Task"},
        format="json",
        **auth_headers(token),
    )
    assert task.status_code == 201
    activate = api_client.post(
        checklist_template_url(owner.establishment_id, template.json()["id"], "activate/"),
        **auth_headers(token),
    )
    assert activate.status_code == 200
    return template.json(), token


def test_assignment_create_with_schedule(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, token = _active_registered_template(api_client, owner_membership, business_unit)
    response = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(
            staff_membership.id,
            recurrence_days=["monday", "wednesday"],
        ),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["recurrence_days"] == ["monday", "wednesday"]
    assert body["assigned_to_id"] == str(staff_membership.id)


def test_assignment_rejects_end_at_before_start_at(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, token = _active_registered_template(api_client, owner_membership, business_unit)
    schedule = default_assignment_schedule()
    response = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        {
            "assigned_to": str(staff_membership.id),
            "start_date": schedule["start_date"].isoformat(),
            "end_date": schedule["end_date"].isoformat(),
            "start_at": "10:00:00",
            "end_at": "09:00:00",
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400


def test_assignment_create_rejects_assignee_outside_business_unit(
    api_client,
    owner_membership,
    business_unit,
    establishment,
):
    from houston.establishments.tests.taxonomy_helpers import create_membership

    template, token = _active_registered_template(api_client, owner_membership, business_unit)
    unscoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    response = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(unscoped_staff.id),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Cet utilisateur n'est pas rattaché au périmètre de cette checklist."
    )


def test_assignment_patch_rejects_assignee_outside_business_unit(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    from houston.establishments.tests.taxonomy_helpers import create_membership

    assignment, token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    unscoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    response = api_client.patch(
        checklist_assignment_url(owner_membership.establishment_id, assignment["id"]),
        {"assigned_to": str(unscoped_staff.id)},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "Cet utilisateur n'est pas rattaché au périmètre de cette checklist."
    )


def test_assignment_create_denied_for_staff(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.actions.tests.conftest import build_api_membership_on_establishment

    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    staff = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff.user)
    response = api_client.post(
        checklist_template_url(staff.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 403


def test_assignment_list_for_manager_is_scoped(
    api_client,
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
    establishment,
):
    template, token = _active_registered_template(api_client, owner_membership, business_unit)
    in_scope = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(staff_membership.id),
        format="json",
        **auth_headers(token),
    )
    assert in_scope.status_code == 201

    other_bu = create_business_unit(establishment=establishment, key="bar")
    out_template, _ = _active_registered_template(api_client, owner_membership, other_bu)
    out_scope = api_client.post(
        checklist_template_url(
            owner_membership.establishment_id,
            out_template["id"],
            "assignments/",
        ),
        assignment_api_payload(owner_membership.id),
        format="json",
        **auth_headers(token),
    )
    assert out_scope.status_code == 201

    manager_token = login(api_client, user=manager_membership.user)
    response = api_client.get(
        checklist_assignments_url(manager_membership.establishment_id),
        **auth_headers(manager_token),
    )
    ids = {item["id"] for item in response.json()}
    assert in_scope.json()["id"] in ids
    assert out_scope.json()["id"] not in ids


def _deactivated_assignment_with_history(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    execution = ChecklistExecution.objects.get(checklist_assignment_id=created["id"])
    execution.status = ChecklistExecution.Status.DONE
    execution.done_at = timezone.now()
    execution.save(update_fields=["status", "done_at", "updated_at"])
    deactivate = api_client.post(
        checklist_assignment_url(
            owner_membership.establishment_id,
            created["id"],
            "deactivate/",
        ),
        **auth_headers(token),
    )
    assert deactivate.status_code == 200
    assert ChecklistAssignment.objects.filter(id=created["id"], status="inactive").exists()
    return created, token, execution


def test_assignment_list_includes_active(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    response = api_client.get(
        checklist_assignments_url(owner_membership.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert created["id"] in ids


def test_assignment_list_excludes_inactive(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, token, _execution = _deactivated_assignment_with_history(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    response = api_client.get(
        checklist_assignments_url(owner_membership.establishment_id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert created["id"] not in ids


def test_assignment_detail_returns_inactive(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, token, execution = _deactivated_assignment_with_history(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    response = api_client.get(
        checklist_assignment_url(owner_membership.establishment_id, created["id"]),
        **auth_headers(token),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == created["id"]
    assert payload["status"] == "inactive"
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE


def _create_assignment_via_api(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    *,
    extra_tasks: int = 0,
    assignee_membership=None,
):
    assignee = assignee_membership or staff_membership
    template, token = _active_registered_template(api_client, owner_membership, business_unit)
    for index in range(extra_tasks):
        task = api_client.post(
            checklist_template_url(owner_membership.establishment_id, template["id"], "tasks/"),
            {"task": f"Extra task {index + 1}"},
            format="json",
            **auth_headers(token),
        )
        assert task.status_code == 201
    created = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        assignment_api_payload(assignee.id),
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201
    return created.json(), token


def test_assignment_patch_updates_assignment_and_assigned_execution(
    api_client,
    owner_membership,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    from datetime import datetime, timedelta

    template, token = _active_registered_template(api_client, owner_membership, business_unit)
    now = timezone.now()
    days_ahead = (0 - now.weekday()) % 7
    monday_start = datetime.combine(
        (now + timedelta(days=days_ahead)).date(),
        datetime.min.time().replace(hour=8),
        tzinfo=now.tzinfo,
    )
    from houston.checklists.tests.conftest import assignment_schedule_from_datetime

    schedule = assignment_schedule_from_datetime(monday_start, duration_hours=2)
    created = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "assignments/"),
        {
            "assigned_to": str(staff_membership.id),
            "start_date": schedule["start_date"].isoformat(),
            "end_date": schedule["end_date"].isoformat(),
            "start_at": schedule["start_at"].strftime("%H:%M:%S"),
            "end_at": schedule["end_at"].strftime("%H:%M:%S"),
            "recurrence_days": ["monday"],
        },
        format="json",
        **auth_headers(token),
    )
    assert created.status_code == 201
    execution = ChecklistExecution.objects.get(checklist_assignment_id=created.json()["id"])
    response = api_client.patch(
        checklist_assignment_url(owner_membership.establishment_id, created.json()["id"]),
        {
            "assigned_to": str(other_staff_membership.id),
            "start_at": "10:00:00",
            "end_at": "13:00:00",
            "recurrence_days": ["monday"],
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assigned_to_id"] == str(other_staff_membership.id)
    assert body["recurrence_days"] == ["monday"]
    execution.refresh_from_db()
    assert execution.assigned_to_id == other_staff_membership.id
    from django.utils import timezone as dj_timezone

    start_time = datetime.strptime("10:00:00", "%H:%M:%S").time()
    end_time = datetime.strptime("13:00:00", "%H:%M:%S").time()
    tz = dj_timezone.get_current_timezone()
    expected_start = dj_timezone.make_aware(
        datetime.combine(execution.occurrence_date, start_time),
        tz,
    )
    expected_end = dj_timezone.make_aware(
        datetime.combine(execution.occurrence_date, end_time),
        tz,
    )
    assert execution.start_at == expected_start
    assert execution.end_at == expected_end


def test_assignment_patch_denied_for_staff(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.actions.tests.conftest import build_api_membership_on_establishment

    created, owner_token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    staff = build_api_membership_on_establishment(
        owner_membership,
        role=EstablishmentMembership.Role.STAFF,
    )
    token = login(api_client, user=staff.user)
    response = api_client.patch(
        checklist_assignment_url(staff.establishment_id, created["id"]),
        {"recurrence_days": ["monday"]},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_assignment_patch_manager_in_scope(
    api_client,
    owner_membership,
    manager_membership,
    staff_membership,
    business_unit,
):
    created, _owner_token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    manager_token = login(api_client, user=manager_membership.user)
    response = api_client.patch(
        checklist_assignment_url(manager_membership.establishment_id, created["id"]),
        {"recurrence_days": ["friday"]},
        format="json",
        **auth_headers(manager_token),
    )
    assert response.status_code == 200
    assert response.json()["recurrence_days"] == ["friday"]


def test_assignment_patch_manager_out_of_scope(
    api_client,
    owner_membership,
    manager_membership,
    staff_membership,
    establishment,
):
    other_bu = create_business_unit(establishment=establishment, key="spa")
    created, _owner_token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        other_bu,
        assignee_membership=owner_membership,
    )
    manager_token = login(api_client, user=manager_membership.user)
    response = api_client.patch(
        checklist_assignment_url(manager_membership.establishment_id, created["id"]),
        {"recurrence_days": ["monday"]},
        format="json",
        **auth_headers(manager_token),
    )
    assert response.status_code == 404


def test_assignment_patch_director_allowed(
    api_client,
    owner_membership,
    director_membership,
    staff_membership,
    business_unit,
):
    created, _owner_token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    director_token = login(api_client, user=director_membership.user)
    response = api_client.patch(
        checklist_assignment_url(director_membership.establishment_id, created["id"]),
        {"recurrence_days": ["sunday"]},
        format="json",
        **auth_headers(director_token),
    )
    assert response.status_code == 200


def test_assignment_patch_rejects_inactive_assignment(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    deactivate = api_client.post(
        checklist_assignment_url(
            owner_membership.establishment_id,
            created["id"],
            "deactivate/",
        ),
        **auth_headers(token),
    )
    assert deactivate.status_code == 200
    response = api_client.patch(
        checklist_assignment_url(owner_membership.establishment_id, created["id"]),
        {"recurrence_days": ["monday"]},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == _ASSIGNMENT_INACTIVE_PATCH_MESSAGE


def test_assignment_deactivate_cancels_assigned_execution(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    execution = ChecklistExecution.objects.get(checklist_assignment_id=created["id"])
    response = api_client.post(
        checklist_assignment_url(
            owner_membership.establishment_id,
            created["id"],
            "deactivate/",
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.CANCELED


def test_assignment_deactivate_blocks_in_progress(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, owner_token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
        extra_tasks=1,
    )
    execution = ChecklistExecution.objects.get(checklist_assignment_id=created["id"])
    task = execution.task_executions.order_by("position").first()
    staff_token = login(api_client, user=staff_membership.user)
    mark_done = api_client.post(
        checklist_task_execution_url(
            staff_membership.establishment_id,
            task.id,
            "mark-done/",
        ),
        **auth_headers(staff_token),
    )
    assert mark_done.status_code == 200
    response = api_client.post(
        checklist_assignment_url(
            owner_membership.establishment_id,
            created["id"],
            "deactivate/",
        ),
        **auth_headers(owner_token),
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["active_execution_id"] == str(execution.id)
    assert payload["detail"] == _REMOVE_ASSIGNMENT_IN_PROGRESS_MESSAGE
    assert ChecklistAssignment.objects.filter(id=created["id"], status="active").exists()


def test_assignment_deactivate_preserves_terminal_history(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    created, token = _create_assignment_via_api(
        api_client,
        owner_membership,
        staff_membership,
        business_unit,
    )
    execution = ChecklistExecution.objects.get(checklist_assignment_id=created["id"])
    execution.status = ChecklistExecution.Status.DONE
    execution.done_at = timezone.now()
    execution.save(update_fields=["status", "done_at", "updated_at"])
    response = api_client.post(
        checklist_assignment_url(
            owner_membership.establishment_id,
            created["id"],
            "deactivate/",
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200
    execution.refresh_from_db()
    assert execution.status == ChecklistExecution.Status.DONE


def test_assignment_list_query_count_baseline_many_assignments(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    from houston.checklists.services import create_checklist_assignment, create_checklist_template
    from houston.checklists.tests.conftest import add_task_template, default_assignment_schedule
    from houston.testing.query_baseline import (
        CHECKLIST_ASSIGNMENT_LIST_TWELVE_ASSIGNMENTS_MAX_QUERIES,
        assert_query_count_at_most,
        capture_queries,
    )

    template = create_checklist_template(
        establishment_id=owner_membership.establishment_id,
        actor=owner_membership,
        title="Routine bulk",
        business_unit_id=business_unit.id,
    )
    add_task_template(template=template, task="Task")
    template.status = "active"
    template.save(update_fields=["status", "updated_at"])
    schedule = default_assignment_schedule()
    for index in range(12):
        create_checklist_assignment(
            template=template,
            actor=owner_membership,
            assigned_to_id=staff_membership.id,
            recurrence_days=[["monday", "tuesday", "wednesday", "thursday", "friday"][index % 5]],
            **schedule,
        )

    token = login(api_client, user=owner_membership.user)
    url = checklist_assignments_url(owner_membership.establishment_id)
    with capture_queries() as context:
        response = api_client.get(url, **auth_headers(token))

    assert response.status_code == 200
    assert len(response.json()) == 12
    assert_query_count_at_most(
        context,
        max_queries=CHECKLIST_ASSIGNMENT_LIST_TWELVE_ASSIGNMENTS_MAX_QUERIES,
        label="GET checklist-assignments/ twelve active assignments",
    )
