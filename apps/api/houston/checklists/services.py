from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time

from django.db import transaction
from django.utils import timezone

from houston.checklists.constants import (
    ACTIVE_EXECUTION_STATUSES,
    ASSIGNMENT_STATUS_ACTIVE,
    ASSIGNMENT_STATUS_INACTIVE,
    CHECKLIST_DESCRIPTION_MAX_LENGTH,
    CHECKLIST_SKIPPED_REASON_MAX_LENGTH,
    CHECKLIST_TASK_MAX_LENGTH,
    CHECKLIST_TITLE_MAX_LENGTH,
    EXECUTION_SOURCE_TEMPLATE,
    EXECUTION_STATUS_ASSIGNED,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    RECURRENCE_DAYS,
    TASK_STATUS_DONE,
    TASK_STATUS_OBSERVATION_CREATED,
    TASK_STATUS_PENDING,
    TASK_STATUS_SKIPPED,
    TEMPLATE_STATUS_ACTIVE,
    TEMPLATE_STATUS_INACTIVE,
    TERMINAL_EXECUTION_STATUSES,
    TREATED_TASK_STATUSES,
)
from houston.checklists.exceptions import (
    ChecklistConflictError,
    ChecklistPermissionError,
    ChecklistValidationError,
)
from houston.checklists.materialization import (
    VISIBLE_FROM_OFFSET,
    _create_task_execution_snapshots,
    _first_occurrence_date,
    _iter_occurrence_dates,
    _occurrence_datetimes,
    materialize_execution_from_assignment,
)
from houston.checklists.models import (
    ChecklistAssignment,
    ChecklistExecution,
    ChecklistTaskExecution,
    ChecklistTaskTemplate,
    ChecklistTemplate,
)
from houston.checklists.permissions import (
    can_cancel_checklist_execution,
    can_create_checklist_assignment,
    can_create_registered_template,
    can_delete_registered_template,
    can_execute_checklist_tasks,
    can_launch_checklist_execution_for_assignee,
    can_launch_template_execution,
    can_manage_checklist_assignment,
    can_manage_registered_template,
    membership_covers_checklist_business_unit,
)
from houston.checklists.selectors import (
    get_active_execution_for_template,
    get_in_progress_execution_for_assignment,
)
from houston.establishments.membership_scope import (
    membership_covers_business_unit_including_admins,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.timezone_utils import establishment_local_date, establishment_timezone
from houston.observations.exceptions import ObservationValidationError
from houston.observations.models import Observation
from houston.observations.services import submit_observation


def _require_manage_template(
    *,
    actor: EstablishmentMembership,
    template: ChecklistTemplate,
    action: str = "manage this checklist template",
) -> None:
    if not can_manage_registered_template(actor, template):
        raise ChecklistPermissionError(f"Not allowed to {action}.")


def touch_checklist_execution_activity(*, execution: ChecklistExecution, at=None) -> None:
    execution.last_activity_at = at or timezone.now()
    execution.save(update_fields=["last_activity_at", "updated_at"])


def _normalize_title(title: str) -> str:
    normalized = (title or "").strip()
    if not normalized:
        raise ChecklistValidationError("Title is required.")
    if len(normalized) > CHECKLIST_TITLE_MAX_LENGTH:
        raise ChecklistValidationError("Title is too long.")
    return normalized


def _normalize_description(description: str) -> str:
    normalized = (description or "").strip()
    if len(normalized) > CHECKLIST_DESCRIPTION_MAX_LENGTH:
        raise ChecklistValidationError("Description is too long.")
    return normalized


def _normalize_task(task: str) -> str:
    normalized = (task or "").strip()
    if not normalized:
        raise ChecklistValidationError("Task is required.")
    if len(normalized) > CHECKLIST_TASK_MAX_LENGTH:
        raise ChecklistValidationError("Task is too long.")
    return normalized


def _normalize_skipped_reason(skipped_reason: str | None) -> str | None:
    if skipped_reason is None:
        return None
    normalized = skipped_reason.strip()
    if not normalized:
        return None
    if len(normalized) > CHECKLIST_SKIPPED_REASON_MAX_LENGTH:
        raise ChecklistValidationError("Skipped reason is too long.")
    return normalized


def _validate_membership_in_establishment(
    *,
    establishment_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> EstablishmentMembership:
    membership = EstablishmentMembership.objects.filter(
        id=membership_id,
        establishment_id=establishment_id,
        status=EstablishmentMembership.Status.ACTIVE,
    ).first()
    if membership is None:
        raise ChecklistValidationError("Invalid establishment membership.")
    return membership


_ASSIGNEE_OUT_OF_SCOPE_MESSAGE = (
    "Cet utilisateur n'est pas rattaché au périmètre de cette checklist."
)


def _validate_assignee_covers_business_unit(
    *,
    assigned_to: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> None:
    if not membership_covers_business_unit_including_admins(assigned_to, business_unit):
        raise ChecklistValidationError(_ASSIGNEE_OUT_OF_SCOPE_MESSAGE)


def _validate_business_unit_in_establishment(
    *,
    establishment_id: uuid.UUID,
    business_unit_id: uuid.UUID,
) -> BusinessUnit:
    business_unit = BusinessUnit.objects.filter(
        id=business_unit_id,
        establishment_id=establishment_id,
        active=True,
    ).first()
    if business_unit is None:
        raise ChecklistValidationError("Invalid business unit.")
    return business_unit


def _validate_template_establishment(
    *,
    template: ChecklistTemplate,
    establishment_id: uuid.UUID,
) -> None:
    if template.establishment_id != establishment_id:
        raise ChecklistValidationError("Template does not belong to this establishment.")


def _template_has_tasks(template: ChecklistTemplate) -> bool:
    return template.task_templates.exists()


def _validate_active_template_has_tasks(template: ChecklistTemplate) -> None:
    if not _template_has_tasks(template):
        raise ChecklistValidationError("Checklist template must have at least one task.")


def _validate_assignment_schedule(
    *,
    start_date: date,
    end_date: date,
    start_at: time,
    end_at: time,
) -> None:
    if end_date < start_date:
        raise ChecklistValidationError("end_date must be on or after start_date.")
    if end_at <= start_at:
        raise ChecklistValidationError(
            "end_at must be after start_at on the same day (overnight slots are not supported).",
        )


def normalize_recurrence_days(recurrence_days) -> list[str]:
    if recurrence_days is None:
        return []
    if not isinstance(recurrence_days, list):
        raise ChecklistValidationError("recurrence_days must be a list.")
    normalized: list[str] = []
    seen: set[str] = set()
    for day in recurrence_days:
        if not isinstance(day, str):
            raise ChecklistValidationError("recurrence_days must contain weekday strings.")
        day_value = day.strip().lower()
        if day_value not in RECURRENCE_DAYS:
            raise ChecklistValidationError(f"Invalid recurrence day: {day}")
        if day_value in seen:
            continue
        seen.add(day_value)
        normalized.append(day_value)
    return normalized


def _maybe_deactivate_template_without_tasks(template: ChecklistTemplate) -> ChecklistTemplate:
    if template.status == TEMPLATE_STATUS_ACTIVE and not _template_has_tasks(template):
        template.status = TEMPLATE_STATUS_INACTIVE
        template.save(update_fields=["status", "updated_at"])
    return template


def _normalize_task_input(task_item: dict, *, index: int) -> str:
    if not isinstance(task_item, dict):
        raise ChecklistValidationError("Each task must be an object.")
    task_text = task_item.get("task") or task_item.get("title")
    if task_text is None:
        raise ChecklistValidationError(f"Task at index {index} requires task or title.")
    return _normalize_task(str(task_text))


def _activate_template_if_has_tasks(template: ChecklistTemplate) -> ChecklistTemplate:
    if template.status != TEMPLATE_STATUS_ACTIVE and _template_has_tasks(template):
        template.status = TEMPLATE_STATUS_ACTIVE
        template.save(update_fields=["status", "updated_at"])
    return template


def _schedule_checklist_invalidation(*, template: ChecklistTemplate | None) -> None:
    if template is None:
        return

    from houston.realtime.broadcast import schedule_establishment_invalidation

    schedule_establishment_invalidation(
        establishment_id=template.establishment_id,
        subject_type="checklist",
        reason="checklist.updated",
        entity_id=template.id,
    )


def _schedule_execution_invalidation(*, execution: ChecklistExecution, reason: str) -> None:
    from houston.realtime.broadcast import schedule_establishment_invalidation

    schedule_establishment_invalidation(
        establishment_id=execution.establishment_id,
        subject_type="execution",
        reason=reason,
        entity_id=execution.id,
    )


def _schedule_execution_canceled_notifications(
    *,
    execution_ids: list[uuid.UUID],
    actor_membership_id: uuid.UUID,
) -> None:
    from houston.notifications.scheduling import schedule_checklist_execution_canceled_notification

    for execution_id in execution_ids:
        schedule_checklist_execution_canceled_notification(
            execution_id=execution_id,
            actor_membership_id=actor_membership_id,
        )


@transaction.atomic
def create_checklist_template(
    *,
    establishment_id: uuid.UUID,
    actor: EstablishmentMembership,
    title: str,
    description: str = "",
    business_unit_id: uuid.UUID,
    _emit_invalidation: bool = True,
) -> ChecklistTemplate:
    if not can_create_registered_template(actor):
        raise ChecklistPermissionError("Not allowed to create a checklist template.")
    if business_unit_id is None:
        raise ChecklistValidationError("business_unit is required.")
    business_unit = _validate_business_unit_in_establishment(
        establishment_id=establishment_id,
        business_unit_id=business_unit_id,
    )
    if (
        actor.role == EstablishmentMembership.Role.MANAGER
        and not membership_covers_checklist_business_unit(actor, business_unit)
    ):
        raise ChecklistPermissionError("Not allowed to create a checklist template.")

    template = ChecklistTemplate.objects.create(
        establishment_id=establishment_id,
        created_by=actor,
        business_unit=business_unit,
        title=_normalize_title(title),
        description=_normalize_description(description),
        status=TEMPLATE_STATUS_INACTIVE,
    )
    if _emit_invalidation:
        _schedule_checklist_invalidation(template=template)
    return template


@transaction.atomic
def update_checklist_template(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
    title: str | None = None,
    description: str | None = None,
) -> ChecklistTemplate:
    _require_manage_template(
        actor=actor,
        template=template,
        action="update this checklist template",
    )

    update_fields = ["updated_at"]
    if title is not None:
        template.title = _normalize_title(title)
        update_fields.append("title")
    if description is not None:
        template.description = _normalize_description(description)
        update_fields.append("description")
    template.save(update_fields=update_fields)
    _schedule_checklist_invalidation(template=template)
    return template


@transaction.atomic
def add_task_template(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
    task: str,
    position: int | None = None,
) -> ChecklistTaskTemplate:
    _require_manage_template(actor=actor, template=template)

    if position is None:
        last = (
            template.task_templates.order_by("-position").values_list("position", flat=True).first()
        )
        position = (last or 0) + 1

    task_template = ChecklistTaskTemplate.objects.create(
        checklist_template=template,
        task=_normalize_task(task),
        position=position,
    )
    _activate_template_if_has_tasks(template)
    _schedule_checklist_invalidation(template=template)
    return task_template


@transaction.atomic
def update_task_template(
    *,
    task_template: ChecklistTaskTemplate,
    actor: EstablishmentMembership,
    task: str | None = None,
    position: int | None = None,
) -> ChecklistTaskTemplate:
    template = task_template.checklist_template
    _require_manage_template(actor=actor, template=template)

    update_fields = ["updated_at"]
    if task is not None:
        task_template.task = _normalize_task(task)
        update_fields.append("task")
    if position is not None:
        task_template.position = position
        update_fields.append("position")
    task_template.save(update_fields=update_fields)
    _schedule_checklist_invalidation(template=template)
    return task_template


@transaction.atomic
def delete_task_template(
    *,
    task_template: ChecklistTaskTemplate,
    actor: EstablishmentMembership,
) -> None:
    template = task_template.checklist_template
    _require_manage_template(actor=actor, template=template)

    task_template.delete()
    _maybe_deactivate_template_without_tasks(template)
    _schedule_checklist_invalidation(template=template)


@transaction.atomic
def reorder_task_templates(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
    ordered_task_template_ids: list[uuid.UUID],
) -> list[ChecklistTaskTemplate]:
    _require_manage_template(actor=actor, template=template)

    task_templates = list(template.task_templates.order_by("position", "created_at"))
    existing_ids = {task.id for task in task_templates}
    if set(ordered_task_template_ids) != existing_ids:
        raise ChecklistValidationError("Reorder payload must include every task exactly once.")

    by_id = {task.id: task for task in task_templates}
    temp_offset = len(task_templates) + 1
    for index, task_id in enumerate(ordered_task_template_ids):
        task = by_id[task_id]
        task.position = temp_offset + index
        task.save(update_fields=["position", "updated_at"])

    for position, task_id in enumerate(ordered_task_template_ids, start=1):
        task = by_id[task_id]
        task.position = position
        task.save(update_fields=["position", "updated_at"])

    reordered = list(template.task_templates.order_by("position", "created_at"))
    _schedule_checklist_invalidation(template=template)
    return reordered


@transaction.atomic
def activate_checklist_template(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
) -> ChecklistTemplate:
    _require_manage_template(
        actor=actor,
        template=template,
        action="activate this checklist template",
    )

    _validate_active_template_has_tasks(template)
    template.status = TEMPLATE_STATUS_ACTIVE
    template.save(update_fields=["status", "updated_at"])
    _schedule_checklist_invalidation(template=template)
    return template


@transaction.atomic
def deactivate_checklist_template(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
) -> ChecklistTemplate:
    _require_manage_template(
        actor=actor,
        template=template,
        action="deactivate this checklist template",
    )

    template.status = TEMPLATE_STATUS_INACTIVE
    template.save(update_fields=["status", "updated_at"])
    _schedule_checklist_invalidation(template=template)
    return template


_DELETE_ACTIVE_EXECUTION_MESSAGE = (
    "Cette checklist est en cours d'exécution. "
    "Terminez ou annulez l'exécution avant de la supprimer."
)
_ASSIGNMENT_INACTIVE_PATCH_MESSAGE = (
    "Cette affectation a été retirée et ne peut plus être modifiée."
)
_REMOVE_ASSIGNMENT_IN_PROGRESS_MESSAGE = (
    "Cette affectation a une exécution en cours. "
    "Terminez ou annulez cette exécution avant de retirer l'affectation."
)


@transaction.atomic
def delete_checklist_template(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
) -> None:
    if not can_delete_registered_template(actor, template):
        raise ChecklistPermissionError("Not allowed to delete this checklist template.")
    _schedule_checklist_invalidation(template=template)
    _delete_registered_checklist_template(template=template)


def _detach_terminal_executions(*, template: ChecklistTemplate) -> None:
    template.executions.filter(status__in=TERMINAL_EXECUTION_STATUSES).update(
        checklist_template=None,
    )


def _delete_registered_checklist_template(*, template: ChecklistTemplate) -> None:
    active_execution = get_active_execution_for_template(template=template)
    if active_execution is not None:
        raise ChecklistConflictError(
            _DELETE_ACTIVE_EXECUTION_MESSAGE,
            active_execution_id=active_execution.id,
        )

    _detach_terminal_executions(template=template)
    template.assignments.update(status=ASSIGNMENT_STATUS_INACTIVE)
    template.assignments.filter(executions__isnull=True).delete()
    template.delete()


@transaction.atomic
def create_checklist_assignment(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
    assigned_to_id: uuid.UUID,
    start_date: date,
    end_date: date,
    start_at: time,
    end_at: time,
    recurrence_days=None,
) -> ChecklistAssignment:
    if not can_create_checklist_assignment(actor, template):
        raise ChecklistPermissionError("Not allowed to create a checklist assignment.")

    if template.status != TEMPLATE_STATUS_ACTIVE:
        raise ChecklistValidationError("Template must be active.")
    _validate_active_template_has_tasks(template)

    assigned_to = _validate_membership_in_establishment(
        establishment_id=template.establishment_id,
        membership_id=assigned_to_id,
    )
    business_unit = _validate_business_unit_in_establishment(
        establishment_id=template.establishment_id,
        business_unit_id=template.business_unit_id,
    )
    _validate_assignee_covers_business_unit(
        assigned_to=assigned_to,
        business_unit=business_unit,
    )
    _validate_assignment_schedule(
        start_date=start_date,
        end_date=end_date,
        start_at=start_at,
        end_at=end_at,
    )
    normalized_recurrence_days = normalize_recurrence_days(recurrence_days)

    assignment = ChecklistAssignment.objects.create(
        checklist_template=template,
        establishment_id=template.establishment_id,
        assigned_to=assigned_to,
        assigned_by=actor,
        business_unit_id=template.business_unit_id,
        start_date=start_date,
        end_date=end_date,
        start_at=start_at,
        end_at=end_at,
        recurrence_days=normalized_recurrence_days,
        status=ASSIGNMENT_STATUS_ACTIVE,
    )

    first_occurrence_date = _first_occurrence_date(assignment)
    materialize_execution_from_assignment(
        assignment=assignment,
        occurrence_date=first_occurrence_date,
    )
    assignment.last_materialized_at = timezone.now()
    assignment.save(update_fields=["last_materialized_at", "updated_at"])
    _schedule_checklist_invalidation(template=template)
    return assignment


def _execution_still_matches_assignment_schedule(
    *,
    execution: ChecklistExecution,
    assignment: ChecklistAssignment,
) -> bool:
    if execution.occurrence_date is None:
        return False
    return execution.occurrence_date in _iter_occurrence_dates(
        assignment=assignment,
        from_date=execution.occurrence_date,
        until_date=execution.occurrence_date,
    )


def _cancel_assigned_executions_outside_assignment_schedule(
    *,
    assignment: ChecklistAssignment,
) -> list[ChecklistExecution]:
    now = timezone.now()
    assigned_executions = list(
        assignment.executions.filter(status=EXECUTION_STATUS_ASSIGNED).only(
            "id",
            "establishment_id",
            "occurrence_date",
        ),
    )
    executions_to_cancel = [
        execution
        for execution in assigned_executions
        if not _execution_still_matches_assignment_schedule(
            execution=execution,
            assignment=assignment,
        )
    ]
    if not executions_to_cancel:
        return []

    ChecklistExecution.objects.filter(
        id__in=[execution.id for execution in executions_to_cancel],
    ).update(
        status=EXECUTION_STATUS_CANCELED,
        canceled_at=now,
        last_activity_at=now,
        updated_at=now,
    )
    return executions_to_cancel


def _sync_assigned_executions_from_assignment(
    *,
    assignment: ChecklistAssignment,
) -> int:
    now = timezone.now()
    assigned_executions = list(
        assignment.executions.filter(status=EXECUTION_STATUS_ASSIGNED).only(
            "id",
            "occurrence_date",
        ),
    )
    if not assigned_executions:
        return 0

    to_sync: list[ChecklistExecution] = []
    for execution in assigned_executions:
        if execution.occurrence_date is None:
            continue
        if not _execution_still_matches_assignment_schedule(
            execution=execution,
            assignment=assignment,
        ):
            continue
        occurrence_start_at, occurrence_end_at = _occurrence_datetimes(
            assignment=assignment,
            occurrence_date=execution.occurrence_date,
        )
        execution.assigned_to = assignment.assigned_to
        execution.start_at = occurrence_start_at
        execution.end_at = occurrence_end_at
        execution.visible_from = occurrence_start_at - VISIBLE_FROM_OFFSET
        execution.last_activity_at = now
        execution.updated_at = now
        to_sync.append(execution)

    if not to_sync:
        return 0

    ChecklistExecution.objects.bulk_update(
        to_sync,
        [
            "assigned_to",
            "start_at",
            "end_at",
            "visible_from",
            "last_activity_at",
            "updated_at",
        ],
    )
    return len(to_sync)


@transaction.atomic
def update_checklist_assignment(
    *,
    assignment: ChecklistAssignment,
    actor: EstablishmentMembership,
    assigned_to_id: uuid.UUID | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    start_at: time | None = None,
    end_at: time | None = None,
    recurrence_days=None,
) -> ChecklistAssignment:
    if not can_manage_checklist_assignment(actor, assignment):
        raise ChecklistPermissionError("Not allowed to update this checklist assignment.")
    if assignment.status != ASSIGNMENT_STATUS_ACTIVE:
        raise ChecklistValidationError(_ASSIGNMENT_INACTIVE_PATCH_MESSAGE)

    update_fields = ["updated_at"]
    if assigned_to_id is not None and assigned_to_id != assignment.assigned_to_id:
        assigned_to = _validate_membership_in_establishment(
            establishment_id=assignment.establishment_id,
            membership_id=assigned_to_id,
        )
        business_unit = _validate_business_unit_in_establishment(
            establishment_id=assignment.establishment_id,
            business_unit_id=assignment.business_unit_id,
        )
        _validate_assignee_covers_business_unit(
            assigned_to=assigned_to,
            business_unit=business_unit,
        )
        assignment.assigned_to = assigned_to
        update_fields.append("assigned_to")

    next_start_date = start_date if start_date is not None else assignment.start_date
    next_end_date = end_date if end_date is not None else assignment.end_date
    next_start_at = start_at if start_at is not None else assignment.start_at
    next_end_at = end_at if end_at is not None else assignment.end_at
    _validate_assignment_schedule(
        start_date=next_start_date,
        end_date=next_end_date,
        start_at=next_start_at,
        end_at=next_end_at,
    )
    if start_date is not None:
        assignment.start_date = start_date
        update_fields.append("start_date")
    if end_date is not None:
        assignment.end_date = end_date
        update_fields.append("end_date")
    if start_at is not None:
        assignment.start_at = start_at
        update_fields.append("start_at")
    if end_at is not None:
        assignment.end_at = end_at
        update_fields.append("end_at")

    if recurrence_days is not None:
        assignment.recurrence_days = normalize_recurrence_days(recurrence_days)
        update_fields.append("recurrence_days")

    assignment.save(update_fields=update_fields)
    cancelled_executions = _cancel_assigned_executions_outside_assignment_schedule(
        assignment=assignment,
    )
    for execution in cancelled_executions:
        _schedule_execution_invalidation(execution=execution, reason="execution.updated")
    _schedule_execution_canceled_notifications(
        execution_ids=[execution.id for execution in cancelled_executions],
        actor_membership_id=actor.id,
    )
    _sync_assigned_executions_from_assignment(assignment=assignment)
    _schedule_checklist_invalidation(template=assignment.checklist_template)
    return assignment


@transaction.atomic
def deactivate_checklist_assignment(
    *,
    assignment: ChecklistAssignment,
    actor: EstablishmentMembership,
) -> ChecklistAssignment | None:
    if not can_manage_checklist_assignment(actor, assignment):
        raise ChecklistPermissionError("Not allowed to deactivate this checklist assignment.")

    in_progress = get_in_progress_execution_for_assignment(assignment=assignment)
    if in_progress is not None:
        raise ChecklistConflictError(
            _REMOVE_ASSIGNMENT_IN_PROGRESS_MESSAGE,
            active_execution_id=in_progress.id,
        )

    template = assignment.checklist_template
    if not assignment.executions.exists():
        assignment.delete()
        _schedule_checklist_invalidation(template=template)
        return None

    now = timezone.now()
    executions_to_cancel = list(
        assignment.executions.filter(status=EXECUTION_STATUS_ASSIGNED).only(
            "id",
            "establishment_id",
        ),
    )
    if executions_to_cancel:
        ChecklistExecution.objects.filter(
            id__in=[execution.id for execution in executions_to_cancel],
        ).update(
            status=EXECUTION_STATUS_CANCELED,
            canceled_at=now,
            last_activity_at=now,
        )
        for execution in executions_to_cancel:
            _schedule_execution_invalidation(execution=execution, reason="execution.updated")
        _schedule_execution_canceled_notifications(
            execution_ids=[execution.id for execution in executions_to_cancel],
            actor_membership_id=actor.id,
        )

    assignment.status = ASSIGNMENT_STATUS_INACTIVE
    assignment.save(update_fields=["status", "updated_at"])
    _schedule_checklist_invalidation(template=template)
    return assignment


@dataclass(frozen=True)
class ChecklistTemplateScheduleResult:
    result_type: str
    execution: ChecklistExecution | None = None
    assignment: ChecklistAssignment | None = None


@transaction.atomic
def schedule_checklist_from_template(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
    assigned_to_id: uuid.UUID | None = None,
    start_date: date | None = None,
    start_at: time,
    end_at: time,
    recurrence_days=None,
    recurrence_end_date: date | None = None,
) -> ChecklistTemplateScheduleResult:
    schedule_date = start_date or establishment_local_date(establishment=template.establishment)
    normalized_recurrence_days = normalize_recurrence_days(recurrence_days)

    if normalized_recurrence_days:
        if recurrence_end_date is None:
            raise ChecklistValidationError(
                "recurrence_end_date is required for a recurring schedule.",
            )
        _validate_assignment_schedule(
            start_date=schedule_date,
            end_date=recurrence_end_date,
            start_at=start_at,
            end_at=end_at,
        )
        effective_assigned_to_id = assigned_to_id or actor.id
        assignment = create_checklist_assignment(
            template=template,
            actor=actor,
            assigned_to_id=effective_assigned_to_id,
            start_date=schedule_date,
            end_date=recurrence_end_date,
            start_at=start_at,
            end_at=end_at,
            recurrence_days=normalized_recurrence_days,
        )
        return ChecklistTemplateScheduleResult(
            result_type="assignment",
            assignment=assignment,
        )

    _validate_assignment_schedule(
        start_date=schedule_date,
        end_date=schedule_date,
        start_at=start_at,
        end_at=end_at,
    )
    tz = establishment_timezone(template.establishment)
    occurrence_start_at = datetime.combine(schedule_date, start_at, tzinfo=tz)
    occurrence_end_at = datetime.combine(schedule_date, end_at, tzinfo=tz)
    execution = create_execution_from_template(
        template=template,
        actor=actor,
        assigned_to_id=assigned_to_id,
        start_at=occurrence_start_at,
        end_at=occurrence_end_at,
    )
    return ChecklistTemplateScheduleResult(
        result_type="execution",
        execution=execution,
    )


@transaction.atomic
def create_execution_from_template(
    *,
    template: ChecklistTemplate,
    actor: EstablishmentMembership,
    assigned_to_id: uuid.UUID | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
) -> ChecklistExecution:
    if not can_launch_template_execution(actor, template):
        raise ChecklistPermissionError("Not allowed to create a checklist execution.")

    if template.status != TEMPLATE_STATUS_ACTIVE:
        raise ChecklistValidationError("Template must be active.")
    _validate_active_template_has_tasks(template)

    ChecklistTemplate.objects.select_for_update().get(pk=template.pk)

    if assigned_to_id is None:
        assigned_to = actor
    else:
        assigned_to = _validate_membership_in_establishment(
            establishment_id=template.establishment_id,
            membership_id=assigned_to_id,
        )
    _validate_assignee_covers_business_unit(
        assigned_to=assigned_to,
        business_unit=template.business_unit,
    )
    if not can_launch_checklist_execution_for_assignee(actor, template, assigned_to):
        raise ChecklistPermissionError("Not allowed to create a checklist execution.")

    now = timezone.now()
    visible_from = start_at - VISIBLE_FROM_OFFSET if start_at is not None else None
    execution = ChecklistExecution.objects.create(
        checklist_template=template,
        checklist_assignment=None,
        execution_source=EXECUTION_SOURCE_TEMPLATE,
        establishment_id=template.establishment_id,
        assigned_to=assigned_to,
        assigned_by=actor if assigned_to.id != actor.id else None,
        business_unit=template.business_unit,
        template_title=template.title,
        template_description=template.description,
        start_at=start_at,
        visible_from=visible_from,
        end_at=end_at,
        occurrence_date=None,
        status=EXECUTION_STATUS_ASSIGNED,
        last_activity_at=now,
    )
    _create_task_execution_snapshots(execution=execution, template=template)
    _schedule_execution_invalidation(execution=execution, reason="execution.created")
    from houston.notifications.scheduling import schedule_checklist_execution_created_notification

    schedule_checklist_execution_created_notification(
        execution_id=execution.id,
        actor_membership_id=actor.id,
    )
    return execution


@transaction.atomic
def create_registered_checklist_template(
    *,
    establishment_id: uuid.UUID,
    actor: EstablishmentMembership,
    title: str,
    description: str = "",
    business_unit_id: uuid.UUID,
    tasks: list[dict],
    assign_now: bool = False,
    assigned_to_id: uuid.UUID | None = None,
    end_at: datetime | None = None,
) -> tuple[ChecklistTemplate, ChecklistExecution | None]:
    template = create_checklist_template(
        establishment_id=establishment_id,
        actor=actor,
        title=title,
        description=description,
        business_unit_id=business_unit_id,
        _emit_invalidation=False,
    )

    for index, task_item in enumerate(tasks, start=1):
        ChecklistTaskTemplate.objects.create(
            checklist_template=template,
            task=_normalize_task_input(task_item, index=index),
            position=index,
        )

    template.status = TEMPLATE_STATUS_ACTIVE
    template.save(update_fields=["status", "updated_at"])

    execution = None
    if assign_now:
        if assigned_to_id is None:
            raise ChecklistValidationError("assigned_to is required when assign_now is true.")
        execution = create_execution_from_template(
            template=template,
            actor=actor,
            assigned_to_id=assigned_to_id,
            end_at=end_at,
        )
    _schedule_checklist_invalidation(template=template)
    return template, execution


@transaction.atomic
def cancel_checklist_execution(
    *,
    execution: ChecklistExecution,
    actor: EstablishmentMembership,
) -> ChecklistExecution:
    if not can_cancel_checklist_execution(actor, execution):
        raise ChecklistPermissionError("Not allowed to cancel this checklist execution.")

    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ChecklistValidationError(
            "Checklist execution cannot be canceled in its current state.",
        )

    now = timezone.now()
    execution.status = EXECUTION_STATUS_CANCELED
    execution.canceled_at = now
    execution.last_activity_at = now
    execution.save(
        update_fields=["status", "canceled_at", "last_activity_at", "updated_at"],
    )
    _schedule_execution_invalidation(execution=execution, reason="execution.updated")
    from houston.notifications.scheduling import schedule_checklist_execution_canceled_notification

    schedule_checklist_execution_canceled_notification(
        execution_id=execution.id,
        actor_membership_id=actor.id,
    )
    return execution


def _maybe_start_execution(*, execution: ChecklistExecution, at: datetime) -> ChecklistExecution:
    if execution.status != EXECUTION_STATUS_ASSIGNED:
        return execution
    execution.status = EXECUTION_STATUS_IN_PROGRESS
    execution.started_at = at
    execution.last_activity_at = at
    execution.save(
        update_fields=["status", "started_at", "last_activity_at", "updated_at"],
    )
    return execution


def _maybe_complete_execution(*, execution: ChecklistExecution, at: datetime) -> ChecklistExecution:
    pending_exists = execution.task_executions.exclude(status__in=TREATED_TASK_STATUSES).exists()
    if pending_exists:
        return execution
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        return execution

    execution.status = EXECUTION_STATUS_DONE
    execution.done_at = at
    execution.last_activity_at = at
    execution.save(
        update_fields=["status", "done_at", "last_activity_at", "updated_at"],
    )
    return execution


@transaction.atomic
def mark_task_done(
    *,
    task_execution: ChecklistTaskExecution,
    actor: EstablishmentMembership,
) -> ChecklistTaskExecution:
    execution = task_execution.checklist_execution
    if not can_execute_checklist_tasks(actor, execution):
        raise ChecklistPermissionError("Not allowed to execute this checklist task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ChecklistValidationError("Checklist execution is not active.")
    if task_execution.status != TASK_STATUS_PENDING:
        raise ChecklistValidationError("Task cannot be marked done in its current state.")

    now = timezone.now()
    _maybe_start_execution(execution=execution, at=now)
    task_execution.status = TASK_STATUS_DONE
    task_execution.completed_at = now
    task_execution.save(update_fields=["status", "completed_at", "updated_at"])
    touch_checklist_execution_activity(execution=execution, at=now)
    _maybe_complete_execution(execution=execution, at=now)
    _schedule_execution_invalidation(execution=execution, reason="execution.updated")
    return task_execution


@transaction.atomic
def skip_task(
    *,
    task_execution: ChecklistTaskExecution,
    actor: EstablishmentMembership,
    skipped_reason: str | None = None,
) -> ChecklistTaskExecution:
    execution = task_execution.checklist_execution
    if not can_execute_checklist_tasks(actor, execution):
        raise ChecklistPermissionError("Not allowed to execute this checklist task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ChecklistValidationError("Checklist execution is not active.")
    if task_execution.status != TASK_STATUS_PENDING:
        raise ChecklistValidationError("Task cannot be skipped in its current state.")

    now = timezone.now()
    _maybe_start_execution(execution=execution, at=now)
    task_execution.status = TASK_STATUS_SKIPPED
    task_execution.skipped_reason = _normalize_skipped_reason(skipped_reason)
    task_execution.skipped_at = now
    task_execution.save(
        update_fields=["status", "skipped_reason", "skipped_at", "updated_at"],
    )
    touch_checklist_execution_activity(execution=execution, at=now)
    _maybe_complete_execution(execution=execution, at=now)
    _schedule_execution_invalidation(execution=execution, reason="execution.updated")
    return task_execution


@transaction.atomic
def record_task_observation_created(
    *,
    task_execution: ChecklistTaskExecution,
    actor: EstablishmentMembership,
    observation,
) -> ChecklistTaskExecution:
    """Internal transition used by Observation handoff (LOT 3 / CL-07)."""
    execution = task_execution.checklist_execution
    if not can_execute_checklist_tasks(actor, execution):
        raise ChecklistPermissionError("Not allowed to execute this checklist task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ChecklistValidationError("Checklist execution is not active.")
    if task_execution.status != TASK_STATUS_PENDING:
        raise ChecklistValidationError("Task cannot create an observation in its current state.")

    now = timezone.now()
    _maybe_start_execution(execution=execution, at=now)
    task_execution.status = TASK_STATUS_OBSERVATION_CREATED
    task_execution.observation = observation
    task_execution.observation_created_at = now
    task_execution.save(
        update_fields=["status", "observation", "observation_created_at", "updated_at"],
    )
    touch_checklist_execution_activity(execution=execution, at=now)
    _maybe_complete_execution(execution=execution, at=now)
    _schedule_execution_invalidation(execution=execution, reason="execution.updated")
    return task_execution


@transaction.atomic
def create_observation_from_task(
    *,
    task_execution: ChecklistTaskExecution,
    actor: EstablishmentMembership,
    text: str,
    temporary_upload_ids: list[uuid.UUID] | None = None,
) -> ChecklistTaskExecution:
    execution = task_execution.checklist_execution
    if not can_execute_checklist_tasks(actor, execution):
        raise ChecklistPermissionError("Not allowed to execute this checklist task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ChecklistValidationError("Checklist execution is not active.")
    if task_execution.status != TASK_STATUS_PENDING:
        raise ChecklistValidationError("Task cannot create an observation in its current state.")

    try:
        observation = submit_observation(
            membership=actor,
            text=text,
            temporary_upload_ids=temporary_upload_ids or [],
            origin=Observation.Origin.CHECKLIST_TASK,
            checklist_execution=execution,
            checklist_task_execution=task_execution,
        )
    except ObservationValidationError as exc:
        raise ChecklistValidationError(str(exc)) from exc

    return record_task_observation_created(
        task_execution=task_execution,
        actor=actor,
        observation=observation,
    )
