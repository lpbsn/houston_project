from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
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


def vapid_public_key_url() -> str:
    return "/api/v1/push/vapid-public-key/"


def web_push_subscriptions_url() -> str:
    return "/api/v1/me/web-push-subscriptions/"


def web_push_subscription_revoke_url(subscription_id) -> str:
    return f"/api/v1/me/web-push-subscriptions/{subscription_id}/"


def create_test_notification(
    *,
    recipient: EstablishmentMembership,
    status: str = Notification.Status.UNREAD,
    event_key: str = Notification.EventKey.ACTION_PLAN_EXECUTION_CREATED,
    subject_type: str = Notification.SubjectType.ACTION_PLAN_EXECUTION,
    subject_id: uuid.UUID | None = None,
    dedupe_key: str = "",
    title: str = "Nouvelle exécution de plan",
    body: str = "Une exécution de plan d'action est disponible.",
) -> Notification:
    return Notification.objects.create(
        establishment_id=recipient.establishment_id,
        recipient_membership=recipient,
        actor_membership=None,
        event_key=event_key,
        subject_type=subject_type,
        subject_id=subject_id or uuid.uuid4(),
        priority=Notification.Priority.ACTION_REQUIRED,
        status=status,
        title=title,
        body=body,
        dedupe_key=dedupe_key,
    )


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
