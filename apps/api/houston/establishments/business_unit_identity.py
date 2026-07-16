from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from houston.core.exceptions import DomainConflictError, DomainValidationError
from houston.establishments.taxonomy_normalization import slugify_label

if TYPE_CHECKING:
    from houston.establishments.models import (
        ActivitySubject,
        BusinessUnit,
        CatalogActivitySubject,
        CatalogBusinessUnit,
        OnboardingProposal,
    )


class ActivitySubjectEstablishmentDerivation(Protocol):
    establishment_id: UUID | None
    business_unit: object


def normalize_business_unit_specific_name(specific_name: str) -> str:
    return slugify_label(specific_name)


def build_business_unit_routing_key(
    *,
    business_unit_id: UUID,
    catalog_key: str,
    specific_name: str,
) -> str:
    specific_slug = slugify_label(specific_name).replace("_", "-")[:48]
    return f"{catalog_key}--{specific_slug}--{business_unit_id.hex[:16]}"


def build_free_activity_subject_routing_key(
    *,
    activity_subject_id: UUID,
    label: str,
) -> str:
    label_slug = slugify_label(label).replace("_", "-")[:64]
    return f"custom--{label_slug}--{activity_subject_id.hex[:16]}"


def normalize_generic_activity_subject_name(catalog_label: str) -> str:
    return slugify_label(catalog_label)


def derive_activity_subject_establishment(
    activity_subject: ActivitySubjectEstablishmentDerivation,
) -> None:
    activity_subject.establishment_id = activity_subject.business_unit.establishment_id


def validate_activity_subject_catalog_coherence(
    *,
    business_unit: BusinessUnit,
    catalog_activity_subject: CatalogActivitySubject,
) -> None:
    if (
        catalog_activity_subject.catalog_business_unit_id
        != business_unit.catalog_business_unit_id
    ):
        raise DomainValidationError(
            "Catalog activity subject does not belong to the business unit catalog.",
            code="catalog_subject_business_unit_mismatch",
        )


def populate_business_unit_legacy_fields(
    *,
    business_unit: BusinessUnit,
    specific_name: str,
    instance_description: str,
    catalog_business_unit: CatalogBusinessUnit,
) -> None:
    key_max_length = business_unit._meta.get_field("key").max_length
    business_unit.key = slugify_label(specific_name)[:key_max_length]
    business_unit.label = specific_name
    business_unit.description = instance_description
    business_unit.unit_type = catalog_business_unit.unit_type


def build_generic_activity_subject_row(
    *,
    business_unit: BusinessUnit,
    catalog_activity_subject: CatalogActivitySubject,
    managed_by_onboarding_proposal: OnboardingProposal | None = None,
) -> ActivitySubject:
    from houston.establishments.models import ActivitySubject

    validate_activity_subject_catalog_coherence(
        business_unit=business_unit,
        catalog_activity_subject=catalog_activity_subject,
    )
    row = ActivitySubject(
        business_unit=business_unit,
        catalog_activity_subject=catalog_activity_subject,
        normalized_name=normalize_generic_activity_subject_name(
            catalog_activity_subject.label
        ),
        routing_key=catalog_activity_subject.key,
        label=catalog_activity_subject.label,
        description=catalog_activity_subject.description,
        source=ActivitySubject.Source.CATALOG_SUGGESTION,
        active=True,
        managed_by_onboarding_proposal=managed_by_onboarding_proposal,
    )
    derive_activity_subject_establishment(row)
    return row


def build_free_activity_subject_row(
    *,
    business_unit: BusinessUnit,
    label: str,
    description: str = "",
    managed_by_onboarding_proposal: OnboardingProposal | None = None,
) -> ActivitySubject:
    from houston.establishments.models import ActivitySubject

    normalized_label = label.strip()
    if not normalized_label:
        raise DomainValidationError(
            "Free activity subject label is required.",
            code="invalid_free_activity_subject_label",
        )

    row = ActivitySubject(
        business_unit=business_unit,
        normalized_name=slugify_label(normalized_label),
        label=normalized_label,
        description=description.strip(),
        source=ActivitySubject.Source.MANUAL,
        active=True,
        managed_by_onboarding_proposal=managed_by_onboarding_proposal,
    )
    row.routing_key = build_free_activity_subject_routing_key(
        activity_subject_id=row.id,
        label=normalized_label,
    )
    derive_activity_subject_establishment(row)
    return row


def preflight_activity_subject_rows(
    *,
    business_unit: BusinessUnit,
    rows: Iterable[ActivitySubject],
) -> list[ActivitySubject]:
    from houston.establishments.models import ActivitySubject

    materialized_rows = list(rows)
    generic_keys: set[str] = set()
    normalized_names: set[str] = set()
    routing_keys: set[str] = set()

    for row in materialized_rows:
        if row.business_unit_id != business_unit.id:
            raise DomainValidationError(
                "Activity subject belongs to another business unit.",
                code="catalog_subject_business_unit_mismatch",
            )
        derive_activity_subject_establishment(row)

        if row.catalog_activity_subject_id is None and not row.label.strip():
            raise DomainValidationError(
                "Free activity subject label is required.",
                code="invalid_free_activity_subject_label",
            )

        if row.catalog_activity_subject_id is not None:
            catalog_key = row.catalog_activity_subject.key
            if catalog_key in generic_keys:
                raise DomainConflictError(
                    "Catalog activity subject key is duplicated.",
                    code="duplicate_generic_catalog_subject_key",
                )
            generic_keys.add(catalog_key)

        if row.normalized_name in normalized_names:
            raise DomainConflictError(
                "Activity subject normalized name is duplicated.",
                code="duplicate_activity_subject_normalized_name",
            )
        normalized_names.add(row.normalized_name)

        if row.routing_key in routing_keys:
            raise DomainConflictError(
                "Activity subject routing key is duplicated.",
                code="duplicate_activity_subject_routing_key",
            )
        routing_keys.add(row.routing_key)

    existing_rows = ActivitySubject.objects.filter(business_unit=business_unit)
    if normalized_names and existing_rows.filter(
        normalized_name__in=normalized_names
    ).exists():
        raise DomainConflictError(
            "Activity subject normalized name already exists.",
            code="duplicate_activity_subject_normalized_name",
        )
    if routing_keys and existing_rows.filter(routing_key__in=routing_keys).exists():
        raise DomainConflictError(
            "Activity subject routing key already exists.",
            code="duplicate_activity_subject_routing_key",
        )

    return materialized_rows


def build_activity_subject_rows_for_insert(
    *,
    business_unit: BusinessUnit,
    catalog_activity_subjects: Iterable[CatalogActivitySubject] = (),
    free_activity_subjects: Iterable[dict[str, str]] = (),
    managed_by_onboarding_proposal: OnboardingProposal | None = None,
) -> list[ActivitySubject]:
    rows = [
        build_generic_activity_subject_row(
            business_unit=business_unit,
            catalog_activity_subject=catalog_subject,
            managed_by_onboarding_proposal=managed_by_onboarding_proposal,
        )
        for catalog_subject in catalog_activity_subjects
    ]
    rows.extend(
        build_free_activity_subject_row(
            business_unit=business_unit,
            label=subject.get("label", ""),
            description=subject.get("description", ""),
            managed_by_onboarding_proposal=managed_by_onboarding_proposal,
        )
        for subject in free_activity_subjects
    )
    return preflight_activity_subject_rows(
        business_unit=business_unit,
        rows=rows,
    )
