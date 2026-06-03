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
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.establishments.tests.test_membership_scope import (
    create_establishment,
    create_membership,
    create_taxonomy_tree,
)
from houston.organizations.models import Organization
from houston.signals.models import Signal
from houston.signals.permissions import signal_matches_membership_scope
from houston.signals.selectors import active_signals_for_establishment, signal_feed_queryset
from houston.signals.tests.conftest import (
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
) -> Signal:
    now = timezone.now()
    return Signal.objects.create(
        establishment=establishment,
        operational_module=module,
        operational_domain=domain,
        operational_subject=subject,
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


@pytest.mark.parametrize(
    "scope_type",
    [
        MembershipScopeType.MODULE,
        MembershipScopeType.DOMAIN,
        MembershipScopeType.SUBJECT,
    ],
)
def test_personal_feed_matches_signal_matches_membership_scope_oracle(scope_type):
    establishment = create_establishment()
    module, domain, subject = create_taxonomy_tree(establishment)
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.MANAGER,
    )

    scope_id = {
        MembershipScopeType.MODULE: module.id,
        MembershipScopeType.DOMAIN: domain.id,
        MembershipScopeType.SUBJECT: subject.id,
    }[scope_type]
    replace_membership_scopes(
        membership=membership,
        scope_inputs=[MembershipScopeInput(scope_type, scope_id)],
    )

    _create_signal(
        establishment=establishment,
        module=module,
        domain=domain,
        subject=subject,
        title="In scope",
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
    _create_signal(
        establishment=establishment,
        module=module,
        domain=sibling_domain,
        subject=sibling_subject,
        title="Out of scope",
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )


def test_domain_scope_bar_does_not_see_salle_signal():
    establishment = create_establishment(name="Restaurant isolation bar")
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(
        establishment,
        include_salle_maintenance=True,
        include_bar_stock=True,
    )
    assert taxonomy.salle_maintenance_subject is not None
    assert taxonomy.bar_stock_subject is not None

    bar_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.bar_domain,
        subject=taxonomy.bar_stock_subject,
        title="Bar signal",
    )
    salle_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.salle_domain,
        subject=taxonomy.salle_maintenance_subject,
        title="Salle signal",
    )

    bar_membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    MembershipScope.objects.create(
        membership=bar_membership,
        operational_domain=taxonomy.bar_domain,
    )

    assert _feed_personal_ids(membership=bar_membership) == {bar_signal.id}
    assert salle_signal.id not in _feed_personal_ids(membership=bar_membership)


def test_domain_scope_salle_does_not_see_bar_signal():
    establishment = create_establishment(name="Restaurant isolation salle")
    taxonomy = create_restaurant_lighting_bar_stock_taxonomy(
        establishment,
        include_salle_maintenance=True,
        include_bar_stock=True,
    )
    assert taxonomy.salle_maintenance_subject is not None
    assert taxonomy.bar_stock_subject is not None

    bar_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.bar_domain,
        subject=taxonomy.bar_stock_subject,
        title="Bar signal",
    )
    salle_signal = _create_signal(
        establishment=establishment,
        module=taxonomy.module,
        domain=taxonomy.salle_domain,
        subject=taxonomy.salle_maintenance_subject,
        title="Salle signal",
    )

    salle_membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    MembershipScope.objects.create(
        membership=salle_membership,
        operational_domain=taxonomy.salle_domain,
    )

    assert _feed_personal_ids(membership=salle_membership) == {salle_signal.id}
    assert bar_signal.id not in _feed_personal_ids(membership=salle_membership)


def test_personal_feed_parity_with_multiple_scope_rows():
    establishment = create_establishment(name="Multi scope parity")
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
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

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.SUBJECT, subject_a.id),
            MembershipScopeInput(MembershipScopeType.DOMAIN, domain_b.id),
        ],
    )

    _create_signal(
        establishment=establishment,
        module=module_a,
        domain=domain_a,
        subject=subject_a,
        title="Subject A",
    )
    _create_signal(
        establishment=establishment,
        module=module_b,
        domain=domain_b,
        subject=subject_b,
        title="Domain B",
    )
    other_module, other_domain, other_subject = create_taxonomy_tree(
        establishment,
        module_key="mod_other",
        domain_key="mod_other__dom",
        subject_key="mod_other__dom__sub",
    )
    _create_signal(
        establishment=establishment,
        module=other_module,
        domain=other_domain,
        subject=other_subject,
        title="Other",
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )


def test_personal_feed_subject_scope_uses_create_taxonomy_helper():
    """Regression: subject-level scope via shared test helper."""
    organization = Organization.objects.create(
        name=f"Org {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    establishment = Establishment.objects.create(
        name="Subject scope feed",
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )
    membership = create_membership(
        establishment=establishment,
        role=EstablishmentMembership.Role.STAFF,
    )
    module, domain, subject = create_taxonomy(establishment)
    MembershipScope.objects.create(membership=membership, operational_subject=subject)
    _create_signal(
        establishment=establishment,
        module=module,
        domain=domain,
        subject=subject,
        title="Scoped subject",
    )

    assert _feed_personal_ids(membership=membership) == _oracle_matching_ids(
        membership=membership
    )
