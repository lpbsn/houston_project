from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from houston.action_plans.services import create_action_plan_with_execution
from houston.action_plans.tests.helpers import build_assignee_payload, build_task_payload
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.services import pin_signal
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_establishment, create_membership, create_user
from houston.testing.pipeline import create_observation
from houston.testing.signal_feed import flatten_signal_feed_items
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
    owner.user.first_name = "Marie"
    owner.user.last_name = "Renaud"
    owner.user.save(update_fields=["first_name", "last_name"])
    signal = create_minimal_v3_signal(owner, title="Cross visible")
    created_from = create_observation(membership=owner)
    aggregated_from = create_observation(membership=owner)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=created_from,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=aggregated_from,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )
    token = login(api_client, user=owner.user)

    response = api_client.get("/api/v1/cross/signal-feed/", **auth_headers(token))
    post = api_client.post("/api/v1/cross/signal-feed/", **auth_headers(token))

    assert response.status_code == 200
    item = flatten_signal_feed_items(response.json())[0]
    assert item["establishment_id"] == str(owner.establishment_id)
    assert item["establishment_name"] == owner.establishment.name
    assert item["aggregation_count"] == 1
    assert item["reporter_display_name"] == "Marie R."
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
    titles = {item["title"] for item in flatten_signal_feed_items(response.json())}
    assert titles == {"From A", "From B"}


def test_cross_signal_list_continuation_preserves_order_and_excludes_pins(api_client):
    user = create_user(username="cross-signal-list-continuation")
    memberships = [
        create_membership(
            establishment=create_establishment(name=establishment_name),
            user=user,
            role=EstablishmentMembership.Role.OWNER,
        )
        for establishment_name in ("Alpha Signal List", "Beta Signal List")
    ]
    signals = [
        create_minimal_v3_signal(
            memberships[index % len(memberships)],
            title=f"Cross list {index}",
        )
        for index in range(5)
    ]
    pinned = signals.pop()
    pin_signal(signal=pinned, membership=memberships[0])
    shared_activity = timezone.now() - timedelta(hours=1)
    Signal.objects.filter(id__in=[signal.id for signal in signals]).update(
        last_activity_at=shared_activity,
        created_at=shared_activity,
    )
    expected_ids = [
        str(signal.id)
        for signal in sorted(signals, key=lambda item: item.id, reverse=True)
    ]
    token = login(api_client, user=user)

    first = api_client.get(
        "/api/v1/cross/signal-feed/?page_size=2",
        **auth_headers(token),
    )

    assert first.status_code == 200, first.content
    first_body = first.json()
    assert [item["id"] for item in first_body["items"]] == expected_ids[:2]
    assert [item["id"] for item in first_body["pins"]] == [str(pinned.id)]
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]
    assert "counts" in first_body

    second = api_client.get(
        f"/api/v1/cross/signal-feed/?page_size=2&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )

    assert second.status_code == 200, second.content
    second_body = second.json()
    assert [item["id"] for item in second_body["items"]] == expected_ids[2:]
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None
    assert "pins" not in second_body
    assert "counts" not in second_body
    seen_ids = [item["id"] for item in first_body["items"] + second_body["items"]]
    assert seen_ids == expected_ids
    assert str(pinned.id) not in seen_ids


def test_cross_hydration_revalidates_list_and_pin_membership():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="Revalidated Cross signal")

    from houston.signals.feed_filters import SignalFeedFilters
    from houston.signals.selectors import (
        cross_signal_feed_queryset,
        hydrate_cross_signal_feed_queryset,
        signal_feed_list_queryset,
        signal_feed_pins_queryset,
    )

    base = cross_signal_feed_queryset(memberships=[owner])
    selected_list = signal_feed_list_queryset(base, filters=None)
    hydrated_list = hydrate_cross_signal_feed_queryset(selected_list, limit=2)
    pin_signal(signal=signal, membership=owner)

    assert list(hydrated_list) == []

    base = cross_signal_feed_queryset(memberships=[owner])
    selected_pins = signal_feed_pins_queryset(base, filters=None)
    hydrated_pins = hydrate_cross_signal_feed_queryset(selected_pins, limit=2)
    Signal.objects.filter(pk=signal.pk).update(
        is_pinned=False,
        pinned_at=None,
        pinned_by_membership=None,
    )

    assert list(hydrated_pins) == []

    base = cross_signal_feed_queryset(memberships=[owner])
    selected_list = signal_feed_list_queryset(base, filters=None)
    hydrated_list = hydrate_cross_signal_feed_queryset(selected_list, limit=2)
    Signal.objects.filter(pk=signal.pk).update(status=Signal.Status.RESOLVED)

    assert list(hydrated_list) == []

    deleted = create_minimal_v3_signal(owner, title="Deleted before Cross hydration")
    base = cross_signal_feed_queryset(memberships=[owner])
    selected_list = signal_feed_list_queryset(base, filters=None).filter(pk=deleted.pk)
    hydrated_list = hydrate_cross_signal_feed_queryset(selected_list, limit=2)
    deleted.delete()

    assert list(hydrated_list) == []

    filtered = create_minimal_v3_signal(owner, title="Filtered before Cross hydration")
    original_unit = filtered.affected_business_unit
    assert original_unit is not None
    filters = SignalFeedFilters(business_unit_ids=(original_unit.id,))
    base = cross_signal_feed_queryset(memberships=[owner], filters=filters)
    selected_list = signal_feed_list_queryset(base, filters=filters)
    hydrated_list = hydrate_cross_signal_feed_queryset(selected_list, limit=2)
    other_unit = create_business_unit(
        establishment=owner.establishment,
        key="cross-revalidation-other",
    )
    Signal.objects.filter(pk=filtered.pk).update(
        affected_business_unit=other_unit,
        responsible_business_unit=other_unit,
    )

    assert list(hydrated_list) == []


def test_cross_signal_feed_query_count_stays_flat_as_cards_grow(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=owner.user)
    url = "/api/v1/cross/signal-feed/"

    from houston.testing.query_baseline import capture_queries

    create_minimal_v3_signal(owner, title="Cross query count 1")
    with capture_queries() as one_item_context:
        one_item_response = api_client.get(url, **auth_headers(token))

    create_minimal_v3_signal(owner, title="Cross query count 2")
    create_minimal_v3_signal(owner, title="Cross query count 3")
    with capture_queries() as three_item_context:
        three_item_response = api_client.get(url, **auth_headers(token))

    assert one_item_response.status_code == 200
    assert three_item_response.status_code == 200
    assert len(one_item_response.json()["items"]) == 1
    assert len(three_item_response.json()["items"]) == 3
    assert len(three_item_context.captured_queries) == len(one_item_context.captured_queries)


def test_cross_signal_pins_paginate_and_reject_changed_filter_context(api_client):
    user = create_user(username="cross-signal-pin-continuation")
    memberships = [
        create_membership(
            establishment=create_establishment(name=establishment_name),
            user=user,
            role=EstablishmentMembership.Role.OWNER,
        )
        for establishment_name in ("Alpha Signal Pins", "Beta Signal Pins")
    ]
    pinned = []
    for membership in memberships:
        for index in range(2):
            signal = create_minimal_v3_signal(
                membership,
                title=f"{membership.establishment.name} {index}",
            )
            pin_signal(signal=signal, membership=membership)
            pinned.append(signal)

    token = login(api_client, user=user)
    first = api_client.get(
        "/api/v1/cross/signal-feed-pins/?page_size=2",
        **auth_headers(token),
    )

    assert first.status_code == 200, first.content
    first_body = first.json()
    assert len(first_body["items"]) == 2
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]
    assert all(item["establishment_id"] for item in first_body["items"])
    assert all(item["permission_hints"]["can_pin"] is False for item in first_body["items"])

    mismatched = api_client.get(
        "/api/v1/cross/signal-feed-pins/"
        f"?statuses=interesting&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert mismatched.status_code == 400
    assert mismatched.json()["code"] == "cursor_context_mismatch"

    second = api_client.get(
        "/api/v1/cross/signal-feed-pins/"
        f"?page_size=2&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert second.status_code == 200, second.content
    second_body = second.json()
    assert len(second_body["items"]) == 2
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None

    seen_ids = [item["id"] for item in first_body["items"] + second_body["items"]]
    assert len(seen_ids) == len(set(seen_ids)) == 4
    assert set(seen_ids) == {str(signal.id) for signal in pinned}


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
    titles = {item["title"] for item in flatten_signal_feed_items(response.json())}
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


def test_establishment_execution_cursor_is_rejected_by_cross_feed(api_client):
    from houston.action_plans.tests.helpers import create_execution

    user = create_user(username="cross-cursor-surface")
    establishment = create_establishment(name="Cursor Surface")
    membership = create_membership(
        establishment=establishment,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    business_unit = create_business_unit(establishment=establishment, key="salle")
    create_execution(membership, business_unit=business_unit, title="First")
    create_execution(membership, business_unit=business_unit, title="Second")
    token = login(api_client, user=user)

    establishment_page = api_client.get(
        f"/api/v1/establishments/{establishment.id}/action-plan-execution-feed/"
        "?view_mode=general&page_size=1",
        **auth_headers(token),
    )
    assert establishment_page.status_code == 200, establishment_page.content
    cursor = establishment_page.json()["next_cursor"]
    assert cursor

    cross_page = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/"
        f"?view_mode=general&page_size=1&cursor={cursor}",
        **auth_headers(token),
    )
    assert cross_page.status_code == 400
    assert cross_page.json()["code"] == "cursor_context_mismatch"


def test_cross_execution_feed_pins_use_per_establishment_membership_and_paginate(
    api_client,
    monkeypatch,
):
    from houston.action_plans.feed_pin_services import pin_action_plan_execution_for_membership
    from houston.action_plans.tests.helpers import create_execution

    user = create_user(username="cross-pin-paginate")
    # Names ensure management-scope order: Alpha (A) before Beta (B).
    first = create_establishment(name="Alpha Cross Pin")
    second = create_establishment(name="Beta Cross Pin")
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

    exec_a1 = create_execution(membership_a, business_unit=bu_a, title="A1")
    exec_a2 = create_execution(membership_a, business_unit=bu_a, title="A2")
    exec_b_pinned = create_execution(membership_b, business_unit=bu_b, title="B pinned")
    exec_b2 = create_execution(membership_b, business_unit=bu_b, title="B2")
    expected_list_ids = {
        str(exec_a1.id),
        str(exec_a2.id),
        str(exec_b2.id),
    }

    pin_action_plan_execution_for_membership(
        membership=membership_b,
        execution_id=exec_b_pinned.id,
    )

    token = login(api_client, user=user)
    page1 = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=general&page_size=2",
        **auth_headers(token),
    )
    assert page1.status_code == 200, page1.content
    body1 = page1.json()
    assert body1["has_more"] is True
    assert body1["next_cursor"]
    assert body1["section_counts"]["pinned"] == 1
    assert body1["section_counts"]["in_progress"] == 4
    assert "pins" not in body1

    items1 = [row["action_plan_execution"] for row in body1["items"]]
    assert len(items1) == 2
    assert all(item["is_pinned"] is False for item in items1)
    assert all(item["permission_hints"]["can_pin"] is False for item in items1)

    def fail_scheduled_metadata(*args, **kwargs):
        raise AssertionError("L continuation must not recalculate scheduled metadata")

    monkeypatch.setattr(
        "houston.action_plans.execution_feed.scheduled_executions_upcoming_queryset",
        fail_scheduled_metadata,
    )
    monkeypatch.setattr(
        "houston.action_plans.execution_feed.scheduled_executions_next_queryset",
        fail_scheduled_metadata,
    )
    monkeypatch.setattr(
        "houston.action_plans.execution_feed.scheduled_executions_cross_summary",
        fail_scheduled_metadata,
    )

    page2 = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/"
        f"?view_mode=general&page_size=2&cursor={body1['next_cursor']}",
        **auth_headers(token),
    )
    assert page2.status_code == 200, page2.content
    body2 = page2.json()
    assert "section_counts" not in body2
    assert "scheduled" not in body2
    assert "pins" not in body2
    items2 = [row["action_plan_execution"] for row in body2["items"]]
    assert all(item["is_pinned"] is False for item in items2)
    assert all(item["permission_hints"]["can_pin"] is False for item in items2)

    seen_ids = [item["id"] for item in items1] + [item["id"] for item in items2]
    assert len(seen_ids) == len(set(seen_ids))
    assert set(seen_ids) == expected_list_ids

    pins = api_client.get(
        "/api/v1/cross/action-plan-execution-feed-pins/?view_mode=general",
        **auth_headers(token),
    )
    assert pins.status_code == 200, pins.content
    pins_body = pins.json()
    assert pins_body["has_more"] is False
    assert pins_body["next_cursor"] is None
    assert [item["action_plan_execution"]["id"] for item in pins_body["items"]] == [
        str(exec_b_pinned.id),
    ]


def test_cross_execution_pins_preview_and_bounded_continuation(api_client):
    from houston.action_plans.feed_pin_services import pin_action_plan_execution_for_membership
    from houston.action_plans.tests.helpers import create_execution

    user = create_user(username="cross-pin-continuation")
    memberships = []
    executions = []
    for establishment_name in ("Alpha Pins", "Beta Pins"):
        establishment = create_establishment(name=establishment_name)
        membership = create_membership(
            establishment=establishment,
            user=user,
            role=EstablishmentMembership.Role.OWNER,
        )
        memberships.append(membership)
        business_unit = create_business_unit(establishment=establishment, key="salle")
        for index in range(3):
            execution = create_execution(
                membership,
                business_unit=business_unit,
                title=f"{establishment_name} {index}",
            )
            pin_action_plan_execution_for_membership(
                membership=membership,
                execution_id=execution.id,
            )
            executions.append(execution)

    token = login(api_client, user=user)
    feed = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=general",
        **auth_headers(token),
    )
    assert feed.status_code == 200, feed.content
    assert feed.json()["items"] == []
    assert feed.json()["section_counts"]["pinned"] == 6
    assert feed.json()["section_counts"]["in_progress"] == 6

    first = api_client.get(
        "/api/v1/cross/action-plan-execution-feed-pins/?view_mode=general",
        **auth_headers(token),
    )
    assert first.status_code == 200, first.content
    first_body = first.json()
    assert len(first_body["items"]) == 3
    assert first_body["has_more"] is True
    assert first_body["next_cursor"]

    wrong_category = api_client.get(
        "/api/v1/cross/action-plan-execution-feed-pins/"
        f"?view_mode=general&category=overdue&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert wrong_category.status_code == 400
    assert wrong_category.json()["code"] == "cursor_context_mismatch"

    second = api_client.get(
        "/api/v1/cross/action-plan-execution-feed-pins/"
        f"?view_mode=general&page_size=10&cursor={first_body['next_cursor']}",
        **auth_headers(token),
    )
    assert second.status_code == 200, second.content
    second_body = second.json()
    assert len(second_body["items"]) == 3
    assert second_body["has_more"] is False
    assert second_body["next_cursor"] is None

    seen_ids = [
        item["action_plan_execution"]["id"]
        for item in first_body["items"] + second_body["items"]
    ]
    assert len(seen_ids) == len(set(seen_ids)) == 6
    assert set(seen_ids) == {str(execution.id) for execution in executions}


def test_cross_execution_upcoming_unions_and_matches_feed_scheduled_meta(api_client):
    from datetime import timedelta

    from django.utils import timezone

    from houston.action_plans.services import create_action_plan_with_execution

    user = create_user(username="cross-upcoming-owner")
    first = create_establishment(name="Alpha Upcoming")
    second = create_establishment(name="Beta Upcoming")
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
    start_a = now + timedelta(hours=3)
    start_b = now + timedelta(days=1)
    _, exec_a = create_action_plan_with_execution(
        establishment_id=first.id,
        created_by=membership_a,
        pilot_business_unit_id=bu_a.id,
        title="Upcoming A",
        tasks=[build_task_payload(task="a", business_unit=bu_a)],
        assignees=[build_assignee_payload(membership=membership_a, business_unit=bu_a)],
        start_at=start_a,
        end_at=start_a + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    _, exec_b = create_action_plan_with_execution(
        establishment_id=second.id,
        created_by=membership_b,
        pilot_business_unit_id=bu_b.id,
        title="Upcoming B",
        tasks=[build_task_payload(task="b", business_unit=bu_b)],
        assignees=[build_assignee_payload(membership=membership_b, business_unit=bu_b)],
        start_at=start_b,
        end_at=start_b + timedelta(hours=1),
        visible_from=start_b - timedelta(hours=1),
    )

    token = login(api_client, user=user)
    feed = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=general",
        **auth_headers(token),
    )
    upcoming = api_client.get(
        "/api/v1/cross/action-plan-execution-upcoming/?view_mode=general",
        **auth_headers(token),
    )
    assert feed.status_code == 200, feed.content
    assert upcoming.status_code == 200, upcoming.content
    feed_body = feed.json()
    upcoming_ids = [item["action_plan_execution"]["id"] for item in upcoming.json()["items"]]
    assert feed_body["scheduled"]["count"] == 2
    preview_ids = [feed_body["scheduled"]["next"]["id"]]
    assert upcoming_ids == [str(exec_a.id), str(exec_b.id)]
    assert preview_ids == upcoming_ids[:1]
    assert (
        upcoming.json()["items"][0]["action_plan_execution"]["permission_hints"]["can_pin"]
        is False
    )


def test_cross_feed_scheduled_summary_uses_global_next(api_client):
    """Slim scheduled metadata keeps the full count and globally earliest occurrence."""
    from datetime import timedelta

    from django.utils import timezone

    from houston.action_plans.services import create_action_plan_with_execution

    user = create_user(username="cross-preview-cap")
    first = create_establishment(name="Alpha Preview Cap")
    second = create_establishment(name="Beta Preview Cap")
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

    starts = [
        (membership_a, bu_a, first.id, now + timedelta(hours=4), "A late"),
        (membership_a, bu_a, first.id, now + timedelta(hours=1), "A soon"),
        (membership_b, bu_b, second.id, now + timedelta(hours=2), "B mid"),
        (membership_b, bu_b, second.id, now + timedelta(hours=3), "B later"),
    ]
    created = []
    for membership, bu, establishment_id, start_at, title in starts:
        _, execution = create_action_plan_with_execution(
            establishment_id=establishment_id,
            created_by=membership,
            pilot_business_unit_id=bu.id,
            title=title,
            tasks=[build_task_payload(task=title, business_unit=bu)],
            assignees=[build_assignee_payload(membership=membership, business_unit=bu)],
            start_at=start_at,
            end_at=start_at + timedelta(hours=1),
            visible_from=now - timedelta(minutes=1),
        )
        created.append(execution)

    by_title = {execution.title: execution for execution in created}
    expected_first = by_title["A soon"]

    token = login(api_client, user=user)
    feed = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=general",
        **auth_headers(token),
    )
    assert feed.status_code == 200, feed.content
    body = feed.json()

    assert body["scheduled"]["count"] == 4
    assert body["scheduled"]["next"]["id"] == str(expected_first.id)


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


def test_cross_execution_calendar_matches_establishment_on_same_civil_window(api_client):
    from datetime import timedelta

    from django.utils import timezone

    from houston.action_plans.tests.helpers import action_plan_execution_calendar_url

    user = create_user(username="cross-cal-parity")
    first = create_establishment(name="Paris Alpha", timezone="Europe/Paris")
    second = create_establishment(name="Paris Beta", timezone="Europe/Paris")
    membership_a = create_membership(
        establishment=first,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    create_membership(
        establishment=second,
        user=user,
        role=EstablishmentMembership.Role.OWNER,
    )
    bu_a = create_business_unit(establishment=first, key="salle")
    now = timezone.now()
    start_at = now + timedelta(days=2)
    _, execution = create_action_plan_with_execution(
        establishment_id=first.id,
        created_by=membership_a,
        pilot_business_unit_id=bu_a.id,
        title="Shared civil window",
        tasks=[build_task_payload(task="a", business_unit=bu_a)],
        assignees=[build_assignee_payload(membership=membership_a, business_unit=bu_a)],
        start_at=start_at,
        end_at=start_at + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    window_from = (now + timedelta(days=1)).date()
    window_to = (now + timedelta(days=3)).date()
    token = login(api_client, user=user)
    establishment_response = api_client.get(
        action_plan_execution_calendar_url(first.id)
        + f"?view_mode=general&from={window_from.isoformat()}&to={window_to.isoformat()}",
        **auth_headers(token),
    )
    cross_response = api_client.get(
        "/api/v1/cross/action-plan-execution-calendar/"
        + _cross_calendar_query(from_date=window_from, to_date=window_to),
        **auth_headers(token),
    )
    assert establishment_response.status_code == 200, establishment_response.content
    assert cross_response.status_code == 200, cross_response.content
    establishment_ids = {
        item["action_plan_execution"]["id"] for item in establishment_response.json()["items"]
    }
    cross_ids = {item["action_plan_execution"]["id"] for item in cross_response.json()["items"]}
    assert str(execution.id) in establishment_ids
    assert str(execution.id) in cross_ids
    assert establishment_response.json()["timezone"] == "Europe/Paris"
    assert cross_response.json()["timezone"] == "Europe/Paris"


def _scheduled_summary_statement_counts(sqls: list[str]) -> tuple[int, int]:
    next_rows = [
        sql
        for sql in sqls
        if "LIMIT 1" in sql
        and '"action_plans_actionplanexecution"."title"' in sql
        and '"action_plans_actionplanexecution"."start_at"' in sql
        and "is_feed_pinned" not in sql
    ]
    counts = [
        sql
        for sql in sqls
        if "COUNT" in sql.upper()
        and '"action_plans_actionplanexecution"."start_at" IS NOT NULL' in sql
        and "deadline_bucket" not in sql
    ]
    return len(next_rows), len(counts)


def test_cross_feed_scheduled_summary_tie_breaks_on_id(api_client):
    from datetime import timedelta

    from django.utils import timezone

    user = create_user(username="cross-scheduled-tie")
    first = create_establishment(name="Tie Alpha")
    second = create_establishment(name="Tie Beta")
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
    start_at = now + timedelta(hours=5)
    created = []
    for membership, business_unit, establishment_id, title in (
        (membership_a, bu_a, first.id, "Tie A"),
        (membership_b, bu_b, second.id, "Tie B"),
    ):
        _, execution = create_action_plan_with_execution(
            establishment_id=establishment_id,
            created_by=membership,
            pilot_business_unit_id=business_unit.id,
            title=title,
            tasks=[build_task_payload(task=title, business_unit=business_unit)],
            assignees=[
                build_assignee_payload(membership=membership, business_unit=business_unit)
            ],
            start_at=start_at,
            end_at=start_at + timedelta(hours=1),
            visible_from=now - timedelta(minutes=1),
        )
        created.append(execution)
    expected = min(created, key=lambda execution: execution.id)

    token = login(api_client, user=user)
    response = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=general",
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    scheduled = response.json()["scheduled"]
    assert scheduled["count"] == 2
    assert scheduled["next"]["id"] == str(expected.id)
    assert scheduled["next"]["title"] == expected.title


def test_cross_feed_scheduled_summary_respects_manager_scope(api_client):
    from datetime import timedelta

    from django.utils import timezone

    from houston.action_plans.models import ActionPlanExecutionTeam

    user = create_user(username="cross-scheduled-manager")
    establishment = create_establishment(name="Scoped scheduled")
    restaurant = create_business_unit(establishment=establishment, key="salle")
    bar = create_business_unit(establishment=establishment, key="bar")
    maintenance = create_business_unit(establishment=establishment, key="maintenance")
    manager = create_membership(
        establishment=establishment,
        user=user,
        role=EstablishmentMembership.Role.MANAGER,
    )
    create_membership_with_business_unit_scope(membership=manager, business_unit=restaurant)
    create_membership_with_business_unit_scope(membership=manager, business_unit=bar)
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
    now = timezone.now()
    earlier = now + timedelta(hours=1)
    later = now + timedelta(hours=4)
    _, in_scope = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=restaurant.id,
        title="In scope later",
        tasks=[build_task_payload(task="in", business_unit=restaurant)],
        assignees=[build_assignee_payload(membership=owner, business_unit=restaurant)],
        start_at=later,
        end_at=later + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )
    ActionPlanExecutionTeam.objects.create(
        action_plan_execution=in_scope,
        business_unit=bar,
        is_pilot=False,
    )
    _, out_of_scope = create_action_plan_with_execution(
        establishment_id=establishment.id,
        created_by=owner,
        pilot_business_unit_id=maintenance.id,
        title="Out of scope earlier",
        tasks=[build_task_payload(task="out", business_unit=maintenance)],
        assignees=[
            build_assignee_payload(membership=maintenance_staff, business_unit=maintenance)
        ],
        start_at=earlier,
        end_at=earlier + timedelta(hours=1),
        visible_from=now - timedelta(minutes=1),
    )

    token = login(api_client, user=user)
    response = api_client.get(
        "/api/v1/cross/action-plan-execution-feed/?view_mode=general",
        **auth_headers(token),
    )
    assert response.status_code == 200, response.content
    scheduled = response.json()["scheduled"]
    assert scheduled["count"] == 1
    assert scheduled["next"]["id"] == str(in_scope.id)
    assert str(out_of_scope.id) != scheduled["next"]["id"]


def test_cross_execution_feed_scheduled_summary_query_slope_is_preparation_only():
    from datetime import timedelta

    from django.utils import timezone

    from houston.action_plans.execution_feed import build_cross_action_plan_execution_feed_page
    from houston.establishments.membership_scope import membership_business_unit_scope_ids
    from houston.testing.query_baseline import capture_queries

    def select_sql(captured) -> list[str]:
        return [
            query["sql"]
            for query in captured.captured_queries
            if query["sql"].lstrip().upper().startswith(("SELECT", "WITH"))
        ]

    def measure(establishment_count: int) -> list[str]:
        user = create_user(username=f"cross-scheduled-slope-{establishment_count}")
        now = timezone.now()
        start_at = now + timedelta(days=2)
        memberships = []
        for index in range(establishment_count):
            establishment = create_establishment(name=f"Slope {establishment_count}-{index}")
            membership = create_membership(
                establishment=establishment,
                user=user,
                role=EstablishmentMembership.Role.OWNER,
            )
            business_unit = create_business_unit(establishment=establishment, key="salle")
            create_action_plan_with_execution(
                establishment_id=establishment.id,
                created_by=membership,
                pilot_business_unit_id=business_unit.id,
                title=f"Scheduled {index}",
                tasks=[build_task_payload(task="task", business_unit=business_unit)],
                assignees=[
                    build_assignee_payload(membership=membership, business_unit=business_unit)
                ],
                start_at=start_at + timedelta(hours=index),
                end_at=start_at + timedelta(hours=index + 1),
                visible_from=start_at + timedelta(hours=index) - timedelta(hours=1),
            )
            membership.establishment
            membership_business_unit_scope_ids(membership)
            memberships.append(membership)

        with capture_queries() as captured:
            page = build_cross_action_plan_execution_feed_page(
                memberships=memberships,
                view_mode="general",
                category="all",
                page_size=25,
            )
        assert page.scheduled_count == establishment_count
        assert page.scheduled_next is not None
        assert page.scheduled_next.title == "Scheduled 0"
        return select_sql(captured)

    two = measure(2)
    five = measure(5)
    assert len(five) - len(two) == 9
    assert _scheduled_summary_statement_counts(two) == (1, 1)
    assert _scheduled_summary_statement_counts(five) == (1, 1)
