from __future__ import annotations

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership, MembershipScope
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    RESTAURANT_BAR_STOCK_SUBJECT_KEY,
    RESTAURANT_MODULE_KEY,
    RESTAURANT_SALLE_DOMAIN_KEY,
    RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY,
    auth_headers,
    build_api_membership,
    create_restaurant_lighting_bar_stock_taxonomy,
    create_taxonomy,
    login,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db


def _create_signal(
    membership,
    *,
    title: str,
    status: str = Signal.Status.OPEN,
    taxonomy: tuple | None = None,
):
    if taxonomy is None:
        taxonomy = create_taxonomy(membership.establishment)
    module, domain, subject = taxonomy
    now = timezone.now()
    return Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title=title,
        structured_summary="Structured summary safe.",
        status=status,
        last_activity_at=now,
    )


def _feed_get(api_client, membership, query: str):
    token = login(api_client, user=membership.user)
    return api_client.get(
        signal_feed_url(membership.establishment_id) + query,
        **auth_headers(token),
    )


def test_feed_without_filters_unchanged(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership, title="Baseline")

    response = _feed_get(api_client, membership, "?view_mode=general")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(signal.id)
    assert body["applied_filters"]["view_mode"] == "general"
    assert body["applied_filters"]["statuses"] == []
    assert body["applied_filters"]["module_keys"] == []


def test_feed_filters_by_single_status(api_client):
    membership = build_api_membership()
    _create_signal(membership, title="Open", status=Signal.Status.OPEN)
    resolved = _create_signal(membership, title="Resolved", status=Signal.Status.RESOLVED)

    response = _feed_get(api_client, membership, "?view_mode=general&statuses=resolved")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(resolved.id)
    assert body["applied_filters"]["statuses"] == ["resolved"]


def test_feed_filters_by_multiple_statuses(api_client):
    membership = build_api_membership()
    open_signal = _create_signal(membership, title="Open", status=Signal.Status.OPEN)
    _create_signal(membership, title="Resolved", status=Signal.Status.RESOLVED)

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general&statuses=open,in_progress",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(open_signal.id)
    assert body["applied_filters"]["statuses"] == ["in_progress", "open"]


def test_feed_rejects_canceled_and_archived_status_filters(api_client):
    membership = build_api_membership()
    _create_signal(membership, title="Open")

    for status_value in ("canceled", "archived"):
        response = _feed_get(
            api_client,
            membership,
            f"?view_mode=general&statuses={status_value}",
        )
        assert response.status_code == 400
        assert response.json()["code"] == "validation_error"


def test_feed_deduplicates_statuses_in_applied_filters(api_client):
    membership = build_api_membership()
    _create_signal(membership, title="Open", status=Signal.Status.OPEN)

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general&statuses=open,open",
    )

    assert response.status_code == 200
    assert response.json()["applied_filters"]["statuses"] == ["open"]


def test_feed_filters_by_module_key(api_client):
    membership = build_api_membership()
    restaurant = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    hotel = create_taxonomy(membership.establishment)
    restaurant_signal = _create_signal(
        membership,
        title="Restaurant signal",
        taxonomy=(
            restaurant.module,
            restaurant.salle_domain,
            restaurant.salle_maintenance_subject,
        ),
    )
    _create_signal(membership, title="Hotel signal", taxonomy=hotel)

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=general&module_keys={RESTAURANT_MODULE_KEY}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(restaurant_signal.id)
    assert body["applied_filters"]["module_keys"] == [RESTAURANT_MODULE_KEY]


def test_feed_filters_by_domain_key(api_client):
    membership = build_api_membership()
    restaurant = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    signal = _create_signal(
        membership,
        title="Salle",
        taxonomy=(
            restaurant.module,
            restaurant.salle_domain,
            restaurant.salle_maintenance_subject,
        ),
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=general&domain_keys={RESTAURANT_SALLE_DOMAIN_KEY}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(signal.id)


def test_feed_filters_by_subject_key(api_client):
    membership = build_api_membership()
    restaurant = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    signal = _create_signal(
        membership,
        title="Bar stock",
        taxonomy=(
            restaurant.module,
            restaurant.bar_domain,
            restaurant.bar_stock_subject,
        ),
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=general&subject_keys={RESTAURANT_BAR_STOCK_SUBJECT_KEY}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(signal.id)


def test_feed_category_filter_or_across_module_and_subject(api_client):
    membership = build_api_membership()
    restaurant = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    hotel = create_taxonomy(membership.establishment)
    restaurant_signal = _create_signal(
        membership,
        title="Restaurant",
        taxonomy=(
            restaurant.module,
            restaurant.salle_domain,
            restaurant.salle_maintenance_subject,
        ),
    )
    hotel_signal = _create_signal(membership, title="Hotel", taxonomy=hotel)

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general"
        f"&module_keys={RESTAURANT_MODULE_KEY}"
        f"&subject_keys={hotel[2].key}",
    )

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert ids == {str(restaurant_signal.id), str(hotel_signal.id)}


def test_feed_combines_status_and_category_with_and(api_client):
    membership = build_api_membership()
    restaurant = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    hotel = create_taxonomy(membership.establishment)
    match = _create_signal(
        membership,
        title="Match",
        status=Signal.Status.RESOLVED,
        taxonomy=(
            restaurant.module,
            restaurant.salle_domain,
            restaurant.salle_maintenance_subject,
        ),
    )
    _create_signal(
        membership,
        title="Wrong status",
        status=Signal.Status.OPEN,
        taxonomy=(
            restaurant.module,
            restaurant.salle_domain,
            restaurant.salle_maintenance_subject,
        ),
    )
    _create_signal(
        membership,
        title="Wrong module",
        status=Signal.Status.RESOLVED,
        taxonomy=hotel,
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=general&statuses=resolved&module_keys={RESTAURANT_MODULE_KEY}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(match.id)


def test_feed_rejects_unknown_module_key(api_client):
    membership = build_api_membership()
    _create_signal(membership, title="Open")

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general&module_keys=nonexistent_module",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_feed_rejects_too_many_module_keys(api_client):
    membership = build_api_membership()
    keys = ",".join(f"mod_{index}" for index in range(21))

    response = _feed_get(api_client, membership, f"?view_mode=general&module_keys={keys}")

    assert response.status_code == 400


def test_feed_rejects_too_many_domain_keys(api_client):
    membership = build_api_membership()
    keys = ",".join(f"dom_{index}" for index in range(51))

    response = _feed_get(api_client, membership, f"?view_mode=general&domain_keys={keys}")

    assert response.status_code == 400


def test_feed_rejects_too_many_subject_keys(api_client):
    membership = build_api_membership()
    keys = ",".join(f"sub_{index}" for index in range(101))

    response = _feed_get(api_client, membership, f"?view_mode=general&subject_keys={keys}")

    assert response.status_code == 400


def test_personal_feed_scope_intersects_with_filters(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    restaurant = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    hotel = create_taxonomy(membership.establishment)
    _create_signal(
        membership,
        title="In scope",
        taxonomy=(
            restaurant.module,
            restaurant.salle_domain,
            restaurant.salle_maintenance_subject,
        ),
    )
    _create_signal(membership, title="Out of scope", taxonomy=hotel)

    MembershipScope.objects.create(
        membership=membership,
        operational_subject=restaurant.salle_maintenance_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=personal&module_keys={hotel[0].key}",
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_personal_feed_filter_within_scope_returns_signal(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    restaurant = create_restaurant_lighting_bar_stock_taxonomy(membership.establishment)
    visible = _create_signal(
        membership,
        title="In scope",
        taxonomy=(
            restaurant.module,
            restaurant.salle_domain,
            restaurant.salle_maintenance_subject,
        ),
    )

    MembershipScope.objects.create(
        membership=membership,
        operational_subject=restaurant.salle_maintenance_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=personal&subject_keys={RESTAURANT_SALLE_MAINTENANCE_SUBJECT_KEY}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(visible.id)
