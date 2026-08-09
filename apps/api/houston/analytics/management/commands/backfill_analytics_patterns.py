from __future__ import annotations

import json
import uuid
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.analytics.backfill import (
    backfill_analytics_patterns,
    backfill_report_failed,
    backfill_report_to_dict,
    format_backfill_report,
)


class Command(BaseCommand):
    help = "Run a bounded, idempotent Analytics pattern assignment backfill."

    def add_arguments(self, parser):
        parser.add_argument("--organization-id", default="")
        parser.add_argument("--establishment-id", default="")
        parser.add_argument("--start-after-signal-id", default="")
        parser.add_argument(
            "--signal-id",
            action="append",
            dest="signal_ids",
            default=[],
            help="Signal id to replay explicitly (repeatable).",
        )
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument(
            "--provider",
            choices=("fake", "configured"),
            default="configured",
            help=(
                "Classifier provider. configured requires "
                "HOUSTON_RUN_ANALYTICS_PATTERN_BACKFILL=1."
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
            help="Write an archive JSON under .artifacts/analytics-pattern-backfill/.",
        )
        parser.add_argument(
            "--archive-dir",
            default="",
            help="Optional archive directory, used only with --archive.",
        )
        parser.add_argument(
            "--fail-on-error",
            action="store_true",
            help="Exit with code 1 after processing if non-reportable errors occurred.",
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
            signal_ids = [
                _required_uuid(signal_id, "signal-id")
                for signal_id in options.get("signal_ids", [])
            ]
            archive_dir = (
                Path(options["archive_dir"])
                if options["archive"] and options.get("archive_dir")
                else None
            )
            report = backfill_analytics_patterns(
                organization_id=organization_id,
                establishment_id=establishment_id,
                start_after_signal_id=start_after_signal_id,
                signal_ids=signal_ids,
                limit=options["limit"],
                provider_name=options["provider"],
                duplicate_guard_enabled=options["duplicate_guard"],
                archive=options["archive"],
                archive_dir=archive_dir,
            )
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        payload = backfill_report_to_dict(report)
        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        else:
            self.stdout.write(format_backfill_report(report))

        if options["fail_on_error"] and backfill_report_failed(report):
            raise CommandError("Analytics pattern backfill completed with errors.")


def _optional_uuid(value: str, label: str) -> uuid.UUID | None:
    if not value:
        return None
    return _required_uuid(value, label)


def _required_uuid(value: str, label: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid {label}: {value}") from exc
