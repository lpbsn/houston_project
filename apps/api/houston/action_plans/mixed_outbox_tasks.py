from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from houston.action_plans.models import ActionPlanExecution, ActionPlanMixedOutboxEntry
from houston.core.observability import build_celery_task_failure_log_context
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.notifications.scheduling import _resolve_execution_created_event_key
from houston.notifications.services import create_in_app_notification
from houston.realtime.broadcast import notify_establishment_invalidation

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 8
LEASE_TTL_SECONDS = 120
BATCH_SIZE = 50
MAX_BACKOFF_SECONDS = 300


def _compute_backoff_seconds(*, attempts: int) -> int:
    return min(2 ** max(attempts - 1, 0), MAX_BACKOFF_SECONDS)


def _claim_outbox_entries(*, batch_size: int = BATCH_SIZE) -> list[ActionPlanMixedOutboxEntry]:
    now = timezone.now()
    claimed: list[ActionPlanMixedOutboxEntry] = []

    with transaction.atomic():
        eligible = (
            ActionPlanMixedOutboxEntry.objects.filter(
                Q(
                    status=ActionPlanMixedOutboxEntry.Status.PENDING,
                    available_at__lte=now,
                )
                | Q(
                    status=ActionPlanMixedOutboxEntry.Status.PROCESSING,
                    lease_expires_at__lt=now,
                )
                | Q(
                    status=ActionPlanMixedOutboxEntry.Status.FAILED,
                    available_at__lte=now,
                    attempts__lt=MAX_ATTEMPTS,
                )
            )
            .select_for_update(skip_locked=True)
            .order_by("available_at", "created_at")[:batch_size]
        )

        for entry in eligible:
            entry.status = ActionPlanMixedOutboxEntry.Status.PROCESSING
            entry.attempts += 1
            entry.lease_expires_at = now + timedelta(seconds=LEASE_TTL_SECONDS)
            entry.save(
                update_fields=["status", "attempts", "lease_expires_at", "updated_at"],
            )
            claimed.append(entry)

    return claimed


def _process_notification_entry(*, entry: ActionPlanMixedOutboxEntry) -> None:
    payload = entry.payload
    execution = (
        ActionPlanExecution.objects.filter(id=payload["execution_id"])
        .select_related("created_by")
        .prefetch_related("assignees__membership")
        .first()
    )
    if execution is None:
        return

    recipient = EstablishmentMembership.objects.filter(
        id=payload["recipient_membership_id"],
        establishment_id=execution.establishment_id,
    ).first()
    if recipient is None:
        return

    actor = None
    actor_membership_id = payload.get("actor_membership_id")
    if actor_membership_id:
        actor = EstablishmentMembership.objects.filter(
            id=actor_membership_id,
            establishment_id=execution.establishment_id,
        ).first()

    event_key = payload.get("event_key") or _resolve_execution_created_event_key(
        execution=execution,
    )
    try:
        create_in_app_notification(
            establishment_id=execution.establishment_id,
            recipient_membership=recipient,
            event_key=event_key,
            subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
            subject_id=execution.id,
            priority=Notification.Priority.ACTION_REQUIRED,
            actor_membership=actor,
            idempotency_key=payload["idempotency_key"],
        )
    except IntegrityError:
        return


def _process_realtime_entry(*, entry: ActionPlanMixedOutboxEntry) -> None:
    payload = entry.payload
    notify_establishment_invalidation(
        establishment_id=uuid.UUID(str(payload["establishment_id"])),
        subject_type=str(payload["subject_type"]),
        reason=str(payload["reason"]),
        entity_id=uuid.UUID(str(payload["entity_id"])),
    )


def _process_outbox_entry(*, entry: ActionPlanMixedOutboxEntry) -> None:
    if entry.effect_type == ActionPlanMixedOutboxEntry.EffectType.REALTIME_INVALIDATION:
        _process_realtime_entry(entry=entry)
        return
    if entry.effect_type == ActionPlanMixedOutboxEntry.EffectType.NOTIFICATION:
        _process_notification_entry(entry=entry)
        return
    raise ValueError(f"Unsupported outbox effect type: {entry.effect_type}")


def _finalize_outbox_entry(
    *,
    entry: ActionPlanMixedOutboxEntry,
    success: bool,
    error_message: str = "",
) -> None:
    now = timezone.now()
    if success:
        entry.status = ActionPlanMixedOutboxEntry.Status.PROCESSED
        entry.processed_at = now
        entry.lease_expires_at = None
        entry.last_error = ""
        entry.save(
            update_fields=[
                "status",
                "processed_at",
                "lease_expires_at",
                "last_error",
                "updated_at",
            ],
        )
        return

    entry.status = ActionPlanMixedOutboxEntry.Status.FAILED
    entry.lease_expires_at = None
    entry.last_error = error_message[:2000]
    if entry.attempts >= MAX_ATTEMPTS:
        entry.available_at = now
    else:
        entry.available_at = now + timedelta(
            seconds=_compute_backoff_seconds(attempts=entry.attempts),
        )
    entry.save(
        update_fields=[
            "status",
            "lease_expires_at",
            "last_error",
            "available_at",
            "updated_at",
        ],
    )


def process_action_plan_mixed_outbox_batch(*, batch_size: int = BATCH_SIZE) -> int:
    claimed = _claim_outbox_entries(batch_size=batch_size)
    processed_count = 0

    for entry in claimed:
        try:
            _process_outbox_entry(entry=entry)
        except Exception as exc:
            logger.exception(
                "action_plan_mixed_outbox_entry_failed",
                extra={
                    "outbox_entry_id": str(entry.id),
                    "effect_key": entry.effect_key,
                    "attempts": entry.attempts,
                },
            )
            _finalize_outbox_entry(
                entry=entry,
                success=False,
                error_message=str(exc),
            )
            continue

        _finalize_outbox_entry(entry=entry, success=True)
        processed_count += 1

    return processed_count


@shared_task(
    max_retries=0,
    soft_time_limit=settings.HOUSTON_CELERY_BEAT_TASK_SOFT_TIME_LIMIT_SECONDS,
    time_limit=settings.HOUSTON_CELERY_BEAT_TASK_TIME_LIMIT_SECONDS,
)
def process_action_plan_mixed_outbox_batch_task(
    batch_size: int = BATCH_SIZE,
) -> int:
    try:
        return process_action_plan_mixed_outbox_batch(batch_size=batch_size)
    except Exception as exc:
        logger.error(
            "action_plan_mixed_outbox_batch_failed",
            extra=build_celery_task_failure_log_context(
                batch_size=batch_size,
                exception_class=type(exc).__name__,
                task_name="process_action_plan_mixed_outbox_batch_task",
            ),
            exc_info=False,
        )
        raise
