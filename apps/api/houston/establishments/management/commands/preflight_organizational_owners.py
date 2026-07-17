from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.establishments.organizational_owners_consistency import (
    inventory_organizational_owners,
    summarize_inventory,
)


class Command(BaseCommand):
    help = (
        "Inventory organizational owner coverage issues on draft/active establishments "
        "(read-only)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fail-on-issues",
            action="store_true",
            help="Exit non-zero when blocking consistency issues are present.",
        )

    def handle(self, *args, **options):
        inventory = inventory_organizational_owners()
        summary = summarize_inventory(inventory)
        self.stdout.write(
            "Inventory: "
            f"organizations={summary['organizations']} "
            f"blocking_issues={summary['blocking_issues']} "
            f"informative_issues={summary['informative_issues']} "
            f"missing_owner={summary['missing_owner']} "
            f"status_mix={summary['status_mix']} "
            f"non_owner_conflict={summary['non_owner_conflict']} "
            f"owner_user_status_conflict={summary['owner_user_status_conflict']} "
            f"missing_full_coverage_active_owner="
            f"{summary['missing_full_coverage_active_owner']} "
            f"planned_creates={summary['planned_creates']}"
        )

        for report in inventory.organizations:
            for issue in report.issues:
                severity = "blocking" if issue.blocking else "info"
                self.stdout.write(
                    f"  [{severity}] {issue.code} org={issue.organization_id}"
                    + (f" user={issue.user_id}" if issue.user_id else "")
                    + (
                        f" establishment={issue.establishment_id}"
                        if issue.establishment_id
                        else ""
                    )
                    + (f" {issue.detail}" if issue.detail else "")
                )

        if options["fail_on_issues"] and inventory.has_blocking_issues:
            raise CommandError(
                f"{summary['blocking_issues']} blocking organizational owner issue(s) "
                "present. Resolve manually or run repair_organizational_owners for "
                "homogeneous missing-owner gaps only."
            )

        self.stdout.write("Preflight complete (read-only).")
