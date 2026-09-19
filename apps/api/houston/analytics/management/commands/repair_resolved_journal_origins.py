from __future__ import annotations

from django.core.management.base import BaseCommand

from houston.analytics.repair_resolved_journal_origins import repair_resolved_journal_origins


class Command(BaseCommand):
    help = (
        "Copy the current allowlisted Signal.resolution_origin onto matching "
        "signal.resolved journal events that lack one. Dry-run by default; "
        "pass --apply to write."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write matching journal origin repairs (default is dry-run).",
        )

    def handle(self, *args, **options):
        dry_run = not options["apply"]
        result = repair_resolved_journal_origins(dry_run=dry_run)
        mode = "dry-run" if dry_run else "apply"
        patched_label = "would_patch" if dry_run else "patched"
        patched_count = result.would_patch if dry_run else result.patched
        self.stdout.write(
            f"Repair ({mode}): "
            f"{patched_label}={patched_count} "
            f"unrecoverable={result.unrecoverable} "
            f"already_ok={result.already_ok}"
        )
        for event_id, signal_id in zip(result.event_ids, result.signal_ids, strict=True):
            self.stdout.write(
                f"  [{patched_label}] event={event_id} signal={signal_id}"
            )
        if dry_run:
            self.stdout.write("Dry-run only (pass --apply to write).")
        else:
            self.stdout.write(self.style.SUCCESS("Repair apply complete."))
