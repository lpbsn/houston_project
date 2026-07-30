from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
)
from houston.testing.auth import assign_business_unit_scope, build_api_membership_on_establishment

pytestmark = pytest.mark.django_db


def _fetch_signal_detail(api_client, membership, signal):
    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _create_linked_execution(
    *,
    owner_membership,
    signal,
    business_unit,
    title: str,
    assignees=None,
    last_activity_at=None,
):
    _, execution = create_action_plan_with_execution(
        establishment_id=owner_membership.establishment_id,
        created_by=owner_membership,
        pilot_business_unit_id=business_unit.id,
        title=title,
        source_signal_id=signal.id,
        tasks=[build_task_payload(task=f"Task for {title}", business_unit=business_unit)],
        assignees=assignees or [],
    )
    if last_activity_at is not None:
        execution.last_activity_at = last_activity_at
        execution.save(update_fields=["last_activity_at"])
    return execution


def test_signal_detail_without_linked_executions_returns_empty_list(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner)

    body = _fetch_signal_detail(api_client, owner, signal)

    assert body["linked_action_plan_executions"] == []


def test_signal_detail_includes_visible_linked_execution(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    execution = _create_linked_execution(
        owner_membership=owner,
        signal=signal,
        business_unit=taxonomy.maintenance,
        title="Fix leak",
    )

    body = _fetch_signal_detail(api_client, owner, signal)

    assert len(body["linked_action_plan_executions"]) == 1
    item = body["linked_action_plan_executions"][0]
    assert item["id"] == str(execution.id)
    assert item["title"] == "Fix leak"
    assert item["status"] == execution.status
    assert item["validated_at"] is None
    assert item["pilot_business_unit"]["id"] == str(taxonomy.maintenance.id)
    assert "last_activity_at" in item
    assert "created_at" in item


def test_signal_detail_linked_executions_sorted_by_last_activity_desc(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    now = timezone.now()
    older = _create_linked_execution(
        owner_membership=owner,
        signal=signal,
        business_unit=taxonomy.maintenance,
        title="Older plan",
        last_activity_at=now - timedelta(hours=2),
    )
    newer = _create_linked_execution(
        owner_membership=owner,
        signal=signal,
        business_unit=taxonomy.maintenance,
        title="Newer plan",
        last_activity_at=now - timedelta(minutes=5),
    )

    body = _fetch_signal_detail(api_client, owner, signal)

    ids = [item["id"] for item in body["linked_action_plan_executions"]]
    assert ids == [str(newer.id), str(older.id)]


def test_signal_detail_hides_linked_execution_outside_rbac(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    assignee = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    outsider = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    signal = create_minimal_v3_signal(owner)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assign_business_unit_scope(assignee, taxonomy.maintenance)
    assign_business_unit_scope(outsider, taxonomy.maintenance)
    _create_linked_execution(
        owner_membership=owner,
        signal=signal,
        business_unit=taxonomy.maintenance,
        title="Assigned plan",
        assignees=[build_assignee_payload(membership=assignee, business_unit=taxonomy.maintenance)],
    )

    assignee_body = _fetch_signal_detail(api_client, assignee, signal)
    outsider_body = _fetch_signal_detail(api_client, outsider, signal)

    assert len(assignee_body["linked_action_plan_executions"]) == 1
    assert outsider_body["linked_action_plan_executions"] == []


def test_signal_detail_linked_executions_respect_establishment_isolation(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign_owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, status=Signal.Status.OPEN)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    _create_linked_execution(
        owner_membership=owner,
        signal=signal,
        business_unit=taxonomy.maintenance,
        title="Local plan",
    )

    token = login(api_client, user=foreign_owner.user)
    response = api_client.get(
        signal_detail_url(foreign_owner.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404
