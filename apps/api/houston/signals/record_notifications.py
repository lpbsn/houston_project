"""Durable event delivery and date-scoped reminders using existing notification preferences."""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from houston.establishments.models import EstablishmentMembership
from houston.notifications.services import create_in_app_notification
from houston.signals.models import Signal, SignalRecordEvent


def schedule_record_event(event_id):
    from houston.core.celery_publish import publish_celery_task
    from houston.signals.tasks import deliver_record_event_task

    transaction.on_commit(
        lambda: publish_celery_task(deliver_record_event_task, args=(str(event_id),))
    )


def deliver_record_event(event_id):
    event = SignalRecordEvent.objects.select_related("signal", "actor").filter(pk=event_id).first()
    if event is None or event.notified_at:
        return
    signal = event.signal
    reporters = signal.source_observation_links.values_list(
        "observation__submitted_by_membership_id",
        flat=True,
    )
    participants = signal.participants.filter(notifications_enabled=True).values("membership_id")
    muted = signal.participants.filter(notifications_enabled=False).values("membership_id")
    recipients = EstablishmentMembership.objects.filter(
        establishment_id=signal.establishment_id,
        status="active",
    ).filter(Q(pk=signal.owner_membership_id) | Q(pk__in=reporters) | Q(pk__in=participants))
    for recipient in recipients.exclude(pk__in=muted).distinct().iterator(chunk_size=100):
        create_in_app_notification(
            establishment_id=signal.establishment_id,
            recipient_membership=recipient,
            event_key="signal.record.updated",
            subject_type="signal",
            subject_id=signal.id,
            priority="info",
            actor_membership=(
                event.actor if event.actor and event.actor.status == "active" else None
            ),
            idempotency_key=f"record:{event.id}:{recipient.id}",
        )
    SignalRecordEvent.objects.filter(pk=event.id, notified_at__isnull=True).update(
        notified_at=timezone.now()
    )


def deliver_record_reminders(*, now=None):
    now = now or timezone.now()
    # Each site's date is authoritative; a small UTC window bounds the scan.
    records = Signal.objects.filter(
        status__in=["open", "interesting", "in_progress"],
        owner_membership__status="active",
        due_on__gte=now.date() - timedelta(days=2),
        due_on__lte=now.date() + timedelta(days=2),
    ).select_related("establishment", "owner_membership")
    for signal in records.iterator(chunk_size=100):
        local = now.astimezone(ZoneInfo(signal.establishment.timezone))
        if local.hour < 9:
            continue
        delta = (signal.due_on - local.date()).days
        if delta not in (-1, 1):
            continue
        if signal.participants.filter(
            membership=signal.owner_membership, notifications_enabled=False
        ).exists():
            continue
        event = "signal.record.due" if delta == 1 else "signal.record.overdue"
        create_in_app_notification(
            establishment_id=signal.establishment_id,
            recipient_membership=signal.owner_membership,
            event_key=event,
            subject_type="signal",
            subject_id=signal.id,
            priority="action_required",
            idempotency_key=f"record:{signal.id}:due:{signal.due_revision}:{delta}:{signal.owner_membership_id}",
        )
