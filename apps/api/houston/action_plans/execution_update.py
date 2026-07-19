from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from houston.action_plans.constants import (
    MAX_TASK_POSITION,
    MAX_TASKS_PER_PLAN,
    MIN_TASK_POSITION,
    TASK_STATUS_PENDING,
    TERMINAL_TASK_STATUSES,
)
from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanStaleExecutionError,
    ActionPlanStateError,
    ActionPlanValidationError,
)
from houston.action_plans.models import (
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
)
from houston.action_plans.permissions import (
    can_assign_to_execution_business_unit,
    can_create_staff_feed_execution_plan,
    can_define_cross_pole_task,
    can_update_action_plan_execution,
    manages_business_unit,
)
from houston.action_plans.services import (
    ValidatedAssigneePayload,
    _lock_all_execution_tasks_after_execution,
    _lock_execution_for_write,
    _membership_display_name,
    _normalize_description,
    _normalize_task_description,
    _normalize_task_text,
    _normalize_title,
    _validate_assignee_covers_business_unit,
    _validate_business_unit_in_establishment,
    _validate_membership_in_establishment,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.observations.models import Observation


def _get_or_create_execution_teams(
    *,
    execution: ActionPlanExecution,
    pilot_business_unit: BusinessUnit,
    business_unit_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ActionPlanExecutionTeam]:
    teams_by_bu_id: dict[uuid.UUID, ActionPlanExecutionTeam] = {
        team.business_unit_id: team
        for team in ActionPlanExecutionTeam.objects.filter(
            action_plan_execution_id=execution.id,
            business_unit_id__in=business_unit_ids,
        )
    }
    for business_unit_id in sorted(business_unit_ids, key=str):
        if business_unit_id in teams_by_bu_id:
            continue
        teams_by_bu_id[business_unit_id] = ActionPlanExecutionTeam.objects.create(
            action_plan_execution=execution,
            business_unit_id=business_unit_id,
            is_pilot=business_unit_id == pilot_business_unit.id,
        )
    return teams_by_bu_id


@dataclass
class ExecutionUpdateDiff:
    title_changed: bool = False
    description_changed: bool = False
    requires_validation_changed: bool = False
    end_at_changed: bool = False
    added_assignee_ids: set[uuid.UUID] = field(default_factory=set)
    removed_assignee_ids: set[uuid.UUID] = field(default_factory=set)
    individual_end_changed_ids: set[uuid.UUID] = field(default_factory=set)
    pending_structure_changed: bool = False
    newly_assigned_task_membership_ids: set[uuid.UUID] = field(default_factory=set)
    reassigned_from_membership_ids: set[uuid.UUID] = field(default_factory=set)
    reassigned_to_membership_ids: set[uuid.UUID] = field(default_factory=set)
    unassigned_from_membership_ids: set[uuid.UUID] = field(default_factory=set)
    deadline_changed_membership_ids: set[uuid.UUID] = field(default_factory=set)


def _assert_end_after_start(
    *,
    start_at: datetime | None,
    end_at: datetime | None,
) -> None:
    if end_at is None:
        return
    if start_at is None:
        raise ActionPlanValidationError(
            "End datetime requires a start datetime."
        )
    if end_at <= start_at:
        raise ActionPlanValidationError(
            "End datetime must be after start datetime."
        )


def _manager_can_manage_bu(
    actor: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> bool:
    if actor.role in ADMIN_ROLES:
        return True
    return manages_business_unit(actor, business_unit)


def _pending_task_fields_equal(
    existing: ActionPlanExecutionTask,
    *,
    task: str,
    description: str,
    business_unit_id: uuid.UUID,
    position: int,
    deadline_at: datetime | None,
    assigned_membership_id: uuid.UUID | None,
) -> bool:
    return (
        existing.task == task
        and existing.description == description
        and existing.execution_team.business_unit_id == business_unit_id
        and existing.position == position
        and existing.deadline_at == deadline_at
        and existing.assigned_membership_id == assigned_membership_id
    )


def _assert_actor_may_mutate_pending_pole(
    *,
    actor: EstablishmentMembership,
    execution: ActionPlanExecution,
    business_unit: BusinessUnit,
) -> None:
    if actor.role in ADMIN_ROLES:
        return
    if business_unit.id == execution.pilot_business_unit_id:
        return
    if not can_define_cross_pole_task(actor):
        raise ActionPlanPermissionError(
            "Not allowed to modify a task on this business unit."
        )


@transaction.atomic
def update_action_plan_execution(
    *,
    execution_id: uuid.UUID,
    actor: EstablishmentMembership,
    expected_updated_at: datetime,
    title: str | None = None,
    description: str | None = None,
    requires_validation: bool | None = None,
    end_at: datetime | None | object = ...,
    assignees: list[dict] | None = None,
    pending_tasks: list[dict] | None = None,
) -> ActionPlanExecution:
    execution = _lock_execution_for_write(execution_id=execution_id)
    locked_tasks = _lock_all_execution_tasks_after_execution(execution=execution)

    if not can_update_action_plan_execution(actor, execution):
        raise ActionPlanPermissionError("Not allowed to update this execution.")
    if execution.status != ActionPlanExecution.Status.IN_PROGRESS:
        raise ActionPlanStateError("Execution cannot be modified in its current state.")
    if execution.updated_at != expected_updated_at:
        raise ActionPlanStaleExecutionError()

    existing_assignees = list(
        ActionPlanAssignee.objects.select_for_update()
        .select_related("membership", "execution_team__business_unit")
        .filter(action_plan_execution_id=execution.id)
        .order_by("id")
    )
    existing_assignees_by_membership = {
        item.membership_id: item for item in existing_assignees
    }
    pending_by_id = {
        task.id: task
        for task in locked_tasks
        if task.status == TASK_STATUS_PENDING
    }
    treated_tasks = [
        task for task in locked_tasks if task.status in TERMINAL_TASK_STATUSES
    ]

    diff = ExecutionUpdateDiff()
    update_fields = ["last_activity_at", "updated_at"]
    now = timezone.now()

    if title is not None:
        normalized_title = _normalize_title(title)
        if normalized_title != execution.title:
            execution.title = normalized_title
            update_fields.append("title")
            diff.title_changed = True
    if description is not None:
        normalized_description = _normalize_description(description)
        if normalized_description != execution.description:
            execution.description = normalized_description
            update_fields.append("description")
            diff.description_changed = True
    if requires_validation is not None:
        if (
            actor.role == EstablishmentMembership.Role.STAFF
            and requires_validation is True
        ):
            raise ActionPlanPermissionError(
                "Not allowed to enable validation on this execution."
            )
        if requires_validation != execution.requires_validation:
            execution.requires_validation = requires_validation
            update_fields.append("requires_validation")
            diff.requires_validation_changed = True
    if end_at is not ...:
        _assert_end_after_start(start_at=execution.start_at, end_at=end_at)
        if end_at != execution.end_at:
            execution.end_at = end_at
            update_fields.append("end_at")
            diff.end_at_changed = True

    final_assignee_rows = _resolve_final_assignees(
        actor=actor,
        execution=execution,
        existing_assignees_by_membership=existing_assignees_by_membership,
        assignees_payload=assignees,
        now=now,
        diff=diff,
    )
    final_assignee_membership_ids = {
        row["membership"].id for row in final_assignee_rows
    }
    if not final_assignee_membership_ids:
        raise ActionPlanValidationError("At least one assignee is required.")

    final_pending_specs = _resolve_final_pending_tasks(
        actor=actor,
        execution=execution,
        pending_by_id=pending_by_id,
        treated_tasks=treated_tasks,
        pending_tasks_payload=pending_tasks,
        final_assignee_membership_ids=final_assignee_membership_ids,
        removed_assignee_ids=diff.removed_assignee_ids,
        assignees_payload_present=assignees is not None,
        diff=diff,
    )

    if actor.role == EstablishmentMembership.Role.STAFF:
        _validate_staff_update_constraints(
            actor=actor,
            execution=execution,
            final_assignee_rows=final_assignee_rows,
            final_pending_specs=final_pending_specs,
            requires_validation=execution.requires_validation,
        )

    save_id = uuid.uuid4()
    recipient_ids = _compute_notification_recipient_ids(
        actor=actor,
        execution=execution,
        final_assignee_membership_ids=final_assignee_membership_ids,
        existing_assignees_by_membership=existing_assignees_by_membership,
        diff=diff,
    )

    execution.last_activity_at = now
    execution.save(update_fields=update_fields)

    if assignees is not None:
        _apply_assignee_writes(
            execution=execution,
            existing_assignees_by_membership=existing_assignees_by_membership,
            final_assignee_rows=final_assignee_rows,
        )

    if pending_tasks is not None or (
        assignees is not None and diff.removed_assignee_ids
    ):
        _apply_pending_task_writes(
            execution=execution,
            pending_by_id=pending_by_id,
            treated_tasks=treated_tasks,
            final_pending_specs=final_pending_specs,
            apply_auto_unassign_only=pending_tasks is None,
            removed_assignee_ids=diff.removed_assignee_ids,
        )

    _sync_execution_teams_after_update(execution=execution)

    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
    from houston.notifications.scheduling import (
        schedule_action_plan_execution_updated_notification,
    )

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.updated",
    )
    if recipient_ids:
        schedule_action_plan_execution_updated_notification(
            execution_id=execution.id,
            actor_membership_id=actor.id,
            recipient_membership_ids=sorted(recipient_ids),
            save_id=save_id,
        )

    return execution


def _resolve_final_assignees(
    *,
    actor: EstablishmentMembership,
    execution: ActionPlanExecution,
    existing_assignees_by_membership: dict[uuid.UUID, ActionPlanAssignee],
    assignees_payload: list[dict] | None,
    now: datetime,
    diff: ExecutionUpdateDiff,
) -> list[dict]:
    if assignees_payload is None:
        return [
            {
                "membership": item.membership,
                "business_unit": item.execution_team.business_unit,
                "start_at": item.start_at,
                "visible_from": item.visible_from,
                "end_at": item.end_at,
            }
            for item in existing_assignees_by_membership.values()
        ]

    seen: set[uuid.UUID] = set()
    final_rows: list[dict] = []
    for item in assignees_payload:
        if not isinstance(item, dict):
            raise ActionPlanValidationError("Invalid assignee payload.")
        membership_id = item.get("membership_id")
        business_unit_id = item.get("business_unit_id")
        if membership_id is None or business_unit_id is None:
            raise ActionPlanValidationError(
                "Assignee membership and business unit are required."
            )
        if "start_at" in item or "visible_from" in item:
            raise ActionPlanValidationError(
                "Assignee start and visibility cannot be modified."
            )
        membership = _validate_membership_in_establishment(
            establishment_id=execution.establishment_id,
            membership_id=membership_id,
        )
        if membership.id in seen:
            raise ActionPlanValidationError("Duplicate assignees are not allowed.")
        seen.add(membership.id)
        business_unit = _validate_business_unit_in_establishment(
            establishment_id=execution.establishment_id,
            business_unit_id=business_unit_id,
        )
        _validate_assignee_covers_business_unit(
            membership=membership,
            business_unit=business_unit,
        )
        existing = existing_assignees_by_membership.get(membership.id)
        if existing is not None:
            if existing.execution_team.business_unit_id != business_unit.id:
                raise ActionPlanValidationError(
                    "Existing assignee business unit cannot be changed."
                )
            end_at = item.get("end_at", existing.end_at)
            _assert_end_after_start(start_at=existing.start_at, end_at=end_at)
            if end_at != existing.end_at:
                diff.individual_end_changed_ids.add(membership.id)
            final_rows.append(
                {
                    "membership": membership,
                    "business_unit": business_unit,
                    "start_at": existing.start_at,
                    "visible_from": existing.visible_from,
                    "end_at": end_at,
                }
            )
            continue

        if not can_assign_to_execution_business_unit(actor, business_unit=business_unit):
            raise ActionPlanPermissionError(
                "Not allowed to assign members to this business unit."
            )
        if execution.use_shared_chronology:
            start_at = execution.start_at
            visible_from = execution.visible_from
        else:
            start_at = now
            visible_from = now
        end_at = item.get("end_at")
        _assert_end_after_start(start_at=start_at, end_at=end_at)
        diff.added_assignee_ids.add(membership.id)
        final_rows.append(
            {
                "membership": membership,
                "business_unit": business_unit,
                "start_at": start_at,
                "visible_from": visible_from,
                "end_at": end_at,
            }
        )

    final_ids = {row["membership"].id for row in final_rows}
    for membership_id, existing in existing_assignees_by_membership.items():
        if membership_id in final_ids:
            continue
        bu = existing.execution_team.business_unit
        if actor.role not in ADMIN_ROLES and not _manager_can_manage_bu(actor, bu):
            raise ActionPlanPermissionError(
                "Not allowed to remove an assignee outside your scope."
            )
        diff.removed_assignee_ids.add(membership_id)

    return final_rows


def _resolve_final_pending_tasks(
    *,
    actor: EstablishmentMembership,
    execution: ActionPlanExecution,
    pending_by_id: dict[uuid.UUID, ActionPlanExecutionTask],
    treated_tasks: list[ActionPlanExecutionTask],
    pending_tasks_payload: list[dict] | None,
    final_assignee_membership_ids: set[uuid.UUID],
    removed_assignee_ids: set[uuid.UUID],
    assignees_payload_present: bool,
    diff: ExecutionUpdateDiff,
) -> list[dict]:
    treated_positions = {task.position for task in treated_tasks}
    if pending_tasks_payload is None:
        specs = []
        for task in pending_by_id.values():
            assigned_id = task.assigned_membership_id
            if (
                assignees_payload_present
                and assigned_id is not None
                and assigned_id in removed_assignee_ids
            ):
                assigned_id = None
                diff.unassigned_from_membership_ids.add(task.assigned_membership_id)
                diff.pending_structure_changed = True
            specs.append(
                {
                    "id": task.id,
                    "action_plan_task_id": task.action_plan_task_id,
                    "task": task.task,
                    "description": task.description,
                    "business_unit_id": task.execution_team.business_unit_id,
                    "position": task.position,
                    "deadline_at": task.deadline_at,
                    "assigned_membership_id": assigned_id,
                    "observation_id": task.observation_id,
                    "skipped_reason": task.skipped_reason,
                    "completed_at": task.completed_at,
                    "skipped_at": task.skipped_at,
                    "observation_created_at": task.observation_created_at,
                    "is_new": False,
                }
            )
        return specs

    if len(pending_tasks_payload) + len(treated_tasks) > MAX_TASKS_PER_PLAN:
        raise ActionPlanValidationError("Too many tasks.")

    specs: list[dict] = []
    seen_ids: set[uuid.UUID] = set()
    pending_positions: set[int] = set()
    for index, item in enumerate(pending_tasks_payload, start=1):
        if not isinstance(item, dict):
            raise ActionPlanValidationError("Invalid task payload.")
        task_id = item.get("id")
        position = item.get("position", index)
        if not isinstance(position, int):
            raise ActionPlanValidationError("Invalid task position.")
        if position < MIN_TASK_POSITION or position > MAX_TASK_POSITION:
            raise ActionPlanValidationError("Task position is out of bounds.")
        if position in treated_positions or position in pending_positions:
            raise ActionPlanValidationError("Duplicate task positions are not allowed.")
        pending_positions.add(position)

        task_text = _normalize_task_text(item.get("task", ""))
        description = _normalize_task_description(item.get("description"))
        business_unit_id = item.get("business_unit_id")
        if business_unit_id is None:
            raise ActionPlanValidationError("Task business unit is required.")
        business_unit = _validate_business_unit_in_establishment(
            establishment_id=execution.establishment_id,
            business_unit_id=business_unit_id,
        )
        deadline_at = item.get("deadline_at")
        assigned_membership_id = item.get("assigned_membership_id")
        if assigned_membership_id is not None:
            if assigned_membership_id not in final_assignee_membership_ids:
                raise ActionPlanValidationError(
                    "Task assignee must be present in the execution assignees."
                )
            assigned_membership = _validate_membership_in_establishment(
                establishment_id=execution.establishment_id,
                membership_id=assigned_membership_id,
            )
            _validate_assignee_covers_business_unit(
                membership=assigned_membership,
                business_unit=business_unit,
            )

        if task_id is None:
            _assert_actor_may_mutate_pending_pole(
                actor=actor,
                execution=execution,
                business_unit=business_unit,
            )
            if (
                business_unit.id != execution.pilot_business_unit_id
                and not can_define_cross_pole_task(actor)
            ):
                raise ActionPlanPermissionError(
                    "Not allowed to attach tasks to a non-pilot business unit."
                )
            specs.append(
                {
                    "id": uuid.uuid4(),
                    "action_plan_task_id": None,
                    "task": task_text,
                    "description": description,
                    "business_unit_id": business_unit.id,
                    "position": position,
                    "deadline_at": deadline_at,
                    "assigned_membership_id": assigned_membership_id,
                    "observation_id": None,
                    "skipped_reason": None,
                    "completed_at": None,
                    "skipped_at": None,
                    "observation_created_at": None,
                    "is_new": True,
                }
            )
            diff.pending_structure_changed = True
            if assigned_membership_id is not None:
                diff.newly_assigned_task_membership_ids.add(assigned_membership_id)
            continue

        task_uuid = uuid.UUID(str(task_id))
        if task_uuid in seen_ids:
            raise ActionPlanValidationError("Duplicate task ids are not allowed.")
        seen_ids.add(task_uuid)
        existing = pending_by_id.get(task_uuid)
        if existing is None:
            raise ActionPlanValidationError("Pending task not found.")

        unchanged = _pending_task_fields_equal(
            existing,
            task=task_text,
            description=description,
            business_unit_id=business_unit.id,
            position=position,
            deadline_at=deadline_at,
            assigned_membership_id=assigned_membership_id,
        )
        if not unchanged:
            _assert_actor_may_mutate_pending_pole(
                actor=actor,
                execution=execution,
                business_unit=existing.execution_team.business_unit,
            )
            _assert_actor_may_mutate_pending_pole(
                actor=actor,
                execution=execution,
                business_unit=business_unit,
            )
            if (
                business_unit.id != existing.execution_team.business_unit_id
                and business_unit.id != execution.pilot_business_unit_id
                and not can_define_cross_pole_task(actor)
            ):
                raise ActionPlanPermissionError(
                    "Not allowed to attach tasks to a non-pilot business unit."
                )
            diff.pending_structure_changed = True
            old_assigned = existing.assigned_membership_id
            if old_assigned != assigned_membership_id:
                if old_assigned is not None and assigned_membership_id is not None:
                    diff.reassigned_from_membership_ids.add(old_assigned)
                    diff.reassigned_to_membership_ids.add(assigned_membership_id)
                elif old_assigned is not None:
                    diff.unassigned_from_membership_ids.add(old_assigned)
                elif assigned_membership_id is not None:
                    diff.newly_assigned_task_membership_ids.add(assigned_membership_id)
            if existing.deadline_at != deadline_at and assigned_membership_id is not None:
                diff.deadline_changed_membership_ids.add(assigned_membership_id)

        specs.append(
            {
                "id": existing.id,
                "action_plan_task_id": existing.action_plan_task_id,
                "task": task_text,
                "description": description,
                "business_unit_id": business_unit.id,
                "position": position,
                "deadline_at": deadline_at,
                "assigned_membership_id": assigned_membership_id,
                "observation_id": existing.observation_id,
                "skipped_reason": existing.skipped_reason,
                "completed_at": existing.completed_at,
                "skipped_at": existing.skipped_at,
                "observation_created_at": existing.observation_created_at,
                "is_new": False,
            }
        )

    kept_ids = {spec["id"] for spec in specs if not spec["is_new"]}
    for task_id, existing in pending_by_id.items():
        if task_id in kept_ids:
            continue
        _assert_actor_may_mutate_pending_pole(
            actor=actor,
            execution=execution,
            business_unit=existing.execution_team.business_unit,
        )
        if Observation.objects.filter(action_plan_execution_task_id=task_id).exists():
            raise ActionPlanValidationError(
                "Pending task cannot be deleted while linked to an observation."
            )
        diff.pending_structure_changed = True

    return specs


def _validate_staff_update_constraints(
    *,
    actor: EstablishmentMembership,
    execution: ActionPlanExecution,
    final_assignee_rows: list[dict],
    final_pending_specs: list[dict],
    requires_validation: bool,
) -> None:
    if execution.created_by_id != actor.id:
        raise ActionPlanPermissionError("Not allowed to update this execution.")
    validated_assignees = [
        ValidatedAssigneePayload(
            membership=row["membership"],
            business_unit=row["business_unit"],
        )
        for row in final_assignee_rows
    ]
    validated_tasks = [
        {
            "business_unit": _validate_business_unit_in_establishment(
                establishment_id=execution.establishment_id,
                business_unit_id=spec["business_unit_id"],
            )
        }
        for spec in final_pending_specs
    ]
    if not can_create_staff_feed_execution_plan(
        actor,
        pilot_business_unit=execution.pilot_business_unit,
        assignees=validated_assignees,
        tasks=validated_tasks,
        requires_validation=requires_validation,
    ):
        raise ActionPlanPermissionError("Not allowed to update this execution.")


def _compute_notification_recipient_ids(
    *,
    actor: EstablishmentMembership,
    execution: ActionPlanExecution,
    final_assignee_membership_ids: set[uuid.UUID],
    existing_assignees_by_membership: dict[uuid.UUID, ActionPlanAssignee],
    diff: ExecutionUpdateDiff,
) -> set[uuid.UUID]:
    recipients: set[uuid.UUID] = set()
    remaining = set(final_assignee_membership_ids)

    recipients |= diff.added_assignee_ids
    recipients |= diff.removed_assignee_ids
    recipients |= diff.newly_assigned_task_membership_ids
    recipients |= diff.reassigned_from_membership_ids
    recipients |= diff.reassigned_to_membership_ids
    recipients |= diff.unassigned_from_membership_ids
    recipients |= diff.deadline_changed_membership_ids
    recipients |= diff.individual_end_changed_ids

    broadcast = (
        diff.title_changed
        or diff.description_changed
        or diff.requires_validation_changed
        or diff.end_at_changed
        or diff.pending_structure_changed
    )
    if broadcast:
        recipients |= remaining

    recipients.discard(actor.id)
    # Keep only active memberships that still exist or were removed (still notify removed).
    valid_ids = set(existing_assignees_by_membership) | final_assignee_membership_ids
    return {membership_id for membership_id in recipients if membership_id in valid_ids}


def _apply_assignee_writes(
    *,
    execution: ActionPlanExecution,
    existing_assignees_by_membership: dict[uuid.UUID, ActionPlanAssignee],
    final_assignee_rows: list[dict],
) -> None:
    final_ids = {row["membership"].id for row in final_assignee_rows}
    for membership_id, existing in existing_assignees_by_membership.items():
        if membership_id not in final_ids:
            existing.delete()

    bu_ids = {row["business_unit"].id for row in final_assignee_rows}
    bu_ids.add(execution.pilot_business_unit_id)
    teams = _get_or_create_execution_teams(
        execution=execution,
        pilot_business_unit=execution.pilot_business_unit,
        business_unit_ids=bu_ids,
    )
    for row in final_assignee_rows:
        existing = existing_assignees_by_membership.get(row["membership"].id)
        if existing is None:
            ActionPlanAssignee.objects.create(
                action_plan_execution=execution,
                execution_team=teams[row["business_unit"].id],
                membership=row["membership"],
                start_at=row["start_at"],
                visible_from=row["visible_from"],
                end_at=row["end_at"],
            )
            continue
        if existing.end_at != row["end_at"]:
            existing.end_at = row["end_at"]
            existing.save(update_fields=["end_at", "updated_at"])


def _apply_pending_task_writes(
    *,
    execution: ActionPlanExecution,
    pending_by_id: dict[uuid.UUID, ActionPlanExecutionTask],
    treated_tasks: list[ActionPlanExecutionTask],
    final_pending_specs: list[dict],
    apply_auto_unassign_only: bool,
    removed_assignee_ids: set[uuid.UUID],
) -> None:
    if apply_auto_unassign_only:
        for task in pending_by_id.values():
            if (
                task.assigned_membership_id is not None
                and task.assigned_membership_id in removed_assignee_ids
            ):
                task.assigned_membership = None
                task.assigned_display_name = ""
                task.save(
                    update_fields=[
                        "assigned_membership",
                        "assigned_display_name",
                        "updated_at",
                    ]
                )
        return

    ActionPlanExecutionTask.objects.filter(
        action_plan_execution_id=execution.id,
        status=TASK_STATUS_PENDING,
    ).delete()

    bu_ids = {spec["business_unit_id"] for spec in final_pending_specs}
    bu_ids.update(task.execution_team.business_unit_id for task in treated_tasks)
    bu_ids.add(execution.pilot_business_unit_id)
    teams = _get_or_create_execution_teams(
        execution=execution,
        pilot_business_unit=execution.pilot_business_unit,
        business_unit_ids=bu_ids,
    )

    memberships_by_id: dict[uuid.UUID, EstablishmentMembership] = {}
    assigned_ids = {
        spec["assigned_membership_id"]
        for spec in final_pending_specs
        if spec["assigned_membership_id"] is not None
    }
    if assigned_ids:
        memberships_by_id = {
            membership.id: membership
            for membership in EstablishmentMembership.objects.filter(id__in=assigned_ids)
        }

    to_create: list[ActionPlanExecutionTask] = []
    for spec in final_pending_specs:
        assigned_membership = None
        assigned_display_name = ""
        if spec["assigned_membership_id"] is not None:
            assigned_membership = memberships_by_id[spec["assigned_membership_id"]]
            assigned_display_name = _membership_display_name(assigned_membership)
        to_create.append(
            ActionPlanExecutionTask(
                id=spec["id"],
                action_plan_execution=execution,
                execution_team=teams[spec["business_unit_id"]],
                action_plan_task_id=spec["action_plan_task_id"],
                task=spec["task"],
                description=spec["description"],
                deadline_at=spec["deadline_at"],
                assigned_membership=assigned_membership,
                assigned_display_name=assigned_display_name,
                position=spec["position"],
                status=TASK_STATUS_PENDING,
                observation_id=spec["observation_id"],
                skipped_reason=spec["skipped_reason"],
                completed_at=spec["completed_at"],
                skipped_at=spec["skipped_at"],
                observation_created_at=spec["observation_created_at"],
            )
        )
    if to_create:
        ActionPlanExecutionTask.objects.bulk_create(to_create)


def _sync_execution_teams_after_update(*, execution: ActionPlanExecution) -> None:
    needed_bu_ids = {execution.pilot_business_unit_id}
    needed_bu_ids.update(
        ActionPlanAssignee.objects.filter(
            action_plan_execution_id=execution.id,
        ).values_list("execution_team__business_unit_id", flat=True)
    )
    needed_bu_ids.update(
        ActionPlanExecutionTask.objects.filter(
            action_plan_execution_id=execution.id,
        ).values_list("execution_team__business_unit_id", flat=True)
    )
    _get_or_create_execution_teams(
        execution=execution,
        pilot_business_unit=execution.pilot_business_unit,
        business_unit_ids=needed_bu_ids,
    )
    orphan_teams = ActionPlanExecutionTeam.objects.filter(
        action_plan_execution_id=execution.id,
        is_pilot=False,
    ).exclude(business_unit_id__in=needed_bu_ids)
    for team in orphan_teams:
        if team.assignees.exists() or team.task_executions.exists():
            continue
        team.delete()
