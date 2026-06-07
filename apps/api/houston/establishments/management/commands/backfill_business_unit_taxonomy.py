from __future__ import annotations

from django.core.management.base import BaseCommand

from houston.establishments.models import Establishment
from houston.establishments.taxonomy_backfill import backfill_business_units_from_legacy_taxonomy


class Command(BaseCommand):
    help = "Backfill BusinessUnit and ActivitySubject from legacy operational taxonomy."

    def add_arguments(self, parser):
        parser.add_argument(
            "--establishment-id",
            type=str,
            help="Limit backfill to one establishment UUID.",
        )

    def handle(self, *args, **options):
        establishment_id = options.get("establishment_id")
        queryset = Establishment.objects.all()
        if establishment_id:
            queryset = queryset.filter(id=establishment_id)

        for establishment in queryset.order_by("created_at"):
            counts = backfill_business_units_from_legacy_taxonomy(
                establishment_id=establishment.id,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"{establishment.id} ({establishment.name}): "
                    f"BU={counts['business_units']} AS={counts['activity_subjects']} "
                    f"maps={counts['maps']}"
                )
            )
