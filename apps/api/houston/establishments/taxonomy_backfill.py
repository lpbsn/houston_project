from __future__ import annotations

from uuid import UUID

from django.db import transaction

from houston.establishments.business_unit_catalog import default_unit_type_for_key
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    OperationalDomain,
    OperationalModule,
    OperationalSubject,
    TaxonomyMigrationMap,
)
from houston.establishments.taxonomy_normalization import normalize_activity_subject_name


def backfill_business_units_from_legacy_taxonomy(
    *,
    establishment_id: UUID,
) -> dict[str, int]:
    """Idempotently migrate v1 operational taxonomy to v2 for one establishment."""
    establishment = Establishment.objects.get(id=establishment_id)
    counts = {"business_units": 0, "activity_subjects": 0, "maps": 0}

    with transaction.atomic():
        module_to_bu: dict[UUID, BusinessUnit] = {}
        for module in OperationalModule.objects.filter(establishment=establishment):
            existing_map = TaxonomyMigrationMap.objects.filter(
                establishment=establishment,
                legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_MODULE,
                legacy_id=module.id,
            ).first()
            if existing_map:
                bu = BusinessUnit.objects.get(id=existing_map.new_id)
            else:
                bu, created = BusinessUnit.objects.get_or_create(
                    establishment=establishment,
                    key=module.key,
                    defaults={
                        "label": module.label,
                        "unit_type": default_unit_type_for_key(module.key),
                        "source": BusinessUnit.Source.MIGRATED,
                        "active": module.active,
                        "managed_by_onboarding_proposal": module.managed_by_onboarding_proposal,
                    },
                )
                if created:
                    counts["business_units"] += 1
                TaxonomyMigrationMap.objects.get_or_create(
                    establishment=establishment,
                    legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_MODULE,
                    legacy_id=module.id,
                    defaults={
                        "new_type": TaxonomyMigrationMap.NewType.BUSINESS_UNIT,
                        "new_id": bu.id,
                    },
                )
                counts["maps"] += 1
            module_to_bu[module.id] = bu

        domain_to_as: dict[UUID, ActivitySubject] = {}
        for domain in OperationalDomain.objects.filter(establishment=establishment):
            module_id = domain.operational_module_id
            bu = module_to_bu.get(module_id) if module_id else None
            if bu is None:
                bu, created = BusinessUnit.objects.get_or_create(
                    establishment=establishment,
                    key=domain.key,
                    defaults={
                        "label": domain.label,
                        "unit_type": default_unit_type_for_key(domain.key),
                        "source": BusinessUnit.Source.MIGRATED,
                        "active": domain.active,
                    },
                )
                if created:
                    counts["business_units"] += 1

            existing_map = TaxonomyMigrationMap.objects.filter(
                establishment=establishment,
                legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_DOMAIN,
                legacy_id=domain.id,
            ).first()
            if existing_map:
                activity_subject = ActivitySubject.objects.get(id=existing_map.new_id)
            else:
                normalized = normalize_activity_subject_name(domain.label)
                activity_subject, created = ActivitySubject.objects.get_or_create(
                    establishment=establishment,
                    business_unit=bu,
                    normalized_name=normalized,
                    defaults={
                        "label": domain.label,
                        "source": ActivitySubject.Source.MIGRATED,
                        "active": domain.active,
                        "managed_by_onboarding_proposal": domain.managed_by_onboarding_proposal,
                    },
                )
                if created:
                    counts["activity_subjects"] += 1
                TaxonomyMigrationMap.objects.get_or_create(
                    establishment=establishment,
                    legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_DOMAIN,
                    legacy_id=domain.id,
                    defaults={
                        "new_type": TaxonomyMigrationMap.NewType.ACTIVITY_SUBJECT,
                        "new_id": activity_subject.id,
                    },
                )
                counts["maps"] += 1
            domain_to_as[domain.id] = activity_subject

        for subject in OperationalSubject.objects.filter(establishment=establishment):
            domain = subject.operational_domain
            bu = None
            if domain is not None:
                if domain.operational_module_id and domain.operational_module_id in module_to_bu:
                    bu = module_to_bu[domain.operational_module_id]
                elif domain.id in domain_to_as:
                    bu = domain_to_as[domain.id].business_unit
            if bu is None:
                bu, created = BusinessUnit.objects.get_or_create(
                    establishment=establishment,
                    key=f"unassigned_{subject.key[:80]}",
                    defaults={
                        "label": "Unassigned",
                        "unit_type": BusinessUnit.UnitType.DEDICATED,
                        "source": BusinessUnit.Source.MIGRATED,
                        "active": True,
                    },
                )
                if created:
                    counts["business_units"] += 1

            existing_map = TaxonomyMigrationMap.objects.filter(
                establishment=establishment,
                legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_SUBJECT,
                legacy_id=subject.id,
            ).first()
            if existing_map:
                continue

            normalized = normalize_activity_subject_name(subject.label)
            activity_subject, created = ActivitySubject.objects.get_or_create(
                establishment=establishment,
                business_unit=bu,
                normalized_name=normalized,
                defaults={
                    "label": subject.label,
                    "source": ActivitySubject.Source.MIGRATED,
                    "active": subject.active,
                    "managed_by_onboarding_proposal": subject.managed_by_onboarding_proposal,
                },
            )
            if created:
                counts["activity_subjects"] += 1
            TaxonomyMigrationMap.objects.get_or_create(
                establishment=establishment,
                legacy_type=TaxonomyMigrationMap.LegacyType.OPERATIONAL_SUBJECT,
                legacy_id=subject.id,
                defaults={
                    "new_type": TaxonomyMigrationMap.NewType.ACTIVITY_SUBJECT,
                    "new_id": activity_subject.id,
                },
            )
            counts["maps"] += 1

    return counts
