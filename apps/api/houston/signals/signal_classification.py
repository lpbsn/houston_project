from __future__ import annotations

from dataclasses import dataclass

from houston.establishments.models import ActivitySubject, BusinessUnit, Establishment
from houston.signals.models import Signal


class InvalidSignalClassificationError(Exception):
    pass


@dataclass(frozen=True)
class SignalClassification:
    affected_business_unit: BusinessUnit
    responsible_business_unit: BusinessUnit
    activity_subject: ActivitySubject


def validate_partial_signal_routing(
    *,
    establishment: Establishment,
    affected_business_unit: BusinessUnit | None = None,
    responsible_business_unit: BusinessUnit | None = None,
    activity_subject: ActivitySubject | None = None,
) -> None:
    if (
        affected_business_unit is not None
        and affected_business_unit.establishment_id != establishment.id
    ):
        raise InvalidSignalClassificationError(
            "affected_business_unit must belong to the signal establishment."
        )
    if (
        responsible_business_unit is not None
        and responsible_business_unit.establishment_id != establishment.id
    ):
        raise InvalidSignalClassificationError(
            "responsible_business_unit must belong to the signal establishment."
        )
    if (
        activity_subject is not None
        and activity_subject.establishment_id != establishment.id
    ):
        raise InvalidSignalClassificationError(
            "activity_subject must belong to the signal establishment."
        )
    if activity_subject is not None:
        if responsible_business_unit is None:
            raise InvalidSignalClassificationError(
                "activity_subject requires responsible_business_unit."
            )
        if activity_subject.business_unit_id != responsible_business_unit.id:
            raise InvalidSignalClassificationError(
                "activity_subject must belong to responsible_business_unit."
            )


def validate_signal_classification(
    *,
    establishment: Establishment,
    affected_business_unit: BusinessUnit,
    responsible_business_unit: BusinessUnit,
    activity_subject: ActivitySubject,
) -> None:
    validate_partial_signal_routing(
        establishment=establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
    )


def routing_status_for_classification(
    *,
    establishment: Establishment,
    affected_business_unit: BusinessUnit | None = None,
    responsible_business_unit: BusinessUnit | None = None,
    activity_subject: ActivitySubject | None = None,
) -> str:
    validate_partial_signal_routing(
        establishment=establishment,
        affected_business_unit=affected_business_unit,
        responsible_business_unit=responsible_business_unit,
        activity_subject=activity_subject,
    )
    if (
        affected_business_unit is not None
        and responsible_business_unit is not None
        and activity_subject is not None
    ):
        return Signal.RoutingStatus.RESOLVED
    return Signal.RoutingStatus.UNASSIGNED
