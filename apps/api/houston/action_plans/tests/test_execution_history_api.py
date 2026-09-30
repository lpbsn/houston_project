from __future__ import annotations

from datetime import datetime, timedelta
from datetime import timezone as datetime_timezone

import pytest
from django.utils import timezone

from houston.action_plans.constants import (
    CANCEL_ORIGIN_MANUAL,
    CANCEL_ORIGIN_SCHEDULE_SYNC,
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
)
from houston.action_plans.lifecycle_events import record_execution_lifecycle_event
from houston.action_plans.models import ActionPlanExecutionLifecycleEvent
from houston.action_plans.tests.helpers import create_execution
from houston.core.civil_time import PARIS
from houston.testing.auth import auth_headers, login

pytestmark = pytest.mark.django_db


def _history_url(establishment_id, **params: str) -> str:
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return f"/api/v1/establishments/{establishment_id}/history/executions/?{query}"


def _fetch(api_client, membership, **params: str):
    token = login(api_client, user=membership.user)
    return api_client.get(
        _history_url(membership.establishment_id, view_mode="general", **params),
        **auth_headers(token),
    )


def test_validated_execution_uses_validated_at_and_detail_stays_open(
    api_client,
    owner_membership,
    business_unit,
):
    owner_membership.user.first_name = "Grace"
    owner_membership.user.last_name = "Hopper"
    owner_membership.user.save(update_fields=["first_name", "last_name"])
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Validée",
        status=EXECUTION_STATUS_DONE,
    )
    marked = timezone.now() - timedelta(days=2)
    validated = timezone.now() - timedelta(hours=1)
    execution.marked_done_at = marked
    execution.marked_done_by_membership = owner_membership
    execution.validated_at = validated
    execution.validated_by_membership = owner_membership
    execution.save(
        update_fields=[
            "marked_done_at",
            "marked_done_by_membership",
            "validated_at",
            "validated_by_membership",
            "updated_at",
        ]
    )
    active = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="En cours",
        status=EXECUTION_STATUS_IN_PROGRESS,
    )
    response = _fetch(api_client, owner_membership, period="all")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["items"]]
    assert str(execution.id) in ids
    assert str(active.id) not in ids
    item = next(row for row in response.json()["items"] if row["id"] == str(execution.id))
    assert item["terminal_date_source"] == "field"
    assert item["termination_origin"] == "manual"
    assert item["termination_actor_display_name"] == "Grace Hopper"
    assert item["title"] == "Validée"
    assert item["pilot_business_unit"]["id"] == str(business_unit.id)
    assert item["validated_at"] is not None
    parsed = datetime.fromisoformat(item["terminal_at"].replace("Z", "+00:00"))
    assert abs((parsed - validated.astimezone(datetime_timezone.utc)).total_seconds()) < 1

    token = login(api_client, user=owner_membership.user)
    detail = api_client.get(
        f"/api/v1/establishments/{owner_membership.establishment_id}/action-plan-executions/{execution.id}/",
        **auth_headers(token),
    )
    assert detail.status_code == 200


def test_done_without_validation_uses_marked_done_at(api_client, owner_membership, business_unit):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Terminée",
        status=EXECUTION_STATUS_DONE,
        requires_validation=False,
    )
    execution.marked_done_at = timezone.now()
    execution.marked_done_by_membership = owner_membership
    execution.validated_at = None
    execution.save(
        update_fields=["marked_done_at", "marked_done_by_membership", "validated_at", "updated_at"]
    )
    response = _fetch(api_client, owner_membership, period="all")
    item = next(row for row in response.json()["items"] if row["id"] == str(execution.id))
    assert item["terminal_date_source"] == "field"
    assert item["termination_origin"] == "manual"


def test_done_requiring_validation_ignores_marked_done_as_a_terminal_date(
    api_client,
    owner_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Validée via événement",
        status=EXECUTION_STATUS_DONE,
        requires_validation=True,
    )
    execution.marked_done_at = timezone.now() - timedelta(days=1)
    execution.marked_done_by_membership = owner_membership
    execution.validated_at = None
    execution.save(
        update_fields=[
            "marked_done_at",
            "marked_done_by_membership",
            "validated_at",
            "updated_at",
        ]
    )
    validated_at = timezone.now()
    record_execution_lifecycle_event(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_VALIDATED,
        occurred_at=validated_at,
        actor_membership=owner_membership,
    )

    response = _fetch(api_client, owner_membership, period="all")
    item = next(row for row in response.json()["items"] if row["id"] == str(execution.id))
    parsed = datetime.fromisoformat(item["terminal_at"].replace("Z", "+00:00"))
    assert abs((parsed - validated_at.astimezone(datetime_timezone.utc)).total_seconds()) < 1
    assert item["terminal_date_source"] == "event"
    assert item["termination_origin"] == "unknown"
    assert item["termination_actor_display_name"] is None


def test_manual_cancel_without_actor_is_unknown(api_client, owner_membership, business_unit):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Annulée",
        status=EXECUTION_STATUS_CANCELED,
    )
    execution.canceled_at = timezone.now()
    execution.cancel_origin = CANCEL_ORIGIN_MANUAL
    execution.canceled_by_membership = None
    execution.save(
        update_fields=["canceled_at", "cancel_origin", "canceled_by_membership", "updated_at"]
    )
    response = _fetch(api_client, owner_membership, period="all")
    item = next(row for row in response.json()["items"] if row["id"] == str(execution.id))
    assert item["termination_origin"] == "unknown"
    assert item["termination_actor_display_name"] is None


def test_schedule_sync_cancel_keeps_its_path(api_client, owner_membership, business_unit):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Sync",
        status=EXECUTION_STATUS_CANCELED,
    )
    execution.canceled_at = timezone.now()
    execution.cancel_origin = CANCEL_ORIGIN_SCHEDULE_SYNC
    execution.save(update_fields=["canceled_at", "cancel_origin", "updated_at"])
    response = _fetch(api_client, owner_membership, period="all")
    item = next(row for row in response.json()["items"] if row["id"] == str(execution.id))
    assert item["termination_origin"] == "schedule_sync"
    assert item["termination_actor_display_name"] is None


def test_orphan_execution_is_counted_outside_the_period(
    api_client,
    owner_membership,
    business_unit,
):
    dated = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Datée",
        status=EXECUTION_STATUS_DONE,
    )
    dated.validated_at = timezone.now()
    dated.validated_by_membership = owner_membership
    dated.save(update_fields=["validated_at", "validated_by_membership", "updated_at"])
    orphan = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Sans date",
        status=EXECUTION_STATUS_DONE,
    )
    orphan.validated_at = None
    orphan.marked_done_at = None
    orphan.save(update_fields=["validated_at", "marked_done_at", "updated_at"])
    bounded = _fetch(api_client, owner_membership, period="30")
    assert bounded.json()["undated_count"] == 1
    assert str(orphan.id) not in [item["id"] for item in bounded.json()["items"]]
    everything = _fetch(api_client, owner_membership, period="all")
    rows = everything.json()["items"]
    assert rows[-1]["id"] == str(orphan.id)
    assert rows[-1]["terminal_date_source"] == "unknown"


def test_missing_cancel_field_uses_the_lifecycle_event(api_client, owner_membership, business_unit):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Événement",
        status=EXECUTION_STATUS_CANCELED,
    )
    execution.canceled_at = None
    execution.cancel_origin = None
    execution.save(update_fields=["canceled_at", "cancel_origin", "updated_at"])
    occurred_at = datetime(2026, 9, 28, 15, tzinfo=PARIS)
    record_execution_lifecycle_event(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        occurred_at=occurred_at,
    )
    response = _fetch(
        api_client,
        owner_membership,
        period="custom",
        **{"from": "2026-09-28", "to": "2026-09-28"},
    )
    item = response.json()["items"][0]
    assert item["id"] == str(execution.id)
    assert item["terminal_date_source"] == "event"
    assert item["termination_origin"] == "unknown"


def test_reactivation_removes_the_execution_until_it_is_terminal_again(
    api_client,
    owner_membership,
    business_unit,
):
    execution = create_execution(
        owner_membership,
        business_unit=business_unit,
        title="Cycle",
        status=EXECUTION_STATUS_CANCELED,
    )
    first_at = timezone.now() - timedelta(days=3)
    execution.canceled_at = first_at
    execution.cancel_origin = CANCEL_ORIGIN_MANUAL
    execution.canceled_by_membership = owner_membership
    execution.save(
        update_fields=[
            "canceled_at",
            "cancel_origin",
            "canceled_by_membership",
            "updated_at",
        ]
    )
    record_execution_lifecycle_event(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        occurred_at=first_at,
        actor_membership=owner_membership,
    )
    assert str(execution.id) in [
        item["id"] for item in _fetch(api_client, owner_membership, period="all").json()["items"]
    ]

    execution.status = EXECUTION_STATUS_IN_PROGRESS
    execution.canceled_at = None
    execution.cancel_origin = None
    execution.canceled_by_membership = None
    execution.save(
        update_fields=[
            "status",
            "canceled_at",
            "cancel_origin",
            "canceled_by_membership",
            "updated_at",
        ]
    )
    assert str(execution.id) not in [
        item["id"] for item in _fetch(api_client, owner_membership, period="all").json()["items"]
    ]
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=execution,
            event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        ).count()
        == 1
    )

    second_at = timezone.now()
    execution.status = EXECUTION_STATUS_CANCELED
    execution.canceled_at = second_at
    execution.cancel_origin = CANCEL_ORIGIN_MANUAL
    execution.canceled_by_membership = owner_membership
    execution.save(
        update_fields=[
            "status",
            "canceled_at",
            "cancel_origin",
            "canceled_by_membership",
            "updated_at",
        ]
    )
    record_execution_lifecycle_event(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        occurred_at=second_at,
        actor_membership=owner_membership,
    )
    rows = _fetch(api_client, owner_membership, period="all").json()["items"]
    item = next(row for row in rows if row["id"] == str(execution.id))
    parsed = datetime.fromisoformat(item["terminal_at"].replace("Z", "+00:00"))
    assert abs((parsed - second_at.astimezone(datetime_timezone.utc)).total_seconds()) < 1
    assert (
        ActionPlanExecutionLifecycleEvent.objects.filter(
            action_plan_execution=execution,
            event_type=EXECUTION_LIFECYCLE_EVENT_CANCELED,
        ).count()
        == 2
    )
