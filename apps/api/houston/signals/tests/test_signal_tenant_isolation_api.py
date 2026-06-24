from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    login,
    signal_detail_url,
)
from houston.testing.auth import build_api_membership as build_foreign_membership

pytestmark = pytest.mark.django_db


def _open_signal(owner):
    return create_minimal_v3_signal(owner, title="Cross-establishment signal")


def test_active_signal_detail_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _open_signal(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.get(
        signal_detail_url(foreign.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_pin_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _open_signal(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        signal_detail_url(foreign.establishment_id, signal.id) + "pin/",
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_cancel_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _open_signal(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        signal_detail_url(foreign.establishment_id, signal.id) + "cancel/",
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_resolve_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, title="Resolve me", status=Signal.Status.IN_PROGRESS)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        signal_detail_url(foreign.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )

    assert response.status_code == 404
