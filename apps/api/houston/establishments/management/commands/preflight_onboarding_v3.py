from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.establishments.onboarding_proposal_v3_migration import (
    assert_no_non_terminal_v3_proposals,
    inventory_onboarding_v3_proposals,
    process_non_terminal_v3_proposals,
)


class Command(BaseCommand):
    help = (
        "Inventory / convert-or-reject non-terminal onboarding_proposal_v3 rows "
        "before rejecting v3 at runtime."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Convert convertible non-terminal v3 proposals; reject the rest.",
        )
        parser.add_argument(
            "--fail-if-present",
            action="store_true",
            help="Exit non-zero when non-terminal v3 proposals are present (dry-run).",
        )

    def handle(self, *args, **options):
        inventory = inventory_onboarding_v3_proposals()
        self.stdout.write(
            "Inventory: "
            f"v3_non_terminal={inventory['v3_non_terminal']} "
            f"v3_terminal={inventory['v3_terminal']} "
            f"other={inventory['other']}"
        )

        if options["apply"]:
            counts = process_non_terminal_v3_proposals(dry_run=False)
            self.stdout.write(
                "Applied: "
                f"scanned={counts['scanned']} "
                f"converted={counts['converted']} "
                f"rejected={counts['rejected']} "
                f"terminal_left={counts['terminal_left']}"
            )
            try:
                assert_no_non_terminal_v3_proposals()
            except RuntimeError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(self.style.SUCCESS("No non-terminal v3 proposals remain."))
            return

        if options["fail_if_present"] and inventory["v3_non_terminal"] > 0:
            raise CommandError(
                f"{inventory['v3_non_terminal']} non-terminal onboarding_proposal_v3 "
                "row(s) present. Re-run with --apply."
            )
        self.stdout.write("Dry-run only (pass --apply to process).")
