from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from houston.signals.pipeline_v6_corpus_eval import (
    evaluate_v6_corpus_cases,
    format_v6_corpus_eval_report,
    list_v6_eval_case_ids,
    v6_corpus_eval_report_to_dict,
)
from houston.testing.pipeline_v6_acceptance import list_pipeline_v6_acceptance_case_ids


class Command(BaseCommand):
    help = (
        "Evaluate Lot 0 S15 acceptance corpus against V6 runtime using independent "
        "fake provider fixtures (not derived from expected_v6). Writes A–J report under "
        ".artifacts/pipeline-v6-eval/. Fake provider is the CI reference."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--case-id",
            action="append",
            dest="case_ids",
            default=[],
            help="S15 case id to run (repeatable). Default: Lot 10 case ids.",
        )
        parser.add_argument(
            "--lot",
            default="lot10",
            help="Default case set when --case-id omitted (lot10|all|<lotN>).",
        )
        parser.add_argument(
            "--provider",
            choices=("fake",),
            default="fake",
            help="Only fake is supported for deterministic expected_v6 comparison.",
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
        parser.add_argument(
            "--no-archive",
            action="store_true",
            help="Do not write .artifacts/pipeline-v6-eval report.",
        )

    def handle(self, *args, **options):
        raw_case_ids = options["case_ids"] or []
        if isinstance(raw_case_ids, str):
            raw_case_ids = [raw_case_ids]
        try:
            if raw_case_ids:
                known = set(list_pipeline_v6_acceptance_case_ids())
                unknown = [case_id for case_id in raw_case_ids if case_id not in known]
                if unknown:
                    raise CommandError(
                        f"Unknown S15 case id(s): {', '.join(unknown)}. "
                        f"Known: {', '.join(list_pipeline_v6_acceptance_case_ids())}"
                    )
                case_ids = raw_case_ids
            else:
                lot = options["lot"]
                if lot == "all":
                    case_ids = list_v6_eval_case_ids(lot=None)
                else:
                    case_ids = list_v6_eval_case_ids(lot=lot)

            report = evaluate_v6_corpus_cases(
                case_ids=case_ids,
                provider_name=options["provider"],
                archive=not options["no_archive"],
            )
        except (RuntimeError, ValueError, NotImplementedError) as exc:
            raise CommandError(str(exc)) from exc

        if options["json"]:
            self.stdout.write(
                json.dumps(v6_corpus_eval_report_to_dict(report), indent=2, sort_keys=True)
            )
        else:
            self.stdout.write(format_v6_corpus_eval_report(report))

        if options["fail_on_diff"]:
            has_failures = any(not result.passed for result in report.case_results)
            if has_failures or report.errors:
                raise CommandError("V6 corpus eval reported failures or errors.")
