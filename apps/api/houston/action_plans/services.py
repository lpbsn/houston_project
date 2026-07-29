from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from houston.action_plans.constants import (
    ACTION_PLAN_DESCRIPTION_MAX_LENGTH,
    ACTION_PLAN_SKIPPED_REASON_MAX_LENGTH,
    ACTION_PLAN_TASK_MAX_LENGTH,
    ACTION_PLAN_TITLE_MAX_LENGTH,
    ACTIVE_EXECUTION_STATUSES,
    CANCEL_ORIGIN_MANUAL,
    CANCELABLE_EXECUTION_STATUSES,
    CATALOG_STATUS_ACTIVE,
    CATALOG_STATUS_INACTIVE,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
    MAX_TASK_POSITION,
    MAX_TASKS_PER_PLAN,
    MIN_TASK_POSITION,
    SIGNAL_BLOCKING_EXECUTION_STATUSES,
    TASK_STATUS_DONE,
    TASK_STATUS_OBSERVATION_CREATED,
    TASK_STATUS_PENDING,
    TASK_STATUS_SKIPPED,
)
from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanStateError,
    ActionPlanValidationError,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanTask,
)
from houston.action_plans.permissions import (
    can_assign_to_execution_business_unit,
    can_cancel_action_plan_execution,
    can_cancel_scheduled_action_plan_execution,
    can_create_action_plan,
    can_create_linked_action_plan,
    can_create_staff_feed_execution_plan,
    can_define_cross_pole_task,
    can_execute_action_plan_task,
    can_manage_action_plan,
    can_mark_action_plan_execution_done,
    can_reopen_action_plan_execution,
    can_use_action_plan,
    can_validate_action_plan_execution,
    staff_catalog_action_plan_in_scope,
)
from houston.establishments.membership_scope import (
    membership_business_unit_scope_ids,
    membership_covers_business_unit_including_admins,
)
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.role_constants import ADMIN_ROLES
from houston.observations.exceptions import ObservationValidationError
from houston.observations.models import Observation
from houston.observations.services import submit_observation
from houston.signals.models import Signal


@dataclass(frozen=True)
class ValidatedAssigneePayload:
    membership: EstablishmentMembership
    business_unit: BusinessUnit
    start_at: datetime | None = None
    visible_from: datetime | None = None
    end_at: datetime | None = None


@dataclass(frozen=True)
class AssigneeChronologyDefaults:
    start_at: datetime | None = None
    visible_from: datetime | None = None
    end_at: datetime | None = None


def _membership_display_name(membership: EstablishmentMembership) -> str:
    user = membership.user
    return user.get_full_name() or user.email or user.username


def _normalize_skipped_reason(skipped_reason: str | None) -> str | None:
    if skipped_reason is None:
        return None
    normalized = skipped_reason.strip()
    if not normalized:
        return None
    if len(normalized) > ACTION_PLAN_SKIPPED_REASON_MAX_LENGTH:
        raise ActionPlanValidationError("Skipped reason is too long.")
    return normalized


def touch_execution_activity(*, execution: ActionPlanExecution, at=None) -> None:
    execution.last_activity_at = at or timezone.now()
    execution.save(update_fields=["last_activity_at", "updated_at"])
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.updated",
    )


def _linked_active_executions_block_signal_sync(*, signal: Signal) -> bool:
    return ActionPlanExecution.objects.filter(
        source_signal_id=signal.id,
        status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES,
    ).exists()


@transaction.atomic
def sync_signal_after_execution_change(*, signal: Signal) -> Signal:
    linked = ActionPlanExecution.objects.filter(source_signal_id=signal.id)
    if linked.filter(status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES).exists():
        return signal

    if (
        linked.exists()
        and linked.filter(status=EXECUTION_STATUS_CANCELED).count() == linked.count()
    ):
        from houston.signals.constants import CANCEL_RESOLVE_SIGNAL_STATUSES
        from houston.signals.services import (
            _schedule_signal_invalidation,
            touch_signal_activity,
        )

        if signal.status in CANCEL_RESOLVE_SIGNAL_STATUSES:
            signal.status = Signal.Status.OPEN
            signal.is_pinned = False
            signal.pinned_at = None
            signal.pinned_by_membership = None
            touch_signal_activity(signal=signal)
            signal.save(
                update_fields=[
                    "status",
                    "is_pinned",
                    "pinned_at",
                    "pinned_by_membership",
                    "last_activity_at",
                    "updated_at",
                ]
            )
            _schedule_signal_invalidation(signal=signal, reason="signal.updated")
        return signal

    if linked.exists() and linked.filter(status=EXECUTION_STATUS_DONE).exists():
        from houston.signals.constants import CANCEL_RESOLVE_SIGNAL_STATUSES
        from houston.signals.services import resolve_signal_from_execution_sync

        if signal.status in CANCEL_RESOLVE_SIGNAL_STATUSES:
            return resolve_signal_from_execution_sync(signal=signal)
    return signal


def _sync_linked_signal_after_execution_change(*, execution: ActionPlanExecution) -> None:
    if execution.source_signal_id is None:
        return
    signal = Signal.objects.get(pk=execution.source_signal_id)
    sync_signal_after_execution_change(signal=signal)


def _lock_source_signal_created_from_set_if_any(*, execution_id: uuid.UUID) -> None:
    """Lock CREATED_FROM siblings (or self) before locking the execution row.

    This prevents an order inversion between:
    - Signal lifecycle transitions (which lock CREATED_FROM siblings)
    - Action plan execution transitions (which hold row locks on executions)
    """
    source_signal_id = (
        ActionPlanExecution.objects.filter(id=execution_id)
        .values_list("source_signal_id", flat=True)
        .first()
    )
    if source_signal_id is None:
        return

    signal = Signal.objects.filter(id=source_signal_id).first()
    if signal is None:
        return

    from houston.signals.services import _lock_signal_created_from_set_or_self

    _lock_signal_created_from_set_or_self(signal=signal)


def _cancel_linked_active_executions_for_signal_resolve(
    *,
    signal: Signal,
    actor_membership: EstablishmentMembership | None = None,
) -> None:
    _ = actor_membership
    now = timezone.now()
    active_executions = ActionPlanExecution.objects.filter(
        source_signal_id=signal.id,
        status__in=SIGNAL_BLOCKING_EXECUTION_STATUSES,
    ).select_for_update()
    for execution in active_executions:
        execution.status = EXECUTION_STATUS_CANCELED
        execution.canceled_at = now
        execution.cancel_origin = CANCEL_ORIGIN_MANUAL
        execution.last_activity_at = now
        execution.save(
            update_fields=[
                "status",
                "canceled_at",
                "cancel_origin",
                "last_activity_at",
                "updated_at",
            ]
        )
        from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
        from houston.notifications.scheduling import (
            schedule_action_plan_execution_canceled_notification,
        )

        schedule_action_plan_execution_invalidation(
            execution=execution,
            reason="action_plan_execution.canceled",
        )
        schedule_action_plan_execution_canceled_notification(
            execution_id=execution.id,
            actor_membership_id=None,
        )


def _reopen_linked_signal_after_execution_reopen(*, execution: ActionPlanExecution) -> None:
    if execution.source_signal_id is None:
        return
    signal = Signal.objects.get(pk=execution.source_signal_id)
    if signal.status != Signal.Status.RESOLVED:
        return
    from houston.signals.services import (
        _schedule_signal_invalidation,
        touch_signal_activity,
    )

    signal.status = Signal.Status.IN_PROGRESS
    touch_signal_activity(signal=signal)
    signal.save(update_fields=["status", "last_activity_at", "updated_at"])
    _schedule_signal_invalidation(signal=signal, reason="signal.updated")


def _validate_linked_signal_active(*, signal: Signal) -> None:
    from houston.signals.constants import ACTIVE_SIGNAL_STATUSES

    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        raise ActionPlanValidationError("Signal is not active.")


def _validate_linked_signal_pilot_consistency(
    *,
    signal: Signal,
    pilot_business_unit: BusinessUnit,
    actor: EstablishmentMembership,
) -> None:
    """Validate pilot against existing responsible or null-responsible selection rules."""
    if signal.responsible_business_unit_id is not None:
        if pilot_business_unit.id != signal.responsible_business_unit_id:
            raise ActionPlanValidationError(
                "Pilot business unit must match the signal responsible business unit."
            )
        return

    if not pilot_business_unit.active:
        raise ActionPlanValidationError("Invalid business unit.")

    subject = signal.activity_subject
    if subject is not None:
        subject_bu = subject.business_unit
        if subject_bu is None or subject_bu.id != pilot_business_unit.id:
            raise ActionPlanValidationError(
                "Pilot business unit must match the activity subject business unit.",
                code="invalid_pilot_business_unit",
            )

    if not can_create_action_plan(
        actor,
        establishment_id=signal.establishment_id,
        pilot_business_unit=pilot_business_unit,
    ):
        raise ActionPlanPermissionError("Not allowed to create this action plan.")


def _effective_routing_status_for_linked_pilot(
    *,
    signal: Signal,
    pilot_business_unit: BusinessUnit,
) -> str:
    from houston.signals.signal_classification import (
        InvalidSignalClassificationError,
        routing_status_for_classification,
    )

    try:
        return routing_status_for_classification(
            establishment=signal.establishment,
            affected_business_unit=signal.affected_business_unit,
            responsible_business_unit=pilot_business_unit,
            activity_subject=signal.activity_subject,
        )
    except InvalidSignalClassificationError as exc:
        raise ActionPlanValidationError(str(exc), code="invalid_routing") from exc


def _resolve_effective_issue_focus_for_linked_create(
    *,
    signal: Signal,
    pilot_business_unit: BusinessUnit,
    requested_issue_focus: str | None,
) -> str | None:
    """Return focus to pass to qualify, or None when unassigned (not required)."""
    from houston.signals.services import normalize_issue_focus

    routing_status = _effective_routing_status_for_linked_pilot(
        signal=signal,
        pilot_business_unit=pilot_business_unit,
    )
    if routing_status != Signal.RoutingStatus.RESOLVED:
        return None

    existing = normalize_issue_focus(signal.issue_focus)
    if existing:
        return existing
    provided = normalize_issue_focus(requested_issue_focus)
    if provided:
        return provided
    raise ActionPlanValidationError(
        "issue_focus is required when routing is resolved.",
        code="invalid_issue_focus",
    )


def _qualify_linked_signal_for_create(
    *,
    signal: Signal,
    actor: EstablishmentMembership,
    pilot_business_unit: BusinessUnit,
    issue_focus: str | None,
) -> Signal:
    """Assign responsible via qualify_signal_routing; return surviving signal."""
    from houston.signals.exceptions import (
        SignalAlreadyMergedError,
        SignalPermissionError,
        SignalStateError,
        SignalValidationError,
    )
    from houston.signals.services import qualify_signal_routing

    patch: dict = {"responsible_business_unit_id": pilot_business_unit.id}
    if issue_focus is not None:
        patch["issue_focus"] = issue_focus

    try:
        result = qualify_signal_routing(
            signal=signal,
            membership=actor,
            patch=patch,
        )
    except SignalPermissionError as exc:
        raise ActionPlanPermissionError(str(exc) or "Permission denied.") from exc
    except SignalAlreadyMergedError as exc:
        raise ActionPlanValidationError(str(exc), code="already_merged") from exc
    except SignalStateError as exc:
        raise ActionPlanValidationError(str(exc), code="invalid_signal_state") from exc
    except SignalValidationError as exc:
        code = getattr(exc, "code", None) or "validation_error"
        raise ActionPlanValidationError(str(exc), code=code) from exc

    linked = result.signal
    if linked.responsible_business_unit_id != pilot_business_unit.id:
        raise ActionPlanValidationError(
            "Pilot business unit must match the signal responsible business unit."
        )
    return linked


def _activate_linked_signal_on_execution_create(*, signal: Signal) -> None:
    from houston.signals.services import (
        _schedule_signal_invalidation,
        touch_signal_activity,
    )

    status_changed = signal.status in {
        Signal.Status.OPEN,
        Signal.Status.INTERESTING,
    }
    unpin_changed = signal.is_pinned
    if not status_changed and not unpin_changed:
        return

    if status_changed and signal.status == Signal.Status.OPEN:
        from houston.signals.models import SignalResolutionRequest
        from houston.signals.resolution_request_services import (
            cancel_pending_resolution_request_for_signal,
        )

        cancel_pending_resolution_request_for_signal(
            signal=signal,
            reason=SignalResolutionRequest.CanceledReason.ACTION_PLAN_CREATED,
            notify_requester=True,
        )

    if status_changed:
        signal.status = Signal.Status.IN_PROGRESS
    if unpin_changed:
        signal.is_pinned = False
        signal.pinned_at = None
        signal.pinned_by_membership = None

    touch_signal_activity(signal=signal)
    update_fields = ["last_activity_at", "updated_at"]
    if status_changed:
        update_fields.append("status")
    if unpin_changed:
        update_fields.extend(["is_pinned", "pinned_at", "pinned_by_membership"])
    signal.save(update_fields=update_fields)
    _schedule_signal_invalidation(signal=signal, reason="signal.updated")


def _normalize_title(title: str) -> str:
    normalized = (title or "").strip()
    if not normalized:
        raise ActionPlanValidationError("Title is required.")
    if len(normalized) > ACTION_PLAN_TITLE_MAX_LENGTH:
        raise ActionPlanValidationError("Title is too long.")
    return normalized


def _normalize_description(description: str) -> str:
    normalized = (description or "").strip()
    if len(normalized) > ACTION_PLAN_DESCRIPTION_MAX_LENGTH:
        raise ActionPlanValidationError("Description is too long.")
    return normalized


def _normalize_task_text(task: str) -> str:
    normalized = (task or "").strip()
    if not normalized:
        raise ActionPlanValidationError("Task is required.")
    if len(normalized) > ACTION_PLAN_TASK_MAX_LENGTH:
        raise ActionPlanValidationError("Task is too long.")
    return normalized


def _normalize_task_description(description: str | None) -> str:
    normalized = (description or "").strip()
    if len(normalized) > ACTION_PLAN_DESCRIPTION_MAX_LENGTH:
        raise ActionPlanValidationError("Task description is too long.")
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
        raise ActionPlanValidationError("Invalid establishment membership.")
    return membership


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
        raise ActionPlanValidationError("Invalid business unit.")
    return business_unit


def _validate_assignee_covers_business_unit(
    *,
    membership: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> None:
    if not membership_covers_business_unit_including_admins(membership, business_unit):
        raise ActionPlanValidationError("Assignee is out of scope for the business unit.")


def _resolve_task_business_unit(
    *,
    establishment_id: uuid.UUID,
    task_item: dict,
    assigned_membership: EstablishmentMembership | None,
    pilot_business_unit: BusinessUnit | None,
) -> BusinessUnit:
    business_unit_id = task_item.get("business_unit_id")

    if assigned_membership is not None:
        if assigned_membership.role in ADMIN_ROLES:
            if business_unit_id is not None:
                return _validate_business_unit_in_establishment(
                    establishment_id=establishment_id,
                    business_unit_id=business_unit_id,
                )
            if pilot_business_unit is not None:
                return pilot_business_unit
            raise ActionPlanValidationError("Task business unit is required.")

        assignee_scope_ids = membership_business_unit_scope_ids(assigned_membership)
        if business_unit_id is None:
            if len(assignee_scope_ids) == 1:
                business_unit_id = next(iter(assignee_scope_ids))
            elif len(assignee_scope_ids) > 1:
                raise ActionPlanValidationError(
                    "Task business unit is required when assignee has multiple scopes."
                )
            elif pilot_business_unit is not None:
                business_unit_id = pilot_business_unit.id
            else:
                raise ActionPlanValidationError("Task business unit is required.")
        elif assignee_scope_ids and business_unit_id not in assignee_scope_ids:
            raise ActionPlanValidationError("Assignee is out of scope for the business unit.")

        business_unit = _validate_business_unit_in_establishment(
            establishment_id=establishment_id,
            business_unit_id=business_unit_id,
        )
        _validate_assignee_covers_business_unit(
            membership=assigned_membership,
            business_unit=business_unit,
        )
        return business_unit

    if business_unit_id is None:
        if pilot_business_unit is None:
            raise ActionPlanValidationError("Task business unit is required.")
        return pilot_business_unit

    return _validate_business_unit_in_establishment(
        establishment_id=establishment_id,
        business_unit_id=business_unit_id,
    )


def _validate_task_payloads(
    *,
    establishment_id: uuid.UUID,
    tasks: list[dict],
    pilot_business_unit: BusinessUnit | None = None,
    actor: EstablishmentMembership | None = None,
) -> list[dict]:
    if len(tasks) > MAX_TASKS_PER_PLAN:
        raise ActionPlanValidationError("Too many tasks.")

    positions: set[int] = set()
    validated: list[dict] = []
    for index, task_item in enumerate(tasks, start=1):
        if not isinstance(task_item, dict):
            raise ActionPlanValidationError("Invalid task payload.")

        position = task_item.get("position", index)
        if not isinstance(position, int):
            raise ActionPlanValidationError("Invalid task position.")
        if position < MIN_TASK_POSITION or position > MAX_TASK_POSITION:
            raise ActionPlanValidationError("Task position is out of bounds.")
        if position in positions:
            raise ActionPlanValidationError("Duplicate task positions are not allowed.")
        positions.add(position)

        assigned_membership = None
        assigned_membership_id = task_item.get("assigned_membership_id")
        if assigned_membership_id is not None:
            assigned_membership = _validate_membership_in_establishment(
                establishment_id=establishment_id,
                membership_id=assigned_membership_id,
            )
        business_unit = _resolve_task_business_unit(
            establishment_id=establishment_id,
            task_item=task_item,
            assigned_membership=assigned_membership,
            pilot_business_unit=pilot_business_unit,
        )
        if (
            actor is not None
            and assigned_membership is not None
            and actor.role != EstablishmentMembership.Role.STAFF
            and not can_assign_to_execution_business_unit(actor, business_unit=business_unit)
        ):
            raise ActionPlanPermissionError("Not allowed to assign members to this business unit.")
        validated.append(
            {
                "task": _normalize_task_text(str(task_item.get("task", ""))),
                "description": _normalize_task_description(task_item.get("description", "")),
                "deadline_at": task_item.get("deadline_at"),
                "assigned_membership": assigned_membership,
                "business_unit": business_unit,
                "position": position,
            }
        )
    return validated


def _validate_assignee_payloads(
    *,
    establishment_id: uuid.UUID,
    assignees: list[dict],
) -> list[ValidatedAssigneePayload]:
    if not assignees:
        return []

    seen_membership_ids: set[uuid.UUID] = set()
    validated: list[ValidatedAssigneePayload] = []
    for assignee_item in assignees:
        if not isinstance(assignee_item, dict):
            raise ActionPlanValidationError("Invalid assignee payload.")

        membership_id = assignee_item.get("membership_id")
        business_unit_id = assignee_item.get("business_unit_id")
        if membership_id is None or business_unit_id is None:
            raise ActionPlanValidationError("Assignee membership and business unit are required.")

        membership = _validate_membership_in_establishment(
            establishment_id=establishment_id,
            membership_id=membership_id,
        )
        if membership.id in seen_membership_ids:
            raise ActionPlanValidationError("Duplicate assignees are not allowed.")
        seen_membership_ids.add(membership.id)

        business_unit = _validate_business_unit_in_establishment(
            establishment_id=establishment_id,
            business_unit_id=business_unit_id,
        )
        _validate_assignee_covers_business_unit(
            membership=membership,
            business_unit=business_unit,
        )
        validated.append(
            ValidatedAssigneePayload(
                membership=membership,
                business_unit=business_unit,
                start_at=assignee_item.get("start_at"),
                visible_from=assignee_item.get("visible_from"),
                end_at=assignee_item.get("end_at"),
            )
        )
    return validated


def _resolve_merge_chronology(
    *,
    use_shared_chronology: bool,
    start_at: datetime | None,
    end_at: datetime | None,
    visible_from: datetime | None,
    validated_assignees: list[ValidatedAssigneePayload],
) -> AssigneeChronologyDefaults:
    chronology_values = (start_at, end_at, visible_from)
    if use_shared_chronology and any(value is not None for value in chronology_values):
        return AssigneeChronologyDefaults(
            start_at=start_at,
            end_at=end_at,
            visible_from=visible_from,
        )
    if validated_assignees:
        first = validated_assignees[0]
        return AssigneeChronologyDefaults(
            start_at=first.start_at,
            end_at=first.end_at,
            visible_from=first.visible_from,
        )
    return AssigneeChronologyDefaults()


def _merge_validated_task_assignees_into_assignee_payloads(
    *,
    validated_tasks: list[dict],
    assignee_payloads: list[dict],
    chronology: AssigneeChronologyDefaults,
) -> list[dict]:
    seen_membership_ids = {
        item.get("membership_id")
        for item in assignee_payloads
        if isinstance(item, dict) and item.get("membership_id") is not None
    }
    merged = list(assignee_payloads)
    for task_item in validated_tasks:
        assigned_membership = task_item.get("assigned_membership")
        if assigned_membership is None:
            continue
        if assigned_membership.id in seen_membership_ids:
            continue
        seen_membership_ids.add(assigned_membership.id)
        merged.append(
            {
                "membership_id": assigned_membership.id,
                "business_unit_id": task_item["business_unit"].id,
                "start_at": chronology.start_at,
                "visible_from": chronology.visible_from,
                "end_at": chronology.end_at,
            }
        )
    return merged


def _merge_plan_task_assignees_into_assignee_payloads(
    *,
    plan_tasks: list[ActionPlanTask],
    assignee_payloads: list[dict],
    chronology: AssigneeChronologyDefaults,
) -> list[dict]:
    seen_membership_ids = {
        item.get("membership_id")
        for item in assignee_payloads
        if isinstance(item, dict) and item.get("membership_id") is not None
    }
    merged = list(assignee_payloads)
    for plan_task in plan_tasks:
        if plan_task.assigned_membership_id is None:
            continue
        if plan_task.assigned_membership_id in seen_membership_ids:
            continue
        seen_membership_ids.add(plan_task.assigned_membership_id)
        merged.append(
            {
                "membership_id": plan_task.assigned_membership_id,
                "business_unit_id": plan_task.business_unit_id,
                "start_at": chronology.start_at,
                "visible_from": chronology.visible_from,
                "end_at": chronology.end_at,
            }
        )
    return merged


def _execution_task_snapshot_fields(*, plan_task: ActionPlanTask) -> dict:
    assigned_display_name = ""
    if plan_task.assigned_membership is not None:
        assigned_display_name = _membership_display_name(plan_task.assigned_membership)
    return {
        "description": plan_task.description,
        "deadline_at": plan_task.deadline_at,
        "assigned_membership": plan_task.assigned_membership,
        "assigned_display_name": assigned_display_name,
    }


def merge_plan_task_assignees_into_validated_assignees(
    *,
    establishment_id: uuid.UUID,
    plan_tasks: list[ActionPlanTask],
    assignees: list[ValidatedAssigneePayload],
    chronology: AssigneeChronologyDefaults,
) -> list[ValidatedAssigneePayload]:
    assignee_payloads = [
        {
            "membership_id": assignee.membership.id,
            "business_unit_id": assignee.business_unit.id,
            "start_at": assignee.start_at,
            "visible_from": assignee.visible_from,
            "end_at": assignee.end_at,
        }
        for assignee in assignees
    ]
    merged_payloads = _merge_plan_task_assignees_into_assignee_payloads(
        plan_tasks=plan_tasks,
        assignee_payloads=assignee_payloads,
        chronology=chronology,
    )
    return _validate_assignee_payloads(
        establishment_id=establishment_id,
        assignees=merged_payloads,
    )


def _assert_staff_self_assignee_payload(
    *,
    actor: EstablishmentMembership,
    pilot_business_unit: BusinessUnit,
    assignees: list[dict] | None,
) -> None:
    if not assignees:
        return
    for assignee_item in assignees:
        if not isinstance(assignee_item, dict):
            raise ActionPlanPermissionError("Not allowed to assign other members.")
        membership_id = assignee_item.get("membership_id")
        business_unit_id = assignee_item.get("business_unit_id")
        if membership_id is not None and membership_id != actor.id:
            raise ActionPlanPermissionError("Not allowed to assign other members.")
        if business_unit_id is not None and business_unit_id != pilot_business_unit.id:
            raise ActionPlanPermissionError(
                "Not allowed to assign members to this business unit."
            )


def _resolve_staff_catalog_self_assignees(
    *,
    actor: EstablishmentMembership,
    pilot_business_unit: BusinessUnit,
    establishment_id: uuid.UUID,
    assignees: list[dict] | None,
) -> list[ValidatedAssigneePayload]:
    _assert_staff_self_assignee_payload(
        actor=actor,
        pilot_business_unit=pilot_business_unit,
        assignees=assignees,
    )
    return _validate_assignee_payloads(
        establishment_id=establishment_id,
        assignees=[
            {
                "membership_id": actor.id,
                "business_unit_id": pilot_business_unit.id,
            }
        ],
    )


def _validate_execution_has_content(
    *,
    task_count: int,
    assignee_count: int,
) -> None:
    if task_count == 0 and assignee_count == 0:
        raise ActionPlanValidationError("At least one task or assignee is required.")


def _validate_cross_pole_tasks_allowed(
    *,
    actor: EstablishmentMembership,
    pilot_business_unit: BusinessUnit,
    validated_tasks: list[dict],
    creation_context: str,
) -> None:
    if creation_context == "catalog":
        return
    for task_item in validated_tasks:
        if task_item["business_unit"].id != pilot_business_unit.id:
            if not can_define_cross_pole_task(actor):
                raise ActionPlanPermissionError(
                    "Not allowed to attach tasks to a non-pilot business unit."
                )


def _validate_actor_can_assign_poles(
    *,
    actor: EstablishmentMembership,
    pilot_business_unit: BusinessUnit,
    validated_assignees: list[ValidatedAssigneePayload],
) -> None:
    for assignee in validated_assignees:
        if not can_assign_to_execution_business_unit(
            actor,
            business_unit=assignee.business_unit,
        ):
            raise ActionPlanPermissionError("Not allowed to assign members to this business unit.")


def _validate_staff_feed_create_constraints(
    *,
    created_by: EstablishmentMembership,
    pilot_business_unit: BusinessUnit,
    validated_assignees: list[ValidatedAssigneePayload],
    validated_tasks: list[dict],
    requires_validation: bool,
    source_signal_id: uuid.UUID | None,
    is_reusable: bool,
    catalog_status: str | None,
) -> None:
    if source_signal_id is not None:
        raise ActionPlanPermissionError("Not allowed to create this action plan.")
    if is_reusable or catalog_status is not None:
        raise ActionPlanPermissionError("Not allowed to create this action plan.")
    if not can_create_staff_feed_execution_plan(
        created_by,
        pilot_business_unit=pilot_business_unit,
        assignees=validated_assignees,
        tasks=validated_tasks,
        requires_validation=requires_validation,
    ):
        raise ActionPlanPermissionError("Not allowed to create this action plan.")


def _create_plan_tasks(
    *,
    action_plan: ActionPlan,
    validated_tasks: list[dict],
) -> list[ActionPlanTask]:
    if not validated_tasks:
        return []
    return ActionPlanTask.objects.bulk_create(
        [
            ActionPlanTask(
                action_plan=action_plan,
                business_unit=task_item["business_unit"],
                task=task_item["task"],
                description=task_item["description"],
                deadline_at=task_item.get("deadline_at"),
                assigned_membership=task_item.get("assigned_membership"),
                position=task_item["position"],
            )
            for task_item in validated_tasks
        ]
    )


def _ensure_execution_teams(
    *,
    execution: ActionPlanExecution,
    pilot_business_unit: BusinessUnit,
    business_unit_ids: set[uuid.UUID],
) -> dict[uuid.UUID, ActionPlanExecutionTeam]:
    teams_by_bu_id: dict[uuid.UUID, ActionPlanExecutionTeam] = {}
    ordered_bu_ids = sorted(business_unit_ids, key=str)
    for business_unit_id in ordered_bu_ids:
        team = ActionPlanExecutionTeam.objects.create(
            action_plan_execution=execution,
            business_unit_id=business_unit_id,
            is_pilot=business_unit_id == pilot_business_unit.id,
        )
        teams_by_bu_id[business_unit_id] = team
    return teams_by_bu_id


def _collect_involved_business_unit_ids(
    *,
    pilot_business_unit: BusinessUnit,
    plan_tasks: list[ActionPlanTask],
    assignees: list[ValidatedAssigneePayload],
) -> set[uuid.UUID]:
    business_unit_ids = {pilot_business_unit.id}
    for plan_task in plan_tasks:
        business_unit_ids.add(plan_task.business_unit_id)
    for assignee in assignees:
        business_unit_ids.add(assignee.business_unit.id)
    return business_unit_ids


def _materialize_execution_structure(
    *,
    execution: ActionPlanExecution,
    pilot_business_unit: BusinessUnit,
    plan_tasks: list[ActionPlanTask],
    assignees: list[ValidatedAssigneePayload],
) -> None:
    business_unit_ids = _collect_involved_business_unit_ids(
        pilot_business_unit=pilot_business_unit,
        plan_tasks=plan_tasks,
        assignees=assignees,
    )
    teams_by_bu_id = _ensure_execution_teams(
        execution=execution,
        pilot_business_unit=pilot_business_unit,
        business_unit_ids=business_unit_ids,
    )

    if assignees:
        ActionPlanAssignee.objects.bulk_create(
            [
                ActionPlanAssignee(
                    action_plan_execution=execution,
                    execution_team=teams_by_bu_id[assignee.business_unit.id],
                    membership=assignee.membership,
                    start_at=assignee.start_at,
                    visible_from=assignee.visible_from,
                    end_at=assignee.end_at,
                )
                for assignee in assignees
            ]
        )

    if plan_tasks:
        ActionPlanExecutionTask.objects.bulk_create(
            [
                ActionPlanExecutionTask(
                    action_plan_execution=execution,
                    execution_team=teams_by_bu_id[plan_task.business_unit_id],
                    action_plan_task=plan_task,
                    task=plan_task.task,
                    position=plan_task.position,
                    status=TASK_STATUS_PENDING,
                    **_execution_task_snapshot_fields(plan_task=plan_task),
                )
                for plan_task in plan_tasks
            ]
        )


def initial_execution_status(
    *,
    start_at: datetime | None,
    now: datetime | None = None,
) -> str:
    resolved_now = now or timezone.now()
    if start_at is not None and start_at > resolved_now:
        return EXECUTION_STATUS_SCHEDULED
    return EXECUTION_STATUS_IN_PROGRESS


def execution_visibility_is_due(
    *,
    execution: ActionPlanExecution,
    now: datetime | None = None,
) -> bool:
    resolved_now = now or timezone.now()
    return execution.visible_from is None or execution.visible_from <= resolved_now


def _create_execution_record(
    *,
    action_plan: ActionPlan | None,
    establishment_id: uuid.UUID,
    created_by: EstablishmentMembership,
    pilot_business_unit: BusinessUnit,
    title: str,
    description: str,
    requires_validation: bool,
    source_signal_id: uuid.UUID | None = None,
    action_plan_schedule: ActionPlanSchedule | None = None,
    chronology_owner_membership: EstablishmentMembership | None = None,
    use_shared_chronology: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    visible_from: datetime | None = None,
    occurrence_date=None,
    affected_business_unit=None,
    responsible_business_unit=None,
    activity_subject=None,
) -> ActionPlanExecution:
    now = timezone.now()
    if use_shared_chronology:
        chronology_owner_membership = None
    elif chronology_owner_membership is None:
        raise ActionPlanValidationError(
            "Individual chronology requires a chronology owner membership.",
        )
    return ActionPlanExecution.objects.create(
        action_plan=action_plan,
        action_plan_schedule=action_plan_schedule,
        chronology_owner_membership=chronology_owner_membership,
        establishment_id=establishment_id,
        source_signal_id=source_signal_id,
        created_by=created_by,
        title=title,
        description=description,
        pilot_business_unit=pilot_business_unit,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        requires_validation=requires_validation,
        use_shared_chronology=use_shared_chronology,
        status=initial_execution_status(start_at=start_at, now=now),
        occurrence_date=occurrence_date,
        start_at=start_at,
        visible_from=visible_from,
        end_at=end_at,
        last_activity_at=now,
    )


def _lock_execution_for_write(*, execution_id: uuid.UUID) -> ActionPlanExecution:
    return ActionPlanExecution.objects.select_for_update().get(pk=execution_id)


def _lock_execution_for_transition(*, execution_id: uuid.UUID) -> ActionPlanExecution:
    return _lock_execution_for_write(execution_id=execution_id)


def _lock_execution_task_after_execution(
    *,
    execution: ActionPlanExecution,
    task_execution_id: uuid.UUID,
) -> ActionPlanExecutionTask:
    task_execution = (
        ActionPlanExecutionTask.objects.select_for_update()
        .select_related(
            "action_plan_execution",
            "execution_team__business_unit",
        )
        .filter(id=task_execution_id, action_plan_execution_id=execution.id)
        .first()
    )
    if task_execution is None:
        raise ActionPlanValidationError("Task execution not found.")
    return task_execution


def _lock_all_execution_tasks_after_execution(
    *,
    execution: ActionPlanExecution,
) -> list[ActionPlanExecutionTask]:
    return list(
        ActionPlanExecutionTask.objects.select_for_update()
        .select_related("execution_team__business_unit")
        .filter(action_plan_execution_id=execution.id)
        .order_by("id")
    )


@transaction.atomic
def update_action_plan(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
    title: str | None = None,
    description: str | None = None,
    requires_validation: bool | None = None,
    tasks: list[dict] | None = None,
) -> ActionPlan:
    if not can_manage_action_plan(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to update this action plan.")

    update_fields = ["updated_at"]
    if title is not None:
        action_plan.title = _normalize_title(title)
        update_fields.append("title")
    if description is not None:
        action_plan.description = _normalize_description(description)
        update_fields.append("description")
    if requires_validation is not None:
        action_plan.requires_validation = requires_validation
        update_fields.append("requires_validation")
    action_plan.save(update_fields=update_fields)
    if tasks is not None:
        replace_action_plan_tasks(
            action_plan=action_plan,
            actor=actor,
            tasks=tasks,
        )
    from houston.action_plans.realtime import schedule_action_plan_invalidation

    schedule_action_plan_invalidation(action_plan=action_plan, reason="action_plan.updated")
    return action_plan


@transaction.atomic
def replace_action_plan_tasks(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
    tasks: list[dict],
) -> list[ActionPlanTask]:
    if not can_manage_action_plan(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to update this action plan.")

    validated_tasks = _validate_task_payloads(
        establishment_id=action_plan.establishment_id,
        tasks=tasks,
        pilot_business_unit=action_plan.pilot_business_unit,
        actor=actor,
    )
    _validate_cross_pole_tasks_allowed(
        actor=actor,
        pilot_business_unit=action_plan.pilot_business_unit,
        validated_tasks=validated_tasks,
        creation_context="direct",
    )
    ActionPlanTask.objects.filter(action_plan=action_plan).delete()
    return _create_plan_tasks(action_plan=action_plan, validated_tasks=validated_tasks)


@transaction.atomic
def activate_action_plan(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
) -> ActionPlan:
    if not can_manage_action_plan(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to activate this action plan.")

    if not action_plan.is_reusable:
        raise ActionPlanValidationError("Only reusable action plans can be activated.")
    action_plan.catalog_status = CATALOG_STATUS_ACTIVE
    action_plan.save(update_fields=["catalog_status", "updated_at"])
    from houston.action_plans.realtime import schedule_action_plan_invalidation

    schedule_action_plan_invalidation(action_plan=action_plan, reason="action_plan.updated")
    return action_plan


@transaction.atomic
def deactivate_action_plan(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
) -> ActionPlan:
    if not can_manage_action_plan(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to deactivate this action plan.")
    if not action_plan.is_reusable:
        raise ActionPlanValidationError("Only reusable action plans can be deactivated.")

    from houston.action_plans.schedule_services import (
        deactivate_schedules_for_catalog_deactivation,
    )

    deactivate_schedules_for_catalog_deactivation(action_plan=action_plan)

    action_plan.catalog_status = CATALOG_STATUS_INACTIVE
    action_plan.save(update_fields=["catalog_status", "updated_at"])
    from houston.action_plans.realtime import schedule_action_plan_invalidation

    schedule_action_plan_invalidation(action_plan=action_plan, reason="action_plan.updated")
    return action_plan


@transaction.atomic
def create_action_plan(
    *,
    establishment_id: uuid.UUID,
    created_by: EstablishmentMembership,
    pilot_business_unit_id: uuid.UUID,
    title: str,
    description: str = "",
    requires_validation: bool = True,
    is_reusable: bool = True,
    catalog_status: str | None = CATALOG_STATUS_ACTIVE,
    tasks: list[dict] | None = None,
) -> ActionPlan:
    pilot_business_unit = _validate_business_unit_in_establishment(
        establishment_id=establishment_id,
        business_unit_id=pilot_business_unit_id,
    )
    if not can_create_action_plan(
        created_by,
        establishment_id=establishment_id,
        pilot_business_unit=pilot_business_unit,
    ):
        raise ActionPlanPermissionError("Not allowed to create this action plan.")

    normalized_title = _normalize_title(title)
    normalized_description = _normalize_description(description)
    validated_tasks = _validate_task_payloads(
        establishment_id=establishment_id,
        tasks=tasks or [],
        pilot_business_unit=pilot_business_unit,
        actor=created_by,
    )
    _validate_cross_pole_tasks_allowed(
        actor=created_by,
        pilot_business_unit=pilot_business_unit,
        validated_tasks=validated_tasks,
        creation_context="direct",
    )

    action_plan = ActionPlan.objects.create(
        establishment_id=establishment_id,
        created_by=created_by,
        pilot_business_unit=pilot_business_unit,
        title=normalized_title,
        description=normalized_description,
        requires_validation=requires_validation,
        is_reusable=is_reusable,
        catalog_status=catalog_status,
    )
    _create_plan_tasks(action_plan=action_plan, validated_tasks=validated_tasks)
    from houston.action_plans.realtime import schedule_action_plan_invalidation

    schedule_action_plan_invalidation(action_plan=action_plan, reason="action_plan.created")
    return action_plan


@transaction.atomic
def create_action_plan_with_execution(
    *,
    establishment_id: uuid.UUID,
    created_by: EstablishmentMembership,
    pilot_business_unit_id: uuid.UUID,
    title: str,
    description: str = "",
    requires_validation: bool = True,
    tasks: list[dict] | None = None,
    assignees: list[dict] | None = None,
    source_signal_id: uuid.UUID | None = None,
    issue_focus: str | None = None,
    is_reusable: bool = False,
    catalog_status: str | None = None,
    use_shared_chronology: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    visible_from: datetime | None = None,
    occurrence_date=None,
) -> tuple[ActionPlan, ActionPlanExecution]:
    pilot_business_unit = _validate_business_unit_in_establishment(
        establishment_id=establishment_id,
        business_unit_id=pilot_business_unit_id,
    )
    validated_tasks = _validate_task_payloads(
        establishment_id=establishment_id,
        tasks=tasks or [],
        pilot_business_unit=pilot_business_unit,
        actor=created_by,
    )
    if source_signal_id is not None:
        use_shared_chronology = True

    requested_assignees = assignees or []
    if not requested_assignees:
        use_shared_chronology = True
    elif not use_shared_chronology and len(requested_assignees) > 1:
        raise ActionPlanValidationError(
            "Individual chronology with multiple assignees requires planning-submit.",
        )

    chronology_owner = None
    resolved_start_at = start_at
    resolved_end_at = end_at
    resolved_visible_from = visible_from

    if created_by.role == EstablishmentMembership.Role.STAFF:
        validated_assignees = _validate_assignee_payloads(
            establishment_id=establishment_id,
            assignees=requested_assignees,
        )
        if not use_shared_chronology and validated_assignees:
            owner = validated_assignees[0]
            chronology_owner = owner.membership
            resolved_start_at = owner.start_at if owner.start_at is not None else start_at
            resolved_end_at = owner.end_at if owner.end_at is not None else end_at
            resolved_visible_from = (
                owner.visible_from if owner.visible_from is not None else visible_from
            )
    else:
        initial_assignees = _validate_assignee_payloads(
            establishment_id=establishment_id,
            assignees=requested_assignees,
        )
        if not use_shared_chronology and initial_assignees:
            owner = initial_assignees[0]
            chronology_owner = owner.membership
            resolved_start_at = owner.start_at if owner.start_at is not None else start_at
            resolved_end_at = owner.end_at if owner.end_at is not None else end_at
            resolved_visible_from = (
                owner.visible_from if owner.visible_from is not None else visible_from
            )
        chronology = _resolve_merge_chronology(
            use_shared_chronology=use_shared_chronology,
            start_at=resolved_start_at,
            end_at=resolved_end_at,
            visible_from=resolved_visible_from,
            validated_assignees=initial_assignees,
        )
        merged_assignee_payloads = _merge_validated_task_assignees_into_assignee_payloads(
            validated_tasks=validated_tasks,
            assignee_payloads=requested_assignees,
            chronology=chronology,
        )
        validated_assignees = _validate_assignee_payloads(
            establishment_id=establishment_id,
            assignees=merged_assignee_payloads,
        )
    _validate_execution_has_content(
        task_count=len(validated_tasks),
        assignee_count=len(validated_assignees),
    )

    signal = None
    if created_by.role == EstablishmentMembership.Role.STAFF:
        _validate_staff_feed_create_constraints(
            created_by=created_by,
            pilot_business_unit=pilot_business_unit,
            validated_assignees=validated_assignees,
            validated_tasks=validated_tasks,
            requires_validation=requires_validation,
            source_signal_id=source_signal_id,
            is_reusable=is_reusable,
            catalog_status=catalog_status,
        )
    elif source_signal_id is not None:
        signal = (
            Signal.objects.filter(
                id=source_signal_id,
                establishment_id=establishment_id,
            )
            .select_related(
                "establishment",
                "affected_business_unit",
                "responsible_business_unit",
                "activity_subject",
                "activity_subject__business_unit",
            )
            .first()
        )
        if signal is None:
            raise ActionPlanValidationError("Invalid signal.")
        from houston.signals.services import _lock_signals_by_uuid_order

        signal = _lock_signals_by_uuid_order(signal)[0]
        _validate_linked_signal_active(signal=signal)
        if not can_create_linked_action_plan(created_by, signal=signal):
            raise ActionPlanPermissionError("Not allowed to create this action plan.")
        _validate_linked_signal_pilot_consistency(
            signal=signal,
            pilot_business_unit=pilot_business_unit,
            actor=created_by,
        )
        if signal.responsible_business_unit_id is None:
            effective_focus = _resolve_effective_issue_focus_for_linked_create(
                signal=signal,
                pilot_business_unit=pilot_business_unit,
                requested_issue_focus=issue_focus,
            )
            signal = _qualify_linked_signal_for_create(
                signal=signal,
                actor=created_by,
                pilot_business_unit=pilot_business_unit,
                issue_focus=effective_focus,
            )
        elif not can_create_action_plan(
            created_by,
            establishment_id=establishment_id,
            pilot_business_unit=pilot_business_unit,
        ):
            raise ActionPlanPermissionError("Not allowed to create this action plan.")
    elif not can_create_action_plan(
        created_by,
        establishment_id=establishment_id,
        pilot_business_unit=pilot_business_unit,
    ):
        raise ActionPlanPermissionError("Not allowed to create this action plan.")

    _validate_cross_pole_tasks_allowed(
        actor=created_by,
        pilot_business_unit=pilot_business_unit,
        validated_tasks=validated_tasks,
        creation_context="direct",
    )
    if created_by.role != EstablishmentMembership.Role.STAFF:
        _validate_actor_can_assign_poles(
            actor=created_by,
            pilot_business_unit=pilot_business_unit,
            validated_assignees=validated_assignees,
        )

    normalized_title = _normalize_title(title)
    normalized_description = _normalize_description(description)

    affected_business_unit = signal.affected_business_unit if signal is not None else None
    responsible_business_unit = (
        signal.responsible_business_unit if signal is not None else None
    )
    activity_subject = signal.activity_subject if signal is not None else None

    action_plan = ActionPlan.objects.create(
        establishment_id=establishment_id,
        created_by=created_by,
        pilot_business_unit=pilot_business_unit,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        title=normalized_title,
        description=normalized_description,
        requires_validation=requires_validation,
        is_reusable=is_reusable,
        catalog_status=catalog_status,
    )
    plan_tasks = _create_plan_tasks(action_plan=action_plan, validated_tasks=validated_tasks)

    execution = _create_execution_record(
        action_plan=action_plan,
        establishment_id=establishment_id,
        created_by=created_by,
        pilot_business_unit=pilot_business_unit,
        title=normalized_title,
        description=normalized_description,
        requires_validation=requires_validation,
        source_signal_id=signal.id if signal is not None else None,
        chronology_owner_membership=chronology_owner,
        use_shared_chronology=use_shared_chronology,
        start_at=resolved_start_at,
        end_at=resolved_end_at,
        visible_from=resolved_visible_from,
        occurrence_date=occurrence_date,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
    )
    _materialize_execution_structure(
        execution=execution,
        pilot_business_unit=pilot_business_unit,
        plan_tasks=plan_tasks,
        assignees=validated_assignees,
    )
    if signal is not None:
        _activate_linked_signal_on_execution_create(signal=signal)
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
    from houston.notifications.scheduling import (
        schedule_action_plan_execution_created_notification,
    )

    if not is_reusable:
        from houston.action_plans.realtime import schedule_action_plan_invalidation

        schedule_action_plan_invalidation(action_plan=action_plan, reason="action_plan.created")
    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.created",
    )
    schedule_action_plan_execution_created_notification(
        execution_id=execution.id,
        actor_membership_id=created_by.id,
    )
    return action_plan, execution


@transaction.atomic
def create_execution_from_action_plan(
    *,
    action_plan_id: uuid.UUID,
    actor: EstablishmentMembership,
    assignees: list[dict] | None = None,
    use_shared_chronology: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    visible_from: datetime | None = None,
    occurrence_date=None,
    emit_side_effects: bool = True,
) -> ActionPlanExecution:
    action_plan = ActionPlan.objects.select_for_update().filter(id=action_plan_id).first()
    if action_plan is None:
        raise ActionPlanValidationError("Invalid action plan.")

    action_plan = (
        ActionPlan.objects.select_related(
            "establishment",
            "pilot_business_unit",
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
        )
        .prefetch_related(
            Prefetch(
                "tasks",
                queryset=ActionPlanTask.objects.select_related(
                    "assigned_membership__user",
                    "business_unit",
                ).order_by("position", "created_at"),
            )
        )
        .get(pk=action_plan.id)
    )

    if not can_use_action_plan(actor, action_plan):
        raise ActionPlanPermissionError("Not allowed to use this action plan.")

    if action_plan.catalog_status != CATALOG_STATUS_ACTIVE:
        raise ActionPlanValidationError("Action plan catalog entry is not active.")

    plan_tasks = list(action_plan.tasks.order_by("position", "created_at"))

    requested_assignees = assignees or []
    if not requested_assignees:
        use_shared_chronology = True
    elif not use_shared_chronology and len(requested_assignees) > 1:
        raise ActionPlanValidationError(
            "Individual chronology with multiple assignees requires planning-submit.",
        )

    chronology_owner = None
    resolved_start_at = start_at
    resolved_end_at = end_at
    resolved_visible_from = visible_from

    if actor.role == EstablishmentMembership.Role.STAFF:
        if not staff_catalog_action_plan_in_scope(actor, action_plan):
            raise ActionPlanPermissionError("Not allowed to use this action plan.")
        validated_assignees = _resolve_staff_catalog_self_assignees(
            actor=actor,
            pilot_business_unit=action_plan.pilot_business_unit,
            establishment_id=action_plan.establishment_id,
            assignees=assignees,
        )
        if not use_shared_chronology and validated_assignees:
            chronology_owner = validated_assignees[0].membership
            owner = validated_assignees[0]
            resolved_start_at = owner.start_at if owner.start_at is not None else start_at
            resolved_end_at = owner.end_at if owner.end_at is not None else end_at
            resolved_visible_from = (
                owner.visible_from if owner.visible_from is not None else visible_from
            )
    else:
        initial_assignees = _validate_assignee_payloads(
            establishment_id=action_plan.establishment_id,
            assignees=requested_assignees,
        )
        if not use_shared_chronology and initial_assignees:
            chronology_owner = initial_assignees[0].membership
            owner = initial_assignees[0]
            resolved_start_at = owner.start_at if owner.start_at is not None else start_at
            resolved_end_at = owner.end_at if owner.end_at is not None else end_at
            resolved_visible_from = (
                owner.visible_from if owner.visible_from is not None else visible_from
            )
        chronology = _resolve_merge_chronology(
            use_shared_chronology=use_shared_chronology,
            start_at=resolved_start_at,
            end_at=resolved_end_at,
            visible_from=resolved_visible_from,
            validated_assignees=initial_assignees,
        )
        merged_assignee_payloads = _merge_plan_task_assignees_into_assignee_payloads(
            plan_tasks=plan_tasks,
            assignee_payloads=requested_assignees,
            chronology=chronology,
        )
        validated_assignees = _validate_assignee_payloads(
            establishment_id=action_plan.establishment_id,
            assignees=merged_assignee_payloads,
        )
        _validate_actor_can_assign_poles(
            actor=actor,
            pilot_business_unit=action_plan.pilot_business_unit,
            validated_assignees=validated_assignees,
        )
    _validate_execution_has_content(
        task_count=len(plan_tasks),
        assignee_count=len(validated_assignees),
    )

    execution = _create_execution_record(
        action_plan=action_plan,
        establishment_id=action_plan.establishment_id,
        created_by=actor,
        pilot_business_unit=action_plan.pilot_business_unit,
        title=action_plan.title,
        description=action_plan.description,
        requires_validation=action_plan.requires_validation,
        chronology_owner_membership=chronology_owner,
        use_shared_chronology=use_shared_chronology,
        start_at=resolved_start_at,
        end_at=resolved_end_at,
        visible_from=resolved_visible_from,
        occurrence_date=occurrence_date,
        affected_business_unit=action_plan.affected_business_unit,
        responsible_business_unit=action_plan.responsible_business_unit,
        activity_subject=action_plan.activity_subject,
    )
    _materialize_execution_structure(
        execution=execution,
        pilot_business_unit=action_plan.pilot_business_unit,
        plan_tasks=plan_tasks,
        assignees=validated_assignees,
    )
    if emit_side_effects:
        from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
        from houston.notifications.scheduling import (
            schedule_action_plan_execution_created_notification,
        )

        schedule_action_plan_execution_invalidation(
            execution=execution,
            reason="action_plan_execution.created",
        )
        schedule_action_plan_execution_created_notification(
            execution_id=execution.id,
            actor_membership_id=actor.id,
        )
    return execution


@transaction.atomic
def mark_action_plan_execution_done(
    *,
    execution_id: uuid.UUID,
    actor_membership: EstablishmentMembership,
) -> ActionPlanExecution:
    _lock_source_signal_created_from_set_if_any(execution_id=execution_id)
    execution = _lock_execution_for_transition(execution_id=execution_id)
    if execution.status != EXECUTION_STATUS_IN_PROGRESS:
        raise ActionPlanStateError("Execution cannot be marked done in its current state.")
    if not can_mark_action_plan_execution_done(actor_membership, execution):
        raise ActionPlanPermissionError("Not allowed to mark this execution done.")

    now = timezone.now()
    execution.marked_done_at = now
    execution.last_activity_at = now
    if execution.requires_validation:
        execution.status = EXECUTION_STATUS_PENDING_VALIDATION
        execution.save(update_fields=["status", "marked_done_at", "last_activity_at", "updated_at"])
        from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
        from houston.notifications.scheduling import (
            schedule_action_plan_execution_pending_validation_notification,
        )

        schedule_action_plan_execution_invalidation(
            execution=execution,
            reason="action_plan_execution.pending_validation",
        )
        schedule_action_plan_execution_pending_validation_notification(
            execution_id=execution.id,
            actor_membership_id=actor_membership.id,
        )
        return execution

    execution.status = EXECUTION_STATUS_DONE
    execution.save(update_fields=["status", "marked_done_at", "last_activity_at", "updated_at"])
    from houston.action_plans.feed_pin_services import delete_action_plan_execution_feed_pins
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    delete_action_plan_execution_feed_pins(execution_id=execution.id)

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.done",
    )
    _sync_linked_signal_after_execution_change(execution=execution)
    return execution


@transaction.atomic
def validate_action_plan_execution(
    *,
    execution_id: uuid.UUID,
    actor_membership: EstablishmentMembership,
) -> ActionPlanExecution:
    _lock_source_signal_created_from_set_if_any(execution_id=execution_id)
    execution = _lock_execution_for_transition(execution_id=execution_id)
    if execution.status != EXECUTION_STATUS_PENDING_VALIDATION:
        raise ActionPlanStateError("Execution cannot be validated in its current state.")
    if not can_validate_action_plan_execution(actor_membership, execution):
        raise ActionPlanPermissionError("Not allowed to validate this execution.")

    now = timezone.now()
    execution.status = EXECUTION_STATUS_DONE
    execution.validated_at = now
    execution.last_activity_at = now
    execution.save(update_fields=["status", "validated_at", "last_activity_at", "updated_at"])
    from houston.action_plans.feed_pin_services import delete_action_plan_execution_feed_pins
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    delete_action_plan_execution_feed_pins(execution_id=execution.id)

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.done",
    )
    _sync_linked_signal_after_execution_change(execution=execution)
    return execution


@transaction.atomic
def reopen_action_plan_execution(
    *,
    execution_id: uuid.UUID,
    actor: EstablishmentMembership,
) -> ActionPlanExecution:
    _lock_source_signal_created_from_set_if_any(execution_id=execution_id)
    execution = _lock_execution_for_transition(execution_id=execution_id)
    if execution.status not in {
        EXECUTION_STATUS_PENDING_VALIDATION,
        EXECUTION_STATUS_DONE,
    }:
        raise ActionPlanStateError("Execution cannot be reopened in its current state.")
    if not can_reopen_action_plan_execution(actor, execution):
        raise ActionPlanPermissionError("Not allowed to reopen this execution.")

    now = timezone.now()
    execution.status = EXECUTION_STATUS_IN_PROGRESS
    execution.marked_done_at = None
    execution.validated_at = None
    execution.canceled_at = None
    execution.cancel_origin = None
    execution.last_activity_at = now
    execution.save(
        update_fields=[
            "status",
            "marked_done_at",
            "validated_at",
            "canceled_at",
            "cancel_origin",
            "last_activity_at",
            "updated_at",
        ]
    )
    _reopen_linked_signal_after_execution_reopen(execution=execution)
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
    from houston.notifications.scheduling import (
        schedule_action_plan_execution_reopened_notification,
    )

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.updated",
    )
    schedule_action_plan_execution_reopened_notification(
        execution_id=execution.id,
        actor_membership_id=actor.id,
    )
    return execution


@transaction.atomic
def cancel_action_plan_execution(
    *,
    execution_id: uuid.UUID,
    actor: EstablishmentMembership,
) -> ActionPlanExecution:
    _lock_source_signal_created_from_set_if_any(execution_id=execution_id)
    execution = _lock_execution_for_transition(execution_id=execution_id)
    if execution.status not in CANCELABLE_EXECUTION_STATUSES:
        raise ActionPlanStateError("Execution cannot be canceled in its current state.")
    if execution.status == EXECUTION_STATUS_SCHEDULED:
        if not can_cancel_scheduled_action_plan_execution(actor, execution):
            raise ActionPlanPermissionError("Not allowed to cancel this execution.")
    elif not can_cancel_action_plan_execution(actor, execution):
        raise ActionPlanPermissionError("Not allowed to cancel this execution.")

    now = timezone.now()
    execution.status = ActionPlanExecution.Status.CANCELED
    execution.canceled_at = now
    execution.cancel_origin = CANCEL_ORIGIN_MANUAL
    execution.last_activity_at = now
    execution.save(
        update_fields=[
            "status",
            "canceled_at",
            "cancel_origin",
            "last_activity_at",
            "updated_at",
        ]
    )
    from houston.action_plans.feed_pin_services import delete_action_plan_execution_feed_pins
    _sync_linked_signal_after_execution_change(execution=execution)
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation
    from houston.notifications.scheduling import (
        schedule_action_plan_execution_canceled_notification,
    )

    delete_action_plan_execution_feed_pins(execution_id=execution.id)

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.canceled",
    )
    schedule_action_plan_execution_canceled_notification(
        execution_id=execution.id,
        actor_membership_id=actor.id,
    )
    return execution


def _apply_task_observation_created(
    *,
    task_execution: ActionPlanExecutionTask,
    execution: ActionPlanExecution,
    observation: Observation,
) -> ActionPlanExecutionTask:
    now = timezone.now()
    task_execution.status = TASK_STATUS_OBSERVATION_CREATED
    task_execution.observation = observation
    task_execution.observation_created_at = now
    task_execution.save(
        update_fields=["status", "observation", "observation_created_at", "updated_at"],
    )
    touch_execution_activity(execution=execution, at=now)
    from houston.action_plans.realtime import schedule_action_plan_execution_task_invalidation

    schedule_action_plan_execution_task_invalidation(task=task_execution)
    return task_execution


@transaction.atomic
def mark_execution_task_done(
    *,
    task_execution: ActionPlanExecutionTask,
    actor: EstablishmentMembership,
) -> ActionPlanExecutionTask:
    execution = _lock_execution_for_write(
        execution_id=task_execution.action_plan_execution_id,
    )
    task_execution = _lock_execution_task_after_execution(
        execution=execution,
        task_execution_id=task_execution.id,
    )
    if not can_execute_action_plan_task(actor, task_execution):
        raise ActionPlanPermissionError("Not allowed to execute this action plan task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ActionPlanValidationError("Action plan execution is not active.")
    if task_execution.status != TASK_STATUS_PENDING:
        raise ActionPlanValidationError("Task cannot be marked done in its current state.")

    now = timezone.now()
    task_execution.status = TASK_STATUS_DONE
    task_execution.completed_at = now
    task_execution.save(update_fields=["status", "completed_at", "updated_at"])
    touch_execution_activity(execution=execution, at=now)
    from houston.action_plans.realtime import schedule_action_plan_execution_task_invalidation

    schedule_action_plan_execution_task_invalidation(task=task_execution)
    return task_execution


@transaction.atomic
def mark_execution_task_pending(
    *,
    task_execution: ActionPlanExecutionTask,
    actor: EstablishmentMembership,
) -> ActionPlanExecutionTask:
    execution = _lock_execution_for_write(
        execution_id=task_execution.action_plan_execution_id,
    )
    task_execution = _lock_execution_task_after_execution(
        execution=execution,
        task_execution_id=task_execution.id,
    )
    if not can_execute_action_plan_task(actor, task_execution):
        raise ActionPlanPermissionError("Not allowed to execute this action plan task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ActionPlanValidationError("Action plan execution is not active.")
    if task_execution.status != TASK_STATUS_DONE:
        raise ActionPlanValidationError("Task cannot be marked pending in its current state.")

    now = timezone.now()
    task_execution.status = TASK_STATUS_PENDING
    task_execution.completed_at = None
    task_execution.save(update_fields=["status", "completed_at", "updated_at"])
    touch_execution_activity(execution=execution, at=now)
    from houston.action_plans.realtime import schedule_action_plan_execution_task_invalidation

    schedule_action_plan_execution_task_invalidation(task=task_execution)
    return task_execution


@transaction.atomic
def skip_execution_task(
    *,
    task_execution: ActionPlanExecutionTask,
    actor: EstablishmentMembership,
    skipped_reason: str | None = None,
) -> ActionPlanExecutionTask:
    execution = _lock_execution_for_write(
        execution_id=task_execution.action_plan_execution_id,
    )
    task_execution = _lock_execution_task_after_execution(
        execution=execution,
        task_execution_id=task_execution.id,
    )
    if not can_execute_action_plan_task(actor, task_execution):
        raise ActionPlanPermissionError("Not allowed to execute this action plan task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ActionPlanValidationError("Action plan execution is not active.")
    if task_execution.status != TASK_STATUS_PENDING:
        raise ActionPlanValidationError("Task cannot be skipped in its current state.")

    now = timezone.now()
    task_execution.status = TASK_STATUS_SKIPPED
    task_execution.skipped_reason = _normalize_skipped_reason(skipped_reason)
    task_execution.skipped_at = now
    task_execution.save(
        update_fields=["status", "skipped_reason", "skipped_at", "updated_at"],
    )
    touch_execution_activity(execution=execution, at=now)
    from houston.action_plans.realtime import schedule_action_plan_execution_task_invalidation

    schedule_action_plan_execution_task_invalidation(task=task_execution)
    return task_execution


@transaction.atomic
def create_observation_from_execution_task(
    *,
    task_execution: ActionPlanExecutionTask,
    actor: EstablishmentMembership,
    text: str,
    temporary_upload_ids: list[uuid.UUID] | None = None,
) -> ActionPlanExecutionTask:
    execution = _lock_execution_for_write(
        execution_id=task_execution.action_plan_execution_id,
    )
    task_execution = _lock_execution_task_after_execution(
        execution=execution,
        task_execution_id=task_execution.id,
    )
    if not can_execute_action_plan_task(actor, task_execution):
        raise ActionPlanPermissionError("Not allowed to execute this action plan task.")
    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        raise ActionPlanValidationError("Action plan execution is not active.")
    if task_execution.status != TASK_STATUS_PENDING:
        raise ActionPlanValidationError("Task cannot create an observation in its current state.")

    try:
        observation = submit_observation(
            membership=actor,
            text=text,
            temporary_upload_ids=temporary_upload_ids or [],
            origin=Observation.Origin.ACTION_PLAN_TASK,
            action_plan_execution=execution,
            action_plan_execution_task=task_execution,
        )
    except ObservationValidationError as exc:
        raise ActionPlanValidationError(str(exc)) from exc

    return _apply_task_observation_created(
        task_execution=task_execution,
        execution=execution,
        observation=observation,
    )


@transaction.atomic
def create_action_plan_with_optional_schedule(
    *,
    establishment_id: uuid.UUID,
    created_by: EstablishmentMembership,
    pilot_business_unit_id: uuid.UUID,
    title: str,
    description: str = "",
    requires_validation: bool = True,
    tasks: list[dict] | None = None,
    schedule: dict,
    assignees: list[dict] | None = None,
    source_signal_id: uuid.UUID | None = None,
    use_shared_chronology: bool = False,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    visible_from: datetime | None = None,
    occurrence_date=None,
) -> tuple[ActionPlan, ActionPlanExecution | None]:
    if created_by.role == EstablishmentMembership.Role.STAFF:
        raise ActionPlanPermissionError("Not allowed to create a schedule for this action plan.")
    if source_signal_id is not None:
        raise ActionPlanValidationError("Schedule cannot be combined with signal-linked creation.")

    from houston.action_plans.schedule_services import create_action_plan_schedule
    from houston.establishments.timezone_utils import establishment_local_date

    action_plan = create_action_plan(
        establishment_id=establishment_id,
        created_by=created_by,
        pilot_business_unit_id=pilot_business_unit_id,
        title=title,
        description=description,
        requires_validation=requires_validation,
        is_reusable=True,
        catalog_status=CATALOG_STATUS_ACTIVE,
        tasks=tasks,
    )

    schedule_assignees = [
        {
            "membership_id": item["membership_id"],
            "business_unit_id": item["business_unit_id"],
        }
        for item in (schedule.get("assignees") or [])
    ]
    create_action_plan_schedule(
        action_plan=action_plan,
        actor=created_by,
        start_date=schedule.get("start_date")
        or establishment_local_date(establishment=action_plan.establishment),
        end_date=schedule["end_date"],
        start_at=schedule["start_at"],
        end_at=schedule["end_at"],
        recurrence_days=schedule["recurrence_days"],
        assignees=schedule_assignees,
        use_shared_chronology=schedule.get("use_shared_chronology", True),
    )

    one_shot_assignees = _assignee_payloads_from_dicts(assignees or [])
    if not one_shot_assignees:
        return action_plan, None

    execution = create_execution_from_action_plan(
        action_plan_id=action_plan.id,
        actor=created_by,
        assignees=one_shot_assignees,
        use_shared_chronology=use_shared_chronology,
        start_at=start_at,
        end_at=end_at,
        visible_from=visible_from,
        occurrence_date=occurrence_date,
    )
    return action_plan, execution


def _assignee_payloads_from_dicts(assignees_data: list[dict]) -> list[dict]:
    return [
        {
            "membership_id": item["membership_id"],
            "business_unit_id": item["business_unit_id"],
            "start_at": item.get("start_at"),
            "visible_from": item.get("visible_from"),
            "end_at": item.get("end_at"),
        }
        for item in assignees_data
    ]
