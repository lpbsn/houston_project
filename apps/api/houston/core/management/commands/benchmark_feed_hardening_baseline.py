from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.core.dev_guards import LocalDevEnvironmentError
from houston.core.feed_hardening_baseline import (
    DEFAULT_SEED,
    FEED_BASELINE_PROFILES,
    benchmark_feed_baseline,
    format_feed_baseline_report,
    load_feed_baseline_dataset,
    resolve_feed_baseline_profile,
    seed_feed_baseline_dataset,
    write_feed_baseline_archive,
)


class Command(BaseCommand):
    help = (
        "Local/dev only: seed and capture the post-Lots 0-7 Feed hardening baseline. "
        "The command changes only namespaced synthetic data and measurement artifacts."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            choices=tuple(FEED_BASELINE_PROFILES),
            default="smoke",
        )
        parser.add_argument("--establishments", type=int, default=None)
        parser.add_argument("--signals-per-establishment", type=int, default=None)
        parser.add_argument("--executions-per-establishment", type=int, default=None)
        parser.add_argument("--warmups", type=int, default=None)
        parser.add_argument("--iterations", type=int, default=None)
        parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
        parser.add_argument(
            "--reference-commit",
            required=True,
            help="Git commit being measured; stored verbatim in the report.",
        )
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="Reuse the matching namespaced dataset.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required when rebuilding the namespaced synthetic dataset.",
        )
        parser.add_argument("--no-explain", action="store_true")
        parser.add_argument("--explain-limit", type=int, default=2)
        parser.add_argument("--json", action="store_true")
        parser.add_argument(
            "--archive",
            action="store_true",
            help="Archive raw JSON under .artifacts/feed-hardening-baseline/.",
        )
        parser.add_argument("--archive-dir", default="")
        parser.add_argument("--archive-filename", default="")

    def handle(self, *args, **options):
        try:
            profile = resolve_feed_baseline_profile(
                options["profile"],
                establishments=options["establishments"],
                signals_per_establishment=options["signals_per_establishment"],
                executions_per_establishment=options["executions_per_establishment"],
                warmups=options["warmups"],
                iterations=options["iterations"],
            )
            if options["skip_seed"]:
                dataset = load_feed_baseline_dataset(profile, seed=options["seed"])
            else:
                if not options["confirm"]:
                    raise CommandError(
                        "Refusing to rebuild synthetic data without --confirm."
                    )
                dataset = seed_feed_baseline_dataset(profile, seed=options["seed"])
            report = benchmark_feed_baseline(
                dataset,
                profile,
                reference_commit=options["reference_commit"],
                explain=not options["no_explain"],
                explain_limit=options["explain_limit"],
            )
        except (LocalDevEnvironmentError, RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        if options["archive"]:
            path = write_feed_baseline_archive(
                report,
                archive_dir=Path(options["archive_dir"]) if options["archive_dir"] else None,
                filename=options["archive_filename"] or None,
            )
            self.stderr.write(f"Archived: {path}")
        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        else:
            self.stdout.write(format_feed_baseline_report(report))
