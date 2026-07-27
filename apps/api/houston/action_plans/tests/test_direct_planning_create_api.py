from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanPlanningOutboxEntry,
    ActionPlanPlanningSubmission,
    ActionPlanSchedule,
)
from houston.action_plans.tests.helpers import (
    action_plan_planning_submit_url,
    action_plans_url,
    api_planning_submit_payload,
    api_task_payload,
    create_catalog_action_plan,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_membership
from houston.testing.taxonomy import create_membership_with_business_unit_scope


def _direct_planning_create_payload(
    *,
    business_unit,
    recurring_membership,
    one_shot_membership,
    submission_id=None,
    title: str = "Direct individual plan",
) -> dict:
    planning = api_planning_submit_payload(
        submission_id=submission_id,
        recurring_membership=recurring_membership,
        one_shot_membership=one_shot_membership,
        business_unit=business_unit,
    )
    return {
        "title": title,
        "description": "One-shot non-catalog",
        "pilot_business_unit_id": str(business_unit.id),
        "requires_validation": True,
        "is_reusable": False,
        "tasks": [api_task_payload(task="Check fridge", business_unit=business_unit)],
        "use_shared_chronology": planning["use_shared_chronology"],
        "submission_id": planning["submission_id"],
        "items": planning["items"],
    }


@pytest.mark.django_db
def test_direct_planning_create_individual_creates_resources_and_stays_out_of_catalog(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    staff_b = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff_b,
        business_unit=business_unit,
    )
    payload = _direct_planning_create_payload(
        business_unit=business_unit,
        recurring_membership=staff_b,
        one_shot_membership=staff_membership,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plans_url(owner_membership.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.content
    body = response.json()
    assert body["replayed"] is False
    assert body["summary"]["executions_created"] == 1
    assert body["summary"]["schedules_created"] == 1
    assert body["action_plan_id"]

    plan = ActionPlan.objects.get(id=body["action_plan_id"])
    assert plan.is_reusable is False
    assert plan.catalog_status is None

    assert ActionPlanExecution.objects.filter(action_plan=plan).count() >= 1
    assert ActionPlanSchedule.objects.filter(action_plan=plan).count() == 1
    assert ActionPlanPlanningSubmission.objects.filter(
        submission_id=payload["submission_id"]
    ).count() == 1
    assert ActionPlanPlanningOutboxEntry.objects.filter(
        planning_submission__submission_id=payload["submission_id"]
    ).exists()

    catalog = api_client.get(
        action_plans_url(owner_membership.establishment_id),
        **auth_headers(token),
    )
    assert catalog.status_code == 200
    assert all(item["id"] != str(plan.id) for item in catalog.json())


@pytest.mark.django_db
def test_direct_planning_create_replay_same_hash_does_not_create_second_plan(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    payload = _direct_planning_create_payload(
        business_unit=business_unit,
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
    )
    url = action_plans_url(owner_membership.establishment_id)
    token = login(api_client, user=owner_membership.user)
    first = api_client.post(url, payload, format="json", **auth_headers(token))
    assert first.status_code == 201, first.content
    plan_id = first.json()["action_plan_id"]
    plans_before = ActionPlan.objects.count()

    second = api_client.post(url, payload, format="json", **auth_headers(token))
    assert second.status_code == 200, second.content
    assert second.json()["replayed"] is True
    assert second.json()["action_plan_id"] == plan_id
    assert ActionPlan.objects.count() == plans_before
    assert (
        ActionPlanPlanningSubmission.objects.filter(
            submission_id=payload["submission_id"]
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_direct_planning_create_hash_conflict_keeps_single_plan(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    submission_id = uuid.uuid4()
    payload = _direct_planning_create_payload(
        business_unit=business_unit,
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
        submission_id=submission_id,
    )
    url = action_plans_url(owner_membership.establishment_id)
    token = login(api_client, user=owner_membership.user)
    assert (
        api_client.post(url, payload, format="json", **auth_headers(token)).status_code
        == 201
    )
    plans_before = ActionPlan.objects.count()

    payload["items"][0]["end_at"] = (
        (timezone.now() + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    )
    conflict = api_client.post(url, payload, format="json", **auth_headers(token))
    assert conflict.status_code == 409
    assert ActionPlan.objects.count() == plans_before


@pytest.mark.django_db
def test_direct_planning_create_rolls_back_when_resource_creation_fails(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    payload = _direct_planning_create_payload(
        business_unit=business_unit,
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
    )
    # Valid structure, unknown membership → fails inside resource engine after plan insert.
    payload["items"][0]["primary_membership_id"] = str(uuid.uuid4())

    plans_before = ActionPlan.objects.count()
    submissions_before = ActionPlanPlanningSubmission.objects.count()
    executions_before = ActionPlanExecution.objects.count()
    schedules_before = ActionPlanSchedule.objects.count()
    outbox_before = ActionPlanPlanningOutboxEntry.objects.count()

    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plans_url(owner_membership.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code in {400, 403}
    assert ActionPlan.objects.count() == plans_before
    assert ActionPlanPlanningSubmission.objects.count() == submissions_before
    assert ActionPlanExecution.objects.count() == executions_before
    assert ActionPlanSchedule.objects.count() == schedules_before
    assert ActionPlanPlanningOutboxEntry.objects.count() == outbox_before


@pytest.mark.django_db
def test_planning_submit_rejects_non_reusable_plan(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    payload = _direct_planning_create_payload(
        business_unit=business_unit,
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
    )
    token = login(api_client, user=owner_membership.user)
    create = api_client.post(
        action_plans_url(owner_membership.establishment_id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert create.status_code == 201, create.content
    plan_id = create.json()["action_plan_id"]

    submit_payload = api_planning_submit_payload(
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
        business_unit=business_unit,
    )
    denied = api_client.post(
        action_plan_planning_submit_url(owner_membership.establishment_id, plan_id),
        submit_payload,
        format="json",
        **auth_headers(token),
    )
    assert denied.status_code == 403


@pytest.mark.django_db
def test_planning_submit_on_catalog_template_still_works(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    payload = api_planning_submit_payload(
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
        business_unit=business_unit,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plan_planning_submit_url(owner_membership.establishment_id, catalog.id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 201, response.content
    assert response.json()["summary"]["executions_created"] == 1
    assert response.json()["summary"]["schedules_created"] == 1
