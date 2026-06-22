from __future__ import annotations

import uuid
from dataclasses import dataclass

from django.db.models import Q, QuerySet

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.notification_cursor import (
    decode_notification_cursor,
    encode_notification_cursor,
)


@dataclass(frozen=True)
class NotificationsPage:
    items: list[Notification]
    next_cursor: str | None
    has_more: bool
    applied_status: str | None


def _notifications_queryset(*, membership: EstablishmentMembership) -> QuerySet[Notification]:
    return (
        Notification.objects.filter(
            establishment_id=membership.establishment_id,
            recipient_membership_id=membership.id,
        )
        .select_related("actor_membership__user")
        .order_by("-created_at", "-id")
    )


def apply_status_filter(
    queryset: QuerySet[Notification],
    *,
    status: str | None,
) -> tuple[QuerySet[Notification], str | None]:
    if status is None:
        return queryset.exclude(status=Notification.Status.ARCHIVED), None
    return queryset.filter(status=status), status


def notifications_queryset_for_recipient(
    membership: EstablishmentMembership,
    *,
    status: str | None = None,
) -> QuerySet[Notification]:
    queryset, _ = apply_status_filter(
        _notifications_queryset(membership=membership),
        status=status,
    )
    return queryset


def get_notification_for_recipient(
    *,
    membership: EstablishmentMembership,
    notification_id: uuid.UUID,
) -> Notification | None:
    return (
        _notifications_queryset(membership=membership)
        .filter(id=notification_id)
        .first()
    )


def count_unread_notifications(*, membership: EstablishmentMembership) -> int:
    return Notification.objects.filter(
        establishment_id=membership.establishment_id,
        recipient_membership_id=membership.id,
        status=Notification.Status.UNREAD,
    ).count()


def build_notifications_page(
    *,
    membership: EstablishmentMembership,
    status: str | None,
    cursor: str | None,
    page_size: int,
) -> NotificationsPage:
    queryset, applied_status = apply_status_filter(
        _notifications_queryset(membership=membership),
        status=status,
    )

    cursor_values = decode_notification_cursor(
        cursor,
        expected_status_filter=applied_status,
    )
    if cursor_values is not None:
        queryset = queryset.filter(
            Q(created_at__lt=cursor_values.created_at)
            | Q(created_at=cursor_values.created_at, id__lt=cursor_values.notification_id)
        )

    rows = list(queryset[: page_size + 1])
    has_more = len(rows) > page_size
    page = rows[:page_size]

    next_cursor = None
    if has_more and page:
        last = page[-1]
        next_cursor = encode_notification_cursor(
            created_at=last.created_at,
            notification_id=last.id,
            status_filter=applied_status,
        )

    return NotificationsPage(
        items=page,
        next_cursor=next_cursor,
        has_more=has_more,
        applied_status=applied_status,
    )
