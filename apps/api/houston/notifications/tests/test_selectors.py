from __future__ import annotations

import pytest

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.selectors import (
    build_notifications_page,
    count_unread_notifications,
    notifications_queryset_for_recipient,
)
from houston.notifications.tests.conftest import create_test_notification
from houston.testing.auth import build_api_membership

pytestmark = pytest.mark.django_db


def test_default_list_excludes_archived():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    active = create_test_notification(recipient=recipient, status=Notification.Status.UNREAD)
    archived = create_test_notification(
        recipient=recipient,
        status=Notification.Status.ARCHIVED,
    )

    page = build_notifications_page(
        membership=recipient,
        status=None,
        cursor=None,
        page_size=25,
    )
    ids = {item.id for item in page.items}

    assert active.id in ids
    assert archived.id not in ids


def test_status_archived_filter_returns_archived_only():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=recipient, status=Notification.Status.UNREAD)
    archived = create_test_notification(
        recipient=recipient,
        status=Notification.Status.ARCHIVED,
    )

    page = build_notifications_page(
        membership=recipient,
        status=Notification.Status.ARCHIVED,
        cursor=None,
        page_size=25,
    )

    assert len(page.items) == 1
    assert page.items[0].id == archived.id
    assert page.applied_status == Notification.Status.ARCHIVED


def test_notifications_ordered_newest_first():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    first = create_test_notification(recipient=recipient, title="First")
    second = create_test_notification(recipient=recipient, title="Second")

    items = list(notifications_queryset_for_recipient(recipient))
    assert items[0].id == second.id
    assert items[1].id == first.id


def test_count_unread_notifications():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=recipient, status=Notification.Status.UNREAD)
    create_test_notification(recipient=recipient, status=Notification.Status.READ)
    create_test_notification(recipient=recipient, status=Notification.Status.ARCHIVED)

    assert count_unread_notifications(membership=recipient) == 1


def test_build_notifications_page_cursor_pagination():
    recipient = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    create_test_notification(recipient=recipient, title="Third")
    create_test_notification(recipient=recipient, title="Second")
    create_test_notification(recipient=recipient, title="First")
    ordered = list(notifications_queryset_for_recipient(recipient))
    assert len(ordered) == 3

    page_one = build_notifications_page(
        membership=recipient,
        status=None,
        cursor=None,
        page_size=2,
    )

    assert page_one.has_more is True
    assert page_one.next_cursor is not None
    assert [item.id for item in page_one.items] == [ordered[0].id, ordered[1].id]

    page_two = build_notifications_page(
        membership=recipient,
        status=None,
        cursor=page_one.next_cursor,
        page_size=2,
    )

    assert page_two.has_more is False
    assert [item.id for item in page_two.items] == [ordered[2].id]
