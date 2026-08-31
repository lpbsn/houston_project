from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from houston.core.dev_guards import LocalDevEnvironmentError
from houston.establishments.konoha_dataset_replay import (
    EVENT_MARK_INTERESTING,
    EVENT_PLAN_CANCEL,
    EVENT_PLAN_CREATE,
    EVENT_PLAN_MARK_DONE,
    EVENT_PLAN_PROMOTE,
    EVENT_PLAN_VALIDATE,
    EVENT_QUALIFY,
    EVENT_RESOLVE,
    EVENT_RR_APPROVE,
    EVENT_RR_CREATE,
    EVENT_RR_REJECT,
    EVENT_SUBMIT,
    KonohaDatasetReplayError,
    ReplayResult,
    replay_konoha_dataset_observations,
)


class Command(BaseCommand):
    help = (
        "Local/dev only: replay KONOHA observations, signals, and action-plan cycles "
        "through product writers. Does not write AnalyticsHistoryCoverage.reliable_from. "
        "Reset operational data before the first --confirm after corpus changes. "
        "Requires --confirm unless --dry-run."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate corpus and preflight, print the event timeline, no writes.",
        )
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Required to write observations, plans, and resolves.",
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Skip events whose writer fingerprint is already persisted.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        confirm = bool(options.get("confirm"))
        resume = bool(options.get("resume"))
        if not dry_run and not confirm:
            raise CommandError(
                "Refusing to run without --confirm. Use --dry-run to preview."
            )
        try:
            result = replay_konoha_dataset_observations(dry_run=dry_run, resume=resume)
        except LocalDevEnvironmentError as exc:
            raise CommandError(str(exc)) from exc
        except KonohaDatasetReplayError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        self._print_summary(result)

    def _print_summary(self, result: ReplayResult) -> None:
        prefix = "Dry run — would apply" if result.dry_run else "Applied"
        self.stdout.write(self.style.WARNING(f"{prefix} KONOHA dataset replay:"))
        self.stdout.write(f"  events: {len(result.events)}")
        counts = {
            EVENT_SUBMIT: 0,
            EVENT_QUALIFY: 0,
            EVENT_RR_CREATE: 0,
            EVENT_RR_APPROVE: 0,
            EVENT_RR_REJECT: 0,
            EVENT_MARK_INTERESTING: 0,
            EVENT_PLAN_CREATE: 0,
            EVENT_PLAN_PROMOTE: 0,
            EVENT_PLAN_MARK_DONE: 0,
            EVENT_PLAN_VALIDATE: 0,
            EVENT_PLAN_CANCEL: 0,
            EVENT_RESOLVE: 0,
        }
        for event in result.events:
            counts[event.kind] = counts.get(event.kind, 0) + 1
        self.stdout.write(f"  submits: {counts[EVENT_SUBMIT]}")
        self.stdout.write(f"  qualify: {counts[EVENT_QUALIFY]}")
        self.stdout.write(f"  rr_create: {counts[EVENT_RR_CREATE]}")
        self.stdout.write(f"  rr_approve: {counts[EVENT_RR_APPROVE]}")
        self.stdout.write(f"  rr_reject: {counts[EVENT_RR_REJECT]}")
        self.stdout.write(f"  mark_interesting: {counts[EVENT_MARK_INTERESTING]}")
        self.stdout.write(f"  plan_create: {counts[EVENT_PLAN_CREATE]}")
        self.stdout.write(f"  plan_promote: {counts[EVENT_PLAN_PROMOTE]}")
        self.stdout.write(f"  plan_mark_done: {counts[EVENT_PLAN_MARK_DONE]}")
        self.stdout.write(f"  plan_validate: {counts[EVENT_PLAN_VALIDATE]}")
        self.stdout.write(f"  plan_cancel: {counts[EVENT_PLAN_CANCEL]}")
        self.stdout.write(f"  resolves: {counts[EVENT_RESOLVE]}")
        if result.dry_run:
            for event in result.events:
                self.stdout.write(
                    f"    {event.at.isoformat()} {event.kind} {event.corpus_id} "
                    f"{event.signal_group}"
                )
            self.stdout.write(
                self.style.SUCCESS("Dry run complete. No database changes applied.")
            )
            return
        self.stdout.write(f"  submitted: {result.submitted}")
        self.stdout.write(f"  skipped: {result.skipped}")
        self.stdout.write(f"  resolved: {result.resolved}")
        self.stdout.write(f"  classified: {result.classified}")
        self.stdout.write(f"  plans_created: {result.plans_created}")
        self.stdout.write(f"  plans_promoted: {result.plans_promoted}")
        self.stdout.write(f"  plans_marked_done: {result.plans_marked_done}")
        self.stdout.write(f"  plans_validated: {result.plans_validated}")
        self.stdout.write(f"  plans_canceled: {result.plans_canceled}")
        self.stdout.write(f"  qualified: {result.qualified}")
        self.stdout.write(f"  marked_interesting: {result.marked_interesting}")
        self.stdout.write(f"  rr_created: {result.rr_created}")
        self.stdout.write(f"  rr_approved: {result.rr_approved}")
        self.stdout.write(f"  rr_rejected: {result.rr_rejected}")
        self.stdout.write(
            self.style.SUCCESS(
                "KONOHA dataset replay complete. "
                "AnalyticsHistoryCoverage.reliable_from was not written."
            )
        )
