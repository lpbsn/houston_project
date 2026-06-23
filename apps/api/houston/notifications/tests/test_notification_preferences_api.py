from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.notifications.tests.conftest import (
    notifications_preferences_url,
)
from houston.testing.auth import auth_headers, build_api_membership, login

pytestmark = pytest.mark.django_db


def test_get_notification_preferences_defaults_to_enabled(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    response = api_client.get(
        notifications_preferences_url(recipient.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {"notifications_enabled": True}


def test_patch_notification_preferences_updates_value(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    patch_response = api_client.patch(
        notifications_preferences_url(recipient.establishment_id),
        {"notifications_enabled": False},
        format="json",
        **auth_headers(token),
    )

    assert patch_response.status_code == 200
    assert patch_response.json() == {"notifications_enabled": False}

    get_response = api_client.get(
        notifications_preferences_url(recipient.establishment_id),
        **auth_headers(token),
    )
    assert get_response.status_code == 200
    assert get_response.json() == {"notifications_enabled": False}

    recipient.refresh_from_db()
    assert recipient.notifications_enabled is False


def test_get_notification_preferences_requires_authentication(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)

    response = api_client.get(notifications_preferences_url(recipient.establishment_id))

    assert response.status_code == 401


def test_patch_notification_preferences_requires_authentication(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)

    response = api_client.patch(
        notifications_preferences_url(recipient.establishment_id),
        {"notifications_enabled": False},
        format="json",
    )

    assert response.status_code == 401


def test_notification_preferences_returns_not_found_for_out_of_scope_establishment(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=outsider.user)

    response = api_client.get(
        notifications_preferences_url(recipient.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_patch_notification_preferences_rejects_missing_field(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    response = api_client.patch(
        notifications_preferences_url(recipient.establishment_id),
        {},
        format="json",
        **auth_headers(token),
    )

    assert response.status_code == 400
