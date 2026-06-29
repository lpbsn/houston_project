from __future__ import annotations

from houston.action_plans.models import ActionPlan, ActionPlanExecution
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import (
    can_create_action as establishment_can_create_action,
)
from houston.establishments.role_constants import ADMIN_ROLES
from houston.signals.models import Signal


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


def can_mark_action_plan_execution_done(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    """Lot 2B will implement §26.4 (pilot assignee, pilot manager, not contributor)."""
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if execution.status != ActionPlanExecution.Status.IN_PROGRESS:
        return False
    return membership.role in ADMIN_ROLES


def can_validate_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    """Lot 2B will implement §8 (pilot manager, Director/Owner)."""
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    if not execution.requires_validation:
        return False
    if execution.status != ActionPlanExecution.Status.PENDING_VALIDATION:
        return False
    return membership.role in ADMIN_ROLES


def can_reopen_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    """Lot 2B will implement full reopen RBAC."""
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
    return membership.role in ADMIN_ROLES


def can_cancel_action_plan_execution(
    membership: EstablishmentMembership | None,
    execution: ActionPlanExecution,
) -> bool:
    """Lot 2B will implement full cancel RBAC."""
    if not _is_active_membership_in_establishment(
        membership,
        establishment_id=execution.establishment_id,
    ):
        return False
    from houston.action_plans.constants import ACTIVE_EXECUTION_STATUSES

    if execution.status not in ACTIVE_EXECUTION_STATUSES:
        return False
    return membership.role in ADMIN_ROLES


def can_create_action_plan(
    membership: EstablishmentMembership | None,
    *,
    establishment_id,
) -> bool:
    """Lot 2B will implement scope and role rules for plan creation."""
    if not establishment_can_create_action(membership):
        return False
    return _is_active_membership_in_establishment(membership, establishment_id=establishment_id)


def can_create_linked_action_plan(
    membership: EstablishmentMembership | None,
    *,
    signal: Signal,
) -> bool:
    """Lot 2B will implement signal-linked create RBAC."""
    if not can_create_action_plan(membership, establishment_id=signal.establishment_id):
        return False
    if membership is None:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    return signal.establishment_id == membership.establishment_id


def can_use_action_plan(
    membership: EstablishmentMembership | None,
    action_plan: ActionPlan,
) -> bool:
    """Lot 2B will implement catalog use RBAC."""
    if not can_create_action_plan(membership, establishment_id=action_plan.establishment_id):
        return False
    if not action_plan.is_reusable:
        return False
    from houston.action_plans.constants import CATALOG_STATUS_ACTIVE

    return action_plan.catalog_status == CATALOG_STATUS_ACTIVE
