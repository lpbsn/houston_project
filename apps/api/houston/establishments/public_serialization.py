"""Public serialization helpers for BusinessUnit / ActivitySubject (Lot 5 shape).

Cross-app consumers (action plans, signals nested refs) must import from this
module — not private selectors helpers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from houston.establishments.models import ActivitySubject, BusinessUnit

logger = logging.getLogger(__name__)


class IncompleteBusinessUnitIdentityError(RuntimeError):
    """Raised when a BusinessUnit row is missing required identity fields."""


class IncompleteActivitySubjectIdentityError(RuntimeError):
    """Raised when an ActivitySubject row is missing required identity fields."""


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


def serialize_activity_subject_public(*, activity_subject: ActivitySubject) -> dict:
    """Lot 5 public ActivitySubject shape (no routing_key)."""
    catalog = activity_subject.catalog_activity_subject
    is_generic = catalog is not None
    if is_generic:
        if not activity_subject.routing_key:
            logger.error(
                "incomplete_activity_subject_identity",
                extra={"activity_subject_id": str(activity_subject.id), "kind": "generic"},
            )
            raise IncompleteActivitySubjectIdentityError(
                f"ActivitySubject {activity_subject.id} has incomplete generic identity."
            )
        return {
            "id": activity_subject.id,
            "catalog_key": catalog.key,
            "label": catalog.label,
            "description": catalog.description or "",
            "source": activity_subject.source,
            "active": activity_subject.active,
            "is_generic": True,
        }
    if not activity_subject.label or not activity_subject.routing_key:
        logger.error(
            "incomplete_activity_subject_identity",
            extra={"activity_subject_id": str(activity_subject.id), "kind": "free"},
        )
        raise IncompleteActivitySubjectIdentityError(
            f"ActivitySubject {activity_subject.id} has incomplete free identity."
        )
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
) -> dict:
    """Lot 5 public BusinessUnit shape (no routing_key)."""
    catalog = None
    if business_unit.catalog_business_unit_id is not None:
        catalog = getattr(business_unit, "catalog_business_unit", None)
        if catalog is None:
            from houston.establishments.models import CatalogBusinessUnit

            catalog = CatalogBusinessUnit.objects.filter(
                id=business_unit.catalog_business_unit_id
            ).first()
    if (
        catalog is None
        or not (business_unit.specific_name or "").strip()
        or not (business_unit.normalized_specific_name or "").strip()
        or not (business_unit.routing_key or "").strip()
    ):
        logger.error(
            "incomplete_business_unit_identity",
            extra={"business_unit_id": str(business_unit.id)},
        )
        raise IncompleteBusinessUnitIdentityError(
            f"BusinessUnit {business_unit.id} has incomplete identity."
        )

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
            .order_by("normalized_name", "id")
        )

    payload["activity_subjects"] = [
        serialize_activity_subject_public(activity_subject=subject)
        for subject in subjects
    ]
    return payload


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
    return serialize_business_unit_public(
        business_unit=business_unit,
        include_activity_subjects=False,
    )


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
