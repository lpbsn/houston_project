from __future__ import annotations

import uuid

from django.utils import timezone

from houston.notifications.constants import DEFAULT_ACTOR_DISPLAY_NAME
from houston.notifications.models import Notification


def scrub_notifications_for_deleted_memberships(*, membership_ids: list[uuid.UUID]) -> None:
    if not membership_ids:
        return
    now = timezone.now()
    Notification.objects.filter(recipient_membership_id__in=membership_ids).delete()
    Notification.objects.filter(
        actor_membership_id__in=membership_ids,
        event_key=Notification.EventKey.CHAT_MESSAGE_RECEIVED,
    ).update(
        title=f"Message reçu de {DEFAULT_ACTOR_DISPLAY_NAME}",
        updated_at=now,
    )
