from __future__ import annotations

import pytest
from houston.establishments.models import EstablishmentMembership
from houston.testing.auth import login
from houston.testing.factories import (
    create_establishment,
    create_membership,
    create_user,
)
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

__all__ = [
    "api_client",
    "business_unit",
    "create_establishment",
    "create_membership",
    "create_user",
    "default_ws_headers",
    "establishment",
    "get_realtime_ws_ticket",
    "login",
    "other_staff_membership",
    "owner_membership",
    "staff_membership",
    "ws_realtime_path",
    "ws_realtime_ticket_url",
]


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def establishment():
    return create_establishment(name="Checklist Hotel", timezone="UTC")


@pytest.fixture
def business_unit(establishment):
    return create_business_unit(establishment=establishment, key="restaurant")


@pytest.fixture
def owner_membership(establishment):
    return create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.OWNER,
    )


@pytest.fixture
def staff_membership(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return EstablishmentMembership.objects.prefetch_related("scope_links").get(pk=membership.pk)


@pytest.fixture
def other_staff_membership(establishment, business_unit):
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    return EstablishmentMembership.objects.prefetch_related("scope_links").get(pk=membership.pk)


def ws_realtime_ticket_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/realtime/ws-ticket/"


def ws_realtime_path(establishment_id) -> str:
    return f"/ws/v1/establishments/{establishment_id}/realtime/"


def get_realtime_ws_ticket(api_client, *, user, establishment) -> str:
    token = login(api_client, user=user)
    response = api_client.post(
        ws_realtime_ticket_url(establishment.id),
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == 200
    return response.json()["ticket"]


def default_ws_headers() -> list[tuple[bytes, bytes]]:
    return [
        (b"host", b"localhost"),
        (b"origin", b"http://localhost"),
    ]
