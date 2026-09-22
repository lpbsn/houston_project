from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from houston.establishments.models import EstablishmentMembership
from houston.notifications.tests.helpers import create_test_notification
from houston.testing.auth import auth_headers, build_api_membership, login
from houston.testing.factories import create_establishment, create_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

__all__ = [
    "api_client",
    "auth_headers",
    "build_api_membership",
    "business_unit",
    "establishment",
    "login",
    "owner_membership",
    "create_test_notification",
    "staff_membership",
]


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


@pytest.fixture
def establishment():
    return create_establishment(name="Notification Hotel", timezone="UTC")


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
    return membership


def notifications_url(establishment_id, query: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/notifications/"
    return base + query


def notification_mark_read_url(establishment_id, notification_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/notifications/{notification_id}/mark-read/"


def notifications_mark_all_read_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/notifications/mark-all-read/"


def notifications_preferences_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/notifications/preferences/"


def push_devices_url() -> str:
    return "/api/v1/me/push-devices/"


def push_device_revoke_url(device_id) -> str:
    return f"/api/v1/me/push-devices/{device_id}/"


NOTIFICATION_RESPONSE_ALLOWLIST = frozenset(
    {
        "id",
        "event_key",
        "subject_type",
        "subject_id",
        "priority",
        "status",
        "title",
        "body",
        "actor",
        "navigation",
        "created_at",
        "read_at",
        "archived_at",
    }
)
