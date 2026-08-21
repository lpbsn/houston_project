from __future__ import annotations

import logging
import uuid

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from houston.action_plans.constants import EXECUTION_STATUS_IN_PROGRESS, EXECUTION_STATUS_SCHEDULED
from houston.action_plans.models import ActionPlanExecution

logger = logging.getLogger(__name__)

# Beat / lazy establishment tick only — never reused for schedule-scoped reconciliation.
_BEAT_PROMOTION_BATCH_LIMIT = 200


def _apply_lifecycle_scope(
    queryset,
    *,
    establishment_id: uuid.UUID | None = None,
    execution_id: uuid.UUID | None = None,
):
    """Apply optional establishment and/or execution filters (both allowed together)."""
    if execution_id is not None:
        queryset = queryset.filter(pk=execution_id)
    if establishment_id is not None:
        queryset = queryset.filter(establishment_id=establishment_id)
    return queryset


def _due_scheduled_queryset(
    *,
    establishment_id: uuid.UUID | None = None,
    execution_id: uuid.UUID | None = None,
):
    now = timezone.now()
    queryset = ActionPlanExecution.objects.filter(
        status=EXECUTION_STATUS_SCHEDULED,
        start_at__lte=now,
    )
    return _apply_lifecycle_scope(
        queryset,
        establishment_id=establishment_id,
        execution_id=execution_id,
    )


def _due_availability_queryset(
    *,
    establishment_id: uuid.UUID | None = None,
    execution_id: uuid.UUID | None = None,
):
    now = timezone.now()
    queryset = ActionPlanExecution.objects.filter(
        status=EXECUTION_STATUS_SCHEDULED,
        availability_notified_at__isnull=True,
    ).filter(Q(visible_from__isnull=True) | Q(visible_from__lte=now))
    return _apply_lifecycle_scope(
        queryset,
        establishment_id=establishment_id,
        execution_id=execution_id,
    )


def _promote_one_execution(*, execution_id: uuid.UUID) -> bool:
    now = timezone.now()
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
    from houston.notifications.scheduling import (
        emit_action_plan_execution_availability_if_due,
        schedule_action_plan_execution_started_notification,
    )

    execution = (
        ActionPlanExecution.objects.select_for_update()
        .filter(pk=execution_id, status=EXECUTION_STATUS_SCHEDULED, start_at__lte=now)
        .first()
    )
    if execution is None:
        return False

    # Availability first while still scheduled (or if already due before start).
    emit_action_plan_execution_availability_if_due(
        execution_id=execution.id,
        actor_membership_id=None,
    )
    execution.refresh_from_db()
    if execution.status != EXECUTION_STATUS_SCHEDULED:
        return False

    execution.status = EXECUTION_STATUS_IN_PROGRESS
    execution.started_at = now
    execution.started_by_membership = None
    execution.last_activity_at = now
    execution.save(
        update_fields=[
            "status",
            "started_at",
            "started_by_membership",
            "last_activity_at",
            "updated_at",
        ]
    )

    from houston.action_plans.constants import EXECUTION_LIFECYCLE_EVENT_STARTED
    from houston.action_plans.lifecycle_events import (
        execution_transition_metadata,
        record_execution_lifecycle_event,
    )

    lifecycle_event = record_execution_lifecycle_event(
        execution=execution,
        event_type=EXECUTION_LIFECYCLE_EVENT_STARTED,
        occurred_at=now,
        actor_membership=None,
        metadata_safe=execution_transition_metadata(
            status=EXECUTION_STATUS_IN_PROGRESS,
            end_at=execution.end_at,
        ),
    )
    from houston.gamification.services import award_action_plan_execution_started_points

    award_action_plan_execution_started_points(
        execution=execution,
        lifecycle_event=lifecycle_event,
    )

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.started",
    )
    schedule_action_plan_execution_started_notification(
        execution_id=execution.id,
        actor_membership_id=None,
    )
    return True


def _promote_candidate_ids(candidate_ids: list[uuid.UUID]) -> int:
    promoted = 0
    for candidate_id in candidate_ids:
        if _promote_one_execution(execution_id=candidate_id):
            promoted += 1
    return promoted


@transaction.atomic
def promote_due_scheduled_executions(
    *,
    establishment_id: uuid.UUID | None = None,
    execution_id: uuid.UUID | None = None,
) -> int:
    """Promote scheduled → in_progress. Beat: global. Lazy: establishment and/or id."""
    candidate_ids = list(
        _due_scheduled_queryset(
            establishment_id=establishment_id,
            execution_id=execution_id,
        ).values_list("id", flat=True)[:_BEAT_PROMOTION_BATCH_LIMIT]
    )
    return _promote_candidate_ids(candidate_ids)


@transaction.atomic
def promote_due_scheduled_executions_for_schedule(*, schedule_id: uuid.UUID) -> int:
    """Promote all due scheduled executions for one schedule. Exhaustive; no Beat batch cap."""
    now = timezone.now()
    candidate_ids = list(
        ActionPlanExecution.objects.filter(
            action_plan_schedule_id=schedule_id,
            status=EXECUTION_STATUS_SCHEDULED,
            start_at__lte=now,
        ).values_list("id", flat=True)
    )
    return _promote_candidate_ids(candidate_ids)


@transaction.atomic
def emit_due_availability_notifications(
    *,
    establishment_id: uuid.UUID | None = None,
    execution_id: uuid.UUID | None = None,
) -> int:
    """Emit mise à disposition for due scheduled executions (Beat principal)."""
    from houston.notifications.scheduling import emit_action_plan_execution_availability_if_due

    candidate_ids = list(
        _due_availability_queryset(
            establishment_id=establishment_id,
            execution_id=execution_id,
        ).values_list("id", flat=True)[:_BEAT_PROMOTION_BATCH_LIMIT]
    )
    emitted = 0
    for candidate_id in candidate_ids:
        if emit_action_plan_execution_availability_if_due(
            execution_id=candidate_id,
            actor_membership_id=None,
        ):
            emitted += 1
    return emitted


def run_scheduled_execution_lifecycle_tick(
    *,
    establishment_id: uuid.UUID | None = None,
    execution_id: uuid.UUID | None = None,
) -> dict[str, int]:
    availability_count = emit_due_availability_notifications(
        establishment_id=establishment_id,
        execution_id=execution_id,
    )
    promoted_count = promote_due_scheduled_executions(
        establishment_id=establishment_id,
        execution_id=execution_id,
    )
    return {
        "availability_emitted": availability_count,
        "promoted": promoted_count,
    }


def ensure_execution_lifecycle_for_read(
    *,
    establishment_id: uuid.UUID,
    execution_id: uuid.UUID | None = None,
) -> None:
    """Lazy filet: always establishment-scoped; optional single execution id."""
    if establishment_id is None:
        raise ValueError("establishment_id is required for read-path lifecycle.")
    try:
        run_scheduled_execution_lifecycle_tick(
            establishment_id=establishment_id,
            execution_id=execution_id,
        )
    except Exception:
        logger.exception(
            "action_plan_execution_lifecycle_lazy_failed",
            extra={
                "establishment_id": str(establishment_id),
                "execution_id": str(execution_id) if execution_id else None,
            },
        )
