from __future__ import annotations

import uuid

from houston.accounts.models import User
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name
from houston.organizations.models import Organization


def create_establishment(
    *,
    name: str = "Demo Hotel",
    timezone: str | None = None,
) -> Establishment:
    organization = Organization.objects.create(
        name=f"{name} Group {uuid.uuid4().hex[:6]}",
        status=Organization.Status.ACTIVE,
    )
    kwargs = {
        "name": name,
        "organization": organization,
        "status": Establishment.Status.ACTIVE,
    }
    if timezone is not None:
        kwargs["timezone"] = timezone
    return Establishment.objects.create(**kwargs)


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


def create_business_unit(
    *,
    establishment: Establishment,
    key: str,
    label: str | None = None,
    description: str = "",
    unit_type: str = BusinessUnit.UnitType.DEDICATED,
) -> BusinessUnit:
    return BusinessUnit.objects.create(
        establishment=establishment,
        key=key,
        label=label or key.replace("_", " ").title(),
        description=description,
        unit_type=unit_type,
        source=BusinessUnit.Source.MANUAL,
        active=True,
    )


def create_activity_subject(
    *,
    establishment: Establishment,
    business_unit: BusinessUnit,
    label: str,
    description: str = "",
) -> ActivitySubject:
    return ActivitySubject.objects.create(
        establishment=establishment,
        business_unit=business_unit,
        normalized_name=normalize_activity_subject_name(label),
        label=label,
        description=description,
        source=ActivitySubject.Source.MANUAL,
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
    assert body["scope_summary"] == {"business_unit_count": 1}
