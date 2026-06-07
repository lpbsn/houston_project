from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction

from houston.establishments.membership_scope import (
    InvalidMembershipScopeAssignmentError,
    MembershipScopeInput,
    MembershipScopeType,
    membership_scope_covers_domain,
    membership_scope_covers_module,
    membership_scope_covers_subject,
    normalize_membership_scope_inputs,
    replace_membership_scopes,
)
from houston.establishments.models import (
    MembershipScope,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.establishments.tests.taxonomy_helpers import (
    create_business_unit,
    create_establishment,
    create_legacy_taxonomy_with_business_unit_mapping,
    create_membership,
    create_taxonomy_tree,
)

pytestmark = pytest.mark.django_db


def test_membership_scope_model_requires_exactly_one_target():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    module, _, _ = create_taxonomy_tree(establishment, module_key="hotel_scope_model")

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MembershipScope.objects.create(membership=membership)

    scope = MembershipScope.objects.create(membership=membership, operational_module=module)
    assert scope.scope_type == "module"
    assert scope.scope_id == module.id


def test_duplicate_scope_type_and_id_rejected():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    module, _, _ = create_taxonomy_tree(establishment, module_key="hotel_scope_dup")
    MembershipScope.objects.create(membership=membership, operational_module=module)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MembershipScope.objects.create(membership=membership, operational_module=module)


def test_normalize_dedupes_duplicate_business_unit_inputs():
    establishment = create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    assert len(normalized) == 1
    assert normalized[0].business_unit.id == business_unit.id


def test_normalize_dedupes_redundant_business_unit_scope_inputs():
    establishment = create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    assert len(normalized) == 1
    assert normalized[0].business_unit.key == "hotel"


def test_cross_establishment_business_unit_rejected():
    establishment_a = create_establishment(name="Hotel A")
    establishment_b = create_establishment(name="Hotel B")
    business_unit_a = create_business_unit(establishment=establishment_a, key="hotel")

    with pytest.raises(InvalidMembershipScopeAssignmentError):
        normalize_membership_scope_inputs(
            establishment=establishment_b,
            scope_inputs=[
                MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit_a.id)
            ],
        )


def test_inactive_business_unit_rejected():
    establishment = create_establishment()
    business_unit = create_business_unit(establishment=establishment, key="hotel")
    business_unit.active = False
    business_unit.save(update_fields=["active", "updated_at"])

    with pytest.raises(InvalidMembershipScopeAssignmentError):
        normalize_membership_scope_inputs(
            establishment=establishment,
            scope_inputs=[
                MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id)
            ],
        )


def test_legacy_module_input_resolves_to_business_unit():
    establishment = create_establishment()
    module, _, _, business_unit = create_legacy_taxonomy_with_business_unit_mapping(
        establishment,
    )

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.MODULE, module.id)],
    )

    assert len(normalized) == 1
    assert normalized[0].business_unit.id == business_unit.id


def test_legacy_domain_input_resolves_to_business_unit():
    establishment = create_establishment()
    _, domain, _, business_unit = create_legacy_taxonomy_with_business_unit_mapping(
        establishment,
    )

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.DOMAIN, domain.id)],
    )

    assert len(normalized) == 1
    assert normalized[0].business_unit.id == business_unit.id


def test_legacy_subject_input_resolves_to_business_unit():
    establishment = create_establishment()
    _, _, subject, business_unit = create_legacy_taxonomy_with_business_unit_mapping(
        establishment,
    )

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.SUBJECT, subject.id)],
    )

    assert len(normalized) == 1
    assert normalized[0].business_unit.id == business_unit.id


def test_module_scope_covers_child_domain_and_subject():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    module, domain, subject, _ = create_legacy_taxonomy_with_business_unit_mapping(
        establishment,
    )

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.MODULE, module.id)],
    )

    assert membership_scope_covers_module(membership, module) is True
    assert membership_scope_covers_domain(membership, domain) is True
    assert membership_scope_covers_subject(membership, subject) is True


def test_domain_scope_covers_subject_not_sibling_domain():
    from houston.establishments.taxonomy_backfill import (
        backfill_business_units_from_legacy_taxonomy,
    )

    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    module, domain, subject, _ = create_legacy_taxonomy_with_business_unit_mapping(
        establishment,
    )
    other_module = OperationalModule.objects.create(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
        active=True,
    )
    sibling_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=other_module,
        key="proprete_restaurant",
        label="Propreté restaurant",
        active=True,
    )
    backfill_business_units_from_legacy_taxonomy(establishment_id=establishment.id)

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.DOMAIN, domain.id)],
    )

    assert membership_scope_covers_domain(membership, domain) is True
    assert membership_scope_covers_subject(membership, subject) is True
    assert membership_scope_covers_domain(membership, sibling_domain) is False


def test_subject_scope_is_specific():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    _, domain, subject, _ = create_legacy_taxonomy_with_business_unit_mapping(
        establishment,
    )
    sibling_subject = OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key="proprete_chambre_deep",
        label="Propreté approfondie chambre",
        active=True,
    )

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.SUBJECT, subject.id)],
    )

    assert membership_scope_covers_subject(membership, subject) is True
    assert membership_scope_covers_subject(membership, sibling_subject) is False
    # v2 expand-contract: subject scope resolves to the parent BusinessUnit.
    assert membership_scope_covers_domain(membership, domain) is True


def test_label_collision_does_not_grant_access_across_unrelated_domains():
    from houston.establishments.taxonomy_backfill import (
        backfill_business_units_from_legacy_taxonomy,
    )

    establishment = create_establishment()
    membership = create_membership(establishment=establishment)

    module_a = OperationalModule.objects.create(
        establishment=establishment,
        key="hotel",
        label="Hotel",
        active=True,
    )
    module_b = OperationalModule.objects.create(
        establishment=establishment,
        key="restaurant",
        label="Restaurant",
        active=True,
    )
    domain_a = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module_a,
        key="hotel_proprete",
        label="Propreté",
        active=True,
    )
    domain_b = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module_b,
        key="restaurant_proprete",
        label="Propreté",
        active=True,
    )
    backfill_business_units_from_legacy_taxonomy(establishment_id=establishment.id)

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.DOMAIN, domain_a.id)],
    )

    assert membership_scope_covers_domain(membership, domain_a) is True
    assert membership_scope_covers_domain(membership, domain_b) is False


def test_replace_membership_scopes_persists_business_unit_row():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    business_unit = create_business_unit(establishment=establishment, key="hotel")

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.BUSINESS_UNIT, business_unit.id),
        ],
    )

    scopes = list(MembershipScope.objects.filter(membership=membership))
    assert len(scopes) == 1
    assert scopes[0].business_unit_id == business_unit.id


def test_domain_membership_scope_shape():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        key="maintenance",
        label="Maintenance",
        active=True,
    )

    scope = MembershipScope.objects.create(membership=membership, operational_domain=domain)

    assert scope.scope_type == "domain"
    assert scope.scope_id == domain.id
    assert scope.operational_domain_id == domain.id
