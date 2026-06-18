from __future__ import annotations

import uuid

import pytest

from houston.accounts.models import User
from houston.establishments.models import EstablishmentMembership
from houston.establishments.tests.conftest import TEST_PASSWORD
from houston.establishments.tests.taxonomy_helpers import create_membership_with_business_unit_scope
from houston.signals.models import Signal
from houston.signals.tests.conftest import (
    auth_headers,
    build_api_membership,
    create_minimal_v3_signal,
    create_restaurant_v3_taxonomy,
    login,
    signal_detail_url,
)

pytestmark = pytest.mark.django_db


def _fetch_hints(api_client, membership, signal):
    token = login(api_client, user=membership.user)
    response = api_client.get(
        signal_detail_url(membership.establishment_id, signal.id),
        **auth_headers(token),
    )
    assert response.status_code == 200
    return response.json()["permission_hints"]


def test_owner_open_signal_can_create_action_hint_true(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, status=Signal.Status.OPEN)

    hints = _fetch_hints(api_client, membership, signal)

    assert hints["can_create_action"] is True


def test_staff_open_signal_can_create_action_hint_false(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.STAFF)
    signal = create_minimal_v3_signal(membership, status=Signal.Status.OPEN)

    hints = _fetch_hints(api_client, membership, signal)

    assert hints["can_create_action"] is False


def test_staff_scoped_signal_can_create_action_hint_false(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, status=Signal.Status.OPEN)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None

    user = User.objects.create_user(
        username=f"staff_{uuid.uuid4().hex[:6]}",
        email=f"staff_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    staff = EstablishmentMembership.objects.create(
        user=user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.STAFF,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=staff,
        business_unit=taxonomy.maintenance,
    )

    hints = _fetch_hints(api_client, staff, signal)

    assert hints["can_create_action"] is False


def test_resolved_signal_can_create_action_hint_false(api_client):
    membership = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(membership, status=Signal.Status.RESOLVED)

    hints = _fetch_hints(api_client, membership, signal)

    assert hints["can_create_action"] is False


def test_manager_without_responsible_scope_can_create_action_hint_false(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, status=Signal.Status.OPEN)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.bar is not None

    user = User.objects.create_user(
        username=f"mgr_{uuid.uuid4().hex[:6]}",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    manager = EstablishmentMembership.objects.create(
        user=user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=taxonomy.bar,
    )

    hints = _fetch_hints(api_client, manager, signal)

    assert hints["can_create_action"] is False


def test_manager_with_responsible_scope_can_create_action_hint_true(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    signal = create_minimal_v3_signal(owner, status=Signal.Status.OPEN)
    taxonomy = create_restaurant_v3_taxonomy(owner.establishment)
    assert taxonomy.maintenance is not None

    user = User.objects.create_user(
        username=f"mgr_{uuid.uuid4().hex[:6]}",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        password=TEST_PASSWORD,
        status=User.Status.ACTIVE,
    )
    manager = EstablishmentMembership.objects.create(
        user=user,
        establishment=owner.establishment,
        role=EstablishmentMembership.Role.MANAGER,
        status=EstablishmentMembership.Status.ACTIVE,
    )
    create_membership_with_business_unit_scope(
        membership=manager,
        business_unit=taxonomy.maintenance,
    )

    hints = _fetch_hints(api_client, manager, signal)

    assert hints["can_create_action"] is True
