from __future__ import annotations

from collections import Counter

from houston.establishments.catalog_source_normalization import (
    CatalogActivitySubjectRow,
    CatalogBusinessUnitRow,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogActivitySubject,
    CatalogBusinessUnit,
)

RESERVED_CATALOG_KEY_PREFIX = "custom--"


class CatalogImportError(Exception):
    def __init__(self, *, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _assert_no_duplicate_keys(
    *,
    keys: tuple[str, ...],
    entity_label: str,
) -> None:
    counts = Counter(keys)
    duplicates = [key for key, count in counts.items() if count > 1]
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise CatalogImportError(
            code="duplicate_catalog_key",
            detail=f"Duplicate {entity_label} key(s) in import file: {joined}",
        )


def _catalog_business_unit_is_referenced(*, catalog_business_unit_id) -> bool:
    return BusinessUnit.objects.filter(catalog_business_unit_id=catalog_business_unit_id).exists()


def _catalog_activity_subject_is_referenced(*, catalog_activity_subject_id) -> bool:
    return ActivitySubject.objects.filter(
        catalog_activity_subject_id=catalog_activity_subject_id
    ).exists()


def preflight_catalog_import(
    *,
    business_unit_rows: tuple[CatalogBusinessUnitRow, ...],
    activity_subject_rows: tuple[CatalogActivitySubjectRow, ...],
    locked_catalog_business_units: dict[str, CatalogBusinessUnit],
    locked_catalog_activity_subjects: dict[str, CatalogActivitySubject],
) -> None:
    _assert_no_duplicate_keys(
        keys=tuple(row.key for row in business_unit_rows),
        entity_label="catalog business unit",
    )
    _assert_no_duplicate_keys(
        keys=tuple(row.key for row in activity_subject_rows),
        entity_label="catalog activity subject",
    )

    import_business_unit_keys = {row.key for row in business_unit_rows}

    for row in activity_subject_rows:
        if row.key.startswith(RESERVED_CATALOG_KEY_PREFIX):
            raise CatalogImportError(
                code="reserved_catalog_key_prefix",
                detail=(
                    f"Catalog activity subject key {row.key!r} uses reserved prefix "
                    f"{RESERVED_CATALOG_KEY_PREFIX!r}."
                ),
            )
        if row.catalog_business_unit_key not in import_business_unit_keys:
            if row.catalog_business_unit_key not in locked_catalog_business_units:
                raise CatalogImportError(
                    code="invalid_catalog_structure",
                    detail=(
                        f"Unknown business_unit_key {row.catalog_business_unit_key!r} "
                        f"for activity subject {row.key!r}."
                    ),
                )

    for row in business_unit_rows:
        existing = locked_catalog_business_units.get(row.key)
        if existing is None:
            continue
        if _catalog_business_unit_is_referenced(catalog_business_unit_id=existing.id):
            if row.unit_type != existing.unit_type:
                raise CatalogImportError(
                    code="catalog_immutable_field",
                    detail=(
                        f"Cannot change unit_type for referenced catalog business unit "
                        f"{row.key!r}."
                    ),
                )

    for row in activity_subject_rows:
        existing = locked_catalog_activity_subjects.get(row.key)
        if existing is None:
            continue
        if not _catalog_activity_subject_is_referenced(
            catalog_activity_subject_id=existing.id
        ):
            continue
        existing_parent_key = (
            existing.catalog_business_unit.key
            if existing.catalog_business_unit_id is not None
            else None
        )
        if existing_parent_key != row.catalog_business_unit_key:
            raise CatalogImportError(
                code="catalog_subject_immutable_business_unit",
                detail=(
                    f"Cannot change catalog business unit parent for referenced activity "
                    f"subject {row.key!r}."
                ),
            )
