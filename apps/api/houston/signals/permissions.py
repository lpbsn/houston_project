from __future__ import annotations

from houston.establishments.membership_scope import membership_scope_covers_business_unit
from houston.establishments.models import ActivitySubject, BusinessUnit, EstablishmentMembership
from houston.establishments.permissions import (
    can_view_signal_feed as establishment_can_view_signal_feed,
)
from houston.establishments.role_constants import ADMIN_ROLES
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES, FEED_SIGNAL_STATUSES
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
    if membership.role in ADMIN_ROLES:
        return True
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
    if membership.role in ADMIN_ROLES:
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
    if membership.role in ADMIN_ROLES:
        return True

    if signal.responsible_business_unit_id is not None:
        return membership_scope_covers_business_unit(membership, signal.responsible_business_unit)

    return False


def signal_matches_membership_scope(
    membership: EstablishmentMembership,
    signal: Signal,
) -> bool:
    return signal_visible_in_membership_scope(membership, signal)


def can_view_signal_detail(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if not can_view_signal_feed(membership):
        return False
    if signal.status == Signal.Status.CANCELED:
        return signal_pole_visible_to_membership(membership, signal)
    if signal.status in FEED_SIGNAL_STATUSES:
        return True
    return False


def _signal_commandable_by_membership(
    membership: EstablishmentMembership | None,
    signal: Signal,
    *,
    statuses: frozenset[str],
) -> bool:
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.status not in statuses:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return signal_actionable_by_membership(membership, signal)


def can_pin_signal(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    return _signal_commandable_by_membership(
        membership,
        signal,
        statuses=frozenset({Signal.Status.OPEN}),
    )


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
    if membership.role in ADMIN_ROLES:
        return True
    return signal_actionable_by_membership(membership, signal)


def _membership_covers_business_unit(
    membership: EstablishmentMembership,
    business_unit: BusinessUnit | None,
) -> bool:
    if business_unit is None:
        return False
    return membership_scope_covers_business_unit(membership, business_unit)


def can_access_qualify_routing_endpoint(
    membership: EstablishmentMembership | None,
    signal: Signal,
) -> bool:
    """Gate for the qualify HTTP endpoint.

    Allows already-merged (typically archived) sources through so the service can
    evaluate idempotent 200 / 409. Staff always denied.

    Live path: admins always; managers need source pole visibility. Proposed-pole
    checks happen in the service after patch application.
    """
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if signal.merged_into_id is not None:
        return True
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return False
    if membership.role in ADMIN_ROLES:
        return True
    return signal_pole_visible_to_membership(membership, signal)


def can_qualify_routing(
    membership: EstablishmentMembership | None,
    signal: Signal,
    *,
    proposed_affected_business_unit: BusinessUnit | None = None,
    proposed_responsible_business_unit: BusinessUnit | None = None,
    proposed_activity_subject: ActivitySubject | None = None,
) -> bool:
    """Live qualify permission (signal not yet merged).

    Manager must cross scope on the source signal poles and on proposed poles/subject.
    """
    if membership is None:
        return False
    if signal.establishment_id != membership.establishment_id:
        return False
    if signal.merged_into_id is not None:
        return False
    if signal.status not in ACTIVE_SIGNAL_STATUSES:
        return False
    if membership.role == EstablishmentMembership.Role.STAFF:
        return False
    if membership.role in ADMIN_ROLES:
        return True

    if not signal_pole_visible_to_membership(membership, signal):
        return False

    proposed_units: list[BusinessUnit] = []
    if proposed_affected_business_unit is not None:
        proposed_units.append(proposed_affected_business_unit)
    if proposed_responsible_business_unit is not None:
        proposed_units.append(proposed_responsible_business_unit)
    if proposed_activity_subject is not None:
        proposed_units.append(proposed_activity_subject.business_unit)

    if not proposed_units:
        # Totally unclassified with no proposed poles: managers cannot qualify.
        return False

    return any(
        _membership_covers_business_unit(membership, unit) for unit in proposed_units
    )
