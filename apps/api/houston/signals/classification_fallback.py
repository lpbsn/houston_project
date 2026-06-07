from __future__ import annotations

from dataclasses import dataclass

from houston.establishments.models import ActivitySubject, BusinessUnit, Establishment
from houston.signals.signal_classification import (
    InvalidSignalClassificationError,
    validate_signal_classification,
)


@dataclass(frozen=True)
class ResolvedClassification:
    affected_business_unit: BusinessUnit
    responsible_business_unit: BusinessUnit
    activity_subject: ActivitySubject


def try_apply_responsible_affected_fallback(
    *,
    establishment: Establishment,
    affected: BusinessUnit,
    responsible: BusinessUnit | None,
    activity_subject: ActivitySubject | None,
    subject_under_affected: ActivitySubject | None,
) -> ResolvedClassification | None:
    """
    Single allowed fallback: responsible = affected when activity_subject belongs to affected.

    Used when responsible is missing/invalid or classification fails, and the subject
    is valid under affected only.
    """
    if subject_under_affected is None:
        return None
    if activity_subject is not None and activity_subject.id != subject_under_affected.id:
        return None
    if responsible is not None and responsible.id == affected.id:
        if activity_subject is None:
            return None
        try:
            validate_signal_classification(
                establishment=establishment,
                affected_business_unit=affected,
                responsible_business_unit=affected,
                activity_subject=activity_subject,
            )
        except InvalidSignalClassificationError:
            return None
        return ResolvedClassification(
            affected_business_unit=affected,
            responsible_business_unit=affected,
            activity_subject=activity_subject,
        )

    try:
        validate_signal_classification(
            establishment=establishment,
            affected_business_unit=affected,
            responsible_business_unit=affected,
            activity_subject=subject_under_affected,
        )
    except InvalidSignalClassificationError:
        return None
    return ResolvedClassification(
        affected_business_unit=affected,
        responsible_business_unit=affected,
        activity_subject=subject_under_affected,
    )
