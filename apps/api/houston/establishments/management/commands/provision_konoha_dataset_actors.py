from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.core.dev_guards import LocalDevEnvironmentError
from houston.establishments.konoha_dataset_actors import (
    KonohaDatasetActorsError,
    ProvisionResult,
    provision_konoha_dataset_actors,
)


class Command(BaseCommand):
    help = (
        "Local/dev only: provision the KONOHA ANBU + AKATSUKI dataset actors "
        "(invite/reinvite/accept). Requires --confirm unless --dry-run. "
        "Does not create observations or other operational data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Classify seats and check dependencies without writing.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required to provision missing seats (ignored with --dry-run).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        confirm = bool(options.get("confirm"))

        if not dry_run and not confirm:
            raise CommandError("Refusing to run without --confirm. Use --dry-run to preview.")

        try:
            result = provision_konoha_dataset_actors(dry_run=dry_run)
        except LocalDevEnvironmentError as exc:
            raise CommandError(str(exc)) from exc
        except KonohaDatasetActorsError as exc:
            raise CommandError("; ".join(exc.messages)) from exc

        self._print_summary(result)

    def _print_summary(self, result: ProvisionResult) -> None:
        prefix = "Dry run — would apply" if result.dry_run else "Applied"
        self.stdout.write(self.style.WARNING(f"{prefix}:"))
        self.stdout.write(f"  skipped: {result.skipped}")
        self.stdout.write(f"  invited_accepted: {result.invited_accepted}")
        self.stdout.write(f"  reinvited_accepted: {result.reinvited_accepted}")
        if result.dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No database changes applied."))
        else:
            self.stdout.write(self.style.SUCCESS("Konoha dataset actors provisioned."))
