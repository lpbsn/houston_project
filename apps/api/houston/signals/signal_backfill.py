from __future__ import annotations

from uuid import UUID

from django.db import transaction

from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    OperationalModule,
    TaxonomyMigrationMap,
)
from houston.establishments.taxonomy_backfill import backfill_business_units_from_legacy_taxonomy
from houston.signals.models import Signal
from houston.signals.signal_classification import validate_signal_classification


def backfill_signal_classifications(*, establishment_id: UUID) -> int:
    backfill_business_units_from_legacy_taxonomy(establishment_id=establishment_id)
    establishment = Establishment.objects.get(id=establishment_id)
    updated = 0

    with transaction.atomic():
        for signal in Signal.objects.filter(
            establishment=establishment,
            affected_business_unit__isnull=True,
        ).select_related(
            "operational_module",
            "operational_domain",
            "operational_subject",
        ):
            classification = _derive_classification_from_legacy(signal)
            if classification is None:
                continue
            validate_signal_classification(
                establishment=establishment,
                affected_business_unit=classification["affected"],
                responsible_business_unit=classification["responsible"],
                activity_subject=classification["activity_subject"],
            )
            signal.affected_business_unit = classification["affected"]
            signal.responsible_business_unit = classification["responsible"]
            signal.activity_subject = classification["activity_subject"]
            signal.save(
                update_fields=[
                    "affected_business_unit",
                    "responsible_business_unit",
                    "activity_subject",
                    "updated_at",
                ]
            )
            updated += 1

    return updated


def _derive_classification_from_legacy(signal: Signal) -> dict | None:
    establishment = signal.establishment
    affected = _business_unit_for_module(establishment, signal.operational_module)
    if affected is None:
        return None

    subject_map = TaxonomyMigrationMap.objects.filter(
        establishment=establishment,
        legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_SUBJECT,
        legacy_id=signal.operational_subject_id,
        new_type=TaxonomyMigrationMap.NewType.ACTIVITY_SUBJECT,
    ).first()
    if subject_map is None:
        return None
    activity_subject = ActivitySubject.objects.filter(id=subject_map.new_id).first()
    if activity_subject is None:
        return None

    responsible = affected
    if (
        signal.operational_domain_id is not None
        and signal.operational_domain.operational_module_id != signal.operational_module_id
    ):
        transversal = BusinessUnit.objects.filter(
            establishment=establishment,
            unit_type=BusinessUnit.UnitType.TRANSVERSAL,
            active=True,
        ).first()
        if transversal is not None:
            responsible = transversal

    return {
        "affected": affected,
        "responsible": responsible,
        "activity_subject": activity_subject,
    }


def _business_unit_for_module(
    establishment: Establishment,
    module: OperationalModule,
) -> BusinessUnit | None:
    mapping = TaxonomyMigrationMap.objects.filter(
        establishment=establishment,
        legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_MODULE,
        legacy_id=module.id,
        new_type=TaxonomyMigrationMap.NewType.BUSINESS_UNIT,
    ).first()
    if mapping is None:
        return None
    return BusinessUnit.objects.filter(id=mapping.new_id).first()
