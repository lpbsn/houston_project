from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.db import close_old_connections, connections
from django.utils import timezone

from houston.action_plans.models import (
    ActionPlanExecution,
    ActionPlanPlanningOutboxEntry,
    ActionPlanPlanningSubmission,
    ActionPlanSchedule,
)
from houston.action_plans.planning_services import submit_action_plan_planning
from houston.action_plans.tests.helpers import (
    action_plan_planning_submit_url,
    action_plan_url,
    api_assignee_payload,
    api_planning_submit_payload,
    create_catalog_action_plan,
    recurrence_days_for_visible_today,
    visible_schedule_window,
)
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, login
from houston.testing.factories import create_membership
from houston.testing.taxonomy import create_membership_with_business_unit_scope


@pytest.mark.django_db
def test_planning_submit_individual_mixed_creates_resources(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    staff_b = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff_b,
        business_unit=business_unit,
    )

    payload = api_planning_submit_payload(
        recurring_membership=staff_b,
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
    body = response.json()
    assert body["summary"]["executions_created"] == 1
    assert body["summary"]["schedules_created"] == 1

    execution = ActionPlanExecution.objects.get(id=body["executions"][0]["id"])
    assert execution.use_shared_chronology is False
    assert execution.chronology_owner_membership_id == staff_membership.id
    assert execution.status == "scheduled"

    schedule = ActionPlanSchedule.objects.get(id=body["schedules"][0]["id"])
    assert schedule.use_shared_chronology is False
    assert schedule.schedule_assignees.count() == 1

    assert ActionPlanPlanningOutboxEntry.objects.filter(
        planning_submission__submission_id=payload["submission_id"]
    ).exists()


@pytest.mark.django_db
def test_planning_submit_replay_is_idempotent(
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
    url = action_plan_planning_submit_url(owner_membership.establishment_id, catalog.id)
    token = login(api_client, user=owner_membership.user)
    first = api_client.post(url, payload, format="json", **auth_headers(token))
    assert first.status_code == 201, first.content
    second = api_client.post(url, payload, format="json", **auth_headers(token))
    assert second.status_code == 200, second.content
    assert second.json()["replayed"] is True
    assert second.json()["executions"][0]["id"] == first.json()["executions"][0]["id"]
    assert (
        ActionPlanPlanningSubmission.objects.filter(
            submission_id=payload["submission_id"]
        ).count()
        == 1
    )


@pytest.mark.django_db
def test_planning_submit_hash_conflict(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    submission_id = uuid.uuid4()
    payload = api_planning_submit_payload(
        submission_id=submission_id,
        recurring_membership=staff_membership,
        one_shot_membership=staff_membership,
        business_unit=business_unit,
    )
    url = action_plan_planning_submit_url(owner_membership.establishment_id, catalog.id)
    token = login(api_client, user=owner_membership.user)
    assert (
        api_client.post(url, payload, format="json", **auth_headers(token)).status_code
        == 201
    )

    payload["items"][0]["end_at"] = (
        (timezone.now() + timedelta(days=2)).isoformat().replace("+00:00", "Z")
    )
    conflict = api_client.post(url, payload, format="json", **auth_headers(token))
    assert conflict.status_code == 409


@pytest.mark.django_db
def test_planning_submit_incomplete_schedule_item_returns_400_indexed_by_item(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    item_id = str(uuid.uuid4())
    payload = {
        "submission_id": str(uuid.uuid4()),
        "use_shared_chronology": False,
        "items": [
            {
                "item_id": item_id,
                "kind": "schedule",
                "primary_membership_id": str(staff_membership.id),
                "business_unit_id": str(business_unit.id),
                # missing end_date / start_at / end_at / recurrence_days
            }
        ],
    }
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plan_planning_submit_url(owner_membership.establishment_id, catalog.id),
        payload,
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400, response.content
    body = response.json()
    item_errors = body["errors"]["items"][0]
    assert "end_date" in item_errors
    assert "start_at" in item_errors
    assert "end_at" in item_errors
    assert "recurrence_days" in item_errors
    assert ActionPlanSchedule.objects.count() == 0
    assert ActionPlanPlanningSubmission.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_concurrent_planning_submit_same_hash_replays_without_false_conflict(
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    staff_b = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff_b,
        business_unit=business_unit,
    )

    window = visible_schedule_window(period_days=14)
    start_at = timezone.now() + timedelta(days=1)
    end_at = start_at + timedelta(hours=2)
    submission_id = uuid.uuid4()
    items = [
        {
            "item_id": uuid.uuid4(),
            "kind": "execution",
            "primary_membership_id": staff_membership.id,
            "business_unit_id": business_unit.id,
            "start_at": start_at,
            "end_at": end_at,
            "visible_from": None,
            "assignees": [],
        },
        {
            "item_id": uuid.uuid4(),
            "kind": "schedule",
            "primary_membership_id": staff_b.id,
            "business_unit_id": business_unit.id,
            "start_date": window["start_date"],
            "end_date": window["end_date"],
            "start_at": window["start_at"],
            "end_at": window["end_at"],
            "recurrence_days": recurrence_days_for_visible_today(),
            "assignees": [],
        },
    ]

    def _worker(_: int):
        close_old_connections()
        try:
            return submit_action_plan_planning(
                actor=owner_membership,
                establishment_id=owner_membership.establishment_id,
                submission_id=submission_id,
                use_shared_chronology=False,
                items=items,
                action_plan=catalog,
            )
        finally:
            connections.close_all()

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(_worker, range(2)))
    finally:
        connections.close_all()

    assert len(results) == 2
    assert {result.replayed for result in results} == {False, True}
    assert results[0].executions[0].resource_id == results[1].executions[0].resource_id
    assert results[0].schedules[0].resource_id == results[1].schedules[0].resource_id
    assert (
        ActionPlanPlanningSubmission.objects.filter(submission_id=submission_id).count()
        == 1
    )
    assert ActionPlanExecution.objects.filter(action_plan=catalog).count() >= 1


@pytest.mark.django_db
def test_use_rejects_individual_multi_assignee(
    api_client,
    owner_membership,
    staff_membership,
    business_unit,
    establishment,
):
    catalog = create_catalog_action_plan(
        owner_membership=owner_membership,
        business_unit=business_unit,
    )
    staff_b = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=staff_b,
        business_unit=business_unit,
    )
    token = login(api_client, user=owner_membership.user)
    response = api_client.post(
        action_plan_url(owner_membership.establishment_id, catalog.id, "use/"),
        {
            "use_shared_chronology": False,
            "assignees": [
                api_assignee_payload(membership=staff_membership, business_unit=business_unit),
                api_assignee_payload(membership=staff_b, business_unit=business_unit),
            ],
        },
        format="json",
        **auth_headers(token),
    )
    assert response.status_code == 400
    assert "planning-submit" in response.json()["detail"]
