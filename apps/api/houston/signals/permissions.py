from __future__ import annotations

from houston.establishments.membership_scope import (
    membership_scope_covers_domain,
    membership_scope_covers_subject,
)
from houston.establishments.models import EstablishmentMembership
from houston.establishments.permissions import (
    can_view_signal_feed as establishment_can_view_signal_feed,
)
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import Signal

_ADMIN_ROLES = frozenset(
    {
        EstablishmentMembership.Role.OWNER,
        EstablishmentMembership.Role.DIRECTOR,
    }
)


def can_view_signal_feed(membership: EstablishmentMembership | None) -> bool:
    return establishment_can_view_signal_feed(membership)


def signal_matches_membership_scope(
    membership: EstablishmentMembership,
    signal: Signal,
) -> bool:
    if membership.role in _ADMIN_ROLES:
        return True

    if membership_scope_covers_subject(membership, signal.operational_subject):
        return True
    if membership_scope_covers_domain(membership, signal.operational_domain):
        return True

    module = signal.operational_module
    from houston.establishments.membership_scope import membership_scope_covers_module

    return membership_scope_covers_module(membership, module)


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
    return signal_matches_membership_scope(membership, signal)


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
    return signal_matches_membership_scope(membership, signal)
