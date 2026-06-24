from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from houston.actions.services import create_action
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.comments.tests.conftest import (
    action_comments_url,
    auth_headers,
    build_api_membership,
    login,
    signal_comments_url,
)
from houston.establishments.models import EstablishmentMembership
from houston.signals.models import Signal
from houston.testing.auth import build_api_membership as build_foreign_membership
from houston.testing.taxonomy import create_signal_v3_for_membership, hotel_maintenance_setup

pytestmark = pytest.mark.django_db


def _signal_and_action(owner):
    staff = build_api_membership_on_establishment(owner, role=EstablishmentMembership.Role.STAFF)
    hotel, maintenance, electricite = hotel_maintenance_setup(owner.establishment)
    signal = create_signal_v3_for_membership(
        owner,
        affected_business_unit=hotel,
        responsible_business_unit=maintenance,
        activity_subject=electricite,
        status=Signal.Status.OPEN,
    )
    action = create_action(
        establishment_id=owner.establishment_id,
        created_by=owner,
        title="Linked",
        instruction="Do it",
        assignee_ids=[staff.id],
        due_at=timezone.now() + timedelta(days=1),
        signal_id=signal.id,
    )
    return signal, action


def test_signal_comments_list_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal, _ = _signal_and_action(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.get(
        signal_comments_url(foreign.establishment_id, signal.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_signal_comments_create_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    signal, _ = _signal_and_action(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        signal_comments_url(foreign.establishment_id, signal.id),
        {"body": "Should not post"},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_action_comments_list_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    _, action = _signal_and_action(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.get(
        action_comments_url(foreign.establishment_id, action.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_action_comments_create_cross_establishment_returns_404(api_client):
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    foreign = build_foreign_membership(role=EstablishmentMembership.Role.OWNER)
    _, action = _signal_and_action(owner)
    token = login(api_client, user=foreign.user)

    response = api_client.post(
        action_comments_url(foreign.establishment_id, action.id),
        {"body": "Should not post"},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 404
