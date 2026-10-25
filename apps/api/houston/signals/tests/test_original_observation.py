from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.signals.api.serializers import SignalDetailSerializer, serialize_signal_detail
from houston.signals.models import SignalSourceObservation
from houston.signals.permissions import can_view_original_observation
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_observation,
    login,
    signal_detail_url,
)

pytestmark = pytest.mark.django_db


def make_source(membership, signal, text="  Déposer les chèques le 3 novembre.\nMerci !  "):
    observation = create_observation(membership=membership, text=text)
    SignalSourceObservation.objects.create(
        signal=signal, observation=observation,
        link_type=SignalSourceObservation.LinkType.CREATED_FROM,
    )
    return observation


def detail(api_client, membership, signal):
    token = login(api_client, user=membership.user)
    return api_client.get(
        signal_detail_url(membership.establishment_id, signal.id), **auth_headers(token)
    )


def test_owner_receives_exact_original_text(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner)
    observation = make_source(owner, signal)
    response = detail(api_client, owner, signal)
    assert response.status_code == 200
    body = response.json()
    assert body["can_view_original_observation"] is True
    assert body["original_observation"]["raw_text"] == observation.raw_text
    assert body["original_observation"]["id"] == str(observation.id)
    assert body["original_observation"]["submitted_at"]
    assert "raw_text" not in body["source_context"]


@pytest.mark.parametrize("role", ["director", "manager", "staff"])
def test_non_owner_never_receives_original_text(api_client, role):
    member = build_api_membership(role=role)
    signal = create_minimal_v3_signal(member)
    observation = make_source(member, signal)
    response = detail(api_client, member, signal)
    assert response.status_code == 200
    assert response.json()["can_view_original_observation"] is False
    assert response.json()["original_observation"] is None
    assert observation.raw_text not in response.content.decode()


def test_owner_of_another_establishment_cannot_read_source(api_client):
    owner = build_api_membership(role="owner")
    other = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(other)
    make_source(other, signal)
    assert can_view_original_observation(owner, signal) is False
    assert detail(api_client, owner, signal).status_code == 404


def test_inactive_owner_has_no_original_access():
    owner = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(owner)
    owner.status = EstablishmentMembership.Status.INVITED
    assert can_view_original_observation(owner, signal) is False


def test_missing_original_is_explicit(api_client):
    owner = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(owner)
    response = detail(api_client, owner, signal)
    assert response.status_code == 200
    assert response.json()["can_view_original_observation"] is True
    assert response.json()["original_observation"] is None


def test_cross_read_only_projection_never_exposes_original():
    owner = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(owner)
    make_source(owner, signal)
    payload = serialize_signal_detail(signal=signal, membership=owner, request=None, read_only=True)
    body = SignalDetailSerializer(payload).data
    assert body["can_view_original_observation"] is False
    assert body["original_observation"] is None


def test_foreign_source_link_never_exposes_original(api_client):
    owner = build_api_membership(role="owner")
    other = build_api_membership(role="owner")
    signal = create_minimal_v3_signal(owner)
    make_source(other, signal)
    response = detail(api_client, owner, signal)
    assert response.status_code == 200
    assert response.json()["original_observation"] is None
