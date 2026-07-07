from __future__ import annotations

import uuid

from django.db import transaction

from houston.action_plans.exceptions import ActionPlanValidationError
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionFeedPin
from houston.action_plans.selectors import action_plan_execution_pinnable_by_membership
from houston.establishments.models import EstablishmentMembership


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

    _, created = ActionPlanExecutionFeedPin.objects.get_or_create(
        membership=membership,
        action_plan_execution=execution,
    )
    from houston.action_plans.realtime import schedule_action_plan_execution_invalidation

    schedule_action_plan_execution_invalidation(
        execution=execution,
        reason="action_plan_execution.feed_pin_updated",
    )
    return created


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
