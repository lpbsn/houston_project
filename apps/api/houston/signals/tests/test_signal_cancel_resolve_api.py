from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership, MembershipScope
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_taxonomy,
    login,
    signal_detail_url,
)

pytestmark = pytest.mark.django_db


def _signal(membership, *, status: str = Signal.Status.OPEN):
    module, domain, subject = create_taxonomy(membership.establishment)
    now = timezone.now()
    return Signal.objects.create(
        establishment=membership.establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        title="Issue",
        structured_summary="Summary",
        status=status,
        last_activity_at=now,
    )


def test_staff_cannot_cancel(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = _signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "cancel/",
        **auth_headers(token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_staff_cannot_resolve(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = _signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"


def test_owner_can_cancel_without_body(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "cancel/",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.CANCELED
    assert response.json()["permission_hints"]["can_cancel"] is False


def test_director_can_resolve_without_body(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.DIRECTOR)
    signal = _signal(membership, status=Signal.Status.IN_PROGRESS)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.RESOLVED


def test_manager_cancel_requires_scope(api_client):
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
        signal_detail_url(membership.establishment_id, signal.id) + "cancel/",
        **auth_headers(token),
    )
    assert response.status_code == 403

    MembershipScope.objects.create(membership=other, operational_domain=domain)
    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "cancel/",
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.CANCELED


def test_manager_resolve_requires_scope(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.MANAGER)
    signal = _signal(membership)
    domain = signal.operational_domain
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )
    assert response.status_code == 403

    MembershipScope.objects.create(membership=membership, operational_domain=domain)
    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == Signal.Status.RESOLVED


def test_cancel_terminal_signal_returns_invalid_state(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(membership, status=Signal.Status.CANCELED)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "cancel/",
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_resolve_terminal_signal_returns_permission_denied(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(membership, status=Signal.Status.RESOLVED)
    token = login(api_client, user=membership.user)

    response = api_client.post(
        signal_detail_url(membership.establishment_id, signal.id) + "resolve/",
        **auth_headers(token),
    )

    assert response.status_code == 403


def test_detail_includes_cancel_resolve_hints(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = _signal(membership)
    token = login(api_client, user=membership.user)

    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    hints = response.json()["permission_hints"]
    assert hints["can_cancel"] is True
    assert hints["can_resolve"] is True
