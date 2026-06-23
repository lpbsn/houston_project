from __future__ import annotations

from houston.establishments.membership_scope import membership_scope_covers_business_unit
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import (
    can_view_signal_feed as establishment_can_view_signal_feed,
)
from houston.establishments.role_constants import _ADMIN_ROLES
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import Signal


def can_view_signal_feed(membership: EstablishmentMembership | None) -> bool:
    return establishment_can_view_signal_feed(membership)


def signal_pole_visible_to_membership(
    membership: EstablishmentMembership,
    signal: Signal,
) -> bool:
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.responsible_business_unit_id is not None:
        if membership_scope_covers_business_unit(membership, signal.responsible_business_unit):
            return True
    if signal.affected_business_unit_id is not None:
        if membership_scope_covers_business_unit(membership, signal.affected_business_unit):
            return True
    return False


def signal_visible_in_membership_scope(
    membership: EstablishmentMembership,
    signal: Signal,
) -> bool:
    if membership.role in _ADMIN_ROLES:
        return True

    if signal.affected_business_unit_id is not None:
        if membership_scope_covers_business_unit(membership, signal.affected_business_unit):
            return True
    if signal.responsible_business_unit_id is not None:
        if membership_scope_covers_business_unit(membership, signal.responsible_business_unit):
            return True

    return False


def signal_actionable_by_membership(
    membership: EstablishmentMembership,
    signal: Signal,
) -> bool:
    if membership.role in _ADMIN_ROLES:
        return True

    if signal.responsible_business_unit_id is not None:
        return membership_scope_covers_business_unit(membership, signal.responsible_business_unit)

    return False


def signal_matches_membership_scope(
    membership: EstablishmentMembership,
    signal: Signal,
) -> bool:
    return signal_visible_in_membership_scope(membership, signal)


def can_view_signal(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return False
    return can_view_signal_feed(membership)


def can_pin_signal(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    return signal_actionable_by_membership(membership, signal)


def can_set_signal_urgency(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    return can_pin_signal(membership, signal)


def can_cancel_signal(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    return _can_cancel_or_resolve_signal(membership, signal)


def can_resolve_signal(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    return _can_cancel_or_resolve_signal(membership, signal)


def _can_cancel_or_resolve_signal(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role in _ADMIN_ROLES:
        return True
    return signal_actionable_by_membership(membership, signal)
