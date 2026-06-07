from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import create_membership_with_business_unit_scope
from houston.signals.models import SignalSourceObservation
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
    signal_feed_url,
)

pytestmark = pytest.mark.django_db

_LEAK_MARKER = "LEAK_RAW_OBSERVATION_TEXT_DO_NOT_EXPOSE"


def _signal_with_linked_observation(membership, *, raw_text: str = _LEAK_MARKER):
    observation = create_observation(membership=membership, text=raw_text)
    signal = create_minimal_v3_signal(membership, title="Linked signal")
    SignalSourceObservation.objects.create(
        signal=signal,
        observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    return signal


def test_signal_feed_never_exposes_observation_raw_text(api_client):
    membership = build_api_membership()
    _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)

    for view_mode in ("general", "personal"):
        response = api_client.get(
            signal_feed_url(membership.establishment_id) + f"?view_mode={view_mode}",
            **auth_headers(token),
        )
        assert response.status_code == 200
        body = response.content.decode()
        assert "raw_text" not in body
        assert _LEAK_MARKER not in body


def test_signal_detail_never_exposes_observation_raw_text(api_client):
    membership = build_api_membership()
    signal = _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.content.decode()
    assert "raw_text" not in body
    assert _LEAK_MARKER not in body
    assert response.json()["source_context"]["reporter_display_name"]


@pytest.mark.parametrize(
    ("method", "path_suffix", "data"),
    [
        ("post", "signals/", None),
        ("patch", "signals/{signal_id}/", {"title": "manual edit"}),
        ("delete", "signals/{signal_id}/", None),
    ],
)
def test_no_manual_signal_crud_routes(api_client, method, path_suffix, data):
    membership = build_api_membership()
    signal = _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)
    path = f"/api/v1/establishments/{membership.establishment_id}/"
    path += path_suffix.format(signal_id=signal.id)

    client_method = getattr(api_client, method)
    response = client_method(
        path,
        data=data,
        format="json",
        **auth_headers(token),
    )

    assert response.status_code in {404, 405}


def test_signal_detail_only_allows_get(api_client):
    membership = build_api_membership()
    signal = _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)
    url = signal_detail_url(membership.establishment_id, signal.id)

    headers = auth_headers(token)
    assert api_client.get(url, **headers).status_code == 200
    assert api_client.post(url, **headers).status_code == 405
    patch_response = api_client.patch(url, {"title": "x"}, format="json", **headers)
    assert patch_response.status_code == 405
    assert api_client.delete(url, **headers).status_code == 405


def test_staff_forbidden_pin_unpin_and_urgency(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)
    base = signal_detail_url(membership.establishment_id, signal.id)
    headers = auth_headers(token)

    assert api_client.post(base + "pin/", **headers).status_code == 403
    assert api_client.post(base + "unpin/", **headers).status_code == 403
    assert (
        api_client.patch(
            base + "urgency/",
            {"urgency": "high"},
            format="json",
            **headers,
        ).status_code
        == 403
    )


def test_owner_can_mutate_any_establishment_signal(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)
    base = signal_detail_url(membership.establishment_id, signal.id)
    headers = auth_headers(token)

    assert api_client.post(base + "pin/", **headers).status_code == 200
    assert api_client.post(base + "unpin/", **headers).status_code == 200
    assert (
        api_client.patch(
            base + "urgency/",
            {"urgency": "high"},
            format="json",
            **headers,
        ).status_code
        == 200
    )


def test_manager_urgency_requires_membership_scope(api_client):
    import uuid

    from houston.accounts.models import User
    from houston.establishments.tests.conftest import TEST_PASSWORD

    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    signal = _signal_with_linked_observation(membership)
    taxonomy = create_restaurant_v3_taxonomy(membership.establishment)
    assert taxonomy.maintenance is not None

    manager = User.objects.create_user(
        username=f"mgr_{uuid.uuid4().hex[:6]}",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    other_membership = EstablishmentMembership.objects.create(
        user=manager,
        establishment=membership.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    token = login(api_client, user=other_membership.user)
    base = signal_detail_url(membership.establishment_id, signal.id)
    headers = auth_headers(token)

    denied = api_client.patch(
        base + "urgency/",
        {"urgency": "high"},
        format="json",
        **headers,
    )
    assert denied.status_code == 403

    create_membership_with_business_unit_scope(
        membership=other_membership,
        business_unit=taxonomy.maintenance,
    )
    allowed = api_client.patch(
        base + "urgency/",
        {"urgency": "high"},
        format="json",
        **headers,
    )
    assert allowed.status_code == 200
