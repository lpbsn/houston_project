from __future__ import annotations

import uuid
from dataclasses import dataclass

from houston.actions.exceptions import ActionValidationError
from houston.establishments.models import ActivitySubject, BusinessUnit
from houston.signals.models import Signal
from houston.signals.signal_classification import validate_signal_classification

LEGACY_CLASSIFICATION_ERROR = (
    "Legacy classification (module/domain/subject) is no longer accepted. "
    "A linked Action inherits from its Signal; a free Action must provide "
    "responsible_business_unit_id."
)


@dataclass(frozen=True)
class LinkedActionClassification:
    affected_business_unit: BusinessUnit
    responsible_business_unit: BusinessUnit
    activity_subject: ActivitySubject


def reject_legacy_classification_keys(*, payload: dict) -> None:
    for key in ("module_key", "domain_key", "subject_key"):
        if key in payload:
            raise ActionValidationError(LEGACY_CLASSIFICATION_ERROR)


def classification_from_signal(*, signal: Signal) -> LinkedActionClassification:
    if signal.affected_business_unit_id is None:
        raise ActionValidationError("Signal is missing affected business unit classification.")
    if signal.responsible_business_unit_id is None:
        raise ActionValidationError("Signal is missing responsible business unit classification.")
    if signal.activity_subject_id is None:
        raise ActionValidationError("Signal is missing activity subject classification.")

    affected = signal.affected_business_unit
    responsible = signal.responsible_business_unit
    activity_subject = signal.activity_subject

    validate_signal_classification(
        establishment=signal.establishment,
        affected_business_unit=affected,
        responsible_business_unit=responsible,
        activity_subject=activity_subject,
    )

    return LinkedActionClassification(
        affected_business_unit=affected,
        responsible_business_unit=responsible,
        activity_subject=activity_subject,
    )


def resolve_responsible_business_unit(
    *,
    establishment_id: uuid.UUID,
    business_unit_id: uuid.UUID,
) -> BusinessUnit:
    business_unit = BusinessUnit.objects.filter(
        id=business_unit_id,
        establishment_id=establishment_id,
        active=True,
    ).first()
    if business_unit is None:
        raise ActionValidationError("Invalid responsible business unit.")
    return business_unit
