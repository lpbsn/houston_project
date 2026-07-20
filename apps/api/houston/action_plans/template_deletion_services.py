"""Internal services for template hard-deletion execution fate.

No public API. Future template-delete orchestrator calls these after authorization.
"""

from __future__ import annotations

import uuid

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from houston.action_plans.constants import (
    CATALOG_STATUS_INACTIVE,
    EXECUTION_STATUS_SCHEDULED,
    SCHEDULE_STATUS_ACTIVE,
    SCHEDULE_STATUS_INACTIVE,
)
from houston.action_plans.exceptions import (
    ActionPlanExecutionObservationIntegrityError,
    ActionPlanPermissionError,
    ActionPlanStateError,
    ActionPlanValidationError,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanSchedule,
)
from houston.action_plans.permissions import can_manage_action_plan
from houston.action_plans.template_deletion_policy import (
    TEMPLATE_DELETION_FATE_HARD_DELETE,
    TEMPLATE_DELETION_FATE_KEEP_DETACH,
    classify_execution_for_template_deletion,
)
from houston.comments.models import Comment
from houston.establishments.models import EstablishmentMembership
from houston.notifications.models import Notification
from houston.observations.models import Observation


def _assert_no_observations_block_hard_delete(*, execution: ActionPlanExecution) -> None:
    if Observation.objects.filter(action_plan_execution_id=execution.id).exists():
        raise ActionPlanExecutionObservationIntegrityError(execution_id=execution.id)
    if Observation.objects.filter(
        action_plan_execution_task__action_plan_execution_id=execution.id,
    ).exists():
        raise ActionPlanExecutionObservationIntegrityError(execution_id=execution.id)


def _purge_notifications_for_execution_hard_delete(
    *,
    execution: ActionPlanExecution,
    comment_ids: list[uuid.UUID],
) -> None:
    notification_filter = Q(
        subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
        subject_id=execution.id,
    )
    if comment_ids:
        notification_filter |= Q(
            subject_type=Notification.SubjectType.COMMENT,
            subject_id__in=comment_ids,
        )
    Notification.objects.filter(
        establishment_id=execution.establishment_id,
    ).filter(notification_filter).delete()


def _delete_execution_comments_respecting_parent_protect(
    *,
    execution: ActionPlanExecution,
) -> None:
    """Delete comment trees bottom-up (parent_comment is PROTECT)."""
    while True:
        leaf_ids = list(
            Comment.objects.filter(action_plan_execution_id=execution.id)
            .annotate(reply_count=Count("replies"))
            .filter(reply_count=0)
            .values_list("id", flat=True)[:500]
        )
        if not leaf_ids:
            if Comment.objects.filter(action_plan_execution_id=execution.id).exists():
                raise ActionPlanStateError(
                    "Unable to delete execution comments due to parent_comment protect cycle.",
                )
            return
        Comment.objects.filter(id__in=leaf_ids).delete()


@transaction.atomic
def hard_delete_scheduled_execution_for_template_deletion(
    *,
    execution_id: uuid.UUID,
) -> None:
    """Hard-delete one scheduled execution. Internal only — no public endpoint."""
    execution = (
        ActionPlanExecution.objects.select_for_update()
        .filter(pk=execution_id)
        .first()
    )
    if execution is None:
        raise ActionPlanValidationError("Invalid action plan execution.")

    if (
        classify_execution_for_template_deletion(status=execution.status)
        != TEMPLATE_DELETION_FATE_HARD_DELETE
    ):
        raise ActionPlanStateError(
            "Only scheduled executions can be hard-deleted during template deletion.",
        )
    if execution.status != EXECUTION_STATUS_SCHEDULED:
        raise ActionPlanStateError(
            "Only scheduled executions can be hard-deleted during template deletion.",
        )

    _assert_no_observations_block_hard_delete(execution=execution)

    comment_ids = list(
        Comment.objects.filter(action_plan_execution_id=execution.id).values_list(
            "id",
            flat=True,
        )
    )
    _purge_notifications_for_execution_hard_delete(
        execution=execution,
        comment_ids=comment_ids,
    )
    _delete_execution_comments_respecting_parent_protect(execution=execution)
    execution.delete()


@transaction.atomic
def detach_execution_from_template_for_deletion(
    *,
    execution_id: uuid.UUID,
) -> ActionPlanExecution:
    """Null template/schedule/task FKs on a keep_detach execution. Internal only."""
    execution = (
        ActionPlanExecution.objects.select_for_update()
        .filter(pk=execution_id)
        .first()
    )
    if execution is None:
        raise ActionPlanValidationError("Invalid action plan execution.")

    if (
        classify_execution_for_template_deletion(status=execution.status)
        != TEMPLATE_DELETION_FATE_KEEP_DETACH
    ):
        raise ActionPlanStateError(
            "Scheduled executions must be hard-deleted, not detached.",
        )

    ActionPlanExecutionTask.objects.filter(action_plan_execution_id=execution.id).update(
        action_plan_task=None,
    )
    execution.action_plan = None
    execution.action_plan_schedule = None
    execution.save(
        update_fields=["action_plan", "action_plan_schedule", "updated_at"],
    )
    return execution


@transaction.atomic
def stop_template_materialization_for_deletion(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
) -> ActionPlan:
    """Internal phase: lock template, stop reuse, deactivate schedules.

    Must not cancel or otherwise mutate execution statuses — scheduled rows stay
    scheduled so the template-deletion classifier can hard-delete them.

    Not a public precondition — future delete orchestrator calls this first whether
    the catalog entry is currently active or inactive.
    """
    if not can_manage_action_plan(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to manage this action plan.")
    if not action_plan.is_reusable:
        raise ActionPlanValidationError("Only reusable action plans support template deletion.")

    locked = ActionPlan.objects.select_for_update().filter(pk=action_plan.pk).first()
    if locked is None:
        raise ActionPlanValidationError("Invalid action plan.")

    # Lock all schedules for stable ordering; mark active ones inactive only.
    list(
        ActionPlanSchedule.objects.select_for_update()
        .filter(action_plan_id=locked.id)
        .order_by("id")
    )
    ActionPlanSchedule.objects.filter(
        action_plan_id=locked.id,
        status=SCHEDULE_STATUS_ACTIVE,
    ).update(status=SCHEDULE_STATUS_INACTIVE, updated_at=timezone.now())

    if locked.catalog_status != CATALOG_STATUS_INACTIVE:
        locked.catalog_status = CATALOG_STATUS_INACTIVE
        locked.save(update_fields=["catalog_status", "updated_at"])
        from houston.action_plans.realtime import schedule_action_plan_invalidation

        schedule_action_plan_invalidation(action_plan=locked, reason="action_plan.updated")

    return locked
