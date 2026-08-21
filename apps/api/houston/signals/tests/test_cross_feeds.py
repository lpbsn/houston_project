from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_establishment, create_membership, create_user
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
    create_minimal_v3_signal,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def test_cross_signal_feed_is_read_only_and_includes_establishment(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_minimal_v3_signal(owner, title="Cross visible")
    token = login(api_client, user=owner.user)

    response = api_client.get("/api/v1/cross/signal-feed/", **auth_headers(token))
    post = api_client.post("/api/v1/cross/signal-feed/", **auth_headers(token))

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["establishment_id"] == str(owner.establishment_id)
    assert item["establishment_name"] == owner.establishment.name
    assert item["permission_hints"]["can_pin"] is False
    assert item["permission_hints"]["can_resolve"] is False
    assert post.status_code == 405


def test_cross_signal_feed_staff_forbidden(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    token = login(api_client, user=staff.user)
    response = api_client.get("/api/v1/cross/signal-feed/", **auth_headers(token))
    assert response.status_code == 403


def test_cross_signal_feed_unions_management_establishments(api_client):
    user = create_user(username="cross-feed-owner")
    first = create_establishment(name="Alpha")
    second = create_establishment(name="Beta")
    membership_a = create_membership(
        establishment=first,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    membership_b = create_membership(
        establishment=second,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_minimal_v3_signal(membership_a, title="From A")
    create_minimal_v3_signal(membership_b, title="From B")
    token = login(api_client, user=user)

    response = api_client.get("/api/v1/cross/signal-feed/", **auth_headers(token))
    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {"From A", "From B"}


def test_cross_execution_feed_hints_are_false(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = create_membership(
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    business_unit = create_business_unit(establishment=owner.establishment, key="salle")
    create_membership_with_business_unit_scope(membership=staff, business_unit=business_unit)
    _, execution = create_action_plan_with_execution(
        establishment_id=owner.establishment_id,
        created_by=owner,
        pilot_business_unit_id=business_unit.id,
        title="Cross plan",
        tasks=[build_task_payload(task="Do it", business_unit=business_unit)],
        assignees=[build_assignee_payload(membership=staff, business_unit=business_unit)],
    )
    token = login(api_client, user=owner.user)

    feed = api_client.get("/api/v1/cross/action-plan-execution-feed/", **auth_headers(token))
    detail = api_client.get(
        f"/api/v1/cross/action-plan-executions/{execution.id}/",
        **auth_headers(token),
    )
    post = api_client.post(
        f"/api/v1/cross/action-plan-executions/{execution.id}/",
        **auth_headers(token),
    )

    assert feed.status_code == 200
    item = feed.json()["items"][0]["action_plan_execution"]
    assert item["permission_hints"]["can_mark_done"] is False
    assert item["permission_hints"]["can_pin"] is False
    assert item["establishment_id"] == str(owner.establishment_id)
    assert detail.status_code == 200
    assert detail.json()["permission_hints"]["can_update"] is False
    assert post.status_code == 405


def test_signal_feed_uses_url_establishment_when_session_is_another(api_client):
    user = create_user(username="multi-est-actor")
    first = create_establishment(name="Session A")
    second = create_establishment(name="Target B")
    create_membership(
        establishment=first,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    membership_b = create_membership(
        establishment=second,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_minimal_v3_signal(membership_b, title="Only on B")
    token = login(api_client, user=user)

    response = api_client.get(
        f"/api/v1/establishments/{second.id}/signal-feed/?view_mode=personal",
        **auth_headers(token),
    )
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["items"]}
    assert titles == {"Only on B"}


def test_signal_feed_foreign_establishment_is_not_found(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = create_establishment(name="Foreign")
    token = login(api_client, user=owner.user)
    response = api_client.get(
        f"/api/v1/establishments/{foreign.id}/signal-feed/?view_mode=personal",
        **auth_headers(token),
    )
    assert response.status_code in {403, 404}
