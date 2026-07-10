from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from houston.signals.models import SignalSourceObservation
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


def test_staff_forbidden_pin_and_unpin(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)
    base = signal_detail_url(membership.establishment_id, signal.id)
    headers = auth_headers(token)

    assert api_client.post(base + "pin/", **headers).status_code == 403
    assert api_client.post(base + "unpin/", **headers).status_code == 403


def test_owner_can_pin_and_unpin_establishment_signal(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal_with_linked_observation(membership)
    token = login(api_client, user=membership.user)
    base = signal_detail_url(membership.establishment_id, signal.id)
    headers = auth_headers(token)

    assert api_client.post(base + "pin/", **headers).status_code == 200
    assert api_client.post(base + "unpin/", **headers).status_code == 200


@pytest.mark.parametrize(
    "role",
    [
        EstablishmentMembership.Role.MANAGER,
        EstablishmentMembership.Role.STAFF,
    ],
)
def test_scoped_member_can_read_out_of_scope_signal_detail(api_client, role):
    membership = build_api_membership(role=role)
    in_scope_bu = create_business_unit(
        establishment=membership.establishment,
        key="bar",
        label="Bar",
    )
    out_of_scope_bu = create_business_unit(
        establishment=membership.establishment,
        key="kitchen",
        label="Kitchen",
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=in_scope_bu,
    )
    out_of_scope_signal = create_minimal_v3_signal(
        membership,
        title="Kitchen signal outside personal scope",
    )
    out_of_scope_signal.affected_business_unit = out_of_scope_bu
    out_of_scope_signal.responsible_business_unit = out_of_scope_bu
    out_of_scope_signal.save(
        update_fields=[
            "affected_business_unit",
            "responsible_business_unit",
            "updated_at",
        ]
    )

    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_detail_url(membership.establishment_id, out_of_scope_signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(out_of_scope_signal.id)
    assert response.json()["title"] == "Kitchen signal outside personal scope"
