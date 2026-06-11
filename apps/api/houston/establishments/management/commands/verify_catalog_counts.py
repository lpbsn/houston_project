from __future__ import annotations

import sys

from django.core.management.base import BaseCommand

from houston.establishments.catalog_seed_counts import (
    EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT,
    EXPECTED_CATALOG_BUSINESS_UNIT_COUNT,
)
from houston.establishments.models import CatalogActivitySubject, CatalogBusinessUnit


class Command(BaseCommand):
    help = (
        "Verify CatalogBusinessUnit and CatalogActivitySubject row counts "
        "match the versioned seed CSV expectations."
    )

    def handle(self, *args, **options):
        business_unit_count = CatalogBusinessUnit.objects.count()
        activity_subject_count = CatalogActivitySubject.objects.count()
        expected_bu = EXPECTED_CATALOG_BUSINESS_UNIT_COUNT
        expected_as = EXPECTED_CATALOG_ACTIVITY_SUBJECT_COUNT

        if (
            business_unit_count != expected_bu
            or activity_subject_count != expected_as
        ):
            self.stderr.write(
                "catalog-check FAILED: "
                f"CatalogBusinessUnit={business_unit_count} (expected {expected_bu}), "
                f"CatalogActivitySubject={activity_subject_count} (expected {expected_as})"
            )
            sys.exit(1)

        self.stdout.write(
            self.style.SUCCESS(
                "catalog-check OK: "
                f"{business_unit_count} CatalogBusinessUnit, "
                f"{activity_subject_count} CatalogActivitySubject"
            )
        )
