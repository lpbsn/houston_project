from __future__ import annotations

import uuid
from typing import Any

from houston.establishments.models import BusinessUnit, Establishment, OperationalUnit


def build_establishment_taxonomy_snapshot(
    *,
    establishment_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Runtime establishment taxonomy for the observation pipeline.

    Uses active BusinessUnit / ActivitySubject only — never the global catalogue.
    """
    business_units_qs = (
        BusinessUnit.objects.filter(
            establishment_id=establishment_id,
            active=True,
        )
        .prefetch_related("activity_subjects")
        .order_by("key")
    )

    business_units: list[dict[str, Any]] = []
    for unit in business_units_qs:
        subjects = [
            {
                "key": subject.normalized_name,
                "label": subject.label,
                "description": subject.description or "",
            }
            for subject in unit.activity_subjects.filter(active=True).order_by("normalized_name")
        ]
        business_units.append(
            {
                "key": unit.key,
                "label": unit.label,
                "unit_type": unit.unit_type,
                "description": unit.description or "",
                "activity_subjects": subjects,
            }
        )

    operational_units = list(
        OperationalUnit.objects.filter(
            establishment_id=establishment_id,
            active=True,
        )
        .values("key", "label")
        .order_by("key")
    )

    return {
        "business_units": business_units,
        "operational_units": operational_units,
    }


def establishment_has_active_business_units(*, establishment_id: uuid.UUID) -> bool:
    return BusinessUnit.objects.filter(
        establishment_id=establishment_id,
        active=True,
    ).exists()


def get_establishment_for_snapshot(establishment_id: uuid.UUID) -> Establishment | None:
    return Establishment.objects.filter(id=establishment_id).first()
