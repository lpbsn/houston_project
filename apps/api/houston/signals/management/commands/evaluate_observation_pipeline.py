from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from houston.signals.pipeline_corpus_eval import (
    corpus_eval_report_to_dict,
    evaluate_corpus_cases,
    format_corpus_eval_report,
)
from houston.testing.pipeline_golden_v4 import list_pipeline_golden_v4_case_ids


class Command(BaseCommand):
    help = (
        "Dev-only: evaluate live OpenAI observation pipeline output against the "
        "golden v4 corpus (structural diff). Opt-in via "
        "HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1. Not used in CI."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--case-id",
            action="append",
            dest="case_ids",
            default=[],
            help="Corpus case id to run (repeatable). Default: all corpus cases.",
        )
        parser.add_argument(
            "--provider",
            choices=("openai", "fake"),
            default="openai",
            help=(
                "Pipeline provider. openai requires HOUSTON_RUN_OPENAI_OBSERVATION_SMOKE_TEST=1 "
                "and OPENAI_API_KEY. fake replays expected corpus output (plumbing check only)."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON instead of a human summary.",
        )
        parser.add_argument(
            "--fail-on-diff",
            action="store_true",
            help="Exit with code 1 when any case fails or errors.",
        )

    def handle(self, *args, **options):
        raw_case_ids = options["case_ids"] or []
        if isinstance(raw_case_ids, str):
            raw_case_ids = [raw_case_ids]
        case_ids = raw_case_ids or None
        if case_ids:
            known_ids = set(list_pipeline_golden_v4_case_ids())
            unknown = [case_id for case_id in case_ids if case_id not in known_ids]
            if unknown:
                raise CommandError(
                    f"Unknown corpus case id(s): {', '.join(unknown)}. "
                    f"Known ids: {', '.join(list_pipeline_golden_v4_case_ids())}"
                )

        try:
            report = evaluate_corpus_cases(
                case_ids=case_ids,
                provider_name=options["provider"],
            )
        except RuntimeError as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(
                json.dumps(corpus_eval_report_to_dict(report), indent=2, sort_keys=True)
            )
        else:
            self.stdout.write(format_corpus_eval_report(report))

        if options["fail_on_diff"]:
            has_failures = any(not result.passed for result in report.case_results)
            if has_failures or report.errors:
                raise CommandError("Corpus eval reported failures or errors.")
