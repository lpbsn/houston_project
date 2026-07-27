from __future__ import annotations

import pytest

from houston.action_plans.tests.helpers import (
    action_plan_planning_submit_url,
    action_plan_schedule_deactivate_url,
    action_plan_schedule_detail_url,
    api_planning_schedule_payload,
)
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def test_planning_submit_schedule_rejects_one_shot(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    payload = api_planning_schedule_payload(
        membership=staff_membership,
        business_unit=business_unit,
        recurrence_days=[],
    )
    response = api_client.post(
        action_plan_planning_submit_url(
            owner_membership.establishment_id,
            catalog_action_plan.id,
        ),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400


def test_planning_submit_schedule_recurring_returns_201(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    payload = api_planning_schedule_payload(
        membership=staff_membership,
        business_unit=business_unit,
    )
    response = api_client.post(
        action_plan_planning_submit_url(
            owner_membership.establishment_id,
            catalog_action_plan.id,
        ),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["summary"]["schedules_created"] == 1
    schedule_id = response.json()["schedules"][0]["id"]
    detail = api_client.get(
        action_plan_schedule_detail_url(owner_membership.establishment_id, schedule_id),
        **auth_headers(token),
    )
    assert detail.status_code == 200
    assert detail.json()["recurrence_days"]


def test_schedule_patch_use_shared_chronology_blocked_after_materialization(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    create_response = api_client.post(
        action_plan_planning_submit_url(
            owner_membership.establishment_id,
            catalog_action_plan.id,
        ),
        api_planning_schedule_payload(
            membership=staff_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    schedule_id = create_response.json()["schedules"][0]["id"]

    patch_response = api_client.patch(
        action_plan_schedule_detail_url(owner_membership.establishment_id, schedule_id),
        {"use_shared_chronology": False},
        format="json",
        **auth_headers(token),
    )
    assert patch_response.status_code == 400


def test_staff_planning_submit_schedule_on_in_scope_catalog_returns_201(
    api_client,
    staff_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plan_planning_submit_url(
            staff_membership.establishment_id,
            catalog_action_plan.id,
        ),
        api_planning_schedule_payload(
            membership=staff_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.json()
    schedule_id = response.json()["schedules"][0]["id"]
    detail = api_client.get(
        action_plan_schedule_detail_url(staff_membership.establishment_id, schedule_id),
        **auth_headers(token),
    )
    assert detail.status_code == 200
    assert detail.json()["assignees"][0]["membership_id"] == str(staff_membership.id)


def test_staff_planning_submit_schedule_rejects_third_party_assignee(
    api_client,
    owner_membership,
    staff_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plan_planning_submit_url(
            staff_membership.establishment_id,
            catalog_action_plan.id,
        ),
        api_planning_schedule_payload(
            membership=owner_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    # planning-submit wraps per-item PermissionError as PlanningSubmissionItemError → 400
    assert response.status_code == 400
    assert "Not allowed to assign other members" in response.json()["detail"]


def test_staff_planning_submit_schedule_rejects_cross_pole_catalog(
    api_client,
    staff_membership,
    cross_pole_catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plan_planning_submit_url(
            staff_membership.establishment_id,
            cross_pole_catalog_action_plan.id,
        ),
        api_planning_schedule_payload(
            membership=staff_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 404


def test_schedule_deactivate_conflict_returns_409(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    from django.utils import timezone

    from houston.action_plans.models import ActionPlanExecution

    token = login(api_client, user=owner_membership.user)
    create_response = api_client.post(
        action_plan_planning_submit_url(
            owner_membership.establishment_id,
            catalog_action_plan.id,
        ),
        api_planning_schedule_payload(
            membership=staff_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    schedule_id = create_response.json()["schedules"][0]["id"]
    execution = ActionPlanExecution.objects.filter(action_plan_schedule_id=schedule_id).first()
    execution.start_at = timezone.now() - timezone.timedelta(minutes=1)
    execution.end_at = timezone.now() + timezone.timedelta(hours=1)
    execution.visible_from = execution.start_at - timezone.timedelta(hours=1)
    execution.save(update_fields=["start_at", "end_at", "visible_from", "updated_at"])

    response = api_client.post(
        action_plan_schedule_deactivate_url(owner_membership.establishment_id, schedule_id),
        {},
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 409
    assert response.json()["active_execution_id"] == str(execution.id)
