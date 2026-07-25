from __future__ import annotations

import uuid
from typing import Any

from django.db.models import Prefetch, Q, QuerySet

from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    OperationalUnit,
)


def snapshot_ready_business_units_q() -> Q:
    """Shared predicate: active BU with routing identity and catalog link."""
    return (
        Q(active=True)
        & Q(routing_key__isnull=False)
        & ~Q(routing_key="")
        & Q(catalog_business_unit__isnull=False)
        & Q(specific_name__isnull=False)
        & ~Q(specific_name="")
    )


def snapshot_ready_business_units(*, establishment_id: uuid.UUID) -> QuerySet[BusinessUnit]:
    return BusinessUnit.objects.filter(
        establishment_id=establishment_id,
    ).filter(snapshot_ready_business_units_q())


def is_snapshot_ready_business_unit(business_unit: BusinessUnit | None) -> bool:
    if business_unit is None:
        return False
    if not business_unit.active:
        return False
    if not business_unit.routing_key:
        return False
    if business_unit.catalog_business_unit_id is None:
        return False
    if not business_unit.specific_name:
        return False
    return True


def _activity_subject_snapshot_source(*, activity_subject: ActivitySubject) -> str:
    if activity_subject.catalog_activity_subject_id is not None:
        return "catalog"
    return "free"


def _activity_subject_snapshot_label(*, activity_subject: ActivitySubject) -> str:
    catalog = activity_subject.catalog_activity_subject
    if catalog is not None:
        return catalog.label
    return activity_subject.label or ""


def _activity_subject_snapshot_description(*, activity_subject: ActivitySubject) -> str:
    catalog = activity_subject.catalog_activity_subject
    if catalog is not None:
        return catalog.description or ""
    return activity_subject.description or ""


_ACTIVITY_SUBJECTS_PREFETCH = Prefetch(
    "activity_subjects",
    queryset=(
        ActivitySubject.objects.filter(active=True)
        .exclude(Q(routing_key__isnull=True) | Q(routing_key=""))
        .select_related("catalog_activity_subject")
        .order_by("normalized_name")
    ),
)


def build_establishment_taxonomy_snapshot(
    *,
    establishment_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Runtime establishment taxonomy for the observation pipeline.

    Uses snapshot-ready BusinessUnit / active ActivitySubject with routing_key only
    — never the global catalogue alone.
    """
    business_units_qs = (
        snapshot_ready_business_units(establishment_id=establishment_id)
        .select_related("catalog_business_unit")
        .prefetch_related(_ACTIVITY_SUBJECTS_PREFETCH)
        .order_by("specific_name", "id")
    )

    business_units: list[dict[str, Any]] = []
    for unit in business_units_qs:
        catalog = unit.catalog_business_unit
        subjects = [
            {
                "routing_key": subject.routing_key,
                "label": _activity_subject_snapshot_label(activity_subject=subject),
                "description": _activity_subject_snapshot_description(
                    activity_subject=subject
                ),
                "source": _activity_subject_snapshot_source(activity_subject=subject),
            }
            for subject in unit.activity_subjects.all()
        ]
        business_units.append(
            {
                "routing_key": unit.routing_key,
                "specific_name": unit.specific_name,
                "generic_label": catalog.label,
                "generic_description": catalog.description or "",
                "instance_description": unit.instance_description or "",
                "unit_type": catalog.unit_type,
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
    """True when the establishment has at least one snapshot-ready BusinessUnit."""
    return snapshot_ready_business_units(establishment_id=establishment_id).exists()


def establishment_has_any_active_business_unit(*, establishment_id: uuid.UUID) -> bool:
    """True when the establishment has at least one active BusinessUnit (any identity)."""
    return BusinessUnit.objects.filter(
        establishment_id=establishment_id,
        active=True,
    ).exists()


def get_establishment_for_snapshot(establishment_id: uuid.UUID) -> Establishment | None:
    return Establishment.objects.filter(id=establishment_id).first()


def get_active_establishment_for_pipeline(
    establishment_id: uuid.UUID,
) -> Establishment | None:
    """Return the establishment when it exists and is ACTIVE (pipeline-attachable)."""
    return Establishment.objects.filter(
        id=establishment_id,
        status=Establishment.Status.ACTIVE,
    ).first()
