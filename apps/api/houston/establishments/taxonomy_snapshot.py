from __future__ import annotations

import uuid
from typing import Any

from django.db.models import Prefetch, Q, QuerySet

from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentActivityDescription,
    OperationalUnit,
)
from houston.signals.catalog_capabilities import (
    CATALOG_CAPABILITIES_VERSION,
    capabilities_for_catalog_key,
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


def _catalog_fields_for_business_unit(*, unit: BusinessUnit) -> dict[str, Any]:
    catalog = unit.catalog_business_unit
    if catalog is None:
        return {
            "catalog_key": None,
            "generic_label": None,
            "generic_description": None,
            "unit_type": None,
        }
    return {
        "catalog_key": catalog.key,
        "generic_label": catalog.label,
        "generic_description": catalog.description or "",
        "unit_type": catalog.unit_type,
    }


_ACTIVITY_SUBJECTS_PREFETCH = Prefetch(
    "activity_subjects",
    queryset=(
        ActivitySubject.objects.filter(active=True)
        .exclude(Q(routing_key__isnull=True) | Q(routing_key=""))
        .select_related("catalog_activity_subject")
        .order_by("normalized_name")
    ),
)


def build_active_business_units(*, establishment_id: uuid.UUID) -> list[dict[str, Any]]:
    """All active BusinessUnits — never filtered by snapshot-ready or catalogue."""
    units = (
        BusinessUnit.objects.filter(
            establishment_id=establishment_id,
            active=True,
        )
        .select_related("catalog_business_unit")
        .order_by("specific_name", "id")
    )
    entries: list[dict[str, Any]] = []
    for unit in units:
        catalog_fields = _catalog_fields_for_business_unit(unit=unit)
        entries.append(
            {
                "id": str(unit.id),
                "specific_name": unit.specific_name,
                "catalog_key": catalog_fields["catalog_key"],
                "generic_label": catalog_fields["generic_label"],
                "generic_description": catalog_fields["generic_description"],
                "instance_description": unit.instance_description or "",
                "unit_type": catalog_fields["unit_type"],
            }
        )
    return entries


def build_routing_taxonomy(*, establishment_id: uuid.UUID) -> dict[str, Any]:
    """
    Routable-only taxonomy for proposing/validating routing keys.

    Snapshot-ready BUs with at least one active subject that has a routing_key.
    """
    business_units_qs = (
        snapshot_ready_business_units(establishment_id=establishment_id)
        .select_related("catalog_business_unit")
        .prefetch_related(_ACTIVITY_SUBJECTS_PREFETCH)
        .order_by("specific_name", "id")
    )

    business_units: list[dict[str, Any]] = []
    for unit in business_units_qs:
        subjects_raw = list(unit.activity_subjects.all())
        if not subjects_raw:
            continue
        catalog_fields = _catalog_fields_for_business_unit(unit=unit)
        subjects: list[dict[str, Any]] = []
        for subject in subjects_raw:
            source = _activity_subject_snapshot_source(activity_subject=subject)
            catalog_key = (
                subject.catalog_activity_subject.key
                if subject.catalog_activity_subject_id is not None
                and subject.catalog_activity_subject is not None
                else None
            )
            if source == "catalog":
                capabilities = capabilities_for_catalog_key(catalog_key)
            else:
                capabilities = []
            subjects.append(
                {
                    "routing_key": subject.routing_key,
                    "label": _activity_subject_snapshot_label(activity_subject=subject),
                    "description": _activity_subject_snapshot_description(
                        activity_subject=subject
                    ),
                    "source": source,
                    "catalog_key": catalog_key,
                    "capabilities": capabilities,
                }
            )
        business_units.append(
            {
                "routing_key": unit.routing_key,
                "specific_name": unit.specific_name,
                "catalog_key": catalog_fields["catalog_key"],
                "generic_label": catalog_fields["generic_label"],
                "generic_description": catalog_fields["generic_description"],
                "instance_description": unit.instance_description or "",
                "unit_type": catalog_fields["unit_type"],
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
        "capabilities_version": CATALOG_CAPABILITIES_VERSION,
        "business_units": business_units,
        "operational_units": operational_units,
    }


def build_establishment_context(*, establishment_id: uuid.UUID) -> dict[str, Any]:
    establishment = Establishment.objects.filter(id=establishment_id).first()
    if establishment is None:
        return {
            "id": str(establishment_id),
            "name": "",
            "activity_description": None,
            "active_business_units": [],
        }
    activity_description = (
        EstablishmentActivityDescription.objects.filter(establishment_id=establishment.id)
        .values_list("description", flat=True)
        .first()
    )
    return {
        "id": str(establishment.id),
        "name": establishment.name,
        "activity_description": activity_description,
        "active_business_units": build_active_business_units(
            establishment_id=establishment_id,
        ),
    }


def routing_taxonomy_business_unit_keys(
    *,
    routing_taxonomy: dict[str, Any],
) -> set[str]:
    keys: set[str] = set()
    for unit in routing_taxonomy.get("business_units") or []:
        routing_key = unit.get("routing_key")
        if isinstance(routing_key, str) and routing_key:
            keys.add(routing_key)
    return keys


def build_establishment_taxonomy_snapshot(
    *,
    establishment_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Compatibility wrapper: routable taxonomy without capabilities_version.

    Prefer build_routing_taxonomy / build_establishment_context for V6 pipeline input.
    """
    taxonomy = build_routing_taxonomy(establishment_id=establishment_id)
    return {
        "business_units": [
            {
                "routing_key": unit["routing_key"],
                "specific_name": unit["specific_name"],
                "generic_label": unit["generic_label"] or "",
                "generic_description": unit["generic_description"] or "",
                "instance_description": unit["instance_description"],
                "unit_type": unit["unit_type"] or "",
                "activity_subjects": [
                    {
                        "routing_key": subject["routing_key"],
                        "label": subject["label"],
                        "description": subject["description"],
                        "source": subject["source"],
                    }
                    for subject in unit["activity_subjects"]
                ],
            }
            for unit in taxonomy["business_units"]
        ],
        "operational_units": taxonomy["operational_units"],
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
