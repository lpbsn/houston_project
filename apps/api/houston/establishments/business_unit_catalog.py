from __future__ import annotations

from django.db.models import Q

from houston.establishments.catalog_source_normalization import (
    TRANSVERSAL_BUSINESS_UNIT_KEYS,
    default_unit_type_for_business_unit_key,
)
from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit
from houston.establishments.taxonomy_normalization import slugify_label


def suggest_business_units(
    *,
    query: str,
    limit: int = 20,
    max_limit: int = 200,
) -> list[dict[str, str]]:
    limit = max(1, min(limit, max_limit))
    needle = query.strip().lower()
    queryset = CatalogBusinessUnit.objects.filter(active=True).order_by("sort_order", "key")
    if needle:
        queryset = queryset.filter(Q(label__icontains=needle) | Q(key__icontains=needle))

    results: list[dict[str, str]] = []
    for row in queryset[:limit]:
        results.append(
            {
                "key": row.key,
                "label": row.label,
                "default_unit_type": row.default_unit_type,
            }
        )
    return results


def suggest_activity_subjects(
    *,
    business_unit_key: str | None,
    query: str,
    limit: int = 20,
    max_limit: int = 200,
) -> list[dict[str, str]]:
    limit = max(1, min(limit, max_limit))
    needle = query.strip().lower()
    queryset = (
        CatalogActivitySubject.objects.filter(active=True)
        .select_related("catalog_business_unit")
        .order_by("sort_order", "key")
    )
    if business_unit_key:
        queryset = queryset.filter(catalog_business_unit__key=business_unit_key)
    if needle:
        queryset = queryset.filter(Q(label__icontains=needle) | Q(key__icontains=needle))

    results: list[dict[str, str]] = []
    for row in queryset[:limit]:
        bu_key = row.catalog_business_unit.key if row.catalog_business_unit_id else ""
        results.append(
            {
                "key": row.key,
                "label": row.label,
                "business_unit_key": bu_key,
            }
        )
    return results


def default_unit_type_for_key(key: str) -> str:
    normalized = slugify_label(key)
    if normalized in TRANSVERSAL_BUSINESS_UNIT_KEYS:
        return "transversal"
    return default_unit_type_for_business_unit_key(normalized)
