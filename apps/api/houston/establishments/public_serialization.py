"""Public serialization helpers for BusinessUnit / ActivitySubject (Lot 5 shape).

Cross-app consumers (action plans, signals nested refs) must import from this
module — not private selectors helpers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from houston.establishments.models import ActivitySubject, BusinessUnit


def resolve_activity_subject_public_label(
    *,
    activity_subject: ActivitySubject | None,
) -> str | None:
    """Lot 5 display label: catalog.label for generics, else instance.label."""
    if activity_subject is None:
        return None
    catalog = activity_subject.catalog_activity_subject
    if catalog is not None:
        return catalog.label or None
    label = activity_subject.label
    if not label:
        return None
    return label


def serialize_activity_subject_public(*, activity_subject: ActivitySubject) -> dict | None:
    """Lot 5 public ActivitySubject shape (no routing_key)."""
    catalog = activity_subject.catalog_activity_subject
    is_generic = catalog is not None
    if is_generic:
        return {
            "id": activity_subject.id,
            "catalog_key": catalog.key,
            "label": catalog.label,
            "description": catalog.description or "",
            "source": activity_subject.source,
            "active": activity_subject.active,
            "is_generic": True,
        }
    if not activity_subject.label:
        return None
    return {
        "id": activity_subject.id,
        "label": activity_subject.label,
        "description": activity_subject.description or "",
        "source": activity_subject.source,
        "active": activity_subject.active,
        "is_generic": False,
    }


def serialize_business_unit_public(
    *,
    business_unit: BusinessUnit,
    activity_subjects: list | None = None,
    include_activity_subjects: bool = True,
) -> dict | None:
    """Lot 5 public BusinessUnit shape (no routing_key).

    When ``include_activity_subjects`` is False, omits the ``activity_subjects``
    key (nested Action Plan / feed refs).
    """
    catalog = business_unit.catalog_business_unit
    if catalog is None or not business_unit.specific_name:
        return None

    payload: dict = {
        "id": business_unit.id,
        "specific_name": business_unit.specific_name,
        "instance_description": business_unit.instance_description or "",
        "active": business_unit.active,
        "generic": {
            "key": catalog.key,
            "label": catalog.label,
            "description": catalog.description or "",
            "unit_type": catalog.unit_type,
        },
    }
    if not include_activity_subjects:
        return payload

    from houston.establishments.models import ActivitySubject

    subjects = activity_subjects
    if subjects is None:
        subjects = list(
            ActivitySubject.objects.filter(
                business_unit=business_unit,
                active=True,
            )
            .select_related("catalog_activity_subject")
            .order_by("label", "normalized_name", "id")
        )

    serialized_subjects = []
    for subject in subjects:
        item = serialize_activity_subject_public(activity_subject=subject)
        if item is not None:
            serialized_subjects.append(item)
    payload["activity_subjects"] = serialized_subjects
    return payload


def _serialize_degraded_business_unit_ref(*, business_unit: BusinessUnit) -> dict:
    """Complete Lot 5 nested shape for incomplete identity (legacy / missing catalog)."""
    catalog = getattr(business_unit, "catalog_business_unit", None)
    specific_name = (
        business_unit.specific_name or business_unit.label or business_unit.key or ""
    )
    instance_description = (
        business_unit.instance_description
        if business_unit.instance_description is not None
        else (business_unit.description or "")
    )
    if catalog is not None:
        generic = {
            "key": catalog.key,
            "label": catalog.label,
            "description": catalog.description or "",
            "unit_type": catalog.unit_type,
        }
    else:
        generic = {
            "key": business_unit.key or "unknown",
            "label": business_unit.label or business_unit.key or "Unknown",
            "description": business_unit.description or "",
            "unit_type": business_unit.unit_type,
        }
    return {
        "id": business_unit.id,
        "specific_name": specific_name,
        "instance_description": instance_description or "",
        "active": business_unit.active,
        "generic": generic,
    }


def serialize_business_unit_ref(*, business_unit: BusinessUnit | None) -> dict | None:
    """Nested BusinessUnit ref for Action Plans / feed (Lot 5, no subjects)."""
    if business_unit is None:
        return None
    if (
        business_unit.catalog_business_unit_id is not None
        and getattr(business_unit, "catalog_business_unit", None) is None
    ):
        from houston.establishments.models import BusinessUnit as BusinessUnitModel

        business_unit = (
            BusinessUnitModel.objects.select_related("catalog_business_unit")
            .filter(id=business_unit.id)
            .first()
            or business_unit
        )
    payload = serialize_business_unit_public(
        business_unit=business_unit,
        include_activity_subjects=False,
    )
    if payload is not None:
        return payload
    return _serialize_degraded_business_unit_ref(business_unit=business_unit)


def serialize_activity_subject_ref(*, activity_subject: ActivitySubject | None) -> dict | None:
    """Nested ActivitySubject ref for Action Plans / feed (Lot 5)."""
    if activity_subject is None:
        return None
    if (
        activity_subject.catalog_activity_subject_id is not None
        and getattr(activity_subject, "catalog_activity_subject", None) is None
    ):
        from houston.establishments.models import ActivitySubject as ActivitySubjectModel

        activity_subject = (
            ActivitySubjectModel.objects.select_related("catalog_activity_subject")
            .filter(id=activity_subject.id)
            .first()
            or activity_subject
        )
    return serialize_activity_subject_public(activity_subject=activity_subject)
