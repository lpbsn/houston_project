from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from houston.analytics.analytics_capacity_eval import (
    CAPACITY_PROFILES,
    benchmark_analytics_capacity,
    format_analytics_capacity_report,
    load_analytics_capacity_dataset,
    resolve_capacity_profile,
    seed_analytics_capacity_dataset,
    write_analytics_capacity_archive,
)
from houston.core.dev_guards import LocalDevEnvironmentError, assert_local_dev_environment


class Command(BaseCommand):
    help = (
        "Local/dev only: seed and benchmark the synthetic Analytics capacity dataset. "
        "Timing runs are isolated from query capture, EXPLAIN, and memory profiling."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--profile",
            choices=tuple(CAPACITY_PROFILES),
            default="smoke",
        )
        parser.add_argument("--establishments", type=int, default=None)
        parser.add_argument("--signals", type=int, default=None)
        parser.add_argument("--patterns", type=int, default=None)
        parser.add_argument("--seed", type=int, default=35)
        parser.add_argument("--warmups", type=int, default=None)
        parser.add_argument("--iterations", type=int, default=None)
        parser.add_argument(
            "--skip-seed",
            action="store_true",
            help="Reuse the matching previously seeded dataset.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required when rebuilding the synthetic dataset.",
        )
        parser.add_argument(
            "--no-explain",
            action="store_true",
            help="Skip diagnostic EXPLAIN ANALYZE/BUFFERS.",
        )
        parser.add_argument("--explain-min-ms", type=float, default=25.0)
        parser.add_argument("--explain-limit", type=int, default=2)
        parser.add_argument("--json", action="store_true")
        parser.add_argument(
            "--archive",
            action="store_true",
            help="Archive raw JSON under .artifacts/analytics-capacity-eval/.",
        )
        parser.add_argument("--archive-dir", default="")
        parser.add_argument("--archive-filename", default="")

    def handle(self, *args, **options):
        try:
            assert_local_dev_environment()
            profile = resolve_capacity_profile(
                options["profile"],
                establishments=options["establishments"],
                signals=options["signals"],
                patterns=options["patterns"],
                warmups=options["warmups"],
                timing_iterations=options["iterations"],
            )
            if options["skip_seed"]:
                dataset = load_analytics_capacity_dataset(
                    profile,
                    seed=options["seed"],
                )
            else:
                if not options["confirm"]:
                    raise CommandError(
                        "Refusing to rebuild synthetic data without --confirm. "
                        "Use --skip-seed to reuse an existing dataset."
                    )
                dataset = seed_analytics_capacity_dataset(
                    profile,
                    seed=options["seed"],
                )
            report = benchmark_analytics_capacity(
                dataset,
                profile,
                explain=not options["no_explain"],
                explain_min_ms=options["explain_min_ms"],
                explain_limit=options["explain_limit"],
            )
        except (LocalDevEnvironmentError, RuntimeError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        if options["archive"]:
            archive_path = write_analytics_capacity_archive(
                report,
                archive_dir=(
                    Path(options["archive_dir"]) if options["archive_dir"] else None
                ),
                filename=options["archive_filename"] or None,
            )
            self.stderr.write(f"Archived: {archive_path}")
        if options["json"]:
            self.stdout.write(json.dumps(report, indent=2, sort_keys=True))
        else:
            self.stdout.write(format_analytics_capacity_report(report))
