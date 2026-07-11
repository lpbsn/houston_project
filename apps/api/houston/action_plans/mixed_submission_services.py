from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db import IntegrityError, transaction
from django.utils import timezone

from houston.action_plans.exceptions import (
    ActionPlanPermissionError,
    ActionPlanServiceError,
    ActionPlanValidationError,
    MixedSubmissionActorConflict,
    MixedSubmissionPayloadConflict,
    MixedSubmissionStepError,
)
from houston.action_plans.mixed_submission_hash import compute_mixed_request_hash
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanExecution,
    ActionPlanMixedOutboxEntry,
    ActionPlanMixedSubmission,
)
from houston.action_plans.permissions import (
    can_create_action_plan_schedule,
    can_use_action_plan,
)
from houston.action_plans.schedule_services import create_action_plan_schedule
from houston.action_plans.services import create_execution_from_action_plan
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import is_valid_membership
from houston.establishments.timezone_utils import establishment_local_date
from houston.notifications.recipients import resolve_action_plan_execution_created_recipients
from houston.notifications.scheduling import _resolve_execution_created_event_key

_MIXED_SUBMIT_PERMISSION_DENIED = (
    "Not allowed to submit mixed planning for this action plan."
)


@dataclass(frozen=True)
class MixedSubmissionResult:
    execution: ActionPlanExecution
    schedule_id: uuid.UUID
    replayed: bool


def _assert_mixed_submit_access(
    *,
    actor: EstablishmentMembership,
    action_plan: ActionPlan,
) -> None:
    if not is_valid_membership(actor):
        raise ActionPlanPermissionError(_MIXED_SUBMIT_PERMISSION_DENIED)
    if actor.establishment_id != action_plan.establishment_id:
        raise ActionPlanPermissionError(_MIXED_SUBMIT_PERMISSION_DENIED)
    if not can_use_action_plan(actor, action_plan):
        raise ActionPlanPermissionError(_MIXED_SUBMIT_PERMISSION_DENIED)
    if not can_create_action_plan_schedule(actor, action_plan):
        raise ActionPlanPermissionError(_MIXED_SUBMIT_PERMISSION_DENIED)


def _build_replay_result(
    *,
    submission: ActionPlanMixedSubmission,
    actor: EstablishmentMembership,
    request_hash: str,
) -> MixedSubmissionResult:
    if submission.created_by_id != actor.id:
        raise MixedSubmissionActorConflict("Mixed submission belongs to another actor.")
    if submission.request_hash != request_hash:
        raise MixedSubmissionPayloadConflict("Mixed submission payload does not match.")
    if submission.schedule_id is None or submission.execution_id is None:
        raise ActionPlanValidationError("Mixed submission is incomplete.")

    execution = ActionPlanExecution.objects.get(id=submission.execution_id)
    return MixedSubmissionResult(
        execution=execution,
        schedule_id=submission.schedule_id,
        replayed=True,
    )


def _build_outbox_entries(
    *,
    submission: ActionPlanMixedSubmission,
    executions: list[ActionPlanExecution],
    actor_membership_id: uuid.UUID,
    now: datetime,
) -> list[ActionPlanMixedOutboxEntry]:
    entries: list[ActionPlanMixedOutboxEntry] = []
    client_submission_id = submission.submission_id

    for execution in executions:
        effect_key = (
            f"mixed:{client_submission_id}:realtime_invalidation:{execution.id}"
        )
        entries.append(
            ActionPlanMixedOutboxEntry(
                mixed_submission=submission,
                effect_key=effect_key,
                effect_type=ActionPlanMixedOutboxEntry.EffectType.REALTIME_INVALIDATION,
                payload={
                    "establishment_id": str(execution.establishment_id),
                    "subject_type": "action_plan_execution",
                    "reason": "action_plan_execution.created",
                    "entity_id": str(execution.id),
                },
                status=ActionPlanMixedOutboxEntry.Status.PENDING,
                available_at=now,
            )
        )

        event_key = _resolve_execution_created_event_key(execution=execution)
        recipients = resolve_action_plan_execution_created_recipients(execution=execution)
        for recipient in recipients:
            recipient_effect_key = (
                f"mixed:{client_submission_id}:notification:"
                f"{execution.id}:{recipient.id}"
            )
            idempotency_key = (
                f"action_plan.mixed:{client_submission_id}:{event_key}:{recipient.id}"
            )
            entries.append(
                ActionPlanMixedOutboxEntry(
                    mixed_submission=submission,
                    effect_key=recipient_effect_key,
                    effect_type=ActionPlanMixedOutboxEntry.EffectType.NOTIFICATION,
                    payload={
                        "execution_id": str(execution.id),
                        "recipient_membership_id": str(recipient.id),
                        "event_key": event_key,
                        "actor_membership_id": str(actor_membership_id),
                        "idempotency_key": idempotency_key,
                    },
                    status=ActionPlanMixedOutboxEntry.Status.PENDING,
                    available_at=now,
                )
            )

    return entries


@transaction.atomic
def submit_mixed_action_plan_catalog(
    *,
    action_plan: ActionPlan,
    actor: EstablishmentMembership,
    submission_id: uuid.UUID,
    schedule_body: dict,
    use_body: dict,
) -> MixedSubmissionResult:
    _assert_mixed_submit_access(actor=actor, action_plan=action_plan)
    request_hash = compute_mixed_request_hash(
        schedule_body=schedule_body,
        use_body=use_body,
    )

    try:
        with transaction.atomic():
            submission = ActionPlanMixedSubmission.objects.create(
                establishment_id=action_plan.establishment_id,
                action_plan=action_plan,
                created_by=actor,
                submission_id=submission_id,
                request_hash=request_hash,
                schedule=None,
                execution=None,
            )
    except IntegrityError:
        submission = (
            ActionPlanMixedSubmission.objects.select_for_update()
            .filter(
                establishment_id=action_plan.establishment_id,
                action_plan_id=action_plan.id,
                submission_id=submission_id,
            )
            .get()
        )
        return _build_replay_result(
            submission=submission,
            actor=actor,
            request_hash=request_hash,
        )

    now = timezone.now()
    try:
        schedule = create_action_plan_schedule(
            action_plan=action_plan,
            actor=actor,
            start_date=schedule_body.get("start_date")
            or establishment_local_date(establishment=action_plan.establishment),
            end_date=schedule_body["end_date"],
            start_at=schedule_body["start_at"],
            end_at=schedule_body["end_at"],
            recurrence_days=schedule_body["recurrence_days"],
            assignees=schedule_body.get("assignees"),
            use_shared_chronology=schedule_body.get("use_shared_chronology", False),
            emit_side_effects=False,
        )
    except (ActionPlanPermissionError, ActionPlanValidationError, ActionPlanServiceError) as exc:
        raise MixedSubmissionStepError(
            str(exc) or "Schedule failed.",
            failed_step="schedule",
        ) from exc

    try:
        execution = create_execution_from_action_plan(
            action_plan_id=action_plan.id,
            actor=actor,
            assignees=use_body.get("assignees"),
            use_shared_chronology=use_body.get("use_shared_chronology", False),
            start_at=use_body.get("start_at"),
            end_at=use_body.get("end_at"),
            visible_from=use_body.get("visible_from"),
            occurrence_date=use_body.get("occurrence_date"),
            emit_side_effects=False,
        )
    except (ActionPlanPermissionError, ActionPlanValidationError, ActionPlanServiceError) as exc:
        raise MixedSubmissionStepError(str(exc) or "Use failed.", failed_step="use") from exc

    materialized_executions = list(
        ActionPlanExecution.objects.filter(action_plan_schedule_id=schedule.id)
    )
    executions_for_outbox = list(
        {execution.id: execution for execution in [*materialized_executions, execution]}.values()
    )
    ActionPlanMixedOutboxEntry.objects.bulk_create(
        _build_outbox_entries(
            submission=submission,
            executions=executions_for_outbox,
            actor_membership_id=actor.id,
            now=now,
        )
    )

    submission.schedule_id = schedule.id
    submission.execution_id = execution.id
    submission.save(update_fields=["schedule_id", "execution_id", "updated_at"])

    return MixedSubmissionResult(
        execution=execution,
        schedule_id=schedule.id,
        replayed=False,
    )
