from __future__ import annotations

from houston.action_plans.models import ActionPlan, ActionPlanAssignee, ActionPlanExecution
from houston.actions.permissions import can_access_signal_for_linked_action
from houston.establishments.membership_scope import membership_scope_covers_business_unit
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.permissions import (
    can_create_action as establishment_can_create_action,
)
from houston.establishments.permissions import (
    can_validate_action as establishment_can_validate_action,
)
from houston.establishments.role_constants import ADMIN_ROLES
from houston.signals.models import Signal
from houston.signals.permissions import signal_actionable_by_membership


def _is_active_membership_in_establishment(
    membership: EstablishmentMembership | None,
    *,
    establishment_id,
) -> bool:
    if membership is None:
        return False
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return False
    return membership.establishment_id == establishment_id


def is_action_plan_execution_assignee(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if membership is None:
        return False
    prefetched = getattr(execution, "_prefetched_objects_cache", None)
    if prefetched is not None and "assignees" in prefetched:
        return any(
            assignee.membership_id == membership.id for assignee in execution.assignees.all()
        )
    return ActionPlanAssignee.objects.filter(
        action_plan_execution_id=execution.id,
        membership_id=membership.id,
    ).exists()


def is_pilot_pole_assignee(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if membership is None:
        return False
    prefetched = getattr(execution, "_prefetched_objects_cache", None)
    if prefetched is not None and "assignees" in prefetched:
        return any(
            assignee.membership_id == membership.id and assignee.execution_team.is_pilot
            for assignee in execution.assignees.select_related("execution_team").all()
        )
    return ActionPlanAssignee.objects.filter(
        action_plan_execution_id=execution.id,
        membership_id=membership.id,
        execution_team__is_pilot=True,
    ).exists()


def manages_business_unit(
    membership: EstablishmentMembership | None,
    business_unit: BusinessUnit,
) -> bool:
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role != EstablishmentMembership.Role.MANAGER:
        return False
    return membership_scope_covers_business_unit(membership, business_unit)


def manages_pilot_pole(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if membership is None:
        return False
    pilot_business_unit = execution.pilot_business_unit
    if pilot_business_unit is None:
        return False
    return manages_business_unit(membership, pilot_business_unit)


def can_manage_contributor_pole(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
    business_unit: BusinessUnit,
) -> bool:
    if membership is None:
        return False
    if business_unit.id == execution.pilot_business_unit_id:
        return manages_pilot_pole(membership, execution)
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role != EstablishmentMembership.Role.MANAGER:
        return False
    return membership_scope_covers_business_unit(membership, business_unit)


def action_plan_visible_to_membership(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    if membership is None:
        return False
    if action_plan.establishment_id != membership.establishment_id:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(
            membership,
            action_plan.pilot_business_unit,
        )
    return False


def can_define_cross_pole_task(membership: EstablishmentMembership | None) -> bool:
    if membership is None:
        return False
    return membership.role in ADMIN_ROLES


def can_assign_to_execution_business_unit(
    membership: EstablishmentMembership | None,
    *,
    business_unit: BusinessUnit,
    pilot_business_unit: BusinessUnit,
) -> bool:
    del pilot_business_unit
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(membership, business_unit)
    return False


def can_create_staff_feed_execution_plan(
    membership: EstablishmentMembership | None,
    *,
    pilot_business_unit: BusinessUnit,
    assignees: list,
    tasks: list,
    requires_validation: bool,
) -> bool:
    if membership is None:
        return False
    if membership.role != EstablishmentMembership.Role.STAFF:
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=pilot_business_unit.establishment_id,
    ):
        return False
    if not establishment_can_create_action(membership):
        return False
    if requires_validation:
        return False
    if not membership_scope_covers_business_unit(membership, pilot_business_unit):
        return False
    if len(assignees) != 1:
        return False
    assignee = assignees[0]
    if assignee.membership.id != membership.id:
        return False
    if assignee.business_unit.id != pilot_business_unit.id:
        return False
    for task_item in tasks:
        task_business_unit = task_item["business_unit"]
        if task_business_unit.id != pilot_business_unit.id:
            return False
        if not membership_scope_covers_business_unit(membership, task_business_unit):
            return False
    return True


def can_mark_action_plan_execution_done(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if execution.status != ActionPlanExecution.Status.IN_PROGRESS:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if manages_pilot_pole(membership, execution):
        return True
    return is_pilot_pole_assignee(membership, execution)


def can_validate_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if not execution.requires_validation:
        return False
    if execution.status != ActionPlanExecution.Status.PENDING_VALIDATION:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return manages_pilot_pole(membership, execution)


def can_reopen_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if execution.status not in {
        ActionPlanExecution.Status.PENDING_VALIDATION,
        ActionPlanExecution.Status.DONE,
    }:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return manages_pilot_pole(membership, execution)


def can_cancel_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    from houston.action_plans.constants import ACTIVE_EXECUTION_STATUSES

    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        return False
    if membership is None:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return manages_pilot_pole(membership, execution)


def can_create_action_plan(
    membership: EstablishmentMembership | None,
    *,
    establishment_id,
    pilot_business_unit: BusinessUnit | None = None,
) -> bool:
    if not establishment_can_create_action(membership):
        return False
    if not _is_active_membership_in_establishment(membership, establishment_id=establishment_id):
        return False
    if membership is None:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    if pilot_business_unit is None:
        return membership.role == EstablishmentMembership.Role.MANAGER
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(membership, pilot_business_unit)
    return False


def can_create_linked_action_plan(
    membership: EstablishmentMembership | None,
    *,
    signal: Signal,
) -> bool:
    if not establishment_can_create_action(membership):
        return False
    if membership is None:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if membership.role in ADMIN_ROLES:
        return can_access_signal_for_linked_action(membership, signal)
    if not can_access_signal_for_linked_action(membership, signal):
        return False
    return signal_actionable_by_membership(membership, signal)


def can_use_action_plan(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    from houston.action_plans.constants import CATALOG_STATUS_ACTIVE

    if not action_plan.is_reusable:
        return False
    if action_plan.catalog_status != CATALOG_STATUS_ACTIVE:
        return False
    return action_plan_visible_to_membership(membership, action_plan)
