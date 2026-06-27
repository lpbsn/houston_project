from __future__ import annotations

import pytest

from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
    login,
    signal_detail_url,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db


def _create_signal(membership, *, title: str = "Aggregation signal"):
    return create_minimal_v3_signal(membership, title=title)


def _feed_item_for_signal(api_client, membership, signal: Signal):
    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_feed_url(membership.establishment_id) + "?view_mode=general",
        **auth_headers(token),
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        if item["id"] == str(signal.id):
            return item
    pytest.fail("signal not found in feed")


def _detail_payload_for_signal(api_client, membership, signal: Signal):
    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()


def _assert_aggregation_count(api_client, membership, signal: Signal, expected: int):
    feed_item = _feed_item_for_signal(api_client, membership, signal)
    detail_payload = _detail_payload_for_signal(api_client, membership, signal)
    assert feed_item["aggregation_count"] == expected
    assert detail_payload["aggregation_count"] == expected


def test_aggregation_count_zero_without_links(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership)

    _assert_aggregation_count(api_client, membership, signal, 0)


def test_aggregation_count_zero_with_created_from_only(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership)
    observation = create_observation(membership=membership, text="A" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )

    _assert_aggregation_count(api_client, membership, signal, 0)


def test_aggregation_count_one_with_single_aggregated_from(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership)
    observation = create_observation(membership=membership, text="A" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )

    _assert_aggregation_count(api_client, membership, signal, 1)


def test_aggregation_count_ignores_created_from(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership)
    created_obs = create_observation(membership=membership, text="A" * 20)
    aggregated_obs = create_observation(membership=membership, text="B" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=created_obs,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=aggregated_obs,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )

    _assert_aggregation_count(api_client, membership, signal, 1)


def test_aggregation_count_multiple_aggregated_from(api_client):
    membership = build_api_membership()
    signal = _create_signal(membership)
    for marker in ("A", "B", "C"):
        observation = create_observation(membership=membership, text=marker * 20)
        SignalSourceObservation.objects.create(
            signal=signal,
            observation=observation,
            link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
        )

    _assert_aggregation_count(api_client, membership, signal, 3)


def test_aggregation_count_on_canceled_signal_detail(api_client):
    from houston.establishments.models import EstablishmentMembership

    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _create_signal(membership)
    observation = create_observation(membership=membership, text="A" * 20)
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
    )
    signal.status = Signal.Status.CANCELED
    signal.save(update_fields=["status", "updated_at"])

    detail_payload = _detail_payload_for_signal(api_client, membership, signal)
    assert detail_payload["aggregation_count"] == 1
