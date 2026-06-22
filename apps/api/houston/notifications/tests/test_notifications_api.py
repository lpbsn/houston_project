from __future__ import annotations

import pytest
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.tests.conftest import (
    NOTIFICATION_RESPONSE_ALLOWLIST,
    create_test_notification,
    notification_archive_url,
    notification_mark_read_url,
    notifications_mark_all_read_url,
    notifications_url,
)
from houston.testing.auth import auth_headers, build_api_membership, login

pytestmark = pytest.mark.django_db


def test_list_notifications_returns_safe_payload(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(recipient=recipient)
    token = login(api_client, user=recipient.user)

    response = api_client.get(
        notifications_url(recipient.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["unread"] == 1
    assert body["applied_filters"]["status"] is None
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert set(item.keys()) == NOTIFICATION_RESPONSE_ALLOWLIST
    assert "channel" not in item
    assert item["id"] == str(notification.id)
    assert item["body"] == "Une action vous a été assignée."


def test_default_list_excludes_archived(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=recipient, status=Notification.Status.UNREAD)
    create_test_notification(recipient=recipient, status=Notification.Status.ARCHIVED)
    token = login(api_client, user=recipient.user)

    response = api_client.get(
        notifications_url(recipient.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
    assert response.json()["items"][0]["status"] == Notification.Status.UNREAD


def test_status_archived_filter(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=recipient, status=Notification.Status.UNREAD)
    archived = create_test_notification(
        recipient=recipient,
        status=Notification.Status.ARCHIVED,
    )
    token = login(api_client, user=recipient.user)

    response = api_client.get(
        notifications_url(recipient.establishment_id, "?status=archived"),
        **auth_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(archived.id)
    assert body["applied_filters"]["status"] == Notification.Status.ARCHIVED


def test_archive_unread_decrements_unread_count(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(
        recipient=recipient,
        status=Notification.Status.UNREAD,
    )
    token = login(api_client, user=recipient.user)

    list_before = api_client.get(
        notifications_url(recipient.establishment_id),
        **auth_headers(token),
    )
    assert list_before.json()["counts"]["unread"] == 1

    archive_response = api_client.post(
        notification_archive_url(recipient.establishment_id, notification.id),
        **auth_headers(token),
    )
    assert archive_response.status_code == 200
    archived_body = archive_response.json()
    assert archived_body["status"] == Notification.Status.ARCHIVED
    assert archived_body["read_at"] is not None
    assert archived_body["archived_at"] is not None

    list_after = api_client.get(
        notifications_url(recipient.establishment_id),
        **auth_headers(token),
    )
    assert list_after.json()["counts"]["unread"] == 0


def test_mark_read_returns_updated_notification(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    notification = create_test_notification(
        recipient=recipient,
        status=Notification.Status.UNREAD,
    )
    token = login(api_client, user=recipient.user)

    response = api_client.post(
        notification_mark_read_url(recipient.establishment_id, notification.id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == Notification.Status.READ
    assert response.json()["read_at"] is not None


def test_mark_all_read_returns_updated_count(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=recipient, status=Notification.Status.UNREAD)
    create_test_notification(recipient=recipient, status=Notification.Status.UNREAD)
    token = login(api_client, user=recipient.user)

    response = api_client.post(
        notifications_mark_all_read_url(recipient.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["updated_count"] == 2


def test_notification_404_for_other_recipient(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other = build_api_membership()
    notification = create_test_notification(recipient=recipient)
    token = login(api_client, user=other.user)

    response = api_client.post(
        notification_mark_read_url(other.establishment_id, notification.id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_notification_404_for_wrong_establishment(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    other = build_api_membership()
    create_test_notification(recipient=recipient)
    token = login(api_client, user=recipient.user)

    response = api_client.get(
        notifications_url(other.establishment_id),
        **auth_headers(token),
    )

    assert response.status_code == 404


def test_invalid_status_filter_returns_400(api_client):
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    token = login(api_client, user=recipient.user)

    response = api_client.get(
        notifications_url(recipient.establishment_id, "?status=invalid"),
        **auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
