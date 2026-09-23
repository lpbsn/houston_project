from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.core.dev_guards import LocalDevEnvironmentError
from houston.establishments.mama_nice_dataset_bootstrap import bootstrap_mama_nice_dataset
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_replay import seed_mama_nice_dataset


class Command(BaseCommand):
    help = (
        "Local/dev only: create or retrieve [DEMO] SPORE / Mama Shelter Nice, "
        "OWNER and governance DIRECTOR, then run the shared Mama Nice corpus seed."
    )

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--resume", action="store_true")

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        confirm = bool(options["confirm"])
        resume = bool(options["resume"])
        if not dry_run and not confirm:
            raise CommandError("Refusing to run without --confirm. Use --dry-run to preview.")
        try:
            if dry_run:
                from houston.establishments.mama_nice_dataset_compiler import (
                    validate_mama_nice_dataset_manifest,
                )

                errors = validate_mama_nice_dataset_manifest()
                if errors:
                    raise MamaNiceDatasetError(errors)
                self.stdout.write(self.style.SUCCESS("Dry run: manifest is valid. No writes."))
                return
            bootstrap_mama_nice_dataset(confirm=True)
            result = seed_mama_nice_dataset(
                establishment_id=None,
                dry_run=False,
                confirm=True,
                resume=resume,
                local=True,
            )
        except LocalDevEnvironmentError as exc:
            raise CommandError(str(exc)) from exc
        except MamaNiceDatasetError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"Mama Nice local seed written={result.written} skipped={result.skipped}"
            )
        )
