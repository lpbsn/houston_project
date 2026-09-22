from __future__ import annotations

import uuid

from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification


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
