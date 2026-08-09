from __future__ import annotations

import json
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.analytics.backfill_simulation import (
    backfill_simulation_report_to_dict,
    format_backfill_simulation_report,
    simulate_analytics_pattern_backfill,
)


class Command(BaseCommand):
    help = (
        "Simulate Analytics pattern backfill. The default run rolls back all DB "
        "writes and creates no files."
    )

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default="")
        parser.add_argument("--establishment-id", default="")
        parser.add_argument("--start-after-signal-id", default="")
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--provider",
            choices=("fake", "configured"),
            default="fake",
            help=(
                "Classifier provider. configured requires "
                "HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL_SIMULATION=1."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON instead of a human summary.",
        )
        parser.add_argument(
            "--archive",
            action="store_true",
            help="Write an archive JSON under .artifacts/analytics-pattern-backfill-simulation/.",
        )
        parser.add_argument(
            "--archive-dir",
            default="",
            help="Optional archive directory, used only with --archive.",
        )
        duplicate_guard = parser.add_mutually_exclusive_group()
        duplicate_guard.add_argument(
            "--duplicate-guard",
            dest="duplicate_guard",
            action="store_true",
            default=True,
            help="Enable the Analytics pattern duplicate guard.",
        )
        duplicate_guard.add_argument(
            "--no-duplicate-guard",
            dest="duplicate_guard",
            action="store_false",
            help="Disable the Analytics pattern duplicate guard.",
        )

    def handle(self, *args, **options):
        try:
            organization_id = _optional_uuid(options["organization_id"], "organization-id")
            establishment_id = _optional_uuid(
                options["establishment_id"],
                "establishment-id",
            )
            start_after_signal_id = _optional_uuid(
                options["start_after_signal_id"],
                "start-after-signal-id",
            )
            archive_dir = (
                Path(options["archive_dir"])
                if options["archive"] and options.get("archive_dir")
                else None
            )
            report = simulate_analytics_pattern_backfill(
                organization_id=organization_id,
                establishment_id=establishment_id,
                start_after_signal_id=start_after_signal_id,
                limit=options["limit"],
                provider_name=options["provider"],
                duplicate_guard_enabled=options["duplicate_guard"],
                archive=options["archive"],
                archive_dir=archive_dir,
            )
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        payload = backfill_simulation_report_to_dict(report)
        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        else:
            self.stdout.write(format_backfill_simulation_report(report))


def _optional_uuid(value: str, label: str) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid {label}: {value}") from exc
