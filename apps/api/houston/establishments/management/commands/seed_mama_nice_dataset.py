from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.core.dev_guards import LocalDevEnvironmentError
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError
from houston.establishments.mama_nice_dataset_replay import seed_mama_nice_dataset


class Command(BaseCommand):
    help = (
        "Seed the Mama Shelter Nice demo corpus. Production requires "
        "--establishment-id. Never creates org/OWNER/first DIRECTOR."
    )

    def add_arguments(self, parser):
        parser.add_argument("--establishment-id", dest="establishment_id")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--confirm", action="store_true")
        parser.add_argument("--resume", action="store_true")
        parser.add_argument(
            "--as-of",
            dest="as_of",
            help="Optional timezone-aware ISO instant used as the seed reference clock.",
        )
        parser.add_argument(
            "--local",
            action="store_true",
            help="Target the local bootstrap establishment instead of production UUIDs.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options["dry_run"])
        confirm = bool(options["confirm"])
        if not dry_run and not confirm:
            raise CommandError("Refusing to run without --confirm. Use --dry-run to preview.")
        try:
            result = seed_mama_nice_dataset(
                establishment_id=options.get("establishment_id"),
                dry_run=dry_run,
                confirm=confirm,
                resume=bool(options["resume"]),
                local=bool(options["local"]),
                as_of=options.get("as_of"),
            )
        except LocalDevEnvironmentError as exc:
            raise CommandError(str(exc)) from exc
        except MamaNiceDatasetError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        prefix = "Dry run" if result.dry_run else "Applied"
        self.stdout.write(f"{prefix} Mama Nice seed establishment={result.establishment_id}")
        for message in result.preflight_messages:
            self.stdout.write(f"  {message}")
        if result.dry_run:
            if result.errors:
                self.stdout.write(self.style.WARNING("Dry run preflight notes:"))
                for message in result.errors:
                    self.stdout.write(f"  {message}")
            self.stdout.write(self.style.SUCCESS("Dry run complete. No database changes applied."))
            return
        self.stdout.write(f"  written: {result.written}")
        self.stdout.write(f"  skipped: {result.skipped}")
