from __future__ import annotations

import json
import uuid

from django.core.management.base import BaseCommand, CommandError

from houston.signals.aggregation_eval import (
    compute_issue_focus_eval_metrics,
    issue_focus_eval_metrics_to_dict,
)


class Command(BaseCommand):
    help = (
        "Report issue_focus aggregation evaluation metrics for Lot 5 "
        "(taxonomy duplicate groups, hint mismatches, reformulation proxies)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--establishment-id",
            type=str,
            default="",
            help="Optional establishment UUID to scope the report.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON instead of a human summary.",
        )
        parser.add_argument(
            "--duplicate-group-limit",
            type=int,
            default=50,
            help="Maximum number of taxonomy duplicate groups to include.",
        )

    def handle(self, *args, **options):
        establishment_id: uuid.UUID | None = None
        raw_establishment_id = (options.get("establishment_id") or "").strip()
        if raw_establishment_id:
            try:
                establishment_id = uuid.UUID(raw_establishment_id)
            except ValueError as exc:
                raise CommandError(
                    f"Invalid establishment id: {raw_establishment_id}"
                ) from exc

        metrics = compute_issue_focus_eval_metrics(
            establishment_id=establishment_id,
            duplicate_group_limit=options["duplicate_group_limit"],
        )
        payload = issue_focus_eval_metrics_to_dict(metrics)

        if options["json"]:
            self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
            return

        scope = (
            f"establishment={payload['establishment_id']}"
            if payload["establishment_id"]
            else "all establishments"
        )
        self.stdout.write(f"Issue focus aggregation eval ({scope})")
        self.stdout.write("")
        self.stdout.write(f"Active signals: {payload['active_signal_count']}")
        self.stdout.write(
            "Taxonomy duplicate groups (same quadruplet, multiple issue_focus): "
            f"{payload['taxonomy_duplicate_group_count']} "
            f"({payload['taxonomy_duplicate_signal_count']} signals)"
        )
        self.stdout.write(
            "Candidates with aggregate hint: "
            f"{payload['hint_provided_candidate_count']}"
        )
        self.stdout.write(
            "Hint rejected (created new signal): "
            f"{payload['hint_rejected_created_count']}"
        )
        self.stdout.write(
            "Hint issue_focus mismatches: "
            f"{payload['hint_issue_focus_mismatch_count']}"
        )
        self.stdout.write("")
        self.stdout.write("Lot 4bis trigger indicators:")
        for key, value in payload["lot4bis_trigger_indicators"].items():
            self.stdout.write(f"  - {key}: {value}")

        if payload["taxonomy_duplicate_groups"]:
            self.stdout.write("")
            self.stdout.write("Top taxonomy duplicate groups:")
            for group in payload["taxonomy_duplicate_groups"][:10]:
                focuses = ", ".join(group["issue_focuses"])
                self.stdout.write(
                    f"  - bucket={group['taxonomy_bucket_key']} "
                    f"signals={group['signal_count']} "
                    f"focuses=[{focuses}]"
                )
