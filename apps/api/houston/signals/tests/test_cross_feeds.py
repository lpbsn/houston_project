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


def _cross_calendar_query(*, from_date, to_date, view_mode=None) -> str:
    query = f"?from={from_date.isoformat()}&to={to_date.isoformat()}"
    if view_mode is not None:
        query += f"&view_mode={view_mode}"
    return query


def test_cross_execution_feed_defaults_to_general_view_mode(api_client):
    from houston.action_plans.tests.helpers import create_execution
    from houston.comments.models import Comment, CommentMention
    from houston.testing.taxonomy import create_business_unit as make_bu

    user = create_user(username="cross-view-mode")
    establishment = create_establishment(name="Scoped")
    restaurant = make_bu(establishment=establishment, key="salle")
    maintenance = make_bu(establishment=establishment, key="maintenance")
    manager = create_membership(
        establishment=establishment,
        user=user,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(membership=manager, business_unit=restaurant)
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    maintenance_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=maintenance_staff,
        business_unit=maintenance,
    )
    mentioned = create_execution(
        owner,
        business_unit=maintenance,
        title="Mentioned out of scope",
        assignees=[
            build_assignee_payload(membership=maintenance_staff, business_unit=maintenance)
        ],
    )
    comment = Comment.objects.create(
        establishment=establishment,
        action_plan_execution=mentioned,
        author_membership=owner,
        body="Mention",
    )
    CommentMention.objects.create(comment=comment, mentioned_membership=manager)

    token = login(api_client, user=user)
    default_feed = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/",
        **auth_headers(token),
    )
    general_feed = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=general",
        **auth_headers(token),
    )
    personal_feed = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=personal",
        **auth_headers(token),
    )
    invalid = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=invalid",
        **auth_headers(token),
    )
    assert default_feed.status_code == 200
    assert general_feed.status_code == 200
    assert personal_feed.status_code == 200
    assert invalid.status_code == 400
    default_ids = {item["action_plan_execution"]["id"] for item in default_feed.json()["items"]}
    general_ids = {item["action_plan_execution"]["id"] for item in general_feed.json()["items"]}
    personal_ids = {item["action_plan_execution"]["id"] for item in personal_feed.json()["items"]}
    assert default_ids == general_ids
    assert str(mentioned.id) not in general_ids
    assert str(mentioned.id) in personal_ids


def test_cross_execution_calendar_unions_and_respects_per_membership_rbac(api_client):
    from datetime import timedelta

    from django.utils import timezone

    user = create_user(username="cross-cal-owner")
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
    bu_a = create_business_unit(establishment=first, key="salle")
    bu_b = create_business_unit(establishment=second, key="salle")
    now = timezone.now()
    start_at = now + timedelta(days=2)
    _, exec_a = create_action_plan_with_execution(
        establishment_id=first.id,
        created_by=membership_a,
        pilot_business_unit_id=bu_a.id,
        title="From A",
        tasks=[build_task_payload(task="a", business_unit=bu_a)],
        assignees=[build_assignee_payload(membership=membership_a, business_unit=bu_a)],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    _, exec_b = create_action_plan_with_execution(
        establishment_id=second.id,
        created_by=membership_b,
        pilot_business_unit_id=bu_b.id,
        title="From B",
        tasks=[build_task_payload(task="b", business_unit=bu_b)],
        assignees=[build_assignee_payload(membership=membership_b, business_unit=bu_b)],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    token = login(api_client, user=user)
    response = api_client.get(
        "/api/v1/cross/action-plan-execution-calendar/"
        + _cross_calendar_query(
            from_date=(now + timedelta(days=1)).date(),
            to_date=(now + timedelta(days=3)).date(),
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    body = response.json()
    ids = {item["action_plan_execution"]["id"] for item in body["items"]}
    assert str(exec_a.id) in ids
    assert str(exec_b.id) in ids
    payload_a = next(
        item["action_plan_execution"]
        for item in body["items"]
        if item["action_plan_execution"]["id"] == str(exec_a.id)
    )
    assert payload_a["status"] == "scheduled"
    assert payload_a["permission_hints"]["can_mark_done"] is False
    assert payload_a["establishment_id"] == str(first.id)

    over = api_client.get(
        "/api/v1/cross/action-plan-execution-calendar/"
        + _cross_calendar_query(
            from_date=now.date(),
            to_date=(now + timedelta(days=46)).date(),
        ),
        **auth_headers(token),
    )
    assert over.status_code == 400


def test_cross_execution_calendar_items_are_sorted_by_start_at_then_id(api_client):
    from datetime import timedelta

    from django.utils import timezone

    user = create_user(username="cross-cal-order")
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
    bu_a = create_business_unit(establishment=first, key="salle")
    bu_b = create_business_unit(establishment=second, key="salle")
    now = timezone.now()
    later_start = now + timedelta(days=2, hours=3)
    earlier_start = now + timedelta(days=2, hours=1)
    _, exec_later = create_action_plan_with_execution(
        establishment_id=first.id,
        created_by=membership_a,
        pilot_business_unit_id=bu_a.id,
        title="Later in first membership",
        tasks=[build_task_payload(task="later", business_unit=bu_a)],
        assignees=[build_assignee_payload(membership=membership_a, business_unit=bu_a)],
        start_at=later_start,
        end_at=later_start + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    _, exec_earlier = create_action_plan_with_execution(
        establishment_id=second.id,
        created_by=membership_b,
        pilot_business_unit_id=bu_b.id,
        title="Earlier in second membership",
        tasks=[build_task_payload(task="earlier", business_unit=bu_b)],
        assignees=[build_assignee_payload(membership=membership_b, business_unit=bu_b)],
        start_at=earlier_start,
        end_at=earlier_start + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    token = login(api_client, user=user)
    response = api_client.get(
        "/api/v1/cross/action-plan-execution-calendar/"
        + _cross_calendar_query(
            from_date=(now + timedelta(days=1)).date(),
            to_date=(now + timedelta(days=3)).date(),
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    ids = [item["action_plan_execution"]["id"] for item in response.json()["items"]]
    assert ids == [str(exec_earlier.id), str(exec_later.id)]


def test_cross_execution_calendar_manager_scope_is_not_widened(api_client):
    from datetime import timedelta

    from django.utils import timezone

    user = create_user(username="cross-cal-manager")
    establishment = create_establishment(name="Scoped cal")
    restaurant = create_business_unit(establishment=establishment, key="salle")
    maintenance = create_business_unit(establishment=establishment, key="maintenance")
    manager = create_membership(
        establishment=establishment,
        user=user,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(membership=manager, business_unit=restaurant)
    owner = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )
    now = timezone.now()
    start_at = now + timedelta(days=2)
    _, in_scope = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=restaurant.id,
        title="In scope",
        tasks=[build_task_payload(task="in", business_unit=restaurant)],
        assignees=[build_assignee_payload(membership=owner, business_unit=restaurant)],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    maintenance_staff = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=maintenance_staff,
        business_unit=maintenance,
    )
    _, out_of_scope = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Out of scope",
        tasks=[build_task_payload(task="out", business_unit=maintenance)],
        assignees=[
            build_assignee_payload(membership=maintenance_staff, business_unit=maintenance)
        ],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    token = login(api_client, user=user)
    response = api_client.get(
        "/api/v1/cross/action-plan-execution-calendar/"
        + _cross_calendar_query(
            from_date=(now + timedelta(days=1)).date(),
            to_date=(now + timedelta(days=3)).date(),
        ),
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    ids = {item["action_plan_execution"]["id"] for item in response.json()["items"]}
    assert str(in_scope.id) in ids
    assert str(out_of_scope.id) not in ids


def test_cross_execution_calendar_staff_forbidden(api_client):
    staff = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    token = login(api_client, user=staff.user)
    from django.utils import timezone

    today = timezone.now().date()
    response = api_client.get(
        "/api/v1/cross/action-plan-execution-calendar/"
        + _cross_calendar_query(from_date=today, to_date=today),
        **auth_headers(token),
    )
    assert response.status_code == 403
