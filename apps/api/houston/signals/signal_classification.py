from __future__ import annotations

from dataclasses import dataclass

from houston.establishments.models import ActivitySubject, BusinessUnit, Establishment


class InvalidSignalClassificationError(Exception):
    pass


@dataclass(frozen=True)
class SignalClassification:
    affected_business_unit: BusinessUnit
    responsible_business_unit: BusinessUnit
    activity_subject: ActivitySubject


def validate_signal_classification(
    *,
    establishment: Establishment,
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject: ActivitySubject,
) -> None:
    if affected_business_unit.establishment_id != establishment.id:
        raise InvalidSignalClassificationError(
            "affected_business_unit must belong to the signal establishment."
        )
    if responsible_business_unit.establishment_id != establishment.id:
        raise InvalidSignalClassificationError(
            "responsible_business_unit must belong to the signal establishment."
        )
    if activity_subject.establishment_id != establishment.id:
        raise InvalidSignalClassificationError(
            "activity_subject must belong to the signal establishment."
        )
    if activity_subject.business_unit_id != responsible_business_unit.id:
        raise InvalidSignalClassificationError(
            "activity_subject must belong to responsible_business_unit."
        )
    if (
        affected_business_unit.id != responsible_business_unit.id
        and responsible_business_unit.unit_type != BusinessUnit.UnitType.TRANSVERSAL
    ):
        raise InvalidSignalClassificationError(
            "responsible_business_unit must be transversal when different from affected."
        )
