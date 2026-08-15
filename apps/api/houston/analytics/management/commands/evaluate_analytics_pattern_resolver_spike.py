from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.analytics.pattern_resolver_spike import (
    evaluate_analytics_pattern_resolver_spike,
    format_resolver_spike_report,
)
from houston.analytics.pattern_retrieval_spike import PROJECTION_PHENOMENON_V1
from houston.testing.analytics_pattern_corpus import list_analytics_pattern_scenario_ids


class Command(BaseCommand):
    help = (
        "Phase 1 eval-only spike: semantic retrieval + single resolver. "
        "Requires frozen Phase 0 settings. OpenAI requires "
        "HOUSTON_RUN_ANALYTICS_PATTERN_RESOLVER_SPIKE=1."
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
            "--runs",
            type=int,
            default=4,
            help="Independent resolver runs (default: 4).",
        )
        parser.add_argument(
            "--k",
            type=int,
            default=1,
            help="Frozen top-K from Phase 0 (default: 1).",
        )
        parser.add_argument(
            "--projection",
            default=PROJECTION_PHENOMENON_V1,
            help=f"Frozen projection from Phase 0 (default: {PROJECTION_PHENOMENON_V1}).",
        )
        parser.add_argument(
            "--embedding-provider",
            choices=("fake", "openai"),
            default="openai",
        )
        parser.add_argument(
            "--resolver-provider",
            choices=("fake", "openai"),
            default="openai",
        )
        parser.add_argument(
            "--embedding-model",
            default="",
            help="Embedding model override (default: text-embedding-3-small).",
        )
        parser.add_argument(
            "--resolver-model",
            default="",
            help="Resolver model override (default: gpt-5-mini).",
        )
        parser.add_argument("--json", action="store_true")
        parser.add_argument("--archive", action="store_true")
        parser.add_argument("--archive-dir", default="")
        parser.add_argument(
            "--fail-on-threshold",
            action="store_true",
            help="Exit 1 when architecture_gate status is fail.",
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
            payload = evaluate_analytics_pattern_resolver_spike(
                scenario_ids=list(raw_case_ids) if raw_case_ids else None,
                runs=options["runs"],
                k=options["k"],
                projection=options["projection"],
                embedding_provider_name=options["embedding_provider"],
                resolver_provider_name=options["resolver_provider"],
                embedding_model=options["embedding_model"] or None,
                resolver_model=options["resolver_model"] or None,
                archive=options["archive"],
                archive_dir=archive_dir,
            )
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        else:
            self.stdout.write(format_resolver_spike_report(payload))

        if (
            options["fail_on_threshold"]
            and payload["architecture_gate"]["status"] != "pass"
        ):
            raise CommandError("Analytics pattern resolver spike architecture gate failed.")
