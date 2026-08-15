from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.analytics.pattern_architecture_d_spike import (
    evaluate_architecture_d_k_selection,
    evaluate_architecture_d_spike,
    format_architecture_d_report,
)
from houston.testing.analytics_pattern_corpus import list_analytics_pattern_scenario_ids


class Command(BaseCommand):
    help = (
        "Architecture D eval-only spike: classifier + phenomenon_v1 semantic "
        "retrieval shortlist + current duplicate guard. Replaces token_overlap_v1 "
        "only. OpenAI requires HOUSTON_RUN_ANALYTICS_PATTERN_ARCHITECTURE_D_SPIKE=1 "
        "and HOUSTON_RUN_ANALYTICS_PATTERN_EVAL=1 for configured classifier runs."
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
            "--phase",
            choices=("k-selection", "full"),
            default="full",
            help="k-selection compares K=3 vs K=5 (embeddings only). full runs 4 LLM evals.",
        )
        parser.add_argument("--runs", type=int, default=4)
        parser.add_argument(
            "--k",
            type=int,
            default=0,
            help="Optional frozen K (3 or 5). Default: choose via k-selection.",
        )
        parser.add_argument(
            "--embedding-provider",
            choices=("fake", "openai"),
            default="openai",
        )
        parser.add_argument(
            "--classifier-provider",
            choices=("fake", "configured"),
            default="configured",
        )
        parser.add_argument("--embedding-model", default="")
        parser.add_argument(
            "--classifier-model",
            default="gpt-5-mini",
            help="Classifier/guard model (default: gpt-5-mini).",
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
        k = options["k"] or None
        try:
            if options["phase"] == "k-selection":
                payload = evaluate_architecture_d_k_selection(
                    embedding_provider_name=options["embedding_provider"],
                    embedding_model=options["embedding_model"] or None,
                )
            else:
                payload = evaluate_architecture_d_spike(
                    scenario_ids=list(raw_case_ids) if raw_case_ids else None,
                    runs=options["runs"],
                    k=k,
                    embedding_provider_name=options["embedding_provider"],
                    classifier_provider_name=options["classifier_provider"],
                    embedding_model=options["embedding_model"] or None,
                    classifier_model=options["classifier_model"] or None,
                    archive=options["archive"],
                    archive_dir=archive_dir,
                    skip_k_selection=bool(k),
                )
        except (RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        elif options["phase"] == "k-selection":
            self.stdout.write(
                "Architecture D K selection\n"
                f"status={payload['status']} chosen_k={payload['chosen_k']}\n"
                f"recall@3={payload['recall'].get('3')}\n"
                f"recall@5={payload['recall'].get('5')}\n"
                f"{payload['note']}\n"
            )
        else:
            self.stdout.write(format_architecture_d_report(payload))

        if (
            options["fail_on_threshold"]
            and options["phase"] == "full"
            and payload.get("architecture_gate", {}).get("status") != "pass"
        ):
            raise CommandError("Architecture D spike architecture gate failed.")
