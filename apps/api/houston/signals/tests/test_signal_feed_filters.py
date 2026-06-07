from __future__ import annotations

import pytest

from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    EstablishmentMembership,
)
from houston.establishments.tests.taxonomy_helpers import create_membership_with_business_unit_scope
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    RESTAURANT_MODULE_KEY,
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_restaurant_v3_taxonomy,
    create_v3_signal,
    login,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db


def _create_signal(
    membership,
    *,
    title: str,
    status: str = Signal.Status.OPEN,
):
    return create_minimal_v3_signal(membership, title=title, status=status)


def _feed_get(api_client, membership, query: str):
    token = login(api_client, user=membership.user)
    return api_client.get(
        signal_feed_url(membership.establishment_id) + query,
        **auth_headers(token),
    )


def _create_v3_signal(
    membership,
    *,
    title: str,
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject: ActivitySubject,
    status: str = Signal.Status.OPEN,
) -> Signal:
    return create_v3_signal(
        membership.establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        title=title,
        status=status,
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
    assert body["applied_filters"]["business_unit_keys"] == []


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


def test_feed_filters_v3_by_responsible_business_unit(api_client):
    membership = build_api_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    signal = _create_v3_signal(
        membership,
        title="Lighting",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
    )
    _create_v3_signal(
        membership,
        title="Bar stock",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
        activity_subject=taxonomy.stock_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general&business_unit_keys=maintenance",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(signal.id)
    assert body["applied_filters"]["business_unit_keys"] == ["maintenance"]


def test_feed_filters_v3_by_affected_business_unit(api_client):
    membership = build_api_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    signal = _create_v3_signal(
        membership,
        title="Lighting",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
    )
    _create_v3_signal(
        membership,
        title="Bar stock",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
        activity_subject=taxonomy.stock_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=general&business_unit_keys={RESTAURANT_MODULE_KEY}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(signal.id)


def test_feed_filters_v3_by_activity_subject_id(api_client):
    membership = build_api_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None
    lighting = _create_v3_signal(
        membership,
        title="Lighting",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
    )
    _create_v3_signal(
        membership,
        title="Bar stock",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
        activity_subject=taxonomy.stock_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=general&activity_subject_ids={taxonomy.lighting_subject.id}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(lighting.id)
    assert body["applied_filters"]["activity_subject_ids"] == [str(taxonomy.lighting_subject.id)]


def test_feed_combines_bu_and_activity_subject(api_client):
    membership = build_api_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None
    match = _create_v3_signal(
        membership,
        title="Lighting",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
    )
    _create_v3_signal(
        membership,
        title="Bar stock",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
        activity_subject=taxonomy.stock_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general"
        f"&business_unit_keys={RESTAURANT_MODULE_KEY}"
        f"&activity_subject_ids={taxonomy.lighting_subject.id}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(match.id)


def test_personal_feed_bu_filter_within_scope(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=taxonomy.restaurant,
    )
    _create_v3_signal(
        membership,
        title="In scope",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
    )
    _create_v3_signal(
        membership,
        title="Out of scope",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
        activity_subject=taxonomy.stock_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=personal&business_unit_keys={taxonomy.bar.key}",
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_owner_sees_filtered_v3_signals(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None
    lighting = _create_v3_signal(
        membership,
        title="Lighting",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
        activity_subject=taxonomy.lighting_subject,
    )
    _create_v3_signal(
        membership,
        title="Bar stock",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
        activity_subject=taxonomy.stock_subject,
    )

    response = _feed_get(
        api_client,
        membership,
        f"?view_mode=personal&business_unit_keys={taxonomy.maintenance.key}",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(lighting.id)


def test_applied_filters_echoes_bu_as(api_client):
    membership = build_api_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.lighting_subject is not None

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general"
        f"&business_unit_keys=bar,{RESTAURANT_MODULE_KEY}"
        f"&activity_subject_ids={taxonomy.lighting_subject.id}",
    )

    assert response.status_code == 200
    applied = response.json()["applied_filters"]
    assert applied["business_unit_keys"] == ["bar", RESTAURANT_MODULE_KEY]
    assert applied["activity_subject_ids"] == [str(taxonomy.lighting_subject.id)]


def test_pagination_unchanged_with_bu_filter(api_client):
    membership = build_api_membership()
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    for index in range(3):
        _create_v3_signal(
            membership,
            title=f"Lighting {index}",
            affected_business_unit=taxonomy.restaurant,
            responsible_business_unit=taxonomy.maintenance,
            activity_subject=taxonomy.lighting_subject,
        )

    response = _feed_get(
        api_client,
        membership,
        "?view_mode=general&business_unit_keys=maintenance&page_size=2",
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["has_more"] is True
    assert body["next_cursor"] is None
