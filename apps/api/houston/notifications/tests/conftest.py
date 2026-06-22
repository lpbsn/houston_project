from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIClient

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.testing.auth import auth_headers, build_api_membership, login

__all__ = ["api_client", "auth_headers", "build_api_membership", "login"]


@pytest.fixture
def api_client():
    return APIClient(enforce_csrf_checks=True)


def notifications_url(establishment_id, query: str = "") -> str:
    base = f"/api/v1/establishments/{establishment_id}/notifications/"
    return base + query


def notification_mark_read_url(establishment_id, notification_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/notifications/"
        f"{notification_id}/mark-read/"
    )


def notification_archive_url(establishment_id, notification_id) -> str:
    return (
        f"/api/v1/establishments/{establishment_id}/notifications/"
        f"{notification_id}/archive/"
    )


def notifications_mark_all_read_url(establishment_id) -> str:
    return f"/api/v1/establishments/{establishment_id}/notifications/mark-all-read/"


def create_test_notification(
    *,
    recipient: EstablishmentMembership,
    status: str = Notification.Status.UNREAD,
    event_key: str = Notification.EventKey.ACTION_CREATED,
    subject_type: str = Notification.SubjectType.ACTION,
    subject_id: uuid.UUID | None = None,
    dedupe_key: str = "",
    title: str = "Nouvelle action",
    body: str = "Une action vous a été assignée.",
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
        "created_at",
        "read_at",
        "archived_at",
    }
)
