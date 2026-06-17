from __future__ import annotations

from datetime import date, datetime
from datetime import timezone as dt_timezone
from unittest.mock import patch

import pytest
from django.utils import timezone

from houston.actions.tests.conftest import (
    auth_headers,
    build_api_membership_on_establishment,
    login,
)
from houston.checklists.models import ChecklistAssignment, ChecklistExecution, ChecklistTemplate
from houston.checklists.services import _ASSIGNEE_OUT_OF_SCOPE_MESSAGE
from houston.checklists.tests.conftest import checklist_template_url
from houston.checklists.tests.test_assignment_api import _active_registered_template
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
    create_membership_with_business_unit_scope,
)
from houston.establishments.timezone_utils import establishment_local_date

pytestmark = pytest.mark.django_db

LOCAL_DAY_BOUNDARY_NOW = timezone.make_aware(datetime(2026, 6, 9, 23, 30, 0))


def _schedule_payload(**overrides) -> dict:
    payload = {
        "start_at": "09:00:00",
        "end_at": "10:00:00",
    }
    payload.update(overrides)
    return payload


def _post_schedule(api_client, membership, template_id, token, **overrides):
    return api_client.post(
        checklist_template_url(membership.establishment_id, template_id, "schedule/"),
        _schedule_payload(**overrides),
        format="json",
        **auth_headers(token),
    )


def _utc_datetime(year, month, day, hour, minute):
    return datetime(year, month, day, hour, minute, tzinfo=dt_timezone.utc)


def _paris_context():
    establishment = create_establishment(name="Paris Hotel", timezone="Europe/Paris")
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    business_unit = create_business_unit(establishment=establishment, key="restaurant")
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff,
        business_unit=business_unit,
    )
    return owner, staff, business_unit


def test_schedule_one_shot_creates_execution(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    staff_token = login(api_client, user=staff_membership.user)

    response = _post_schedule(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
        assigned_to=str(staff_membership.id),
        start_at="14:30:00",
        end_at="15:30:00",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result_type"] == "execution"
    assert body["assignment"] is None
    assert body["execution"]["assigned_to_id"] == str(staff_membership.id)
    assert body["execution"]["start_at"] is not None
    assert body["execution"]["end_at"] is not None

    execution = ChecklistExecution.objects.get(id=body["execution"]["id"])
    assert execution.execution_source == ChecklistExecution.ExecutionSource.TEMPLATE
    assert execution.checklist_assignment_id is None


def test_schedule_recurring_creates_assignment_and_materializes_first_execution_in_db(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(staff_membership.id),
        start_date="2026-06-22",
        recurrence_days=["monday"],
        recurrence_end_date="2026-06-30",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result_type"] == "assignment"
    assert body["execution"] is None
    assert body["assignment"]["assigned_to_id"] == str(staff_membership.id)
    assert body["assignment"]["recurrence_days"] == ["monday"]

    assignment_id = body["assignment"]["id"]
    materialized = ChecklistExecution.objects.filter(checklist_assignment_id=assignment_id)
    assert materialized.count() == 1
    execution = materialized.get()
    assert execution.execution_source == ChecklistExecution.ExecutionSource.ASSIGNMENT
    assert execution.occurrence_date == date(2026, 6, 22)


def test_schedule_rejects_end_at_before_start_at(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(staff_membership.id),
        start_at="11:00:00",
        end_at="10:00:00",
    )
    assert response.status_code == 400


def test_schedule_recurring_requires_recurrence_end_date(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(staff_membership.id),
        recurrence_days=["monday"],
    )
    assert response.status_code == 400


def test_schedule_staff_launch_for_other_assignee_denied(
    api_client,
    owner_membership,
    staff_membership,
    other_staff_membership,
    business_unit,
):
    template, _ = _active_registered_template(api_client, owner_membership, business_unit)
    staff_token = login(api_client, user=staff_membership.user)

    response = _post_schedule(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
        assigned_to=str(other_staff_membership.id),
    )
    assert response.status_code == 403


def test_schedule_staff_cannot_create_recurring_assignment(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, _ = _active_registered_template(api_client, owner_membership, business_unit)
    staff_token = login(api_client, user=staff_membership.user)

    response = _post_schedule(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
        assigned_to=str(staff_membership.id),
        recurrence_days=["tuesday"],
        recurrence_end_date="2026-06-30",
    )
    assert response.status_code == 403


@patch("django.utils.timezone.now", return_value=LOCAL_DAY_BOUNDARY_NOW)
def test_schedule_one_shot_uses_establishment_local_date_for_datetimes(mock_now, api_client):
    owner, staff, business_unit = _paris_context()
    template, owner_token = _active_registered_template(api_client, owner, business_unit)

    response = _post_schedule(
        api_client,
        owner,
        template["id"],
        owner_token,
        assigned_to=str(staff.id),
        start_at="14:30:00",
        end_at="15:30:00",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result_type"] == "execution"

    local_today = establishment_local_date(
        establishment=owner.establishment,
        at=LOCAL_DAY_BOUNDARY_NOW,
    )
    assert local_today == date(2026, 6, 10)

    execution = ChecklistExecution.objects.get(id=body["execution"]["id"])
    assert execution.start_at == _utc_datetime(2026, 6, 10, 12, 30)
    assert execution.end_at == _utc_datetime(2026, 6, 10, 13, 30)
    assert execution.visible_from == _utc_datetime(2026, 6, 10, 11, 30)


def test_schedule_rejects_assignee_outside_business_unit(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    other_business_unit = create_business_unit(establishment=establishment, key="spa")
    scoped_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=scoped_staff,
        business_unit=other_business_unit,
    )
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(scoped_staff.id),
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "validation_error"
    assert body["detail"] == _ASSIGNEE_OUT_OF_SCOPE_MESSAGE


def test_schedule_rejects_inactive_assignee(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    inactive_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=inactive_staff,
        business_unit=business_unit,
    )
    inactive_staff.status = EstablishmentMembership.Status.DEACTIVATED
    inactive_staff.save(update_fields=["status", "updated_at"])
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(inactive_staff.id),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid establishment membership."


def test_schedule_rejects_assignee_from_other_establishment(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    other_establishment = create_establishment(name="Other Hotel")
    other_staff = create_membership(
        establishment=other_establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(other_staff.id),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid establishment membership."


def test_schedule_rejects_inactive_template(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    # Selector still returns inactive templates (visibility ignores status); service rejects.
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    deactivate = api_client.post(
        checklist_template_url(owner_membership.establishment_id, template["id"], "deactivate/"),
        **auth_headers(owner_token),
    )
    assert deactivate.status_code == 200

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(staff_membership.id),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Template must be active."


def test_schedule_rejects_template_without_tasks(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template = ChecklistTemplate.objects.create(
        establishment=owner_membership.establishment,
        created_by=owner_membership,
        business_unit=business_unit,
        title="Empty active template",
        status=ChecklistTemplate.Status.ACTIVE,
    )
    owner_token = login(api_client, user=owner_membership.user)

    response = _post_schedule(
        api_client,
        owner_membership,
        template.id,
        owner_token,
        assigned_to=str(staff_membership.id),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Checklist template must have at least one task."


def test_schedule_rejects_recurrence_end_date_before_start_date(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(staff_membership.id),
        start_date="2026-06-16",
        recurrence_days=["monday"],
        recurrence_end_date="2026-06-10",
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "end_date must be on or after start_date."


def test_schedule_defaults_assigned_to_to_actor_when_omitted(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    staff_token = login(api_client, user=staff_membership.user)

    response = _post_schedule(
        api_client,
        staff_membership,
        template["id"],
        staff_token,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result_type"] == "execution"
    assert body["execution"]["assigned_to_id"] == str(staff_membership.id)


def test_schedule_empty_recurrence_days_creates_one_shot_execution(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    template, owner_token = _active_registered_template(api_client, owner_membership, business_unit)
    assignments_before = ChecklistAssignment.objects.count()

    response = _post_schedule(
        api_client,
        owner_membership,
        template["id"],
        owner_token,
        assigned_to=str(staff_membership.id),
        recurrence_days=[],
    )
    assert response.status_code == 201
    body = response.json()
    assert body["result_type"] == "execution"
    assert body["assignment"] is None
    assert ChecklistAssignment.objects.count() == assignments_before
