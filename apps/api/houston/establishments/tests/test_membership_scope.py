from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError, transaction

from houston.accounts.models import User
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
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.organizations.models import Organization

pytestmark = pytest.mark.django_db


def create_establishment(*, name: str = "Demo Hotel") -> Establishment:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    return Establishment.objects.create(
        name=name,
        organization=organization,
        status=Establishment.Status.ACTIVE,
    )


def create_membership(
    *,
    establishment: Establishment,
    role: str = EstablishmentMembership.Role.MANAGER,
) -> EstablishmentMembership:
    user = User.objects.create_user(
        username=f"user_{uuid.uuid4().hex[:8]}",
        email=f"user_{uuid.uuid4().hex[:8]}@example.com",
        password="SecurePass123!",
        status=User.Status.ACTIVE,
    )
    return EstablishmentMembership.objects.create(
        user=user,
        establishment=establishment,
        role=role,
        status=EstablishmentMembership.Status.ACTIVE,
    )


def create_taxonomy_tree(
    establishment: Establishment,
    *,
    module_key: str = "hotel",
    domain_key: str = "proprete_chambre",
    domain_label: str = "Propreté chambre",
    subject_key: str = "proprete_chambre_daily",
    subject_label: str = "Propreté quotidienne chambre",
):
    module = OperationalModule.objects.create(
        establishment=establishment,
        key=module_key,
        label=module_key.title(),
        active=True,
    )
    domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key=domain_key,
        label=domain_label,
        active=True,
    )
    subject = OperationalSubject.objects.create(
        establishment=establishment,
        operational_domain=domain,
        key=subject_key,
        label=subject_label,
        active=True,
    )
    return module, domain, subject


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


def test_normalize_dedupes_duplicate_scope_inputs():
    establishment = create_establishment()
    module, _, _ = create_taxonomy_tree(establishment)

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.MODULE, module.id),
            MembershipScopeInput(MembershipScopeType.MODULE, module.id),
        ],
    )

    assert len(normalized) == 1
    assert normalized[0].scope_type == MembershipScopeType.MODULE


def test_normalize_drops_domain_under_selected_module():
    establishment = create_establishment()
    module, domain, _ = create_taxonomy_tree(establishment)

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.MODULE, module.id),
            MembershipScopeInput(MembershipScopeType.DOMAIN, domain.id),
        ],
    )

    assert len(normalized) == 1
    assert normalized[0].scope_type == MembershipScopeType.MODULE


def test_normalize_drops_subject_under_selected_domain():
    establishment = create_establishment()
    _, domain, subject = create_taxonomy_tree(establishment)

    normalized = normalize_membership_scope_inputs(
        establishment=establishment,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.DOMAIN, domain.id),
            MembershipScopeInput(MembershipScopeType.SUBJECT, subject.id),
        ],
    )

    assert len(normalized) == 1
    assert normalized[0].scope_type == MembershipScopeType.DOMAIN


def test_cross_establishment_scope_id_rejected():
    establishment_a = create_establishment(name="Hotel A")
    establishment_b = create_establishment(name="Hotel B")
    _, domain_a, _ = create_taxonomy_tree(establishment_a)

    with pytest.raises(InvalidMembershipScopeAssignmentError):
        normalize_membership_scope_inputs(
            establishment=establishment_b,
            scope_inputs=[MembershipScopeInput(MembershipScopeType.DOMAIN, domain_a.id)],
        )


def test_inactive_scope_id_rejected():
    establishment = create_establishment()
    module, domain, _ = create_taxonomy_tree(establishment)
    domain.active = False
    domain.save(update_fields=["active", "updated_at"])

    with pytest.raises(InvalidMembershipScopeAssignmentError):
        normalize_membership_scope_inputs(
            establishment=establishment,
            scope_inputs=[MembershipScopeInput(MembershipScopeType.DOMAIN, domain.id)],
        )


def test_module_scope_covers_child_domain_and_subject():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    module, domain, subject = create_taxonomy_tree(establishment)

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.MODULE, module.id)],
    )

    assert membership_scope_covers_module(membership, module) is True
    assert membership_scope_covers_domain(membership, domain) is True
    assert membership_scope_covers_subject(membership, subject) is True


def test_domain_scope_covers_subject_not_sibling_domain():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    module, domain, subject = create_taxonomy_tree(establishment)
    sibling_domain = OperationalDomain.objects.create(
        establishment=establishment,
        operational_module=module,
        key="proprete_restaurant",
        label="Propreté restaurant",
        active=True,
    )

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
    module, domain, subject = create_taxonomy_tree(establishment)
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
    assert membership_scope_covers_domain(membership, domain) is False


def test_label_collision_does_not_grant_access_across_unrelated_domains():
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

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[MembershipScopeInput(MembershipScopeType.DOMAIN, domain_a.id)],
    )

    assert membership_scope_covers_domain(membership, domain_a) is True
    assert membership_scope_covers_domain(membership, domain_b) is False


def test_replace_membership_scopes_persists_normalized_rows():
    establishment = create_establishment()
    membership = create_membership(establishment=establishment)
    module, domain, subject = create_taxonomy_tree(establishment)

    replace_membership_scopes(
        membership=membership,
        scope_inputs=[
            MembershipScopeInput(MembershipScopeType.MODULE, module.id),
            MembershipScopeInput(MembershipScopeType.DOMAIN, domain.id),
            MembershipScopeInput(MembershipScopeType.SUBJECT, subject.id),
        ],
    )

    scopes = list(MembershipScope.objects.filter(membership=membership))
    assert len(scopes) == 1
    assert scopes[0].operational_module_id == module.id


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
