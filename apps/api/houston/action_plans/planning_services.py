from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanServiceError,
    ActionPlanValidationError,
    PlanningSubmissionItemError,
    PlanningSubmissionPayloadConflict,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanPlanningOutboxEntry,
    ActionPlanPlanningSubmission,
    ActionPlanSchedule,
)
from houston.action_plans.permissions import can_use_action_plan
from houston.action_plans.planning_submission_hash import compute_planning_request_hash
from houston.action_plans.schedule_services import create_action_plan_schedule_for_planning_engine
from houston.action_plans.services import (
    _create_execution_record,
    _materialize_execution_structure,
    _merge_plan_task_assignees_into_assignee_payloads,
    _resolve_merge_chronology,
    _resolve_staff_catalog_self_assignees,
    _validate_actor_can_assign_poles,
    _validate_assignee_payloads,
    _validate_execution_has_content,
    create_action_plan,
    create_execution_from_action_plan,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import is_valid_membership
from houston.establishments.timezone_utils import establishment_local_date
from houston.notifications.recipients import resolve_action_plan_execution_created_recipients
from houston.notifications.scheduling import _resolve_execution_created_event_key

_PLANNING_PERMISSION_DENIED = "Not allowed to submit planning for this action plan."
_PLANNING_SUBMISSION_UNIQUE = "uniq_action_plan_planning_submission"
_SUBMISSION_LOOKUP_ATTEMPTS = 5
_SUBMISSION_LOOKUP_DELAY_SECONDS = 0.02


@dataclass(frozen=True)
class PlanningResourceResult:
    item_id: uuid.UUID
    kind: str
    resource_id: uuid.UUID
    primary_membership_id: uuid.UUID | None
    status: str


@dataclass(frozen=True)
class PlanningSubmissionResult:
    replayed: bool
    action_plan_id: uuid.UUID | None
    executions: list[PlanningResourceResult]
    schedules: list[PlanningResourceResult]

    @property
    def summary(self) -> dict[str, int]:
        return {
            "executions_created": len(self.executions),
            "schedules_created": len(self.schedules),
        }


def assert_use_cardinality(*, use_shared_chronology: bool, assignees: list | None) -> None:
    requested = assignees or []
    if not use_shared_chronology and len(requested) > 1:
        raise ActionPlanValidationError(
            "Individual chronology with multiple assignees requires planning-submit.",
        )


def assert_schedule_cardinality(*, use_shared_chronology: bool, assignees: list | None) -> None:
    requested = assignees or []
    if not use_shared_chronology and len(requested) != 1:
        raise ActionPlanValidationError(
            "Individual chronology schedules require exactly one assignee.",
        )


def normalize_oneshot_chronology_mode(
    *,
    use_shared_chronology: bool,
    assignees: list | None,
) -> bool:
    """Tasks-only (no assignees) is shared-by-fact."""
    if not (assignees or []):
        return True
    return use_shared_chronology


def resolve_oneshot_execution_chronology(
    *,
    use_shared_chronology: bool,
    assignees: list[dict],
    start_at: datetime | None,
    end_at: datetime | None,
    visible_from: datetime | None,
) -> tuple[bool, EstablishmentMembership | None, datetime | None, datetime | None, datetime | None]:
    """Return (shared_mode, owner, start_at, end_at, visible_from)."""
    shared = normalize_oneshot_chronology_mode(
        use_shared_chronology=use_shared_chronology,
        assignees=assignees,
    )
    if shared:
        return True, None, start_at, end_at, visible_from

    if len(assignees) != 1:
        raise ActionPlanValidationError(
            "Individual chronology with multiple assignees requires planning-submit.",
        )
    primary = assignees[0]
    # assignees here are ValidatedAssigneePayload after validation in callers
    return (
        False,
        primary.membership,
        primary.start_at if primary.start_at is not None else start_at,
        primary.end_at if primary.end_at is not None else end_at,
        primary.visible_from if primary.visible_from is not None else visible_from,
    )


def _assert_planning_access(*, actor: EstablishmentMembership, action_plan: ActionPlan) -> None:
    if not is_valid_membership(actor):
        raise ActionPlanPermissionError(_PLANNING_PERMISSION_DENIED)
    if actor.establishment_id != action_plan.establishment_id:
        raise ActionPlanPermissionError(_PLANNING_PERMISSION_DENIED)
    if not can_use_action_plan(actor, action_plan):
        raise ActionPlanPermissionError(_PLANNING_PERMISSION_DENIED)


def _validate_items_structure(
    *,
    use_shared_chronology: bool,
    items: list[dict],
) -> None:
    if not items:
        raise ActionPlanValidationError("At least one planning item is required.")

    seen_item_ids: set[uuid.UUID] = set()
    individual_oneshot_principals: set[uuid.UUID] = set()

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise PlanningSubmissionItemError(
                "Invalid planning item.",
                item_index=index,
            )
        raw_item_id = item.get("item_id")
        if raw_item_id is None:
            raise PlanningSubmissionItemError(
                "item_id is required.",
                item_index=index,
            )
        item_id = uuid.UUID(str(raw_item_id))
        if item_id in seen_item_ids:
            raise PlanningSubmissionItemError(
                "Duplicate item_id in submission.",
                item_id=item_id,
                item_index=index,
            )
        seen_item_ids.add(item_id)

        kind = item.get("kind")
        if kind not in {"execution", "schedule"}:
            raise PlanningSubmissionItemError(
                "kind must be execution or schedule.",
                item_id=item_id,
                item_index=index,
            )

        if use_shared_chronology:
            assignees = item.get("assignees") or []
            if kind == "schedule":
                assert_schedule_cardinality(
                    use_shared_chronology=True,
                    assignees=assignees,
                )
            continue

        # Individual mode
        if kind == "execution":
            primary_id = item.get("primary_membership_id")
            if primary_id is None:
                raise PlanningSubmissionItemError(
                    "primary_membership_id is required for individual executions.",
                    item_id=item_id,
                    item_index=index,
                )
            primary_uuid = uuid.UUID(str(primary_id))
            if primary_uuid in individual_oneshot_principals:
                raise PlanningSubmissionItemError(
                    "Duplicate individual one-shot for the same principal.",
                    item_id=item_id,
                    item_index=index,
                )
            individual_oneshot_principals.add(primary_uuid)
        elif kind == "schedule":
            primary_id = item.get("primary_membership_id")
            if primary_id is None:
                raise PlanningSubmissionItemError(
                    "primary_membership_id is required for individual schedules.",
                    item_id=item_id,
                    item_index=index,
                )


def _result_from_snapshot(
    *,
    snapshot: dict,
    replayed: bool,
) -> PlanningSubmissionResult:
    executions = [
        PlanningResourceResult(
            item_id=uuid.UUID(str(item["item_id"])),
            kind="execution",
            resource_id=uuid.UUID(str(item["resource_id"])),
            primary_membership_id=(
                uuid.UUID(str(item["primary_membership_id"]))
                if item.get("primary_membership_id")
                else None
            ),
            status=str(item.get("status") or ""),
        )
        for item in snapshot.get("executions", [])
    ]
    schedules = [
        PlanningResourceResult(
            item_id=uuid.UUID(str(item["item_id"])),
            kind="schedule",
            resource_id=uuid.UUID(str(item["resource_id"])),
            primary_membership_id=(
                uuid.UUID(str(item["primary_membership_id"]))
                if item.get("primary_membership_id")
                else None
            ),
            status=str(item.get("status") or ""),
        )
        for item in snapshot.get("schedules", [])
    ]
    action_plan_id = snapshot.get("action_plan_id")
    return PlanningSubmissionResult(
        replayed=replayed,
        action_plan_id=uuid.UUID(str(action_plan_id)) if action_plan_id else None,
        executions=executions,
        schedules=schedules,
    )


def _build_outbox_entries(
    *,
    submission: ActionPlanPlanningSubmission,
    executions: list[ActionPlanExecution],
    actor_membership_id: uuid.UUID,
    now: datetime,
) -> list[ActionPlanPlanningOutboxEntry]:
    entries: list[ActionPlanPlanningOutboxEntry] = []
    client_submission_id = submission.submission_id

    # Batch list invalidation (one entry) using first execution id as entity anchor.
    if executions:
        first = executions[0]
        entries.append(
            ActionPlanPlanningOutboxEntry(
                planning_submission=submission,
                effect_key=f"planning:{client_submission_id}:realtime_batch",
                effect_type=ActionPlanPlanningOutboxEntry.EffectType.REALTIME_INVALIDATION,
                payload={
                    "establishment_id": str(first.establishment_id),
                    "subject_type": "action_plan_execution",
                    "reason": "action_plan_planning.submitted",
                    "entity_id": str(first.id),
                },
                status=ActionPlanPlanningOutboxEntry.Status.PENDING,
                available_at=now,
            )
        )

    for execution in executions:
        event_key = _resolve_execution_created_event_key(execution=execution)
        recipients = resolve_action_plan_execution_created_recipients(execution=execution)
        for recipient in recipients:
            recipient_effect_key = (
                f"planning:{client_submission_id}:notification:"
                f"{execution.id}:{recipient.id}"
            )
            idempotency_key = (
                f"action_plan.planning:{client_submission_id}:{event_key}:{recipient.id}"
            )
            entries.append(
                ActionPlanPlanningOutboxEntry(
                    planning_submission=submission,
                    effect_key=recipient_effect_key,
                    effect_type=ActionPlanPlanningOutboxEntry.EffectType.NOTIFICATION,
                    payload={
                        "execution_id": str(execution.id),
                        "recipient_membership_id": str(recipient.id),
                        "event_key": event_key,
                        "actor_membership_id": str(actor_membership_id),
                        "idempotency_key": idempotency_key,
                    },
                    status=ActionPlanPlanningOutboxEntry.Status.PENDING,
                    available_at=now,
                )
            )
    return entries


def _create_individual_execution(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
    item: dict,
) -> ActionPlanExecution:
    plan_tasks = list(
        action_plan.tasks.select_related("assigned_membership__user", "business_unit").order_by(
            "position",
            "created_at",
        )
    )
    primary_payload = [
        {
            "membership_id": item["primary_membership_id"],
            "business_unit_id": item["business_unit_id"],
            "start_at": item.get("start_at"),
            "visible_from": item.get("visible_from"),
            "end_at": item.get("end_at"),
        }
    ]
    if actor.role == EstablishmentMembership.Role.STAFF:
        validated_primary = _resolve_staff_catalog_self_assignees(
            actor=actor,
            pilot_business_unit=action_plan.pilot_business_unit,
            establishment_id=action_plan.establishment_id,
            assignees=primary_payload,
        )
    else:
        validated_primary = _validate_assignee_payloads(
            establishment_id=action_plan.establishment_id,
            assignees=primary_payload,
        )
        _validate_actor_can_assign_poles(
            actor=actor,
            pilot_business_unit=action_plan.pilot_business_unit,
            validated_assignees=validated_primary,
        )

    owner = validated_primary[0]
    chronology = _resolve_merge_chronology(
        use_shared_chronology=False,
        start_at=owner.start_at,
        end_at=owner.end_at,
        visible_from=owner.visible_from,
        validated_assignees=validated_primary,
    )
    merged_payloads = _merge_plan_task_assignees_into_assignee_payloads(
        plan_tasks=plan_tasks,
        assignee_payloads=primary_payload,
        chronology=chronology,
    )
    validated_assignees = _validate_assignee_payloads(
        establishment_id=action_plan.establishment_id,
        assignees=merged_payloads,
    )
    _validate_execution_has_content(
        task_count=len(plan_tasks),
        assignee_count=len(validated_assignees),
    )

    execution = _create_execution_record(
        action_plan=action_plan,
        establishment_id=action_plan.establishment_id,
        created_by=actor,
        lifecycle_actor_membership=actor,
        pilot_business_unit=action_plan.pilot_business_unit,
        title=action_plan.title,
        description=action_plan.description,
        requires_validation=action_plan.requires_validation,
        chronology_owner_membership=owner.membership,
        use_shared_chronology=False,
        start_at=owner.start_at,
        end_at=owner.end_at,
        visible_from=owner.visible_from,
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
    return execution


def _create_shared_execution(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
    item: dict,
) -> ActionPlanExecution:
    return create_execution_from_action_plan(
        action_plan_id=action_plan.id,
        actor=actor,
        assignees=item.get("assignees") or [],
        use_shared_chronology=True,
        start_at=item.get("start_at"),
        end_at=item.get("end_at"),
        visible_from=item.get("visible_from"),
        occurrence_date=item.get("occurrence_date"),
        emit_side_effects=False,
    )


def _require_schedule_item_fields(item: dict) -> tuple[object, object, object, list]:
    """Return schedule fields or raise validation error (never KeyError)."""
    end_date = item.get("end_date")
    start_at = item.get("start_at")
    end_at = item.get("end_at")
    recurrence_days = item.get("recurrence_days")
    missing: list[str] = []
    if end_date is None:
        missing.append("end_date")
    if start_at is None or (isinstance(start_at, str) and not str(start_at).strip()):
        missing.append("start_at")
    if end_at is None or (isinstance(end_at, str) and not str(end_at).strip()):
        missing.append("end_at")
    if not recurrence_days:
        missing.append("recurrence_days")
    if missing:
        raise ActionPlanValidationError(
            f"Schedule item missing required fields: {', '.join(missing)}."
        )
    return end_date, start_at, end_at, list(recurrence_days)


def _create_schedule_from_item(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
    item: dict,
    use_shared_chronology: bool,
) -> ActionPlanSchedule:
    if use_shared_chronology:
        assignees = item.get("assignees") or []
    else:
        primary_membership_id = item.get("primary_membership_id")
        business_unit_id = item.get("business_unit_id")
        if primary_membership_id is None or business_unit_id is None:
            raise ActionPlanValidationError(
                "primary_membership_id and business_unit_id are required "
                "for individual schedules."
            )
        assignees = [
            {
                "membership_id": primary_membership_id,
                "business_unit_id": business_unit_id,
            }
        ]
    assert_schedule_cardinality(
        use_shared_chronology=use_shared_chronology,
        assignees=assignees,
    )
    end_date, start_at, end_at, recurrence_days = _require_schedule_item_fields(item)
    return create_action_plan_schedule_for_planning_engine(
        action_plan=action_plan,
        actor=actor,
        start_date=item.get("start_date")
        or establishment_local_date(establishment=action_plan.establishment),
        end_date=end_date,
        start_at=start_at,
        end_at=end_at,
        recurrence_days=recurrence_days,
        assignees=assignees,
        use_shared_chronology=use_shared_chronology,
        emit_side_effects=False,
    )


def _normalize_planning_use_shared_chronology(
    *,
    use_shared_chronology: bool,
    items: list[dict],
) -> bool:
    has_any_assignee = False
    for item in items:
        if item.get("primary_membership_id") or (item.get("assignees") or []):
            has_any_assignee = True
            break
    if not has_any_assignee:
        return True
    return use_shared_chronology


def _lookup_planning_submission(
    *,
    establishment_id: uuid.UUID,
    actor: EstablishmentMembership,
    submission_id: uuid.UUID,
    request_hash: str,
) -> PlanningSubmissionResult | None:
    existing = ActionPlanPlanningSubmission.objects.filter(
        establishment_id=establishment_id,
        created_by_id=actor.id,
        submission_id=submission_id,
    ).first()
    if existing is None:
        return None
    if existing.request_hash != request_hash:
        raise PlanningSubmissionPayloadConflict(
            "Planning submission payload does not match."
        )
    return _result_from_snapshot(snapshot=existing.result_snapshot, replayed=True)


def _is_planning_submission_unique_violation(exc: IntegrityError) -> bool:
    return _PLANNING_SUBMISSION_UNIQUE in str(exc)


def _lookup_planning_submission_with_retry(
    *,
    establishment_id: uuid.UUID,
    actor: EstablishmentMembership,
    submission_id: uuid.UUID,
    request_hash: str,
) -> PlanningSubmissionResult | None:
    for attempt in range(_SUBMISSION_LOOKUP_ATTEMPTS):
        result = _lookup_planning_submission(
            establishment_id=establishment_id,
            actor=actor,
            submission_id=submission_id,
            request_hash=request_hash,
        )
        if result is not None:
            return result
        if attempt + 1 < _SUBMISSION_LOOKUP_ATTEMPTS:
            time.sleep(_SUBMISSION_LOOKUP_DELAY_SECONDS)
    return None


def _create_planning_submission_row(
    *,
    establishment_id: uuid.UUID,
    actor: EstablishmentMembership,
    submission_id: uuid.UUID,
    request_hash: str,
    action_plan: ActionPlan | None,
) -> ActionPlanPlanningSubmission | PlanningSubmissionResult:
    """Insert submission under a savepoint; resolve unique races via replay lookup."""
    try:
        with transaction.atomic():
            return ActionPlanPlanningSubmission.objects.create(
                establishment_id=establishment_id,
                created_by=actor,
                action_plan=action_plan,
                submission_id=submission_id,
                request_hash=request_hash,
                result_snapshot={},
            )
    except IntegrityError as exc:
        if not _is_planning_submission_unique_violation(exc):
            raise
        raced = _lookup_planning_submission_with_retry(
            establishment_id=establishment_id,
            actor=actor,
            submission_id=submission_id,
            request_hash=request_hash,
        )
        if raced is not None:
            return raced
        raise ActionPlanServiceError(
            "Planning submission could not be resolved after concurrent insert."
        ) from None


def create_resources_from_planning_intent(
    *,
    actor: EstablishmentMembership,
    action_plan: ActionPlan,
    submission: ActionPlanPlanningSubmission,
    use_shared_chronology: bool,
    items: list[dict],
) -> PlanningSubmissionResult:
    """Create executions/schedules/outbox for an already-authorized plan + submission."""
    now = timezone.now()
    execution_results: list[PlanningResourceResult] = []
    schedule_results: list[PlanningResourceResult] = []
    created_executions: list[ActionPlanExecution] = []

    for index, item in enumerate(items):
        item_id = uuid.UUID(str(item["item_id"]))
        kind = item["kind"]
        try:
            if kind == "execution":
                if use_shared_chronology:
                    execution = _create_shared_execution(
                        action_plan=action_plan,
                        actor=actor,
                        item=item,
                    )
                    primary_membership_id = None
                else:
                    execution = _create_individual_execution(
                        action_plan=action_plan,
                        actor=actor,
                        item=item,
                    )
                    primary_membership_id = uuid.UUID(str(item["primary_membership_id"]))
                created_executions.append(execution)
                execution_results.append(
                    PlanningResourceResult(
                        item_id=item_id,
                        kind="execution",
                        resource_id=execution.id,
                        primary_membership_id=primary_membership_id,
                        status=execution.status,
                    )
                )
            else:
                schedule = _create_schedule_from_item(
                    action_plan=action_plan,
                    actor=actor,
                    item=item,
                    use_shared_chronology=use_shared_chronology,
                )
                primary_membership_id = None
                if not use_shared_chronology:
                    primary_membership_id = uuid.UUID(str(item["primary_membership_id"]))
                schedule_results.append(
                    PlanningResourceResult(
                        item_id=item_id,
                        kind="schedule",
                        resource_id=schedule.id,
                        primary_membership_id=primary_membership_id,
                        status=schedule.status,
                    )
                )
                created_executions.extend(
                    list(ActionPlanExecution.objects.filter(action_plan_schedule_id=schedule.id))
                )
        except (
            ActionPlanPermissionError,
            ActionPlanValidationError,
            ActionPlanServiceError,
        ) as exc:
            raise PlanningSubmissionItemError(
                str(exc) or "Planning item failed.",
                item_id=item_id,
                item_index=index,
            ) from exc

    executions_for_outbox = list(
        {execution.id: execution for execution in created_executions}.values()
    )
    ActionPlanPlanningOutboxEntry.objects.bulk_create(
        _build_outbox_entries(
            submission=submission,
            executions=executions_for_outbox,
            actor_membership_id=actor.id,
            now=now,
        )
    )

    snapshot = {
        "action_plan_id": str(action_plan.id),
        "executions": [
            {
                "item_id": str(item.item_id),
                "resource_id": str(item.resource_id),
                "primary_membership_id": (
                    str(item.primary_membership_id) if item.primary_membership_id else None
                ),
                "status": item.status,
            }
            for item in execution_results
        ],
        "schedules": [
            {
                "item_id": str(item.item_id),
                "resource_id": str(item.resource_id),
                "primary_membership_id": (
                    str(item.primary_membership_id) if item.primary_membership_id else None
                ),
                "status": item.status,
            }
            for item in schedule_results
        ],
    }
    submission.action_plan = action_plan
    submission.result_snapshot = snapshot
    submission.save(update_fields=["action_plan", "result_snapshot", "updated_at"])

    return PlanningSubmissionResult(
        replayed=False,
        action_plan_id=action_plan.id,
        executions=execution_results,
        schedules=schedule_results,
    )


@transaction.atomic
def submit_action_plan_planning(
    *,
    actor: EstablishmentMembership,
    establishment_id: uuid.UUID,
    submission_id: uuid.UUID,
    use_shared_chronology: bool,
    items: list[dict],
    action_plan: ActionPlan,
) -> PlanningSubmissionResult:
    _assert_planning_access(actor=actor, action_plan=action_plan)
    if action_plan.establishment_id != establishment_id:
        raise ActionPlanPermissionError(_PLANNING_PERMISSION_DENIED)

    use_shared_chronology = _normalize_planning_use_shared_chronology(
        use_shared_chronology=use_shared_chronology,
        items=items,
    )
    _validate_items_structure(use_shared_chronology=use_shared_chronology, items=items)
    request_hash = compute_planning_request_hash(
        use_shared_chronology=use_shared_chronology,
        items=items,
    )

    replayed = _lookup_planning_submission(
        establishment_id=establishment_id,
        actor=actor,
        submission_id=submission_id,
        request_hash=request_hash,
    )
    if replayed is not None:
        return replayed

    submission_or_replay = _create_planning_submission_row(
        establishment_id=establishment_id,
        actor=actor,
        submission_id=submission_id,
        request_hash=request_hash,
        action_plan=action_plan,
    )
    if isinstance(submission_or_replay, PlanningSubmissionResult):
        return submission_or_replay

    return create_resources_from_planning_intent(
        actor=actor,
        action_plan=action_plan,
        submission=submission_or_replay,
        use_shared_chronology=use_shared_chronology,
        items=items,
    )


@transaction.atomic
def create_action_plan_with_planning(
    *,
    establishment_id: uuid.UUID,
    created_by: EstablishmentMembership,
    pilot_business_unit_id: uuid.UUID,
    title: str,
    description: str = "",
    requires_validation: bool = True,
    tasks: list[dict] | None = None,
    submission_id: uuid.UUID,
    use_shared_chronology: bool,
    items: list[dict],
) -> PlanningSubmissionResult:
    """Atomic direct create: non-reusable plan + planning resources + submission/outbox."""
    use_shared_chronology = _normalize_planning_use_shared_chronology(
        use_shared_chronology=use_shared_chronology,
        items=items,
    )
    _validate_items_structure(use_shared_chronology=use_shared_chronology, items=items)
    request_hash = compute_planning_request_hash(
        use_shared_chronology=use_shared_chronology,
        items=items,
    )

    # Idempotence check BEFORE creating ActionPlan.
    replayed = _lookup_planning_submission(
        establishment_id=establishment_id,
        actor=created_by,
        submission_id=submission_id,
        request_hash=request_hash,
    )
    if replayed is not None:
        return replayed

    submission_or_replay = _create_planning_submission_row(
        establishment_id=establishment_id,
        actor=created_by,
        submission_id=submission_id,
        request_hash=request_hash,
        action_plan=None,
    )
    if isinstance(submission_or_replay, PlanningSubmissionResult):
        return submission_or_replay

    action_plan = create_action_plan(
        establishment_id=establishment_id,
        created_by=created_by,
        pilot_business_unit_id=pilot_business_unit_id,
        title=title,
        description=description,
        requires_validation=requires_validation,
        is_reusable=False,
        catalog_status=None,
        tasks=tasks,
    )
    return create_resources_from_planning_intent(
        actor=created_by,
        action_plan=action_plan,
        submission=submission_or_replay,
        use_shared_chronology=use_shared_chronology,
        items=items,
    )
