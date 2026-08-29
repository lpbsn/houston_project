from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.core.dev_guards import LocalDevEnvironmentError
from houston.core.operational_test_data_cleanup import (
    OperationalCleanupCounts,
    OperationalCleanupResult,
    clean_operational_test_data,
)


class Command(BaseCommand):
    help = (
        "Local/dev only: delete operational test data (comments, notifications, "
        "observations, action plans, signals, analytics patterns/sightings, "
        "point transactions, badge awards) while preserving users, establishments, "
        "memberships, business units, catalog infra (Catalog*), and gamification "
        "seasons. Resets AnalyticsHistoryCoverage.reliable_from. ActionPlan "
        "templates are removed. Requires --confirm unless --dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count rows that would be deleted without making changes.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required to execute deletions (ignored with --dry-run).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        confirm = bool(options.get("confirm"))

        if not dry_run and not confirm:
            raise CommandError("Refusing to run without --confirm. Use --dry-run to preview.")

        try:
            result = clean_operational_test_data(dry_run=dry_run)
        except LocalDevEnvironmentError as exc:
            raise CommandError(str(exc)) from exc

        self._print_summary(result)

    def _print_summary(self, result: OperationalCleanupResult) -> None:
        prefix = "Dry run — would delete" if result.dry_run else "Deleted"
        self.stdout.write(self.style.WARNING(f"{prefix}:"))
        for label, value in _iter_count_lines(result.counts):
            self.stdout.write(f"  {label}: {value}")

        self.stdout.write("")
        self.stdout.write(
            "Preserved: users, establishments, memberships, business_units, "
            "catalog_infra (Catalog*), chat, ai_usage_logs, gamification_seasons"
        )
        self.stdout.write(
            "Deleted includes: ActionPlan templates, analytics patterns, point ledger"
        )

        if result.history_reliable_from is not None:
            self.stdout.write(
                f"history_reliable_from: {result.history_reliable_from.isoformat()}"
            )

        if result.dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. No database changes applied."))
        else:
            self.stdout.write(self.style.SUCCESS("Operational test data cleanup complete."))


def _iter_count_lines(counts: OperationalCleanupCounts):
    yield from (
        ("notifications", counts.notifications),
        ("comment_mentions", counts.comment_mentions),
        ("comments", counts.comments),
        ("signal_source_observations", counts.signal_source_observations),
        ("candidate_signals", counts.candidate_signals),
        ("observation_media", counts.observation_media),
        ("observation_processing", counts.observation_processing),
        ("observations", counts.observations),
        ("action_plan_execution_tasks", counts.action_plan_execution_tasks),
        ("action_plan_execution_teams", counts.action_plan_execution_teams),
        ("action_plan_assignees", counts.action_plan_assignees),
        ("action_plan_executions", counts.action_plan_executions),
        ("action_plan_schedule_assignees", counts.action_plan_schedule_assignees),
        ("action_plan_schedules", counts.action_plan_schedules),
        ("action_plan_tasks", counts.action_plan_tasks),
        ("action_plans", counts.action_plans),
        ("signals", counts.signals),
        ("temporary_uploads", counts.temporary_uploads),
        ("media_files", counts.media_files),
        ("pattern_issue_reports", counts.pattern_issue_reports),
        ("pattern_sightings", counts.pattern_sightings),
        ("pattern_lifecycle_events", counts.pattern_lifecycle_events),
        ("signal_pattern_assignments", counts.signal_pattern_assignments),
        ("operational_patterns", counts.operational_patterns),
        ("point_transactions", counts.point_transactions),
        ("badge_awards", counts.badge_awards),
    )
