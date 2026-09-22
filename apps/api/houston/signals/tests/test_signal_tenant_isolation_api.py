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


def _open_signal(owner, *, status=Signal.Status.OPEN, title="Cross-establishment signal"):
    return create_minimal_v3_signal(owner, title=title, status=status)


@pytest.mark.parametrize(
    ("suffix", "method", "status"),
    [
        ("", "get", Signal.Status.OPEN),
        ("pin/", "post", Signal.Status.OPEN),
        ("cancel/", "post", Signal.Status.OPEN),
        ("resolve/", "post", Signal.Status.IN_PROGRESS),
    ],
)
def test_signal_command_cross_establishment_returns_404(api_client, suffix, method, status):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _open_signal(owner, status=status)
    token = login(api_client, user=foreign.user)

    request = getattr(api_client, method)
    response = request(
        signal_detail_url(foreign.establishment_id, signal.id) + suffix,
        **auth_headers(token),
    )

    assert response.status_code == 404
