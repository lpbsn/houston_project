from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.action_plans.repair_marked_done_snapshots import (
    format_repair_report,
    repair_marked_done_snapshots,
)
from houston.core.dev_guards import LocalDevEnvironmentError


class Command(BaseCommand):
    help = (
        "Local/dev only: repair marked_done start_at/end_at snapshots on test "
        "data, or delete the connected test graph when the snapshot cannot be "
        "filled from the live execution. Requires --dry-run or --confirm."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List fills and deletions without writing.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Apply fills and deletions (ignored with --dry-run).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        confirm = bool(options.get("confirm"))
        if not dry_run and not confirm:
            raise CommandError("Refusing to run without --confirm. Use --dry-run to preview.")
        try:
            report = repair_marked_done_snapshots(dry_run=dry_run)
        except LocalDevEnvironmentError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(format_repair_report(report))
