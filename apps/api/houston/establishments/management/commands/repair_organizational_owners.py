from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.establishments.organizational_owners_consistency import (
    repair_organizational_owners,
    summarize_inventory,
)


class Command(BaseCommand):
    help = (
        "Create missing organizational owner memberships when existing owner "
        "statuses are homogeneous. Dry-run by default; pass --apply to write."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply homogeneous missing-owner repairs (default is dry-run).",
        )

    def handle(self, *args, **options):
        dry_run = not options["apply"]
        result = repair_organizational_owners(dry_run=dry_run)
        mode = "dry-run" if dry_run else "apply"
        self.stdout.write(
            f"Repair ({mode}): "
            f"planned_or_created={len(result.created)} "
            f"skipped_organizations={len(result.skipped_organization_ids)}"
        )
        for plan in result.created:
            action = "would_create" if dry_run else "created"
            self.stdout.write(
                f"  [{action}] org={plan.organization_id} user={plan.user_id} "
                f"establishment={plan.establishment_id} status={plan.status}"
            )
        for organization_id in result.skipped_organization_ids:
            self.stdout.write(f"  [skipped] org={organization_id}")

        if result.inventory is not None:
            summary = summarize_inventory(result.inventory)
            self.stdout.write(
                "Post-inventory: "
                f"blocking_issues={summary['blocking_issues']} "
                f"planned_creates={summary['planned_creates']}"
            )

        if result.has_unresolved_conflicts:
            raise CommandError(
                "Organizational owner conflicts remain (status mix, non-owner, "
                "user.status, or unfixable full-coverage). No automatic status "
                "alignment is performed."
            )

        if dry_run:
            self.stdout.write("Dry-run only (pass --apply to write).")
        else:
            self.stdout.write(self.style.SUCCESS("Repair apply complete."))
