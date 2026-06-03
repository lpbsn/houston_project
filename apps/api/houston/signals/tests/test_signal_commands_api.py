from __future__ import annotations

import pytest
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership, MembershipScope
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_taxonomy,
    login,
    signal_detail_url,
)

pytestmark = pytest.mark.django_db


def _signal(membership):
    module, domain, subject = create_taxonomy(membership.establishment)
    now = timezone.now()
    return Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title="Issue",
        structured_summary="Summary",
        last_activity_at=now,
    )


def test_staff_cannot_pin(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = _signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "pin/",
        **auth_headers(token),
    )

    assert response.status_code == 403


def test_director_can_pin_open_signal(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    signal = _signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "pin/",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["is_pinned"] is True


def test_manager_pin_requires_scope(api_client):
    import uuid

    from houston.accounts.models import User
    from houston.establishments.tests.conftest import TEST_PASSWORD

    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    signal = _signal(membership)
    domain = signal.operational_domain

    user2 = User.objects.create_user(
        username=f"mgr_{uuid.uuid4().hex[:6]}",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    other = EstablishmentMembership.objects.create(
        user=user2,
        establishment=membership.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    token = login(api_client, user=other.user)
    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "pin/",
        **auth_headers(token),
    )
    assert response.status_code == 403

    MembershipScope.objects.create(membership=other, operational_domain=domain)
    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "pin/",
        **auth_headers(token),
    )
    assert response.status_code == 200
