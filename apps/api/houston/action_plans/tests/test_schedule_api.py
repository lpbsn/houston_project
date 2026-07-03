from __future__ import annotations

import pytest

from houston.action_plans.tests.conftest import (
    action_plan_schedule_deactivate_url,
    action_plan_schedule_detail_url,
    action_plan_schedule_url,
    action_plan_url,
    api_recurring_schedule_payload,
    auth_headers,
    login,
)

pytestmark = pytest.mark.django_db


def test_schedule_create_rejects_one_shot(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    payload = api_recurring_schedule_payload(
        staff_membership=staff_membership,
        business_unit=business_unit,
        recurrence_days=[],
    )
    response = api_client.post(
        action_plan_schedule_url(owner_membership.establishment_id, catalog_action_plan.id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400


def test_schedule_create_recurring_returns_201(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    payload = api_recurring_schedule_payload(
        staff_membership=staff_membership,
        business_unit=business_unit,
    )
    response = api_client.post(
        action_plan_schedule_url(owner_membership.establishment_id, catalog_action_plan.id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201
    assert response.json()["recurrence_days"]


def test_use_endpoint_still_one_shot_path(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plan_url(owner_membership.establishment_id, catalog_action_plan.id, "use/"),
        {
            "assignees": [
                {
                    "membership_id": str(staff_membership.id),
                    "business_unit_id": str(business_unit.id),
                }
            ]
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201


def test_schedule_patch_use_shared_chronology_blocked_after_materialization(
    api_client,
    owner_membership,
    catalog_action_plan,
    staff_membership,
    business_unit,
):
    token = login(api_client, user=owner_membership.user)
    create_response = api_client.post(
        action_plan_schedule_url(owner_membership.establishment_id, catalog_action_plan.id),
        api_recurring_schedule_payload(
            staff_membership=staff_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    schedule_id = create_response.json()["id"]

    patch_response = api_client.patch(
        action_plan_schedule_detail_url(owner_membership.establishment_id, schedule_id),
        {"use_shared_chronology": False},
        format="json",
        **auth_headers(token),
    )
    assert patch_response.status_code == 400


def test_staff_schedule_create_on_catalog_returns_404(
    api_client,
    staff_membership,
    catalog_action_plan,
    business_unit,
):
    token = login(api_client, user=staff_membership.user)
    response = api_client.post(
        action_plan_schedule_url(staff_membership.establishment_id, catalog_action_plan.id),
        api_recurring_schedule_payload(
            staff_membership=staff_membership,
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
        action_plan_schedule_url(owner_membership.establishment_id, catalog_action_plan.id),
        api_recurring_schedule_payload(
            staff_membership=staff_membership,
            business_unit=business_unit,
        ),
        format="json",
        **auth_headers(token),
    )
    schedule_id = create_response.json()["id"]
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
