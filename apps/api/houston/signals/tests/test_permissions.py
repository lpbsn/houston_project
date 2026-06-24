from __future__ import annotations

import pytest
from django.utils import timezone

from houston.accounts.models import User
from houston.actions.tests.conftest import build_api_membership_on_establishment
from houston.establishments.models import EstablishmentMembership
from houston.organizations.models import Organization
from houston.signals.constants import ACTIVE_SIGNAL_STATUSES
from houston.signals.models import Signal
from houston.signals.permissions import (
    can_cancel_signal,
    can_pin_signal,
    can_resolve_signal,
    can_view_signal,
    can_view_signal_feed,
    signal_actionable_by_membership,
    signal_pole_visible_to_membership,
    signal_visible_in_membership_scope,
)
from houston.testing.auth import build_api_membership
from houston.testing.factories import build_membership
from houston.testing.taxonomy import (
    create_business_unit,
    create_membership_with_business_unit_scope,
)

pytestmark = pytest.mark.django_db


def _build_signal(*, membership, business_unit=None) -> Signal:
    return Signal.objects.create(
        establishment=membership.establishment,
        title="Lighting issue",
        structured_summary="Lighting issue in bar.",
        status=Signal.Status.OPEN,
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
        last_activity_at=timezone.now(),
    )


def test_deactivated_membership_denies_signal_permissions():
    membership = build_membership(membership_status=EstablishmentMembership.Status.DEACTIVATED)
    signal = _build_signal(membership=membership)

    assert not can_view_signal_feed(membership)
    assert not can_view_signal(membership, signal)
    assert not can_pin_signal(membership, signal)


@pytest.mark.parametrize(
    "organization_status",
    [
        Organization.Status.SUSPENDED,
        Organization.Status.ARCHIVED,
    ],
)
def test_non_active_organization_denies_signal_feed(organization_status):
    membership = build_membership(organization_status=organization_status)

    assert not can_view_signal_feed(membership)


@pytest.mark.parametrize(
    "user_status",
    [
        User.Status.PENDING,
        User.Status.SUSPENDED,
        User.Status.ANONYMIZED,
    ],
)
def test_non_active_user_denies_signal_feed(user_status):
    membership = build_membership(user_status=user_status)

    assert not can_view_signal_feed(membership)


def test_signal_visibility_requires_same_establishment():
    owner = build_membership(role=EstablishmentMembership.Role.OWNER)
    outsider = build_membership()
    signal = _build_signal(membership=owner)

    assert can_view_signal(owner, signal)
    assert not can_view_signal(outsider, signal)


def test_manager_scope_limits_signal_visibility():
    membership = build_membership(role=EstablishmentMembership.Role.MANAGER)
    in_scope_bu = create_business_unit(establishment=membership.establishment, key="bar")
    out_of_scope_bu = create_business_unit(establishment=membership.establishment, key="kitchen")
    create_membership_with_business_unit_scope(membership=membership, business_unit=in_scope_bu)

    in_scope_signal = _build_signal(membership=membership, business_unit=in_scope_bu)
    out_of_scope_signal = _build_signal(membership=membership, business_unit=out_of_scope_bu)

    assert signal_visible_in_membership_scope(membership, in_scope_signal)
    assert not signal_visible_in_membership_scope(membership, out_of_scope_signal)
    assert signal_actionable_by_membership(membership, in_scope_signal)
    assert not signal_actionable_by_membership(membership, out_of_scope_signal)


def test_staff_cannot_cancel_or_resolve_signal():
    membership = build_membership(role=EstablishmentMembership.Role.STAFF)
    business_unit = create_business_unit(establishment=membership.establishment, key="bar")
    create_membership_with_business_unit_scope(membership=membership, business_unit=business_unit)
    signal = _build_signal(membership=membership, business_unit=business_unit)

    assert signal.status in ACTIVE_SIGNAL_STATUSES
    assert not can_cancel_signal(membership, signal)
    assert not can_resolve_signal(membership, signal)
    assert not can_pin_signal(membership, signal)


def test_signal_pole_visible_admin_without_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    director = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.DIRECTOR,
    )
    business_unit = create_business_unit(establishment=owner.establishment, key="bar")
    signal = _build_signal(membership=owner, business_unit=business_unit)
    signal.status = Signal.Status.CANCELED
    signal.save(update_fields=["status", "updated_at"])

    assert signal_pole_visible_to_membership(owner, signal)
    assert signal_pole_visible_to_membership(director, signal)


def test_signal_pole_visible_staff_requires_scope():
    owner = build_api_membership(role=EstablishmentMembership.Role.OWNER)
    staff = build_api_membership_on_establishment(
        owner,
        role=EstablishmentMembership.Role.STAFF,
    )
    in_scope_bu = create_business_unit(establishment=owner.establishment, key="bar")
    out_of_scope_bu = create_business_unit(establishment=owner.establishment, key="kitchen")
    create_membership_with_business_unit_scope(membership=staff, business_unit=in_scope_bu)
    in_scope_signal = _build_signal(membership=owner, business_unit=in_scope_bu)
    in_scope_signal.status = Signal.Status.CANCELED
    in_scope_signal.save(update_fields=["status", "updated_at"])
    out_of_scope_signal = _build_signal(membership=owner, business_unit=out_of_scope_bu)
    out_of_scope_signal.status = Signal.Status.CANCELED
    out_of_scope_signal.save(update_fields=["status", "updated_at"])

    assert signal_pole_visible_to_membership(staff, in_scope_signal)
    assert not signal_pole_visible_to_membership(staff, out_of_scope_signal)
