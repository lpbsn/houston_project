from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.analytics.pattern_corpus_eval import (
    analytics_pattern_corpus_eval_passed,
    analytics_pattern_corpus_eval_report_to_dict,
    evaluate_analytics_pattern_corpus,
    format_analytics_pattern_corpus_eval_report,
)
from houston.testing.analytics_pattern_corpus import list_analytics_pattern_scenario_ids


class Command(BaseCommand):
    help = (
        "Evaluate the Analytics pattern grouping corpus. The default run rolls back "
        "all DB writes and creates no files."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--case-id",
            action="append",
            dest="case_ids",
            default=[],
            help="Scenario id to run (repeatable). Default: all scenarios.",
        )
        parser.add_argument(
            "--provider",
            choices=("fake", "configured"),
            default="fake",
            help="Classifier provider. configured requires HOUSTON_RUN_ANALYTICS_PATTERN_EVAL=1.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON instead of a human summary.",
        )
        parser.add_argument(
            "--fail-on-threshold",
            action="store_true",
            help="Exit with code 1 when any applicable main threshold fails.",
        )
        parser.add_argument(
            "--archive",
            action="store_true",
            help="Write an archive JSON under .artifacts/analytics-pattern-eval/.",
        )
        parser.add_argument(
            "--archive-dir",
            default="",
            help="Optional archive directory, used only with --archive.",
        )

    def handle(self, *args, **options):
        raw_case_ids = options["case_ids"] or []
        if isinstance(raw_case_ids, str):
            raw_case_ids = [raw_case_ids]
        known = list_analytics_pattern_scenario_ids()
        unknown = [case_id for case_id in raw_case_ids if case_id not in known]
        if unknown:
            raise CommandError(
                f"Unknown Analytics pattern scenario id(s): {', '.join(unknown)}. "
                f"Known: {', '.join(known)}"
            )

        archive_dir = (
            Path(options["archive_dir"])
            if options["archive"] and options.get("archive_dir")
            else None
        )
        try:
            report = evaluate_analytics_pattern_corpus(
                scenario_ids=list(raw_case_ids) if raw_case_ids else None,
                provider_name=options["provider"],
                archive=options["archive"],
                archive_dir=archive_dir,
            )
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        payload = analytics_pattern_corpus_eval_report_to_dict(report)
        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        else:
            self.stdout.write(format_analytics_pattern_corpus_eval_report(report))

        if options["fail_on_threshold"] and not analytics_pattern_corpus_eval_passed(
            report
        ):
            raise CommandError("Analytics pattern corpus eval failed.")
