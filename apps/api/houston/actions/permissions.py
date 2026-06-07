from __future__ import annotations

from houston.actions.constants import ACTIVE_ACTION_STATUSES
from houston.actions.models import Action
from houston.establishments.membership_scope import membership_scope_covers_business_unit
from houston.establishments.models import BusinessUnit, EstablishmentMembership
from houston.establishments.permissions import (
    can_create_action as establishment_can_create_action,
)
from houston.establishments.permissions import (
    can_validate_action as establishment_can_validate_action,
)
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import Signal
from houston.signals.permissions import (
    signal_actionable_by_membership,
    signal_matches_membership_scope,
)

_ADMIN_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }
)


def can_access_signal_for_linked_action(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    return signal_matches_membership_scope(membership, signal)


def action_visible_in_membership_scope(
    membership: EstablishmentMembership,
    action: Action,
) -> bool:
    if membership.role in _ADMIN_ROLES:
        return True

    if action.signal_id is not None:
        if (
            action.affected_business_unit_id is not None
            and membership_scope_covers_business_unit(
                membership,
                action.affected_business_unit,
            )
        ):
            return True
        if (
            action.responsible_business_unit_id is not None
            and membership_scope_covers_business_unit(
                membership,
                action.responsible_business_unit,
            )
        ):
            return True
        return False

    if action.responsible_business_unit_id is None:
        return False
    return membership_scope_covers_business_unit(
        membership,
        action.responsible_business_unit,
    )


def action_actionable_by_membership(
    membership: EstablishmentMembership,
    action: Action,
) -> bool:
    if membership.role in _ADMIN_ROLES:
        return True
    if action.responsible_business_unit_id is None:
        return False
    return membership_scope_covers_business_unit(
        membership,
        action.responsible_business_unit,
    )


def action_visible_to_membership(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if action.assigned_to_id == membership.id:
        return True
    if action.created_by_id == membership.id:
        return True
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action_visible_in_membership_scope(membership, action)
    return False


def can_create_free_action(
    membership: EstablishmentMembership | None,
    *,
    business_unit: BusinessUnit,
) -> bool:
    if not establishment_can_create_action(membership):
        return False
    if membership is None:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return membership_scope_covers_business_unit(membership, business_unit)
    return False


def can_create_linked_action(
    membership: EstablishmentMembership | None,
    *,
    signal: Signal,
) -> bool:
    if not establishment_can_create_action(membership):
        return False
    if membership is None:
        return False
    if membership.role in _ADMIN_ROLES:
        return can_access_signal_for_linked_action(membership, signal)
    if not can_access_signal_for_linked_action(membership, signal):
        return False
    return signal_actionable_by_membership(membership, signal)


def can_accept_action(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if action.status not in {Action.Status.OPEN, Action.Status.REOPENED}:
        return False
    return action.assigned_to_id == membership.id


def can_mark_action_done(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if action.status != Action.Status.IN_PROGRESS:
        return False
    return action.assigned_to_id == membership.id


def can_validate_action_on_object(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if action.status != Action.Status.PENDING_VALIDATION:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action.created_by_id == membership.id
    return False


def can_reopen_action(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if action.status not in {Action.Status.PENDING_VALIDATION, Action.Status.DONE}:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action.created_by_id == membership.id
    return False


def can_cancel_action(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if action.status not in ACTIVE_ACTION_STATUSES:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action.created_by_id == membership.id
    return False


def can_reassign_action(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if not establishment_can_validate_action(membership):
        return False
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if action.status in {Action.Status.DONE, Action.Status.CANCELED}:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action_actionable_by_membership(membership, action)
    return False


def can_update_action_due_at(
    membership: EstablishmentMembership | None,
    action: Action,
) -> bool:
    if membership is None:
        return False
    if action.establishment_id != membership.establishment_id:
        return False
    if action.status in {Action.Status.DONE, Action.Status.CANCELED}:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    if membership.role == EstablishmentMembership.Role.MANAGER:
        return action.created_by_id == membership.id
    return False
