from __future__ import annotations

import uuid

import pytest

from houston.establishments.membership_scope import (
    MembershipScopeInput,
    MembershipScopeType,
    build_signal_feed_scope_q_v2,
    replace_membership_scopes,
)
from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
    create_membership_with_business_unit_scope,
)
from houston.organizations.models import Organization
from houston.signals.models import Signal
from houston.signals.permissions import (
    signal_actionable_by_membership,
    signal_matches_membership_scope,
    signal_visible_in_membership_scope,
)
from houston.signals.selectors import active_signals_for_establishment, signal_feed_queryset
from houston.signals.tests.conftest import (
    create_restaurant_v3_taxonomy,
    create_v3_signal,
)

pytestmark = pytest.mark.django_db


def _create_signal(
    *,
    establishment: Establishment,
    title: str = "Test signal",
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject=None,
) -> Signal:
    from houston.establishments.tests.taxonomy_helpers import create_activity_subject

    if activity_subject is None:
        activity_subject = create_activity_subject(
            establishment=establishment,
            business_unit=responsible_business_unit,
            label="General",
        )
    return create_v3_signal(
        establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
        title=title,
    )


def _oracle_matching_ids(*, membership: EstablishmentMembership) -> set[uuid.UUID]:
    queryset = active_signals_for_establishment(establishment_id=membership.establishment_id)
    return {
        signal.id
        for signal in queryset
        if signal_matches_membership_scope(membership, signal)
    }


def _feed_personal_ids(*, membership: EstablishmentMembership) -> set[uuid.UUID]:
    return set(
        signal_feed_queryset(membership=membership, view_mode="personal").values_list(
            "id", flat=True
        )
    )


def test_build_signal_feed_scope_q_v2_returns_none_without_scopes():
    establishment = create_establishment()
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )

    assert build_signal_feed_scope_q_v2(membership=membership) is None
    assert _feed_personal_ids(membership=membership) == set()


def test_personal_feed_matches_signal_matches_membership_scope_oracle():
    establishment = create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel")
    other_unit = create_business_unit(establishment=establishment, key="other_unit")
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )
    replace_membership_scopes(
        membership=membership,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    _create_signal(
        establishment=establishment,
        title="In scope",
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
    )
    _create_signal(
        establishment=establishment,
        title="Out of scope",
        affected_business_unit=other_unit,
        responsible_business_unit=other_unit,
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )


def test_business_unit_scope_bar_does_not_see_salle_signal():
    establishment = create_establishment(name="Restaurant isolation bar")
    taxonomy = create_restaurant_v3_taxonomy(establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None

    bar_signal = _create_signal(
        establishment=establishment,
        title="Bar signal",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
    )
    salle_signal = _create_signal(
        establishment=establishment,
        title="Salle signal",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
    )

    bar_membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=bar_membership,
        business_unit=taxonomy.bar,
    )

    assert _feed_personal_ids(membership=bar_membership) == {bar_signal.id}
    assert salle_signal.id not in _feed_personal_ids(membership=bar_membership)


def test_business_unit_scope_salle_does_not_see_bar_signal():
    establishment = create_establishment(name="Restaurant isolation salle")
    taxonomy = create_restaurant_v3_taxonomy(establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    assert taxonomy.stock_subject is not None

    bar_signal = _create_signal(
        establishment=establishment,
        title="Bar signal",
        affected_business_unit=taxonomy.bar,
        responsible_business_unit=taxonomy.bar,
    )
    salle_signal = _create_signal(
        establishment=establishment,
        title="Salle signal",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
    )

    salle_membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=salle_membership,
        business_unit=taxonomy.restaurant,
    )

    assert _feed_personal_ids(membership=salle_membership) == {salle_signal.id}
    assert bar_signal.id not in _feed_personal_ids(membership=salle_membership)


def test_personal_feed_parity_with_multiple_scope_rows():
    establishment = create_establishment(name="Multi scope parity")
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    unit_a = create_business_unit(establishment=establishment, key="mod_a")
    unit_b = create_business_unit(establishment=establishment, key="mod_b")
    replace_membership_scopes(
        membership=membership,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, unit_a.id),
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, unit_b.id),
        ],
    )

    _create_signal(
        establishment=establishment,
        title="Unit A",
        affected_business_unit=unit_a,
        responsible_business_unit=unit_a,
    )
    _create_signal(
        establishment=establishment,
        title="Unit B",
        affected_business_unit=unit_b,
        responsible_business_unit=unit_b,
    )
    other_unit = create_business_unit(establishment=establishment, key="mod_other")
    _create_signal(
        establishment=establishment,
        title="Other",
        affected_business_unit=other_unit,
        responsible_business_unit=other_unit,
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )


def test_personal_feed_business_unit_scope_matches_scope_oracle():
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name="Business unit scope feed",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    business_unit = create_business_unit(establishment=establishment, key="hotel")
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    _create_signal(
        establishment=establishment,
        title="Scoped unit",
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )


def test_visibility_and_actionability_are_separated_for_golden_signals():
    establishment = create_establishment(name="Visibility actionability")
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    taxonomy = create_restaurant_v3_taxonomy(establishment)
    assert taxonomy.maintenance is not None
    assert taxonomy.lighting_subject is not None
    salle_signal = _create_signal(
        establishment=establishment,
        title="Lighting",
        affected_business_unit=taxonomy.restaurant,
        responsible_business_unit=taxonomy.maintenance,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=taxonomy.restaurant,
    )

    assert signal_visible_in_membership_scope(membership, salle_signal) is True
    assert signal_actionable_by_membership(membership, salle_signal) is False
