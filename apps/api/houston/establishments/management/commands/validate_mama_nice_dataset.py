from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.establishments.mama_nice_dataset_acceptance import validate_mama_nice_dataset
from houston.establishments.mama_nice_dataset_compiler import validate_mama_nice_dataset_manifest
from houston.establishments.mama_nice_dataset_constants import (
    LOCAL_ESTABLISHMENT_NAME,
    PROD_ESTABLISHMENT_ID,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.models import Establishment


class Command(BaseCommand):
    help = "Validate the Mama Nice manifest and, if present, the seeded establishment."

    def add_arguments(self, parser):
        parser.add_argument("--establishment-id", dest="establishment_id")
        parser.add_argument("--local", action="store_true")

    def handle(self, *args, **options):
        errors = validate_mama_nice_dataset_manifest()
        if errors:
            raise CommandError("; ".join(errors))
        self.stdout.write(self.style.SUCCESS("Manifest validation passed."))
        establishment_id = options.get("establishment_id")
        if options.get("local"):
            establishment = Establishment.objects.filter(name=LOCAL_ESTABLISHMENT_NAME).first()
        elif establishment_id:
            establishment = Establishment.objects.filter(id=establishment_id).first()
        else:
            establishment = Establishment.objects.filter(id=PROD_ESTABLISHMENT_ID).first()
            if establishment is None:
                establishment = Establishment.objects.filter(name=LOCAL_ESTABLISHMENT_NAME).first()
        if establishment is None:
            self.stdout.write("No Mama Nice establishment in this database; DB checks skipped.")
            return
        try:
            db_errors = validate_mama_nice_dataset(establishment=establishment)
        except MamaNiceDatasetError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        if db_errors:
            raise CommandError("; ".join(db_errors))
        self.stdout.write(self.style.SUCCESS(f"Database validation passed for {establishment.id}."))
