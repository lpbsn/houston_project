from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.analytics.pattern_retrieval_spike import (
    DEFAULT_PROJECTION,
    PROJECTION_PHENOMENON_V1,
    evaluate_analytics_pattern_retrieval_spike,
    format_retrieval_spike_report,
)
from houston.testing.analytics_pattern_corpus import list_analytics_pattern_scenario_ids


class Command(BaseCommand):
    help = (
        "Phase 0 eval-only spike: oracle retrieval recall for semantic pattern search. "
        "No resolver, no production writes. OpenAI provider requires "
        "HOUSTON_RUN_ANALYTICS_PATTERN_RETRIEVAL_SPIKE=1."
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
            choices=("fake", "openai"),
            default="fake",
            help="Embedding provider. openai is opt-in.",
        )
        parser.add_argument(
            "--embedding-model",
            default="",
            help="OpenAI embedding model override (default: text-embedding-3-small).",
        )
        parser.add_argument(
            "--projection",
            default=DEFAULT_PROJECTION,
            help=f"Projection id (default: {PROJECTION_PHENOMENON_V1}).",
        )
        parser.add_argument(
            "--also-run-ablations",
            action="store_true",
            help=(
                "When projection is phenomenon_v1, also evaluate operational_unit "
                "and business-unit ablations."
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
            help="Write an archive JSON under .artifacts/analytics-pattern-retrieval-spike/.",
        )
        parser.add_argument(
            "--archive-dir",
            default="",
            help="Optional archive directory, used only with --archive.",
        )
        parser.add_argument(
            "--fail-on-threshold",
            action="store_true",
            help="Exit with code 1 when Phase 0 does not recommend a satisfying K.",
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
        embedding_model = options.get("embedding_model") or None
        try:
            payload = evaluate_analytics_pattern_retrieval_spike(
                scenario_ids=list(raw_case_ids) if raw_case_ids else None,
                projection=options["projection"],
                provider_name=options["provider"],
                embedding_model=embedding_model,
                archive=options["archive"],
                archive_dir=archive_dir,
                also_run_ablations=options["also_run_ablations"],
            )
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        else:
            self.stdout.write(format_retrieval_spike_report(payload))

        if options["fail_on_threshold"] and payload["phase0_status"] != "pass":
            raise CommandError("Analytics pattern retrieval spike Phase 0 failed.")
