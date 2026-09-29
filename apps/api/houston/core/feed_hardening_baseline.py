from __future__ import annotations

import hashlib
import json
import platform
import statistics
import time
import uuid
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from datetime import time as datetime_time
from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.test import APIClient

from houston.accounts.models import User
from houston.action_plans.api.serializers import serialize_execution_history_page
from houston.action_plans.constants import (
    CANCEL_ORIGIN_MANUAL,
    EXECUTION_STATUS_CANCELED,
    EXECUTION_STATUS_DONE,
    EXECUTION_STATUS_IN_PROGRESS,
    EXECUTION_STATUS_PENDING_VALIDATION,
    EXECUTION_STATUS_SCHEDULED,
)
from houston.action_plans.execution_feed import (
    ActionPlanExecutionFeedPage,
    build_action_plan_execution_feed_page,
    build_cross_action_plan_execution_feed_page,
    build_cross_action_plan_execution_feed_pins_page,
)
from houston.action_plans.execution_history import build_execution_history_page
from houston.action_plans.feed_pin_services import (
    pin_action_plan_execution_for_membership,
)
from houston.action_plans.feed_serializers import (
    ActionPlanExecutionFeedResponseSerializer,
    serialize_action_plan_execution_feed_item,
)
from houston.action_plans.lifecycle_promotion import (
    emit_due_availability_notifications,
    promote_due_scheduled_executions,
)
from houston.action_plans.materialization import (
    ensure_visible_action_plan_executions_materialized,
)
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionFeedPin,
    ActionPlanExecutionLifecycleEvent,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
    ActionPlanTask,
)
from houston.action_plans.selectors import action_plan_execution_overdue
from houston.core.civil_time import history_civil_window
from houston.core.dev_guards import assert_local_dev_environment
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.gamification.models import PointTransaction
from houston.notifications.models import Notification
from houston.observations.models import Observation
from houston.organizations.models import Organization
from houston.signals.api.serializers import serialize_signal_history_page
from houston.signals.api.views import serialize_signal_feed_page
from houston.signals.feed_filters import SignalFeedFilters
from houston.signals.history import build_signal_history_page
from houston.signals.models import Signal, SignalSourceObservation
from houston.signals.signal_feed import (
    build_cross_signal_feed_page,
    build_cross_signal_feed_pins_page,
    build_signal_feed_page,
)

FEED_BASELINE_SCHEMA_VERSION = "feed_hardening_baseline_v3"
FEED_BASELINE_NAMESPACE = "T36 Feed Hardening Baseline"
FEED_BASELINE_ARCHIVE_DIR = Path(".artifacts/feed-hardening-baseline")
DEFAULT_SEED = 36
FEED_BASELINE_PASSWORD = "FeedBaselineOnly123!"


@dataclass(frozen=True)
class FeedBaselineProfile:
    name: str
    establishments: int
    signals_per_establishment: int
    executions_per_establishment: int
    warmups: int
    timing_iterations: int


FEED_BASELINE_PROFILES = {
    "smoke": FeedBaselineProfile(
        name="smoke",
        establishments=2,
        signals_per_establishment=80,
        executions_per_establishment=60,
        warmups=1,
        timing_iterations=3,
    ),
    "representative": FeedBaselineProfile(
        name="representative",
        establishments=20,
        signals_per_establishment=250,
        executions_per_establishment=180,
        warmups=1,
        timing_iterations=7,
    ),
}


@dataclass(frozen=True)
class FeedBaselineDataset:
    profile: str
    seed: int
    organization_id: uuid.UUID
    user_id: uuid.UUID
    membership_ids: tuple[uuid.UUID, ...]
    establishment_ids: tuple[uuid.UUID, ...]
    seeded_at: str


@dataclass(frozen=True)
class QueryDiagnostic:
    sql: str
    params: tuple[Any, ...] | dict[str, Any] | None
    elapsed_ms: float


class _QueryRecorder:
    def __init__(self) -> None:
        self.queries: list[QueryDiagnostic] = []

    def __call__(self, execute, sql, params, many, context):
        started_at = time.perf_counter()
        try:
            return execute(sql, params, many, context)
        finally:
            self.queries.append(
                QueryDiagnostic(
                    sql=str(sql),
                    params=params,
                    elapsed_ms=(time.perf_counter() - started_at) * 1000,
                )
            )


def resolve_feed_baseline_profile(
    profile_name: str,
    *,
    establishments: int | None = None,
    signals_per_establishment: int | None = None,
    executions_per_establishment: int | None = None,
    warmups: int | None = None,
    iterations: int | None = None,
) -> FeedBaselineProfile:
    try:
        base = FEED_BASELINE_PROFILES[profile_name]
    except KeyError as exc:
        raise ValueError(f"Unknown feed baseline profile: {profile_name}") from exc
    profile = FeedBaselineProfile(
        name=base.name,
        establishments=base.establishments if establishments is None else establishments,
        signals_per_establishment=(
            base.signals_per_establishment
            if signals_per_establishment is None
            else signals_per_establishment
        ),
        executions_per_establishment=(
            base.executions_per_establishment
            if executions_per_establishment is None
            else executions_per_establishment
        ),
        warmups=base.warmups if warmups is None else warmups,
        timing_iterations=base.timing_iterations if iterations is None else iterations,
    )
    if profile.establishments < 1:
        raise ValueError("establishments must be positive")
    if profile.signals_per_establishment < 30:
        raise ValueError("signals_per_establishment must be at least 30")
    if profile.executions_per_establishment < 30:
        raise ValueError("executions_per_establishment must be at least 30")
    if profile.warmups < 0 or profile.timing_iterations < 2:
        raise ValueError("warmups must be non-negative and iterations at least two")
    return profile


def seed_feed_baseline_dataset(
    profile: FeedBaselineProfile,
    *,
    seed: int = DEFAULT_SEED,
) -> FeedBaselineDataset:
    assert_local_dev_environment()
    _delete_feed_baseline_dataset()
    now = timezone.now().replace(microsecond=0)
    organization = Organization.objects.create(
        id=_baseline_uuid(seed, profile.name, "organization", 0),
        name=f"{FEED_BASELINE_NAMESPACE} {profile.name} seed {seed}",
        status=Organization.Status.ACTIVE,
    )
    user = User.objects.create_user(
        id=_baseline_uuid(seed, profile.name, "user", 0),
        username=f"feed_baseline_{profile.name}_{seed}",
        email=f"feed-baseline-{profile.name}-{seed}@example.invalid",
        password=FEED_BASELINE_PASSWORD,
        status=User.Status.ACTIVE,
    )
    from houston.accounts.legal_services import grant_current_legal_defaults

    grant_current_legal_defaults(user=user)
    establishments = [
        Establishment(
            id=_baseline_uuid(seed, profile.name, "establishment", index),
            organization=organization,
            name=f"Feed baseline establishment {index + 1:02d}",
            status=Establishment.Status.ACTIVE,
            timezone="Europe/Paris",
        )
        for index in range(profile.establishments)
    ]
    Establishment.objects.bulk_create(establishments, batch_size=500)
    memberships = [
        EstablishmentMembership(
            id=_baseline_uuid(seed, profile.name, "membership", index),
            user=user,
            establishment=establishment,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        for index, establishment in enumerate(establishments)
    ]
    EstablishmentMembership.objects.bulk_create(memberships, batch_size=500)

    catalog, _ = CatalogBusinessUnit.objects.get_or_create(
        key="feed-baseline-operations",
        defaults={
            "label": "Feed baseline operations",
            "description": "Synthetic feed baseline instrumentation",
            "sort_order": 32_100,
        },
    )
    business_units = [
        BusinessUnit(
            id=_baseline_uuid(seed, profile.name, "business-unit", index),
            establishment=establishment,
            catalog_business_unit=catalog,
            specific_name="Operations",
            normalized_specific_name="operations",
            routing_key=f"feed-baseline-operations-{establishment.id}",
            source=BusinessUnit.Source.MANUAL,
            active=True,
        )
        for index, establishment in enumerate(establishments)
    ]
    BusinessUnit.objects.bulk_create(business_units, batch_size=500)
    subjects = [
        ActivitySubject(
            id=_baseline_uuid(seed, profile.name, "activity-subject", index),
            establishment=establishment,
            business_unit=business_units[index],
            normalized_name="feed baseline",
            label="Feed baseline",
            routing_key=f"custom--feed-baseline-subject-{establishment.id}",
            source=ActivitySubject.Source.MANUAL,
            active=True,
        )
        for index, establishment in enumerate(establishments)
    ]
    ActivitySubject.objects.bulk_create(subjects, batch_size=500)

    with transaction.atomic():
        _seed_signals(
            profile=profile,
            seed=seed,
            now=now,
            memberships=memberships,
            business_units=business_units,
            subjects=subjects,
        )
        _seed_executions(
            profile=profile,
            seed=seed,
            now=now,
            memberships=memberships,
            business_units=business_units,
            subjects=subjects,
        )
    return FeedBaselineDataset(
        profile=profile.name,
        seed=seed,
        organization_id=organization.id,
        user_id=user.id,
        membership_ids=tuple(membership.id for membership in memberships),
        establishment_ids=tuple(establishment.id for establishment in establishments),
        seeded_at=now.isoformat(),
    )


def load_feed_baseline_dataset(
    profile: FeedBaselineProfile,
    *,
    seed: int = DEFAULT_SEED,
) -> FeedBaselineDataset:
    assert_local_dev_environment()
    organization = Organization.objects.filter(
        name=f"{FEED_BASELINE_NAMESPACE} {profile.name} seed {seed}"
    ).get()
    memberships = list(
        EstablishmentMembership.objects.filter(
            establishment__organization=organization,
            user__username=f"feed_baseline_{profile.name}_{seed}",
        ).order_by("establishment_id")
    )
    if len(memberships) != profile.establishments:
        raise RuntimeError("Feed baseline dataset does not match the requested profile.")
    first_signal = (
        Signal.objects.filter(establishment__organization=organization)
        .order_by("created_at")
        .first()
    )
    return FeedBaselineDataset(
        profile=profile.name,
        seed=seed,
        organization_id=organization.id,
        user_id=memberships[0].user_id,
        membership_ids=tuple(row.id for row in memberships),
        establishment_ids=tuple(row.establishment_id for row in memberships),
        seeded_at=(first_signal.created_at if first_signal else timezone.now()).isoformat(),
    )


def benchmark_feed_baseline(
    dataset: FeedBaselineDataset,
    profile: FeedBaselineProfile,
    *,
    reference_commit: str,
    explain: bool = True,
    explain_limit: int = 2,
) -> dict[str, Any]:
    assert_local_dev_environment()
    temporal_anchor = datetime.fromisoformat(dataset.seeded_at)
    with patch("django.utils.timezone.now", return_value=temporal_anchor):
        return _benchmark_feed_baseline_at_anchor(
            dataset,
            profile,
            reference_commit=reference_commit,
            explain=explain,
            explain_limit=explain_limit,
        )


def _benchmark_feed_baseline_at_anchor(
    dataset: FeedBaselineDataset,
    profile: FeedBaselineProfile,
    *,
    reference_commit: str,
    explain: bool,
    explain_limit: int,
) -> dict[str, Any]:
    memberships = list(
        EstablishmentMembership.objects.filter(id__in=dataset.membership_ids)
        .select_related("establishment", "user")
        .order_by("establishment_id")
    )
    primary = memberships[0]
    filters = SignalFeedFilters()

    _prepare_execution_read_catch_up_fixture(dataset=dataset, membership=primary)
    read_catch_up_report = _run_pr5d_diagnostic(
        name="historical_combined_catch_up",
        operation=_operation_execution_establishment(primary),
        dataset=dataset,
        explain=explain,
        explain_limit=explain_limit,
    )
    pre_warm_execution = _operation_execution_establishment(primary)
    establishment_no_op_report = _run_pr5d_diagnostic(
        name="establishment_no_op",
        operation=pre_warm_execution,
        dataset=dataset,
        explain=explain,
        explain_limit=explain_limit,
    )
    cross_no_op_scope_sizes = sorted({1, min(5, len(memberships)), len(memberships)})
    pr5d_diagnostics = [
        establishment_no_op_report,
        *[
            _run_pr5d_diagnostic(
                name=f"cross_{scope_size}_no_op",
                operation=_operation_execution_cross(memberships[:scope_size]),
                dataset=dataset,
                explain=explain,
                explain_limit=explain_limit,
            )
            for scope_size in cross_no_op_scope_sizes
        ],
    ]
    pr5d_diagnostics.extend(
        _run_isolated_pr5d_diagnostics(
            dataset=dataset,
            membership=primary,
            explain=explain,
            explain_limit=explain_limit,
        )
    )
    scenarios = _build_scenarios(primary=primary, memberships=memberships, filters=filters)
    scenarios.extend(
        _build_http_scenarios(
            user=primary.user,
            establishment_id=primary.establishment_id,
        )
    )
    scenario_reports = []
    for name, operation in scenarios:
        timing = _run_timing(
            operation,
            warmups=profile.warmups,
            iterations=profile.timing_iterations,
        )
        diagnostic = _run_query_diagnostic(operation)
        result = operation()
        report = {
            "name": name,
            "timing": timing,
            "diagnostic": _diagnostic_payload(diagnostic),
            "payload_bytes": len(
                json.dumps(result, default=str, separators=(",", ":")).encode("utf-8")
            ),
        }
        report["_diagnostic_queries"] = diagnostic["queries"]
        scenario_reports.append(report)

    # EXPLAIN ANALYZE warms buffers substantially. Run every comparable timing and
    # query diagnostic first so one scenario's plan cannot influence a later timing.
    if explain:
        for report in scenario_reports:
            report["explains"] = _explain_slowest_selects(
                report["_diagnostic_queries"],
                limit=explain_limit,
            )
    for report in scenario_reports:
        del report["_diagnostic_queries"]

    return {
        "schema_version": FEED_BASELINE_SCHEMA_VERSION,
        "captured_at": timezone.now().isoformat(),
        "reference_commit": reference_commit,
        "configuration": {"profile": asdict(profile), "seed": dataset.seed},
        "environment": _environment_payload(),
        "dataset": _inventory(dataset),
        # These two compatibility keys preserve the historical PR4/PR5B comparison.
        "execution_read_catch_up": read_catch_up_report["diagnostic"],
        "pre_warm_execution_read_path": establishment_no_op_report["diagnostic"],
        "pr5d_diagnostics": [
            read_catch_up_report,
            *pr5d_diagnostics,
        ],
        "scenarios": scenario_reports,
    }


def write_feed_baseline_archive(
    report: dict[str, Any],
    *,
    archive_dir: Path | None = None,
    filename: str | None = None,
) -> Path:
    target_dir = archive_dir or FEED_BASELINE_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    profile = report["configuration"]["profile"]["name"]
    target_name = filename or f"feed-baseline-{profile}-{timezone.now():%Y%m%d%H%M%S}.json"
    path = target_dir / target_name
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def format_feed_baseline_report(report: dict[str, Any]) -> str:
    dataset = report["dataset"]
    lines = [
        f"Feed baseline profile: {report['configuration']['profile']['name']}",
        f"Reference commit: {report['reference_commit']}",
        (
            f"Dataset: {dataset['establishments']} establishments, "
            f"{dataset['signals_total']} signals, "
            f"{dataset['executions_total']} executions"
        ),
        "PR5D diagnostics:",
    ]
    for scenario in report.get("pr5d_diagnostics", []):
        diagnostic = scenario["diagnostic"]
        lines.append(
            f"  {scenario['name']}: queries={diagnostic['query_count']} "
            f"(select={diagnostic['select_query_count']}, "
            f"write={diagnostic['write_query_count']}, "
            f"control={diagnostic['control_query_count']}) "
            f"sql={diagnostic['sql_total_ms']:.1f}ms "
            f"wall={diagnostic['wall_ms']:.1f}ms"
        )
    lines.append("Scenarios:")
    for scenario in report["scenarios"]:
        lines.append(
            f"  {scenario['name']}: p50={scenario['timing']['p50_ms']:.1f}ms "
            f"p95={scenario['timing']['p95_ms']:.1f}ms "
            f"queries={scenario['diagnostic']['query_count']} "
            f"payload={scenario['payload_bytes']}B"
        )
    return "\n".join(lines)


def _seed_signals(
    *,
    profile: FeedBaselineProfile,
    seed: int,
    now,
    memberships: list[EstablishmentMembership],
    business_units: list[BusinessUnit],
    subjects: list[ActivitySubject],
) -> None:
    signals = []
    for establishment_index, membership in enumerate(memberships):
        for local_index in range(profile.signals_per_establishment):
            global_index = (
                establishment_index * profile.signals_per_establishment + local_index
            )
            bucket = local_index % 20
            if establishment_index == 0 and bucket < 14:
                status = Signal.Status.OPEN
            elif establishment_index == 0 and bucket < 18:
                status = Signal.Status.IN_PROGRESS
            elif establishment_index == 0:
                status = Signal.Status.INTERESTING
            elif establishment_index == 1 and bucket < 2:
                status = Signal.Status.OPEN
            elif establishment_index == 1 and bucket < 4:
                status = Signal.Status.IN_PROGRESS
            elif establishment_index == 1 and bucket < 5:
                status = Signal.Status.INTERESTING
            elif establishment_index == 1 and bucket < 15:
                status = Signal.Status.RESOLVED
            elif establishment_index == 1:
                status = Signal.Status.CANCELED
            elif bucket < 10:
                status = Signal.Status.OPEN
            elif bucket < 14:
                status = Signal.Status.IN_PROGRESS
            elif bucket < 16:
                status = Signal.Status.INTERESTING
            elif bucket < 19:
                status = Signal.Status.RESOLVED
            else:
                status = Signal.Status.CANCELED
            terminal_at = now - timedelta(days=(local_index % 120), minutes=local_index)
            is_pinned = local_index < 5
            is_undated_terminal = local_index % 40 == 19
            signals.append(
                Signal(
                    id=_baseline_uuid(seed, profile.name, "signal", global_index),
                    establishment=membership.establishment,
                    affected_business_unit=business_units[establishment_index],
                    responsible_business_unit=business_units[establishment_index],
                    activity_subject=subjects[establishment_index],
                    status=status,
                    routing_status=Signal.RoutingStatus.RESOLVED,
                    is_pinned=is_pinned,
                    pinned_at=(now - timedelta(minutes=local_index)) if is_pinned else None,
                    pinned_by_membership=membership if is_pinned else None,
                    title=f"Synthetic signal {global_index:06d}",
                    structured_summary="Synthetic safe summary for feed baseline.",
                    issue_focus=f"synthetic-feed-baseline-{global_index}",
                    last_activity_at=now - timedelta(minutes=local_index),
                    resolved_at=(
                        terminal_at
                        if status == Signal.Status.RESOLVED and not is_undated_terminal
                        else None
                    ),
                    resolved_by_membership=(
                        membership if status == Signal.Status.RESOLVED else None
                    ),
                    resolution_origin=(
                        Signal.ResolutionOrigin.MANUAL
                        if status == Signal.Status.RESOLVED
                        else None
                    ),
                    canceled_at=(
                        terminal_at
                        if status == Signal.Status.CANCELED and not is_undated_terminal
                        else None
                    ),
                    canceled_by_membership=(
                        membership if status == Signal.Status.CANCELED else None
                    ),
                )
            )
    Signal.objects.bulk_create(signals, batch_size=1_000)
    observations = [
        Observation(
            id=_baseline_uuid(
                seed,
                profile.name,
                "signal-observation",
                signal_index * 2 + observation_index,
            ),
            establishment=signal.establishment,
            submitted_by_membership=memberships[
                signal_index // profile.signals_per_establishment
            ],
            raw_text="Synthetic observation used only for feed measurement.",
            submitted_at=now
            - timedelta(minutes=signal_index, seconds=observation_index),
        )
        for signal_index, signal in enumerate(signals)
        for observation_index in range(2)
    ]
    Observation.objects.bulk_create(observations, batch_size=1_000)
    SignalSourceObservation.objects.bulk_create(
        [
            SignalSourceObservation(
                id=_baseline_uuid(
                    seed,
                    profile.name,
                    "signal-observation-link",
                    signal_index * 2 + observation_index,
                ),
                signal=signal,
                observation=observations[signal_index * 2 + observation_index],
                link_type=SignalSourceObservation.LinkType.AGGREGATED_FROM,
            )
            for signal_index, signal in enumerate(signals)
            for observation_index in range(2)
        ],
        batch_size=1_000,
    )


def _seed_executions(
    *,
    profile: FeedBaselineProfile,
    seed: int,
    now,
    memberships: list[EstablishmentMembership],
    business_units: list[BusinessUnit],
    subjects: list[ActivitySubject],
) -> None:
    plans = [
        ActionPlan(
            id=_baseline_uuid(seed, profile.name, "action-plan", index),
            establishment=membership.establishment,
            created_by=membership,
            pilot_business_unit=business_units[index],
            affected_business_unit=business_units[index],
            responsible_business_unit=business_units[index],
            activity_subject=subjects[index],
            title=f"Synthetic plan {index + 1:02d}",
            description="Synthetic feed baseline plan.",
            requires_validation=True,
        )
        for index, membership in enumerate(memberships)
    ]
    ActionPlan.objects.bulk_create(plans, batch_size=500)
    executions = []
    pinned_ids: list[tuple[EstablishmentMembership, uuid.UUID]] = []
    for establishment_index, membership in enumerate(memberships):
        for local_index in range(profile.executions_per_establishment):
            global_index = (
                establishment_index * profile.executions_per_establishment + local_index
            )
            bucket = local_index % 20
            if establishment_index == 0 and bucket < 14:
                status = EXECUTION_STATUS_IN_PROGRESS
            elif establishment_index == 0 and bucket < 18:
                status = EXECUTION_STATUS_PENDING_VALIDATION
            elif establishment_index == 0 and bucket < 19:
                status = EXECUTION_STATUS_DONE
            elif establishment_index == 0:
                status = EXECUTION_STATUS_SCHEDULED
            elif establishment_index == 1 and bucket < 3:
                status = EXECUTION_STATUS_IN_PROGRESS
            elif establishment_index == 1 and bucket < 4:
                status = EXECUTION_STATUS_PENDING_VALIDATION
            elif establishment_index == 1 and bucket < 12:
                status = EXECUTION_STATUS_DONE
            elif establishment_index == 1 and bucket < 19:
                status = EXECUTION_STATUS_CANCELED
            elif establishment_index == 1:
                status = EXECUTION_STATUS_SCHEDULED
            elif bucket < 11:
                status = EXECUTION_STATUS_IN_PROGRESS
            elif bucket < 14:
                status = EXECUTION_STATUS_PENDING_VALIDATION
            elif bucket < 17:
                status = EXECUTION_STATUS_DONE
            elif bucket < 19:
                status = EXECUTION_STATUS_CANCELED
            else:
                status = EXECUTION_STATUS_SCHEDULED
            item_id = _baseline_uuid(seed, profile.name, "execution", global_index)
            activity_at = now - timedelta(minutes=local_index)
            terminal_at = now - timedelta(days=(local_index % 120), minutes=local_index)
            is_undated_terminal = local_index % 40 in {16, 18}
            if status == EXECUTION_STATUS_SCHEDULED:
                start_at = now + timedelta(days=2 + (local_index % 14))
                visible_from = start_at - timedelta(hours=1)
                end_at = start_at + timedelta(hours=2)
            elif local_index % 3 == 0:
                start_at = now - timedelta(days=10)
                visible_from = now - timedelta(days=30)
                end_at = now - timedelta(days=1 + local_index % 7)
            elif local_index % 3 == 1:
                start_at = now - timedelta(days=2)
                visible_from = now - timedelta(days=30)
                end_at = now + timedelta(days=1 + local_index % 7)
            else:
                start_at = None
                visible_from = now - timedelta(days=30)
                end_at = None
            executions.append(
                ActionPlanExecution(
                    id=item_id,
                    action_plan=plans[establishment_index],
                    chronology_owner_membership=membership,
                    establishment=membership.establishment,
                    created_by=membership,
                    title=f"Synthetic execution {global_index:06d}",
                    description="Synthetic execution used only for feed measurement.",
                    pilot_business_unit=business_units[establishment_index],
                    affected_business_unit=business_units[establishment_index],
                    responsible_business_unit=business_units[establishment_index],
                    activity_subject=subjects[establishment_index],
                    requires_validation=True,
                    use_shared_chronology=False,
                    status=status,
                    start_at=start_at,
                    visible_from=visible_from,
                    end_at=end_at,
                    last_activity_at=activity_at,
                    marked_done_at=(
                        terminal_at
                        if status in {EXECUTION_STATUS_PENDING_VALIDATION, EXECUTION_STATUS_DONE}
                        else None
                    ),
                    marked_done_by_membership=(
                        membership
                        if status in {EXECUTION_STATUS_PENDING_VALIDATION, EXECUTION_STATUS_DONE}
                        else None
                    ),
                    validated_at=(
                        terminal_at
                        if status == EXECUTION_STATUS_DONE and not is_undated_terminal
                        else None
                    ),
                    validated_by_membership=(
                        membership if status == EXECUTION_STATUS_DONE else None
                    ),
                    canceled_at=(
                        terminal_at
                        if status == EXECUTION_STATUS_CANCELED and not is_undated_terminal
                        else None
                    ),
                    canceled_by_membership=(
                        membership if status == EXECUTION_STATUS_CANCELED else None
                    ),
                    cancel_origin=(
                        CANCEL_ORIGIN_MANUAL
                        if status == EXECUTION_STATUS_CANCELED
                        else None
                    ),
                )
            )
            if local_index < 3 and status == EXECUTION_STATUS_IN_PROGRESS:
                pinned_ids.append((membership, item_id))
    ActionPlanExecution.objects.bulk_create(executions, batch_size=1_000)
    execution_teams = [
        ActionPlanExecutionTeam(
            id=_baseline_uuid(seed, profile.name, "execution-team", index),
            action_plan_execution=execution,
            business_unit=business_units[index // profile.executions_per_establishment],
            is_pilot=True,
        )
        for index, execution in enumerate(executions)
    ]
    ActionPlanExecutionTeam.objects.bulk_create(execution_teams, batch_size=1_000)
    ActionPlanAssignee.objects.bulk_create(
        [
            ActionPlanAssignee(
                id=_baseline_uuid(seed, profile.name, "execution-assignee", index),
                action_plan_execution=execution,
                execution_team=execution_teams[index],
                membership=memberships[index // profile.executions_per_establishment],
            )
            for index, execution in enumerate(executions)
        ],
        batch_size=1_000,
    )
    ActionPlanExecutionTask.objects.bulk_create(
        [
            ActionPlanExecutionTask(
                id=_baseline_uuid(
                    seed,
                    profile.name,
                    "execution-task",
                    execution_index * 3 + task_index,
                ),
                action_plan_execution=execution,
                execution_team=execution_teams[execution_index],
                task=f"Synthetic task {task_index + 1}",
                assigned_membership=memberships[
                    execution_index // profile.executions_per_establishment
                ],
                assigned_display_name="Baseline User",
                position=task_index + 1,
            )
            for execution_index, execution in enumerate(executions)
            for task_index in range(3)
        ],
        batch_size=1_000,
    )
    ActionPlanExecutionFeedPin.objects.bulk_create(
        [
            ActionPlanExecutionFeedPin(
                membership=membership,
                action_plan_execution_id=execution_id,
            )
            for membership, execution_id in pinned_ids
        ],
        batch_size=500,
    )


def _build_scenarios(*, primary, memberships, filters):
    signal_first = _operation_signal_establishment(primary, filters)
    first_signal_payload = signal_first()
    signal_cursor = first_signal_payload["next_cursor"]
    execution_first = _operation_execution_establishment(primary)
    first_execution_payload = execution_first()
    execution_cursor = first_execution_payload["next_cursor"]
    cross_signal_first = _operation_signal_cross(memberships, filters)
    cross_signal_payload = cross_signal_first()
    cross_execution_first = _operation_execution_cross(memberships)
    cross_execution_payload = cross_execution_first()
    cross_scope_sizes = sorted({1, min(5, len(memberships)), len(memberships)})
    scenarios: list[tuple[str, Callable[[], Any]]] = [
        ("signal_establishment_first", signal_first),
        (
            "signal_establishment_continuation",
            _operation_signal_establishment(primary, filters, cursor=signal_cursor),
        ),
        *[
            (
                f"signal_cross_{scope_size}_first",
                (
                    cross_signal_first
                    if scope_size == len(memberships)
                    else _operation_signal_cross(memberships[:scope_size], filters)
                ),
            )
            for scope_size in cross_scope_sizes
        ],
        (
            f"signal_cross_{len(memberships)}_continuation",
            _operation_signal_cross(
                memberships,
                filters,
                cursor=cross_signal_payload["next_cursor"],
            ),
        ),
        (
            f"signal_cross_{len(memberships)}_pins_continuation",
            _operation_signal_cross_pins(
                memberships,
                filters,
                cursor=cross_signal_payload["pins_next_cursor"],
            ),
        ),
        ("execution_establishment_first", execution_first),
        (
            "execution_establishment_continuation",
            _operation_execution_establishment(primary, cursor=execution_cursor),
        ),
        *[
            (
                f"execution_cross_{scope_size}_first",
                (
                    cross_execution_first
                    if scope_size == len(memberships)
                    else _operation_execution_cross(memberships[:scope_size])
                ),
            )
            for scope_size in cross_scope_sizes
        ],
        (
            f"execution_cross_{len(memberships)}_continuation",
            _operation_execution_cross(
                memberships,
                cursor=cross_execution_payload["next_cursor"],
            ),
        ),
        (
            f"execution_cross_{len(memberships)}_pins_first",
            _operation_execution_cross_pins(memberships),
        ),
        ("signal_history_all", _operation_signal_history(memberships)),
        ("signal_history_90_days", _operation_signal_history(memberships, period="90")),
        ("execution_history_all", _operation_execution_history(memberships)),
        (
            "execution_history_90_days",
            _operation_execution_history(memberships, period="90"),
        ),
        ("execution_pin_replace", _operation_execution_pin_replace(primary)),
    ]
    return [
        (name, operation)
        for name, operation in scenarios
        if operation is not None
    ]


def _prepare_execution_read_catch_up_fixture(*, dataset, membership):
    old_schedules = ActionPlanSchedule.objects.filter(
        created_by=membership,
        action_plan__title__startswith="Synthetic plan ",
    )
    ActionPlanExecution.objects.filter(action_plan_schedule__in=old_schedules).delete()
    old_schedules.delete()
    ActionPlanExecution.objects.filter(
        establishment_id=membership.establishment_id,
        title=f"{FEED_BASELINE_NAMESPACE} lifecycle catch-up",
    ).delete()

    now = timezone.now().replace(microsecond=0)
    anchor = now.isoformat()
    plan = ActionPlan.objects.get(
        establishment_id=membership.establishment_id,
    )
    business_unit = BusinessUnit.objects.get(
        establishment_id=membership.establishment_id,
        routing_key=f"feed-baseline-operations-{membership.establishment_id}",
    )
    local_today = now.astimezone(ZoneInfo(membership.establishment.timezone)).date()
    schedule = ActionPlanSchedule(
        id=_baseline_run_uuid(
            dataset.seed,
            dataset.profile,
            "catch-up-schedule",
            0,
            anchor=anchor,
        ),
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        use_shared_chronology=False,
        start_date=local_today,
        end_date=local_today + timedelta(days=7),
        start_at=datetime_time(hour=8),
        end_at=datetime_time(hour=10),
        recurrence_days=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        last_materialized_at=None,
    )
    # Bulk creation bypasses eager schedule hooks: the next measured feed read
    # must own both catch-up writes.
    ActionPlanSchedule.objects.bulk_create([schedule])
    ActionPlanScheduleAssignee.objects.bulk_create(
        [
            ActionPlanScheduleAssignee(
                id=_baseline_run_uuid(
                    dataset.seed,
                    dataset.profile,
                    "catch-up-schedule-assignee",
                    0,
                    anchor=anchor,
                ),
                action_plan_schedule=schedule,
                membership=membership,
                business_unit=business_unit,
            )
        ]
    )
    ActionPlanExecution.objects.bulk_create(
        [
            ActionPlanExecution(
                id=_baseline_run_uuid(
                    dataset.seed,
                    dataset.profile,
                    "lifecycle-catch-up-execution",
                    0,
                    anchor=anchor,
                ),
                action_plan=plan,
                chronology_owner_membership=membership,
                establishment=membership.establishment,
                created_by=membership,
                title=f"{FEED_BASELINE_NAMESPACE} lifecycle catch-up",
                description="Synthetic due execution for read catch-up measurement.",
                pilot_business_unit=business_unit,
                affected_business_unit=business_unit,
                responsible_business_unit=business_unit,
                requires_validation=True,
                use_shared_chronology=False,
                status=EXECUTION_STATUS_SCHEDULED,
                start_at=now - timedelta(hours=1),
                visible_from=now - timedelta(hours=2),
                end_at=now + timedelta(hours=1),
                last_activity_at=now - timedelta(hours=2),
            )
        ]
    )


def _run_isolated_pr5d_diagnostics(
    *,
    dataset: FeedBaselineDataset,
    membership: EstablishmentMembership,
    explain: bool,
    explain_limit: int,
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    scenarios = (
        ("materialization_only", _prepare_pr5d_materialization_fixture),
        ("availability_only", _prepare_pr5d_availability_fixture),
        ("promotion_only", _prepare_pr5d_promotion_fixture),
    )
    for name, prepare in scenarios:
        operation, cleanup = prepare(dataset=dataset, membership=membership)
        try:
            report = _run_pr5d_diagnostic(
                name=name,
                operation=operation,
                dataset=dataset,
                explain=explain,
                explain_limit=explain_limit,
            )
            if name == "materialization_only":
                _assert_pr5d_materialization_only_effect(report)
            diagnostics.append(report)
        finally:
            cleanup()
    return diagnostics


def _pr5d_fixture_context(
    *,
    dataset: FeedBaselineDataset,
    membership: EstablishmentMembership,
    kind: str,
) -> tuple[datetime, ActionPlan, BusinessUnit, uuid.UUID]:
    now = timezone.now().replace(microsecond=0)
    plan = ActionPlan.objects.get(establishment_id=membership.establishment_id)
    business_unit = BusinessUnit.objects.get(
        establishment_id=membership.establishment_id,
        routing_key=f"feed-baseline-operations-{membership.establishment_id}",
    )
    fixture_id = _baseline_run_uuid(
        dataset.seed,
        dataset.profile,
        f"pr5d-{kind}",
        0,
        anchor=now.isoformat(),
    )
    return now, plan, business_unit, fixture_id


def _prepare_pr5d_materialization_fixture(*, dataset, membership):
    now, plan, business_unit, schedule_id = _pr5d_fixture_context(
        dataset=dataset,
        membership=membership,
        kind="materialization-schedule",
    )
    establishment_tz = ZoneInfo(membership.establishment.timezone)
    local_today = now.astimezone(establishment_tz).date()
    # Visibility is occurrence start minus one hour. A fixed 08:00–10:00
    # window is not yet visible when the frozen anchor is before 07:00 local,
    # so the read path materializes nothing. Keep a same-day two-hour span
    # whose start is already inside that window.
    start_at, end_at = _visible_same_day_materialization_window(
        now,
        establishment_tz,
    )
    schedule = ActionPlanSchedule.objects.create(
        id=schedule_id,
        action_plan=plan,
        establishment=membership.establishment,
        created_by=membership,
        use_shared_chronology=False,
        start_date=local_today,
        end_date=local_today,
        start_at=start_at,
        end_at=end_at,
        recurrence_days=[
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        ],
        last_materialized_at=None,
    )
    ActionPlanScheduleAssignee.objects.create(
        action_plan_schedule=schedule,
        membership=membership,
        business_unit=business_unit,
    )
    plan_task = ActionPlanTask.objects.create(
        action_plan=plan,
        business_unit=business_unit,
        task="PR5D isolated materialization task",
        assigned_membership=membership,
        position=1,
    )

    def operation():
        return ensure_visible_action_plan_executions_materialized(
            membership=membership,
            view_mode="general",
        )

    def cleanup():
        execution_ids = list(
            ActionPlanExecution.objects.filter(
                action_plan_schedule_id=schedule_id,
            ).values_list("id", flat=True)
        )
        _cleanup_pr5d_fixture(
            execution_ids=execution_ids,
            schedule_ids=[schedule_id],
        )
        plan_task.delete()

    return operation, cleanup


def _visible_same_day_materialization_window(
    now: datetime,
    tz: ZoneInfo,
) -> tuple[datetime_time, datetime_time]:
    local_now = now.astimezone(tz).replace(second=0, microsecond=0)
    duration = timedelta(hours=2)
    latest_end = local_now.replace(hour=23, minute=59)
    start = min(local_now, latest_end - duration)
    end = min(start + duration, latest_end)
    return (
        datetime_time(hour=start.hour, minute=start.minute),
        datetime_time(hour=end.hour, minute=end.minute),
    )


def _assert_pr5d_materialization_only_effect(report: dict[str, Any]) -> None:
    delta = report["side_effect_delta"]
    if delta.get("executions", 0) < 1 or delta.get("materialized_schedules", 0) < 1:
        raise RuntimeError(
            "materialization_only completed without materializing a visible occurrence."
        )


def _prepare_pr5d_availability_fixture(*, dataset, membership):
    return _prepare_pr5d_lifecycle_fixture(
        dataset=dataset,
        membership=membership,
        kind="availability",
        start_delta=timedelta(hours=1),
        availability_notified=False,
        operation_factory=lambda execution_id: lambda: emit_due_availability_notifications(
            establishment_id=membership.establishment_id,
            execution_id=execution_id,
        ),
    )


def _prepare_pr5d_promotion_fixture(*, dataset, membership):
    return _prepare_pr5d_lifecycle_fixture(
        dataset=dataset,
        membership=membership,
        kind="promotion",
        start_delta=-timedelta(hours=1),
        availability_notified=True,
        operation_factory=lambda execution_id: lambda: promote_due_scheduled_executions(
            establishment_id=membership.establishment_id,
            execution_id=execution_id,
        ),
    )


def _prepare_pr5d_lifecycle_fixture(
    *,
    dataset,
    membership,
    kind,
    start_delta,
    availability_notified,
    operation_factory,
):
    now, plan, business_unit, execution_id = _pr5d_fixture_context(
        dataset=dataset,
        membership=membership,
        kind=f"{kind}-execution",
    )
    execution = ActionPlanExecution.objects.create(
        id=execution_id,
        action_plan=plan,
        chronology_owner_membership=membership,
        establishment=membership.establishment,
        created_by=membership,
        title=f"{FEED_BASELINE_NAMESPACE} PR5D {kind}",
        description=f"Isolated PR5D {kind} diagnostic.",
        pilot_business_unit=business_unit,
        affected_business_unit=business_unit,
        responsible_business_unit=business_unit,
        requires_validation=True,
        use_shared_chronology=False,
        status=EXECUTION_STATUS_SCHEDULED,
        start_at=now + start_delta,
        visible_from=now - timedelta(minutes=1),
        end_at=now + start_delta + timedelta(hours=2),
        availability_notified_at=(now - timedelta(minutes=1) if availability_notified else None),
        last_activity_at=now - timedelta(hours=2),
    )
    team = ActionPlanExecutionTeam.objects.create(
        action_plan_execution=execution,
        business_unit=business_unit,
        is_pilot=True,
    )
    ActionPlanAssignee.objects.create(
        action_plan_execution=execution,
        execution_team=team,
        membership=membership,
        start_at=execution.start_at,
        visible_from=execution.visible_from,
        end_at=execution.end_at,
    )

    def cleanup():
        _cleanup_pr5d_fixture(execution_ids=[execution_id], schedule_ids=[])

    return operation_factory(execution_id), cleanup


def _cleanup_pr5d_fixture(*, execution_ids, schedule_ids):
    if execution_ids:
        Notification.objects.filter(
            subject_type=Notification.SubjectType.ACTION_PLAN_EXECUTION,
            subject_id__in=execution_ids,
        ).delete()
        PointTransaction.objects.filter(
            source_id__in=[str(execution_id) for execution_id in execution_ids],
        ).delete()
        ActionPlanExecution.objects.filter(id__in=execution_ids).delete()
    if schedule_ids:
        ActionPlanSchedule.objects.filter(id__in=schedule_ids).delete()


def _build_http_scenarios(*, user, establishment_id):
    client = APIClient()
    csrf_response = client.get("/api/v1/auth/csrf/", HTTP_HOST="localhost")
    csrf_token = csrf_response.cookies["csrftoken"].value
    login_response = client.post(
        "/api/v1/auth/login/",
        {
            "identifier": user.email,
            "password": FEED_BASELINE_PASSWORD,
            "refresh_token_transport": "cookie",
        },
        format="json",
        HTTP_HOST="localhost",
        HTTP_X_CSRFTOKEN=csrf_token,
    )
    if login_response.status_code != 200:
        raise RuntimeError(
            f"HTTP baseline login failed with {login_response.status_code}."
        )
    authorization = f"Bearer {login_response.json()['access_token']}"

    def operation(path):
        def request():
            response = client.get(
                path,
                HTTP_HOST="localhost",
                HTTP_AUTHORIZATION=authorization,
            )
            if response.status_code != 200:
                raise RuntimeError(
                    f"HTTP baseline request failed: {path} returned {response.status_code}."
                )
            return response.json()

        return request

    signal_establishment_path = (
        f"/api/v1/establishments/{establishment_id}/signal-feed/"
        "?view_mode=general&page_size=25"
    )
    signal_cross_path = "/api/v1/cross/signal-feed/?page_size=25"
    execution_establishment_path = (
        f"/api/v1/establishments/{establishment_id}/"
        "action-plan-execution-feed/?view_mode=general&category=all&page_size=25"
    )
    execution_cross_path = (
        "/api/v1/cross/action-plan-execution-feed/"
        "?view_mode=general&category=all&page_size=25"
    )
    first_pages = {
        "signal_establishment": operation(signal_establishment_path)(),
        "signal_cross": operation(signal_cross_path)(),
        "execution_establishment": operation(execution_establishment_path)(),
        "execution_cross": operation(execution_cross_path)(),
    }

    def continuation(path, cursor):
        separator = "&" if "?" in path else "?"
        return operation(f"{path}{separator}{urlencode({'cursor': cursor})}")

    return [
        (
            "http_signal_establishment_first",
            operation(signal_establishment_path),
        ),
        (
            "http_signal_establishment_continuation",
            continuation(
                signal_establishment_path,
                first_pages["signal_establishment"]["next_cursor"],
            ),
        ),
        (
            "http_signal_cross_first",
            operation(signal_cross_path),
        ),
        (
            "http_signal_cross_continuation",
            continuation(
                signal_cross_path,
                first_pages["signal_cross"]["next_cursor"],
            ),
        ),
        (
            "http_execution_establishment_first",
            operation(execution_establishment_path),
        ),
        (
            "http_execution_establishment_continuation",
            continuation(
                execution_establishment_path,
                first_pages["execution_establishment"]["next_cursor"],
            ),
        ),
        (
            "http_execution_cross_first",
            operation(execution_cross_path),
        ),
        (
            "http_execution_cross_continuation",
            continuation(
                execution_cross_path,
                first_pages["execution_cross"]["next_cursor"],
            ),
        ),
    ]


def _operation_signal_establishment(membership, filters, cursor=None):
    def operation():
        parsed_cursor = None
        if cursor:
            from houston.signals.feed_cursor import parse_signal_feed_cursor

            parsed_cursor = parse_signal_feed_cursor(cursor)
        page = build_signal_feed_page(
            membership=membership,
            view_mode="general",
            filters=filters,
            page_size=25,
            cursor=parsed_cursor,
        )
        return serialize_signal_feed_page(
            page=page,
            view_mode="general",
            filters=filters,
            membership=membership,
        )

    return operation


def _operation_signal_cross(memberships, filters, cursor=None):
    def operation():
        parsed_cursor = None
        if cursor:
            from houston.signals.feed_cursor import parse_signal_feed_cursor

            parsed_cursor = parse_signal_feed_cursor(cursor)
        page = build_cross_signal_feed_page(
            memberships=memberships,
            filters=filters,
            page_size=25,
            pins_page_size=10,
            cursor=parsed_cursor,
        )
        return serialize_signal_feed_page(
            page=page,
            view_mode="general",
            filters=filters,
            membership=memberships[0],
            read_only=True,
        )

    return operation


def _operation_signal_cross_pins(memberships, filters, cursor):
    if not cursor:
        return None

    def operation():
        from houston.signals.feed_cursor import parse_signal_feed_pin_cursor

        page = build_cross_signal_feed_pins_page(
            memberships=memberships,
            filters=filters,
            page_size=10,
            cursor=parse_signal_feed_pin_cursor(cursor),
        )
        return {
            "items": [
                serialize_signal_feed_page(
                    page=type(
                        "Page",
                        (),
                        {"items": [item], "next_cursor": None, "has_more": False, "pins": None},
                    )(),
                    view_mode="general",
                    filters=filters,
                    membership=memberships[0],
                    read_only=True,
                )["items"][0]
                for item in page.items
            ],
            "next_cursor": page.next_cursor,
            "has_more": page.has_more,
        }

    return operation


def _operation_execution_establishment(membership, cursor=None):
    def operation():
        parsed_cursor = None
        if cursor:
            from houston.action_plans.feed_cursor import (
                parse_action_plan_execution_feed_cursor,
            )

            parsed_cursor = parse_action_plan_execution_feed_cursor(cursor)
        page = build_action_plan_execution_feed_page(
            membership=membership,
            view_mode="general",
            category="all",
            page_size=25,
            cursor=parsed_cursor,
        )
        return _serialize_execution_page(page, [membership], read_only=False)

    return operation


def _operation_execution_cross(memberships, cursor=None):
    def operation():
        parsed_cursor = None
        if cursor:
            from houston.action_plans.feed_cursor import (
                parse_action_plan_execution_feed_cursor,
            )

            parsed_cursor = parse_action_plan_execution_feed_cursor(cursor)
        page = build_cross_action_plan_execution_feed_page(
            memberships=memberships,
            view_mode="general",
            category="all",
            page_size=25,
            cursor=parsed_cursor,
        )
        return _serialize_execution_page(page, memberships, read_only=True)

    return operation


def _operation_execution_cross_pins(memberships):
    def operation():
        page = build_cross_action_plan_execution_feed_pins_page(
            memberships=memberships,
            view_mode="general",
            category="all",
            page_size=10,
        )
        return _serialize_execution_page(page, memberships, read_only=True)

    return operation


def _serialize_execution_page(page, memberships, *, read_only):
    by_establishment = {row.establishment_id: row for row in memberships}

    def serialize(execution):
        membership = by_establishment[execution.establishment_id]
        return {
            "item_type": "action_plan_execution",
            "action_plan_execution": serialize_action_plan_execution_feed_item(
                execution=execution,
                membership=membership,
                is_overdue=action_plan_execution_overdue(
                    execution=execution,
                    now=page.as_of,
                ),
                read_only=read_only,
            ),
        }

    payload: dict[str, Any] = {
        "items": [serialize(item) for item in page.items],
        "next_cursor": page.next_cursor,
        "has_more": page.has_more,
    }
    if isinstance(page, ActionPlanExecutionFeedPage):
        if page.pins is not None:
            payload["pins"] = [serialize(item) for item in page.pins]
        if page.scheduled_count is not None:
            payload["scheduled"] = {
                "count": page.scheduled_count,
                "next": (
                    {
                        "id": page.scheduled_next.id,
                        "start_at": page.scheduled_next.start_at,
                        "title": page.scheduled_next.title,
                    }
                    if page.scheduled_next
                    else None
                ),
            }
        if page.section_counts is not None:
            payload["section_counts"] = page.section_counts
    return ActionPlanExecutionFeedResponseSerializer(payload).data


def _operation_signal_history(memberships, *, period="all"):
    def operation():
        window = history_civil_window(period=period, now=timezone.now())
        page = build_signal_history_page(
            memberships=memberships,
            view_mode="general",
            scope="cross",
            status="all",
            period=period,
            period_from=None,
            period_to=None,
            window=window,
            page_size=25,
            cursor=None,
        )
        return serialize_signal_history_page(page)

    return operation


def _operation_execution_history(memberships, *, period="all"):
    def operation():
        window = history_civil_window(period=period, now=timezone.now())
        page = build_execution_history_page(
            memberships=memberships,
            view_mode="general",
            scope="cross",
            status="all",
            period=period,
            period_from=None,
            period_to=None,
            window=window,
            page_size=25,
            cursor=None,
        )
        return serialize_execution_history_page(page)

    return operation


def _operation_execution_pin_replace(membership):
    pins = list(
        ActionPlanExecutionFeedPin.objects.filter(membership=membership)
        .order_by("pinned_at", "id")
        .values_list("action_plan_execution_id", flat=True)
    )
    target_id = (
        ActionPlanExecution.objects.filter(
            establishment_id=membership.establishment_id,
            status=EXECUTION_STATUS_IN_PROGRESS,
        )
        .exclude(id__in=pins)
        .order_by("id")
        .values_list("id", flat=True)
        .first()
    )
    if not pins or target_id is None:
        raise RuntimeError("Execution pin baseline fixture is incomplete.")

    def operation():
        # Exercise the real transactional write path without changing the fixture
        # between iterations or emitting on_commit realtime invalidations.
        with transaction.atomic():
            created = pin_action_plan_execution_for_membership(
                membership=membership,
                execution_id=target_id,
                replace_execution_id=pins[0],
            )
            transaction.set_rollback(True)
        return {"is_pinned": created}

    return operation


def _run_timing(operation, *, warmups, iterations):
    for _ in range(warmups):
        operation()
    samples = []
    for _ in range(iterations):
        started_at = time.perf_counter()
        operation()
        samples.append((time.perf_counter() - started_at) * 1000)
    return {
        "mode": "isolated_wall_clock",
        "warmups": warmups,
        "iterations": iterations,
        "samples_ms": [round(value, 3) for value in samples],
        "p50_ms": round(statistics.median(samples), 3),
        "p95_ms": round(_percentile(samples, 0.95), 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
    }


def _run_query_diagnostic(operation):
    recorder = _QueryRecorder()
    started_at = time.perf_counter()
    with connection.execute_wrapper(recorder):
        operation()
    queries = sorted(recorder.queries, key=lambda row: row.elapsed_ms, reverse=True)
    return {
        "wall_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "query_count": len(queries),
        "sql_total_ms": round(sum(row.elapsed_ms for row in queries), 3),
        "queries": queries,
    }


def _run_pr5d_diagnostic(
    *,
    name: str,
    operation,
    dataset: FeedBaselineDataset,
    explain: bool,
    explain_limit: int,
) -> dict[str, Any]:
    before = _side_effect_snapshot(dataset)
    with _observe_after_commit_effects() as callbacks:
        diagnostic = _run_query_diagnostic(operation)
    after = _side_effect_snapshot(dataset)
    report = {
        "name": name,
        "diagnostic": _diagnostic_payload(diagnostic),
        "side_effect_delta": _snapshot_delta(before, after),
        "callbacks": callbacks,
    }
    if explain:
        report["explains"] = _explain_slowest_selects(
            diagnostic["queries"],
            limit=explain_limit,
        )
    return report


def _side_effect_snapshot(dataset: FeedBaselineDataset) -> dict[str, Any]:
    establishment_ids = dataset.establishment_ids
    executions = ActionPlanExecution.objects.filter(
        establishment_id__in=establishment_ids,
    )
    execution_ids = executions.values_list("id", flat=True)
    return {
        "executions": executions.count(),
        "execution_statuses": dict(
            Counter(executions.values_list("status", flat=True))
        ),
        "availability_notified": executions.filter(
            availability_notified_at__isnull=False,
        ).count(),
        "started": executions.filter(started_at__isnull=False).count(),
        "execution_states": {
            str(row["id"]): {
                "status": row["status"],
                "availability_notified_at": (
                    row["availability_notified_at"].isoformat()
                    if row["availability_notified_at"]
                    else None
                ),
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "last_activity_at": row["last_activity_at"].isoformat(),
            }
            for row in executions.values(
                "id",
                "status",
                "availability_notified_at",
                "started_at",
                "last_activity_at",
            )
        },
        "teams": ActionPlanExecutionTeam.objects.filter(
            action_plan_execution_id__in=execution_ids,
        ).count(),
        "assignees": ActionPlanAssignee.objects.filter(
            action_plan_execution_id__in=execution_ids,
        ).count(),
        "tasks": ActionPlanExecutionTask.objects.filter(
            action_plan_execution_id__in=execution_ids,
        ).count(),
        "materialized_schedules": ActionPlanSchedule.objects.filter(
            establishment_id__in=establishment_ids,
            last_materialized_at__isnull=False,
        ).count(),
        "schedule_freshness": {
            str(schedule_id): (
                last_materialized_at.isoformat() if last_materialized_at else None
            )
            for schedule_id, last_materialized_at in ActionPlanSchedule.objects.filter(
                establishment_id__in=establishment_ids,
            ).values_list("id", "last_materialized_at")
        },
        "lifecycle_events": dict(
            Counter(
                ActionPlanExecutionLifecycleEvent.objects.filter(
                    establishment_id__in=establishment_ids,
                ).values_list("event_type", flat=True)
            )
        ),
        "notifications": dict(
            Counter(
                Notification.objects.filter(
                    establishment_id__in=establishment_ids,
                ).values_list("event_key", flat=True)
            )
        ),
        "point_transactions": dict(
            Counter(
                PointTransaction.objects.filter(
                    establishment_id__in=establishment_ids,
                ).values_list("reason_code", flat=True)
            )
        ),
    }


def _snapshot_delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    delta: dict[str, Any] = {}
    for key, after_value in after.items():
        before_value = before[key]
        if isinstance(after_value, dict):
            if all(
                isinstance(value, int)
                for value in [*before_value.values(), *after_value.values()]
            ):
                names = set(before_value) | set(after_value)
                delta[key] = {
                    name: after_value.get(name, 0) - before_value.get(name, 0)
                    for name in sorted(names)
                    if after_value.get(name, 0) != before_value.get(name, 0)
                }
            else:
                delta[key] = {
                    name: {
                        "before": before_value.get(name),
                        "after": after_value.get(name),
                    }
                    for name in sorted(set(before_value) | set(after_value))
                    if before_value.get(name) != after_value.get(name)
                }
        else:
            delta[key] = after_value - before_value
    return delta


@contextmanager
def _observe_after_commit_effects():
    original_on_commit = transaction.on_commit
    ledger: dict[str, Any] = {
        "scheduled": 0,
        "executed": 0,
        "realtime_invalidations": [],
    }

    def observed_on_commit(callback, using=None, robust=False):
        ledger["scheduled"] += 1

        def observed_callback():
            ledger["executed"] += 1
            return callback()

        return original_on_commit(observed_callback, using=using, robust=robust)

    def observed_realtime(**kwargs):
        ledger["realtime_invalidations"].append(
            {key: str(value) for key, value in kwargs.items()}
        )

    with (
        patch.object(transaction, "on_commit", side_effect=observed_on_commit),
        patch(
            "houston.realtime.broadcast.notify_establishment_invalidation",
            side_effect=observed_realtime,
        ),
    ):
        yield ledger


def _diagnostic_payload(diagnostic):
    queries = diagnostic["queries"]
    query_kinds = [_query_kind(row.sql) for row in queries]
    select_count = query_kinds.count("select")
    write_count = query_kinds.count("write")
    query_attribution = _query_attribution(queries)
    payload = {
        "mode": "instrumented_single_run",
        "wall_ms": diagnostic["wall_ms"],
        "query_count": diagnostic["query_count"],
        "select_query_count": select_count,
        "write_query_count": write_count,
        "control_query_count": diagnostic["query_count"] - select_count - write_count,
        "sql_total_ms": diagnostic["sql_total_ms"],
        "query_attribution": query_attribution,
        "query_role_totals": _query_role_totals(query_attribution),
        "slowest_queries": [
            {
                "elapsed_ms": round(row.elapsed_ms, 3),
                "query_shape": _query_shape(row.sql),
                "sql": row.sql,
            }
            for row in queries[:5]
        ],
    }
    return payload


def _query_role_totals(attribution: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in attribution:
        key = (item["owner"], item["role"], item["kind"])
        row = grouped.setdefault(
            key,
            {
                "owner": item["owner"],
                "role": item["role"],
                "kind": item["kind"],
                "count": 0,
                "sql_total_ms": 0.0,
            },
        )
        row["count"] += item["count"]
        row["sql_total_ms"] += item["sql_total_ms"]
    return [
        {**row, "sql_total_ms": round(row["sql_total_ms"], 3)}
        for row in sorted(
            grouped.values(),
            key=lambda item: (-item["sql_total_ms"], item["owner"], item["role"]),
        )
    ]


def _query_attribution(queries: list[QueryDiagnostic]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for query in queries:
        kind = _query_kind(query.sql)
        owner, role = _query_owner_and_role(query.sql, kind=kind)
        shape = _query_shape(query.sql)
        key = (owner, role, kind, shape)
        row = grouped.setdefault(
            key,
            {
                "owner": owner,
                "role": role,
                "kind": kind,
                "query_shape": shape,
                "count": 0,
                "sql_total_ms": 0.0,
            },
        )
        row["count"] += 1
        row["sql_total_ms"] += query.elapsed_ms
    return [
        {
            **row,
            "sql_total_ms": round(row["sql_total_ms"], 3),
        }
        for row in sorted(
            grouped.values(),
            key=lambda item: (-item["sql_total_ms"], item["owner"], item["role"]),
        )
    ]


def _query_owner_and_role(sql: str, *, kind: str) -> tuple[str, str]:
    normalized = " ".join(sql.lower().split())
    if kind == "control":
        return "django_transaction", "transaction_control"
    if "action_plans_actionplanexecutionlifecycleevent" in normalized:
        return "action_plans.lifecycle_events", "lifecycle_events"
    if "notifications_notification" in normalized:
        return "notifications.scheduling", "notifications"
    if "gamification_" in normalized:
        return "gamification.services", "gamification"
    if "action_plans_actionplanschedule" in normalized:
        if "action_plans_actionplanscheduleassignee" in normalized:
            return "action_plans.materialization", "schedule_assignees"
        if kind == "write":
            return "action_plans.materialization", "freshness_write"
        return "action_plans.materialization", "candidate_discovery_freshness"
    if "action_plans_actionplantask" in normalized:
        return "action_plans.materialization", "action_plan_tasks"
    if "action_plans_actionplanexecutionteam" in normalized:
        return "action_plans.materialization", "execution_structure"
    if "action_plans_actionplanassignee" in normalized:
        return "action_plans.materialization", "execution_assignees"
    if "action_plans_actionplanexecutiontask" in normalized:
        return "action_plans.materialization", "execution_tasks"
    if "action_plans_actionplanexecution" in normalized:
        if "for update" in normalized:
            return "action_plans.lifecycle_promotion", "locks_idempotence"
        if kind == "write":
            if normalized.startswith("insert"):
                return "action_plans.materialization", "execution_write"
            if 'set "availability_notified_at"' in normalized:
                return "notifications.scheduling", "availability_write"
            if 'set "status"' in normalized and '"started_at"' in normalized:
                return "action_plans.lifecycle_promotion", "promotion_write"
            return "action_plans.execution", "business_writes"
        if '"availability_notified_at" is null' in normalized:
            return "action_plans.lifecycle_promotion", "availability_candidates"
        if '"start_at" <=' in normalized and '"status" =' in normalized:
            return "action_plans.lifecycle_promotion", "promotion_candidates"
        if (
            '"occurrence_date" =' in normalized
            and '"action_plan_schedule_id" =' in normalized
        ):
            return "action_plans.materialization", "existence_idempotence"
        return "action_plans.execution_feed", "feed_read"
    if "action_plans_actionplan" in normalized:
        return "action_plans.materialization", "action_plan_load"
    if "establishments_" in normalized:
        return "establishments", "membership_scope"
    return "execution_feed_dependencies", "supporting_read"


def _explain_slowest_selects(queries, *, limit):
    explanations = []
    seen_sql = set()
    for query in queries:
        if not query.sql.lstrip().upper().startswith("SELECT") or query.sql in seen_sql:
            continue
        seen_sql.add(query.sql)
        with connection.cursor() as cursor:
            started_at = time.perf_counter()
            cursor.execute(
                f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query.sql}",
                query.params,
            )
            plan = cursor.fetchone()[0]
        explanations.append(
            {
                "source_query_ms": round(query.elapsed_ms, 3),
                "query_shape": _query_shape(query.sql),
                "explain_wall_ms": round((time.perf_counter() - started_at) * 1000, 3),
                "sql": query.sql,
                "plan": plan,
                "summary": _explain_summary(plan),
            }
        )
        if len(explanations) >= limit:
            break
    return explanations


def _explain_summary(plan) -> dict[str, Any]:
    payload = plan[0] if isinstance(plan, list) else plan
    root = payload["Plan"]
    return {
        "planning_ms": round(payload.get("Planning Time", 0.0), 3),
        "executor_ms": round(payload.get("Execution Time", 0.0), 3),
        "rows": root.get("Actual Rows", 0),
        "shared_hit_blocks": root.get("Shared Hit Blocks", 0),
        "shared_read_blocks": root.get("Shared Read Blocks", 0),
        "shared_dirtied_blocks": root.get("Shared Dirtied Blocks", 0),
        "shared_written_blocks": root.get("Shared Written Blocks", 0),
        "temp_read_blocks": root.get("Temp Read Blocks", 0),
        "temp_written_blocks": root.get("Temp Written Blocks", 0),
    }


def _query_shape(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]


def _query_kind(sql: str) -> str:
    tokens = sql.lstrip().upper().split()
    if not tokens:
        return "control"
    if tokens[0] in {"INSERT", "UPDATE", "DELETE"}:
        return "write"
    if tokens[0] == "WITH" and any(
        token in {"INSERT", "UPDATE", "DELETE"} for token in tokens
    ):
        return "write"
    if tokens[0] in {"SELECT", "WITH"}:
        return "select"
    return "control"


def _inventory(dataset):
    organization_id = dataset.organization_id
    signals = Signal.objects.filter(establishment__organization_id=organization_id)
    executions = ActionPlanExecution.objects.filter(
        establishment__organization_id=organization_id
    )
    return {
        "organization_id": str(organization_id),
        "temporal_anchor": dataset.seeded_at,
        "establishments": len(dataset.establishment_ids),
        "memberships": len(dataset.membership_ids),
        "signals_total": signals.count(),
        "signals_by_status": {
            status: signals.filter(status=status).count()
            for status in Signal.Status.values
        },
        "signal_pins": signals.filter(is_pinned=True).count(),
        "signal_source_observations": SignalSourceObservation.objects.filter(
            signal__establishment__organization_id=organization_id
        ).count(),
        "signal_history_undated": signals.filter(
            Q(status=Signal.Status.RESOLVED, resolved_at__isnull=True)
            | Q(status=Signal.Status.CANCELED, canceled_at__isnull=True)
        ).count(),
        "executions_total": executions.count(),
        "executions_by_status": {
            status: executions.filter(status=status).count()
            for status in ActionPlanExecution.Status.values
        },
        "execution_pins": ActionPlanExecutionFeedPin.objects.filter(
            membership_id__in=dataset.membership_ids
        ).count(),
        "execution_assignees": ActionPlanAssignee.objects.filter(
            action_plan_execution__establishment__organization_id=organization_id
        ).count(),
        "execution_tasks": ActionPlanExecutionTask.objects.filter(
            action_plan_execution__establishment__organization_id=organization_id
        ).count(),
        "execution_history_undated": executions.filter(
            Q(status=EXECUTION_STATUS_DONE, validated_at__isnull=True)
            | Q(status=EXECUTION_STATUS_CANCELED, canceled_at__isnull=True)
        ).count(),
    }


def _environment_payload():
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version")
        postgres_version = cursor.fetchone()[0]
        cursor.execute("SHOW shared_buffers")
        shared_buffers = cursor.fetchone()[0]
        cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        database_size = cursor.fetchone()[0]
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "postgres_version": postgres_version,
        "postgres_shared_buffers": shared_buffers,
        "database_size": database_size,
        "django_debug": settings.DEBUG,
    }


def _delete_feed_baseline_dataset() -> None:
    organizations = Organization.objects.filter(name__startswith=FEED_BASELINE_NAMESPACE)
    organization_ids = list(organizations.values_list("id", flat=True))
    Notification.objects.filter(
        establishment__organization_id__in=organization_ids
    ).delete()
    execution_ids = ActionPlanExecution.objects.filter(
        establishment__organization_id__in=organization_ids
    ).values_list("id", flat=True)
    ActionPlanExecutionFeedPin.objects.filter(
        action_plan_execution_id__in=execution_ids
    ).delete()
    ActionPlanExecution.objects.filter(
        establishment__organization_id__in=organization_ids
    ).delete()
    ActionPlan.objects.filter(establishment__organization_id__in=organization_ids).delete()
    Signal.objects.filter(establishment__organization_id__in=organization_ids).delete()
    Observation.objects.filter(establishment__organization_id__in=organization_ids).delete()
    organizations.delete()
    User.objects.filter(username__startswith="feed_baseline_").delete()


def _baseline_uuid(seed: int, profile: str, kind: str, index: int) -> uuid.UUID:
    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"spore-feed-baseline:{seed}:{profile}:{kind}:{index}",
    )


def _baseline_run_uuid(
    seed: int,
    profile: str,
    kind: str,
    index: int,
    *,
    anchor: str,
) -> uuid.UUID:
    return uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"spore-feed-baseline:{seed}:{profile}:{anchor}:{kind}:{index}",
    )


def _percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction
