from __future__ import annotations

import uuid

from houston.accounts.models import User
from houston.establishments.models import (
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
)
from houston.establishments.taxonomy_backfill import backfill_business_units_from_legacy_taxonomy
from houston.organizations.models import Organization


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


def create_business_unit(
    *,
    establishment: Establishment,
    key: str,
    label: str | None = None,
    unit_type: str = BusinessUnit.UnitType.DEDICATED,
) -> BusinessUnit:
    return BusinessUnit.objects.create(
        establishment=establishment,
        key=key,
        label=label or key.replace("_", " ").title(),
        unit_type=unit_type,
        source=BusinessUnit.Source.MANUAL,
        active=True,
    )


def create_membership_with_business_unit_scope(
    *,
    membership: EstablishmentMembership,
    business_unit: BusinessUnit,
) -> MembershipScope:
    return MembershipScope.objects.create(
        membership=membership,
        business_unit=business_unit,
    )


def business_unit_scope_payload(business_unit: BusinessUnit) -> dict[str, str]:
    return {"scope_type": "business_unit", "scope_id": str(business_unit.id)}


def assert_business_unit_scope_response(body: dict, *, business_unit: BusinessUnit) -> None:
    assert body["scopes"] == [business_unit_scope_payload(business_unit)]
    assert body["scope_summary"]["business_unit_count"] == 1
    assert body["scope_summary"]["domain_count"] == 0
    assert body["scope_summary"]["module_count"] == 0
    assert body["scope_summary"]["subject_count"] == 0


def create_legacy_taxonomy_with_business_unit_mapping(
    establishment: Establishment,
    **kwargs,
):
    """Legacy expand-contract helper: v1 taxonomy + TaxonomyMigrationMap backfill."""
    module, domain, subject = create_taxonomy_tree(establishment, **kwargs)
    backfill_business_units_from_legacy_taxonomy(establishment_id=establishment.id)
    business_unit = BusinessUnit.objects.get(
        establishment=establishment,
        key=module.key,
    )
    return module, domain, subject, business_unit
