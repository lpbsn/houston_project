from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from houston.establishments.mama_nice_dataset_constants import (
    BU_DESCRIPTIONS,
    CATALOG_KEYS,
    LOCAL_ESTABLISHMENT_NAME,
    LOCAL_GOVERNANCE_DIRECTOR_EMAIL,
    LOCAL_ORG_NAME,
    PROD_DIRECTOR_REF,
    PROD_ESTABLISHMENT_ID,
    PROD_ORGANIZATION_ID,
    PROD_OWNER_REF,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_manifest import load_mama_nice_manifest
from houston.establishments.models import (
    BusinessUnit,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.organizations.models import Organization


@dataclass
class PreflightResult:
    establishment: Establishment
    organization: Organization
    owner_membership: EstablishmentMembership
    governance_director: EstablishmentMembership
    owner_ref_kind: str
    director_ref_kind: str
    messages: list[str] = field(default_factory=list)


def _resolve_identity(ref: str) -> tuple[str, EstablishmentMembership]:
    uuid = UUID(ref)
    membership = EstablishmentMembership.objects.filter(id=uuid).select_related("user").first()
    if membership is not None:
        return "membership", membership
    membership = (
        EstablishmentMembership.objects.filter(user_id=uuid)
        .select_related("user", "establishment")
        .first()
    )
    if membership is not None:
        return "user", membership
    raise MamaNiceDatasetError([f"governance ref {ref} matches neither User nor Membership"])


def preflight_mama_nice_production(*, establishment_id: str) -> PreflightResult:
    if establishment_id != PROD_ESTABLISHMENT_ID:
        raise MamaNiceDatasetError(
            [f"production seed must target {PROD_ESTABLISHMENT_ID}"]
        )
    establishment = (
        Establishment.objects.select_related("organization")
        .filter(id=establishment_id)
        .first()
    )
    if establishment is None:
        raise MamaNiceDatasetError(["production establishment was not found"])
    if str(establishment.organization_id) != PROD_ORGANIZATION_ID:
        raise MamaNiceDatasetError(["production organization id diverges"])
    owner_kind, owner = _resolve_identity(PROD_OWNER_REF)
    director_kind, director = _resolve_identity(PROD_DIRECTOR_REF)
    if (
        owner.establishment_id != establishment.id
        or owner.role != EstablishmentMembership.Role.OWNER
    ):
        raise MamaNiceDatasetError(["production OWNER ref role or establishment diverges"])
    if (
        director.establishment_id != establishment.id
        or director.role != EstablishmentMembership.Role.DIRECTOR
    ):
        raise MamaNiceDatasetError(["production DIRECTOR ref role or establishment diverges"])
    _assert_catalog(establishment, rewrite_descriptions=False)
    return PreflightResult(
        establishment=establishment,
        organization=establishment.organization,
        owner_membership=owner,
        governance_director=director,
        owner_ref_kind=owner_kind,
        director_ref_kind=director_kind,
        messages=[
            f"OWNER {PROD_OWNER_REF} resolved as {owner_kind}",
            f"DIRECTOR {PROD_DIRECTOR_REF} resolved as {director_kind}",
        ],
    )


def preflight_mama_nice_local() -> PreflightResult:
    establishment = (
        Establishment.objects.select_related("organization")
        .filter(
            name=LOCAL_ESTABLISHMENT_NAME,
            organization__name=LOCAL_ORG_NAME,
        )
        .first()
    )
    if establishment is None:
        raise MamaNiceDatasetError(["local Mama Shelter Nice establishment is missing"])
    owner = (
        EstablishmentMembership.objects.filter(
            establishment=establishment,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        .select_related("user")
        .first()
    )
    director = (
        EstablishmentMembership.objects.filter(
            establishment=establishment,
            role=EstablishmentMembership.Role.DIRECTOR,
            user__email=LOCAL_GOVERNANCE_DIRECTOR_EMAIL,
        )
        .select_related("user")
        .first()
    )
    if owner is None or director is None:
        raise MamaNiceDatasetError(["local governance OWNER/DIRECTOR slots are missing"])
    _assert_catalog(establishment, rewrite_descriptions=True)
    return PreflightResult(
        establishment=establishment,
        organization=establishment.organization,
        owner_membership=owner,
        governance_director=director,
        owner_ref_kind="membership",
        director_ref_kind="membership",
    )


def _assert_catalog(establishment: Establishment, *, rewrite_descriptions: bool) -> None:
    manifest = load_mama_nice_manifest()
    expected_subjects = set(manifest["catalog_lock"]["activity_subjects"])
    units = list(
        BusinessUnit.objects.filter(establishment=establishment, active=True).select_related(
            "catalog_business_unit"
        )
    )
    keys = {unit.catalog_business_unit.key for unit in units if unit.catalog_business_unit_id}
    if keys != set(CATALOG_KEYS):
        raise MamaNiceDatasetError([f"business unit catalog_key set {sorted(keys)} != expected"])
    for unit in units:
        catalog_key = unit.catalog_business_unit.key
        expected = BU_DESCRIPTIONS[catalog_key]
        if unit.instance_description != expected:
            if not rewrite_descriptions:
                raise MamaNiceDatasetError(
                    [f"{catalog_key}: instance_description diverges from cadrage §5.1"]
                )
            unit.instance_description = expected
            unit.save(update_fields=["instance_description", "updated_at"])
    actual_subjects = set(
        establishment.activity_subjects.filter(active=True).values_list(
            "catalog_activity_subject__key",
            flat=True,
        )
    )
    actual_subjects.discard(None)
    if actual_subjects != expected_subjects:
        raise MamaNiceDatasetError(
            [
                "activity subjects diverge from catalog lock: "
                f"missing={sorted(expected_subjects - actual_subjects)} "
                f"extra={sorted(actual_subjects - expected_subjects)}"
            ]
        )
    for key in CATALOG_KEYS:
        if not CatalogBusinessUnit.objects.filter(key=key, active=True).exists():
            raise MamaNiceDatasetError([f"catalog business unit {key} is missing"])
