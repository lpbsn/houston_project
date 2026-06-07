from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from houston.establishments.membership_scope import (
    MembershipScopeInput,
    MembershipScopeType,
    build_signal_feed_scope_q,
    replace_membership_scopes,
)
from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_membership,
    create_membership_with_business_unit_scope,
    create_taxonomy_tree,
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
    create_restaurant_business_units,
    create_restaurant_lighting_bar_stock_taxonomy,
    create_taxonomy,
)

pytestmark = pytest.mark.django_db


def _create_signal(
    *,
    establishment: Establishment,
    module: OperationalModule,
    domain: OperationalDomain,
    subject: OperationalSubject,
    title: str = "Test signal",
    affected_business_unit: BusinessUnit | None = None,
    responsible_business_unit: BusinessUnit | None = None,
) -> Signal:
    now = timezone.now()
    return Signal.objects.create(
        establishment=establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        title=title,
        structured_summary="Structured summary safe.",
        last_activity_at=now,
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


def test_build_signal_feed_scope_q_returns_none_without_scopes():
    establishment = create_establishment()
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )

    assert build_signal_feed_scope_q(membership=membership) is None
    assert _feed_personal_ids(membership=membership) == set()


def test_personal_feed_matches_signal_matches_membership_scope_oracle():
    establishment = create_establishment()
    module, domain, subject = create_taxonomy_tree(establishment)
    business_unit = create_business_unit(establishment=establishment, key=module.key)
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
        module=module,
        domain=domain,
        subject=subject,
        title="In scope",
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
    )
    sibling_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key="hotel_sibling_domain",
        label="Sibling domain",
        active=True,
    )
    sibling_subject = OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=sibling_domain,
        key="hotel_sibling_subject",
        label="Sibling subject",
        active=True,
    )
    other_unit = create_business_unit(establishment=establishment, key="other_unit")
    _create_signal(
        establishment=establishment,
        module=module,
        domain=sibling_domain,
        subject=sibling_subject,
        title="Out of scope",
        affected_business_unit=other_unit,
        responsible_business_unit=other_unit,
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )


def test_business_unit_scope_bar_does_not_see_salle_signal():
    establishment = create_establishment(name="Restaurant isolation bar")
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(
        establishment,
        include_salle_maintenance=True,
        include_bar_stock=True,
    )
    business_units = create_restaurant_business_units(establishment)
    assert taxonomy.salle_maintenance_subject is not None
    assert taxonomy.bar_stock_subject is not None

    bar_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.bar_domain,
        subject=taxonomy.bar_stock_subject,
        title="Bar signal",
        affected_business_unit=business_units.bar,
        responsible_business_unit=business_units.bar,
    )
    salle_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.salle_domain,
        subject=taxonomy.salle_maintenance_subject,
        title="Salle signal",
        affected_business_unit=business_units.restaurant,
        responsible_business_unit=business_units.maintenance,
    )

    bar_membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=bar_membership,
        business_unit=business_units.bar,
    )

    assert _feed_personal_ids(membership=bar_membership) == {bar_signal.id}
    assert salle_signal.id not in _feed_personal_ids(membership=bar_membership)


def test_business_unit_scope_salle_does_not_see_bar_signal():
    establishment = create_establishment(name="Restaurant isolation salle")
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(
        establishment,
        include_salle_maintenance=True,
        include_bar_stock=True,
    )
    business_units = create_restaurant_business_units(establishment)
    assert taxonomy.salle_maintenance_subject is not None
    assert taxonomy.bar_stock_subject is not None

    bar_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.bar_domain,
        subject=taxonomy.bar_stock_subject,
        title="Bar signal",
        affected_business_unit=business_units.bar,
        responsible_business_unit=business_units.bar,
    )
    salle_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.salle_domain,
        subject=taxonomy.salle_maintenance_subject,
        title="Salle signal",
        affected_business_unit=business_units.restaurant,
        responsible_business_unit=business_units.maintenance,
    )

    salle_membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    create_membership_with_business_unit_scope(
        membership=salle_membership,
        business_unit=business_units.restaurant,
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

    module_a, domain_a, subject_a = create_taxonomy_tree(
        establishment,
        module_key="mod_a",
        domain_key="mod_a__dom_a",
        subject_key="mod_a__dom_a__sub_a",
    )
    module_b = OperationalModule.objects.create(
        establishment=establishment,
        key="mod_b",
        label="Mod B",
        active=True,
    )
    domain_b = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module_b,
        key="mod_b__dom_b",
        label="Dom B",
        active=True,
    )
    subject_b = OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain_b,
        key="mod_b__dom_b__sub_b",
        label="Sub B",
        active=True,
    )

    _create_signal(
        establishment=establishment,
        module=module_a,
        domain=domain_a,
        subject=subject_a,
        title="Unit A",
        affected_business_unit=unit_a,
        responsible_business_unit=unit_a,
    )
    _create_signal(
        establishment=establishment,
        module=module_b,
        domain=domain_b,
        subject=subject_b,
        title="Unit B",
        affected_business_unit=unit_b,
        responsible_business_unit=unit_b,
    )
    other_module, other_domain, other_subject = create_taxonomy_tree(
        establishment,
        module_key="mod_other",
        domain_key="mod_other__dom",
        subject_key="mod_other__dom__sub",
    )
    other_unit = create_business_unit(establishment=establishment, key="mod_other")
    _create_signal(
        establishment=establishment,
        module=other_module,
        domain=other_domain,
        subject=other_subject,
        title="Other",
        affected_business_unit=other_unit,
        responsible_business_unit=other_unit,
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )


def test_personal_feed_business_unit_scope_uses_create_taxonomy_helper():
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
    module, domain, subject = create_taxonomy(establishment)
    business_unit = create_business_unit(establishment=establishment, key=module.key)
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_unit,
    )
    _create_signal(
        establishment=establishment,
        module=module,
        domain=domain,
        subject=subject,
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
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(establishment)
    business_units = create_restaurant_business_units(establishment)
    assert taxonomy.salle_maintenance_subject is not None
    salle_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.salle_domain,
        subject=taxonomy.salle_maintenance_subject,
        title="Lighting",
        affected_business_unit=business_units.restaurant,
        responsible_business_unit=business_units.maintenance,
    )
    create_membership_with_business_unit_scope(
        membership=membership,
        business_unit=business_units.restaurant,
    )

    assert signal_visible_in_membership_scope(membership, salle_signal) is True
    assert signal_actionable_by_membership(membership, salle_signal) is False
