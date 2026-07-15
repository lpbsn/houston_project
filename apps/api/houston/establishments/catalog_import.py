from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from houston.establishments.catalog_preflight import preflight_catalog_import
from houston.establishments.catalog_source_normalization import (
    CatalogActivitySubjectRow,
    CatalogBusinessUnitRow,
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
)
from houston.establishments.catalog_subject_label_service import (
    _apply_catalog_activity_subject_label_update,
)
from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit


@dataclass(frozen=True)
class CatalogSyncResult:
    business_units_created: int
    business_units_updated: int
    activity_subjects_created: int
    activity_subjects_updated: int

    @property
    def total_created(self) -> int:
        return self.business_units_created + self.activity_subjects_created

    @property
    def total_updated(self) -> int:
        return self.business_units_updated + self.activity_subjects_updated


def _lock_catalog_business_units(
    keys: set[str],
) -> dict[str, CatalogBusinessUnit]:
    if not keys:
        return {}
    rows = CatalogBusinessUnit.objects.filter(key__in=keys).select_for_update().order_by("key")
    return {row.key: row for row in rows}


def _lock_catalog_activity_subjects(
    keys: set[str],
) -> dict[str, CatalogActivitySubject]:
    if not keys:
        return {}
    rows = (
        CatalogActivitySubject.objects.filter(key__in=keys)
        .select_for_update(of=("self",))
        .order_by("key")
    )
    return {row.key: row for row in rows}


def _load_catalog_business_units_for_preflight(
    keys: set[str],
) -> dict[str, CatalogBusinessUnit]:
    if not keys:
        return {}
    rows = CatalogBusinessUnit.objects.filter(key__in=keys).order_by("key")
    return {row.key: row for row in rows}


def _load_catalog_activity_subjects_for_preflight(
    keys: set[str],
) -> dict[str, CatalogActivitySubject]:
    if not keys:
        return {}
    rows = (
        CatalogActivitySubject.objects.filter(key__in=keys)
        .select_related("catalog_business_unit")
        .order_by("key")
    )
    return {row.key: row for row in rows}


def preflight_catalog_import_from_rows(
    *,
    business_unit_rows: tuple[CatalogBusinessUnitRow, ...],
    activity_subject_rows: tuple[CatalogActivitySubjectRow, ...],
) -> None:
    bu_keys = {row.key for row in business_unit_rows}
    as_keys = {row.key for row in activity_subject_rows}
    preflight_catalog_import(
        business_unit_rows=business_unit_rows,
        activity_subject_rows=activity_subject_rows,
        locked_catalog_business_units=_load_catalog_business_units_for_preflight(bu_keys),
        locked_catalog_activity_subjects=_load_catalog_activity_subjects_for_preflight(as_keys),
    )


def sync_catalog_from_normalized_rows(
    *,
    business_unit_rows: tuple[CatalogBusinessUnitRow, ...] | None = None,
    activity_subject_rows: tuple[CatalogActivitySubjectRow, ...] | None = None,
) -> CatalogSyncResult:
    if business_unit_rows is not None:
        bu_rows = business_unit_rows
    else:
        bu_rows = load_normalized_business_unit_rows()
    as_rows = (
        activity_subject_rows
        if activity_subject_rows is not None
        else load_normalized_activity_subject_rows()
    )

    bu_created = bu_updated = 0
    as_created = as_updated = 0

    bu_keys = {row.key for row in bu_rows}
    as_keys = {row.key for row in as_rows}

    with transaction.atomic():
        locked_bus = _lock_catalog_business_units(bu_keys)
        locked_ass = _lock_catalog_activity_subjects(as_keys)

        preflight_catalog_import(
            business_unit_rows=bu_rows,
            activity_subject_rows=as_rows,
            locked_catalog_business_units=locked_bus,
            locked_catalog_activity_subjects=locked_ass,
        )

        bu_by_key: dict[str, CatalogBusinessUnit] = dict(locked_bus)

        for row in bu_rows:
            bu, created = CatalogBusinessUnit.objects.update_or_create(
                key=row.key,
                defaults={
                    "label": row.label,
                    "description": row.description,
                    "unit_type": row.unit_type,
                    "active": True,
                    "sort_order": row.sort_order,
                },
            )
            bu_by_key[row.key] = bu
            if created:
                bu_created += 1
            else:
                bu_updated += 1

        for row in as_rows:
            catalog_business_unit = bu_by_key.get(row.catalog_business_unit_key)
            if catalog_business_unit is None:
                raise ValueError(
                    f"Unknown business_unit_key {row.catalog_business_unit_key!r} "
                    f"for activity subject {row.key!r}"
                )

            existing = locked_ass.get(row.key)
            if existing is not None and row.label != existing.label:
                _apply_catalog_activity_subject_label_update(
                    catalog_activity_subject_key=row.key,
                    new_label=row.label,
                )
                CatalogActivitySubject.objects.filter(key=row.key).update(
                    catalog_business_unit=catalog_business_unit,
                    description=row.description,
                    active=True,
                    sort_order=row.sort_order,
                )
                as_updated += 1
                continue

            if existing is None:
                CatalogActivitySubject.objects.create(
                    key=row.key,
                    catalog_business_unit=catalog_business_unit,
                    label=row.label,
                    description=row.description,
                    active=True,
                    sort_order=row.sort_order,
                )
                as_created += 1
            else:
                CatalogActivitySubject.objects.filter(key=row.key).update(
                    catalog_business_unit=catalog_business_unit,
                    description=row.description,
                    active=True,
                    sort_order=row.sort_order,
                )
                as_updated += 1

    return CatalogSyncResult(
        business_units_created=bu_created,
        business_units_updated=bu_updated,
        activity_subjects_created=as_created,
        activity_subjects_updated=as_updated,
    )
