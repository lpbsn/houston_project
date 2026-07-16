from __future__ import annotations

import uuid
from collections.abc import Iterable

from django.db import IntegrityError, transaction

from houston.core.exceptions import (
    DomainConflictError,
    DomainNotFoundError,
    DomainValidationError,
)
from houston.establishments.business_unit_identity import (
    build_activity_subject_rows_for_insert,
    build_business_unit_routing_key,
    normalize_business_unit_specific_name,
    populate_business_unit_legacy_fields,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogActivitySubject,
    CatalogBusinessUnit,
    Establishment,
    OnboardingProposal,
)
from houston.establishments.taxonomy_normalization import slugify_label


def _not_found(message: str) -> DomainNotFoundError:
    return DomainNotFoundError(message, code="business_unit_not_found")


def _lock_establishment(*, establishment_id) -> Establishment:
    try:
        return Establishment.objects.select_for_update().get(id=establishment_id)
    except Establishment.DoesNotExist as exc:
        raise _not_found("Establishment was not found.") from exc


def _lock_catalog_business_unit(
    *,
    catalog_business_unit_id,
) -> CatalogBusinessUnit:
    try:
        return CatalogBusinessUnit.objects.select_for_update().get(
            id=catalog_business_unit_id
        )
    except CatalogBusinessUnit.DoesNotExist as exc:
        raise DomainNotFoundError(
            "Catalog business unit was not found.",
            code="catalog_business_unit_not_found",
        ) from exc


def _lock_catalog_activity_subjects(
    *,
    catalog_business_unit: CatalogBusinessUnit,
    keys: Iterable[str] | None = None,
) -> list[CatalogActivitySubject]:
    queryset = CatalogActivitySubject.objects.filter(
        catalog_business_unit_id=catalog_business_unit.id
    )
    if keys is not None:
        queryset = queryset.filter(key__in=set(keys))
    return list(
        queryset.select_for_update(of=("self",))
        .select_related("catalog_business_unit")
        .order_by("key")
    )


def _validate_catalog_business_unit_active(
    catalog_business_unit: CatalogBusinessUnit,
) -> None:
    if not catalog_business_unit.active:
        raise DomainConflictError(
            "Catalog business unit is inactive.",
            code="catalog_business_unit_inactive",
        )


def _validate_transversal_uniqueness(
    *,
    establishment: Establishment,
    catalog_business_unit: CatalogBusinessUnit,
    exclude_business_unit_id=None,
) -> None:
    if catalog_business_unit.unit_type != CatalogBusinessUnit.DefaultUnitType.TRANSVERSAL:
        return

    siblings = BusinessUnit.objects.filter(
        establishment=establishment,
        catalog_business_unit=catalog_business_unit,
        active=True,
    )
    if exclude_business_unit_id is not None:
        siblings = siblings.exclude(id=exclude_business_unit_id)
    if siblings.exists():
        raise DomainConflictError(
            "An active transversal business unit already exists.",
            code="duplicate_transversal_catalog_instance",
        )


def _raise_business_unit_integrity_conflict(
    *,
    establishment: Establishment,
    normalized_specific_name: str,
    legacy_key: str,
) -> None:
    if BusinessUnit.objects.filter(
        establishment=establishment,
        normalized_specific_name=normalized_specific_name,
    ).exists() or BusinessUnit.objects.filter(
        establishment=establishment,
        key=legacy_key,
    ).exists():
        raise DomainConflictError(
            "A business unit with this specific name already exists.",
            code="duplicate_specific_name",
        )
    raise DomainConflictError(
        "Business unit identity conflicts with an existing row.",
        code="business_unit_identity_conflict",
    )


def _bulk_create_activity_subjects(
    *,
    business_unit: BusinessUnit,
    rows: list[ActivitySubject],
) -> None:
    if not rows:
        return
    try:
        with transaction.atomic():
            ActivitySubject.objects.bulk_create(rows)
    except IntegrityError:
        normalized_names = {row.normalized_name for row in rows}
        routing_keys = {row.routing_key for row in rows}
        existing = ActivitySubject.objects.filter(business_unit=business_unit)
        if existing.filter(normalized_name__in=normalized_names).exists():
            raise DomainConflictError(
                "Activity subject normalized name already exists.",
                code="duplicate_activity_subject_normalized_name",
            ) from None
        if existing.filter(routing_key__in=routing_keys).exists():
            raise DomainConflictError(
                "Activity subject routing key already exists.",
                code="duplicate_activity_subject_routing_key",
            ) from None
        raise DomainConflictError(
            "Activity subject conflicts with an existing row.",
            code="activity_subject_identity_conflict",
        ) from None


@transaction.atomic
def _create_business_unit_core(
    *,
    establishment: Establishment,
    catalog_business_unit: CatalogBusinessUnit,
    specific_name: str,
    instance_description: str = "",
    source: str = BusinessUnit.Source.CATALOG_SUGGESTION,
    managed_by_onboarding_proposal: OnboardingProposal | None = None,
) -> BusinessUnit:
    locked_establishment = _lock_establishment(establishment_id=establishment.id)
    locked_catalog = _lock_catalog_business_unit(
        catalog_business_unit_id=catalog_business_unit.id
    )
    _validate_catalog_business_unit_active(locked_catalog)

    normalized_name_input = specific_name.strip()
    if not normalized_name_input:
        raise DomainValidationError(
            "Specific name is required.",
            code="invalid_normalized_name",
        )
    normalized_specific_name = normalize_business_unit_specific_name(
        normalized_name_input
    )
    if not normalized_specific_name:
        raise DomainValidationError(
            "Specific name must produce a valid normalized name.",
            code="invalid_normalized_name",
        )

    key_max_length = BusinessUnit._meta.get_field("key").max_length
    legacy_key = slugify_label(normalized_name_input)[:key_max_length]
    if BusinessUnit.objects.filter(
        establishment=locked_establishment,
        normalized_specific_name=normalized_specific_name,
    ).exists() or BusinessUnit.objects.filter(
        establishment=locked_establishment,
        key=legacy_key,
    ).exists():
        raise DomainConflictError(
            "A business unit with this specific name already exists.",
            code="duplicate_specific_name",
        )

    _validate_transversal_uniqueness(
        establishment=locked_establishment,
        catalog_business_unit=locked_catalog,
    )

    business_unit_id = uuid.uuid4()
    normalized_description = instance_description.strip()
    business_unit = BusinessUnit(
        id=business_unit_id,
        establishment=locked_establishment,
        catalog_business_unit=locked_catalog,
        specific_name=normalized_name_input,
        normalized_specific_name=normalized_specific_name,
        routing_key=build_business_unit_routing_key(
            business_unit_id=business_unit_id,
            catalog_key=locked_catalog.key,
            specific_name=normalized_name_input,
        ),
        instance_description=normalized_description,
        source=source,
        active=True,
        managed_by_onboarding_proposal=managed_by_onboarding_proposal,
    )
    populate_business_unit_legacy_fields(
        business_unit=business_unit,
        specific_name=normalized_name_input,
        instance_description=normalized_description,
        catalog_business_unit=locked_catalog,
    )
    try:
        with transaction.atomic():
            business_unit.save(force_insert=True)
    except IntegrityError:
        _raise_business_unit_integrity_conflict(
            establishment=locked_establishment,
            normalized_specific_name=normalized_specific_name,
            legacy_key=legacy_key,
        )
    return business_unit


@transaction.atomic
def create_runtime_business_unit(
    *,
    establishment: Establishment,
    catalog_business_unit: CatalogBusinessUnit,
    specific_name: str,
    instance_description: str = "",
    source: str = BusinessUnit.Source.CATALOG_SUGGESTION,
) -> BusinessUnit:
    business_unit = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=catalog_business_unit,
        specific_name=specific_name,
        instance_description=instance_description,
        source=source,
    )
    locked_catalog_subjects = _lock_catalog_activity_subjects(
        catalog_business_unit=business_unit.catalog_business_unit
    )
    active_catalog_subjects = [
        subject for subject in locked_catalog_subjects if subject.active
    ]
    rows = build_activity_subject_rows_for_insert(
        business_unit=business_unit,
        catalog_activity_subjects=active_catalog_subjects,
    )
    _bulk_create_activity_subjects(business_unit=business_unit, rows=rows)
    return business_unit


@transaction.atomic
def create_onboarding_business_unit(
    *,
    establishment: Establishment,
    catalog_business_unit: CatalogBusinessUnit,
    specific_name: str,
    instance_description: str = "",
    generic_activity_subject_keys: Iterable[str] = (),
    free_activity_subjects: Iterable[dict[str, str]] = (),
    source: str = BusinessUnit.Source.CATALOG_SUGGESTION,
    managed_by_onboarding_proposal: OnboardingProposal | None = None,
) -> BusinessUnit:
    generic_keys = list(generic_activity_subject_keys)
    business_unit = _create_business_unit_core(
        establishment=establishment,
        catalog_business_unit=catalog_business_unit,
        specific_name=specific_name,
        instance_description=instance_description,
        source=source,
        managed_by_onboarding_proposal=managed_by_onboarding_proposal,
    )
    locked_catalog_subjects = _lock_catalog_activity_subjects(
        catalog_business_unit=business_unit.catalog_business_unit,
        keys=generic_keys,
    )
    subjects_by_key = {subject.key: subject for subject in locked_catalog_subjects}

    selected_catalog_subjects: list[CatalogActivitySubject] = []
    for key in generic_keys:
        subject = subjects_by_key.get(key)
        if subject is None:
            raise DomainValidationError(
                "Catalog activity subject does not belong to the business unit catalog.",
                code="catalog_subject_business_unit_mismatch",
            )
        if not subject.active:
            raise DomainConflictError(
                "Catalog activity subject is inactive.",
                code="catalog_activity_subject_inactive",
            )
        selected_catalog_subjects.append(subject)

    rows = build_activity_subject_rows_for_insert(
        business_unit=business_unit,
        catalog_activity_subjects=selected_catalog_subjects,
        free_activity_subjects=free_activity_subjects,
        managed_by_onboarding_proposal=managed_by_onboarding_proposal,
    )
    _bulk_create_activity_subjects(business_unit=business_unit, rows=rows)
    return business_unit


@transaction.atomic
def reactivate_business_unit(
    *,
    establishment_id,
    business_unit_id,
) -> BusinessUnit:
    establishment = _lock_establishment(establishment_id=establishment_id)
    business_unit = (
        BusinessUnit.objects.select_for_update()
        .filter(id=business_unit_id, establishment=establishment)
        .first()
    )
    if business_unit is None:
        raise _not_found("Business unit was not found.")
    if business_unit.active:
        raise DomainConflictError(
            "Business unit is already active.",
            code="business_unit_already_active",
        )
    if business_unit.catalog_business_unit_id is None:
        raise DomainConflictError(
            "Business unit has no catalog identity.",
            code="business_unit_catalog_missing",
        )

    catalog_business_unit = _lock_catalog_business_unit(
        catalog_business_unit_id=business_unit.catalog_business_unit_id
    )
    _validate_catalog_business_unit_active(catalog_business_unit)
    _validate_transversal_uniqueness(
        establishment=establishment,
        catalog_business_unit=catalog_business_unit,
        exclude_business_unit_id=business_unit.id,
    )

    business_unit.active = True
    business_unit.save(update_fields=["active", "updated_at"])
    return business_unit


@transaction.atomic
def update_business_unit(
    *,
    establishment_id,
    business_unit_id,
    specific_name: str | None = None,
    instance_description: str | None = None,
) -> BusinessUnit:
    if specific_name is None and instance_description is None:
        raise DomainValidationError(
            "At least one of specific_name or instance_description must be provided.",
            code="empty_business_unit_update",
        )

    establishment = _lock_establishment(establishment_id=establishment_id)
    business_unit = (
        BusinessUnit.objects.select_for_update()
        .filter(id=business_unit_id, establishment=establishment)
        .first()
    )
    if business_unit is None:
        raise _not_found("Business unit was not found.")
    if business_unit.catalog_business_unit_id is None:
        raise DomainConflictError(
            "Business unit has no catalog identity.",
            code="business_unit_catalog_missing",
        )
    if not business_unit.specific_name:
        raise DomainConflictError(
            "Business unit has incomplete identity.",
            code="business_unit_identity_incomplete",
        )

    catalog_business_unit = _lock_catalog_business_unit(
        catalog_business_unit_id=business_unit.catalog_business_unit_id
    )

    next_specific_name = business_unit.specific_name
    next_normalized_specific_name = business_unit.normalized_specific_name
    next_instance_description = business_unit.instance_description or ""
    legacy_key = business_unit.key
    update_fields: list[str] = []

    if specific_name is not None:
        normalized_name_input = specific_name.strip()
        if not normalized_name_input:
            raise DomainValidationError(
                "Specific name is required.",
                code="invalid_normalized_name",
            )
        next_normalized_specific_name = normalize_business_unit_specific_name(
            normalized_name_input
        )
        if not next_normalized_specific_name:
            raise DomainValidationError(
                "Specific name must produce a valid normalized name.",
                code="invalid_normalized_name",
            )
        key_max_length = BusinessUnit._meta.get_field("key").max_length
        legacy_key = slugify_label(normalized_name_input)[:key_max_length]
        collisions = BusinessUnit.objects.filter(establishment=establishment).exclude(
            id=business_unit.id
        )
        if collisions.filter(
            normalized_specific_name=next_normalized_specific_name
        ).exists() or collisions.filter(key=legacy_key).exists():
            raise DomainConflictError(
                "A business unit with this specific name already exists.",
                code="duplicate_specific_name",
            )
        next_specific_name = normalized_name_input
        business_unit.specific_name = next_specific_name
        business_unit.normalized_specific_name = next_normalized_specific_name
        update_fields.extend(["specific_name", "normalized_specific_name", "key", "label"])

    if instance_description is not None:
        next_instance_description = instance_description.strip()
        business_unit.instance_description = next_instance_description
        update_fields.extend(["instance_description", "description"])

    populate_business_unit_legacy_fields(
        business_unit=business_unit,
        specific_name=next_specific_name,
        instance_description=next_instance_description,
        catalog_business_unit=catalog_business_unit,
    )
    if "unit_type" not in update_fields:
        update_fields.append("unit_type")

    try:
        with transaction.atomic():
            business_unit.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
    except IntegrityError:
        _raise_business_unit_integrity_conflict(
            establishment=establishment,
            normalized_specific_name=next_normalized_specific_name or "",
            legacy_key=legacy_key,
        )
    return business_unit


@transaction.atomic
def update_business_unit_specific_name(
    *,
    establishment_id,
    business_unit_id,
    specific_name: str,
) -> BusinessUnit:
    return update_business_unit(
        establishment_id=establishment_id,
        business_unit_id=business_unit_id,
        specific_name=specific_name,
    )


@transaction.atomic
def create_runtime_activity_subject(
    *,
    establishment_id,
    business_unit_id,
    label: str | None = None,
    description: str = "",
    catalog_key: str | None = None,
) -> ActivitySubject:
    establishment = _lock_establishment(establishment_id=establishment_id)
    business_unit = (
        BusinessUnit.objects.select_for_update(of=("self",))
        .filter(
            id=business_unit_id,
            establishment=establishment,
            active=True,
        )
        .first()
    )
    if business_unit is None:
        raise _not_found("Business unit was not found.")
    if business_unit.catalog_business_unit_id is None:
        raise DomainConflictError(
            "Business unit has no catalog identity.",
            code="business_unit_catalog_missing",
        )

    normalized_catalog_key = catalog_key.strip() if isinstance(catalog_key, str) else None
    if normalized_catalog_key == "":
        normalized_catalog_key = None

    if normalized_catalog_key is not None:
        catalog_subject = (
            CatalogActivitySubject.objects.select_for_update(of=("self",))
            .filter(key=normalized_catalog_key)
            .first()
        )
        if catalog_subject is None:
            raise DomainNotFoundError(
                "Catalog activity subject was not found.",
                code="catalog_activity_subject_not_found",
            )
        if not catalog_subject.active:
            raise DomainConflictError(
                "Catalog activity subject is inactive.",
                code="catalog_activity_subject_inactive",
            )
        rows = build_activity_subject_rows_for_insert(
            business_unit=business_unit,
            catalog_activity_subjects=[catalog_subject],
        )
    else:
        if label is None:
            raise DomainValidationError(
                "Free activity subject label is required.",
                code="invalid_free_activity_subject_label",
            )
        rows = build_activity_subject_rows_for_insert(
            business_unit=business_unit,
            free_activity_subjects=[
                {"label": label, "description": description},
            ],
        )

    _bulk_create_activity_subjects(business_unit=business_unit, rows=rows)
    created = rows[0]
    return ActivitySubject.objects.select_related(
        "catalog_activity_subject",
        "business_unit",
        "business_unit__catalog_business_unit",
    ).get(id=created.id)
