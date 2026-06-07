from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from houston.establishments.catalog_source_normalization import (
    CatalogActivitySubjectRow,
    CatalogBusinessUnitRow,
    load_normalized_activity_subject_rows,
    load_normalized_business_unit_rows,
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

    with transaction.atomic():
        bu_by_key: dict[str, CatalogBusinessUnit] = {}
        for row in bu_rows:
            bu, created = CatalogBusinessUnit.objects.update_or_create(
                key=row.key,
                defaults={
                    "label": row.label,
                    "description": row.description,
                    "default_unit_type": row.default_unit_type,
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
            _, created = CatalogActivitySubject.objects.update_or_create(
                key=row.key,
                defaults={
                    "catalog_business_unit": catalog_business_unit,
                    "label": row.label,
                    "description": row.description,
                    "active": True,
                    "sort_order": row.sort_order,
                },
            )
            if created:
                as_created += 1
            else:
                as_updated += 1

    return CatalogSyncResult(
        business_units_created=bu_created,
        business_units_updated=bu_updated,
        activity_subjects_created=as_created,
        activity_subjects_updated=as_updated,
    )
