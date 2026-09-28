from __future__ import annotations

import uuid

from django.db import transaction

from houston.action_plans.exceptions import (
    ActionPlanExecutionFeedPinLimitError,
    ActionPlanValidationError,
)
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionFeedPin
from houston.action_plans.selectors import action_plan_execution_pinnable_by_membership
from houston.establishments.models import EstablishmentMembership

ACTION_PLAN_EXECUTION_FEED_PIN_LIMIT = 3


def delete_action_plan_execution_feed_pins(*, execution_id: uuid.UUID) -> int:
    deleted, _ = ActionPlanExecutionFeedPin.objects.filter(
        action_plan_execution_id=execution_id,
    ).delete()
    return deleted


@transaction.atomic
def pin_action_plan_execution_for_membership(
    *,
    membership: EstablishmentMembership,
    execution_id: uuid.UUID,
    replace_execution_id: uuid.UUID | None = None,
) -> bool:
    locked_membership = EstablishmentMembership.objects.select_for_update().get(
        pk=membership.pk,
    )
    requested_execution_ids = {execution_id}
    if replace_execution_id is not None:
        requested_execution_ids.add(replace_execution_id)
    executions_by_id = {
        execution.id: execution
        for execution in ActionPlanExecution.objects.select_for_update()
        .filter(
            id__in=requested_execution_ids,
            establishment_id=locked_membership.establishment_id,
        )
        .order_by("id")
    }
    execution = executions_by_id.get(execution_id)
    if execution is None:
        raise ActionPlanValidationError("Execution not found.")
    if not action_plan_execution_pinnable_by_membership(locked_membership, execution):
        raise ActionPlanValidationError("Execution not found.")

    pins = list(
        ActionPlanExecutionFeedPin.objects.select_for_update()
        .filter(membership=locked_membership)
        .select_related("action_plan_execution")
        .order_by("pinned_at", "id")
    )
    if any(pin.action_plan_execution_id == execution.id for pin in pins):
        return False

    replaced_execution = None
    if replace_execution_id is not None:
        replacement_pin = next(
            (
                pin
                for pin in pins
                if pin.action_plan_execution_id == replace_execution_id
            ),
            None,
        )
        replacement_execution = executions_by_id.get(replace_execution_id)
        if (
            replacement_pin is None
            or replacement_execution is None
            or not action_plan_execution_pinnable_by_membership(
                locked_membership,
                replacement_execution,
            )
        ):
            raise ActionPlanValidationError("Execution not found.")
        replacement_pin.delete()
        replaced_execution = replacement_execution
    elif len(pins) >= ACTION_PLAN_EXECUTION_FEED_PIN_LIMIT:
        replacement_candidates = [
            {
                "execution_id": pin.action_plan_execution_id,
                "title": pin.action_plan_execution.title,
            }
            for pin in pins
            if action_plan_execution_pinnable_by_membership(
                locked_membership,
                pin.action_plan_execution,
            )
        ]
        raise ActionPlanExecutionFeedPinLimitError(
            replacement_candidates=replacement_candidates,
        )

    ActionPlanExecutionFeedPin.objects.create(
        membership=locked_membership,
        action_plan_execution=execution,
    )
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    if replaced_execution is not None:
        schedule_action_plan_execution_invalidation(
            execution=replaced_execution,
            reason="action_plan_execution.feed_pin_updated",
        )
    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.feed_pin_updated",
    )
    return True


@transaction.atomic
def unpin_action_plan_execution_for_membership(
    *,
    membership: EstablishmentMembership,
    execution_id: uuid.UUID,
) -> bool:
    execution = (
        ActionPlanExecution.objects.filter(
            id=execution_id,
            establishment_id=membership.establishment_id,
        )
        .first()
    )
    if execution is None:
        raise ActionPlanValidationError("Execution not found.")
    if not action_plan_execution_pinnable_by_membership(membership, execution):
        raise ActionPlanValidationError("Execution not found.")

    deleted, _ = ActionPlanExecutionFeedPin.objects.filter(
        membership=membership,
        action_plan_execution=execution,
    ).delete()
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.feed_pin_updated",
    )
    return deleted > 0
