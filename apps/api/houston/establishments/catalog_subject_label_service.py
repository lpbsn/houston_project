from __future__ import annotations

import re
import unicodedata

from django.db import IntegrityError, transaction

from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogActivitySubject,
)
from houston.establishments.taxonomy_normalization import (
    LABEL_FIXES,
    normalize_activity_subject_name,
)


class CatalogSubjectLabelConflictError(Exception):
    def __init__(self, *, detail: str):
        self.code = "catalog_subject_label_conflict"
        self.detail = detail
        super().__init__(detail)


class CatalogSubjectLabelValidationError(Exception):
    def __init__(self, *, detail: str):
        self.code = "invalid_normalized_name"
        self.detail = detail
        super().__init__(detail)


def _normalized_name_without_fallback(label: str) -> str:
    text = label.strip()
    text = LABEL_FIXES.get(text, text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.lower())
    return text.strip("_")


def _validate_catalog_subject_label(new_label: str) -> str:
    if not new_label.strip():
        raise CatalogSubjectLabelValidationError(
            detail="Catalog activity subject label cannot be blank.",
        )
    normalized = _normalized_name_without_fallback(new_label)
    if not normalized:
        raise CatalogSubjectLabelValidationError(
            detail="Catalog activity subject label must produce a non-empty normalized name.",
        )
    return normalize_activity_subject_name(new_label)


def _apply_catalog_activity_subject_label_update(
    *,
    catalog_activity_subject_key: str,
    new_label: str,
) -> CatalogActivitySubject:
    new_normalized = _validate_catalog_subject_label(new_label)

    try:
        catalog_subject = CatalogActivitySubject.objects.select_for_update(of=("self",)).get(
            key=catalog_activity_subject_key
        )
    except CatalogActivitySubject.DoesNotExist as exc:
        raise CatalogSubjectLabelConflictError(
            detail=f"Unknown catalog activity subject key {catalog_activity_subject_key!r}.",
        ) from exc

    associations = list(
        ActivitySubject.objects.select_for_update(of=("self",))
        .filter(catalog_activity_subject_id=catalog_subject.id)
    )

    business_unit_ids = {association.business_unit_id for association in associations}
    if business_unit_ids:
        list(
            BusinessUnit.objects.select_for_update(of=("self",))
            .filter(id__in=business_unit_ids)
            .order_by("id")
        )

    for association in associations:
        collision_exists = (
            ActivitySubject.objects.filter(
                business_unit_id=association.business_unit_id,
                normalized_name=new_normalized,
            )
            .exclude(id=association.id)
            .exists()
        )
        if collision_exists:
            raise CatalogSubjectLabelConflictError(
                detail=(
                    f"Catalog activity subject label {new_label!r} conflicts with an existing "
                    f"activity subject in business unit {association.business_unit_id}."
                ),
            )

    catalog_subject.label = new_label
    try:
        catalog_subject.save(update_fields=["label", "updated_at"])
        for association in associations:
            association.label = new_label
            association.normalized_name = new_normalized
            association.save(update_fields=["label", "normalized_name", "updated_at"])
    except IntegrityError as exc:
        raise CatalogSubjectLabelConflictError(
            detail=(
                f"Catalog activity subject label {new_label!r} conflicts with an existing "
                f"activity subject normalized name."
            ),
        ) from exc

    return catalog_subject


def update_catalog_activity_subject_label(
    *,
    catalog_activity_subject_key: str,
    new_label: str,
) -> CatalogActivitySubject:
    with transaction.atomic():
        return _apply_catalog_activity_subject_label_update(
            catalog_activity_subject_key=catalog_activity_subject_key,
            new_label=new_label,
        )
