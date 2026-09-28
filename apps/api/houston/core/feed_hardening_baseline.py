from __future__ import annotations

import hashlib
import json
import platform
import statistics
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import time as datetime_time
from datetime import timedelta
from pathlib import Path
from typing import Any
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
from houston.action_plans.models import (
    ActionPlan,
    ActionPlanAssignee,
    ActionPlanExecution,
    ActionPlanExecutionFeedPin,
    ActionPlanExecutionTask,
    ActionPlanExecutionTeam,
    ActionPlanSchedule,
    ActionPlanScheduleAssignee,
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

FEED_BASELINE_SCHEMA_VERSION = "feed_hardening_baseline_v2"
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
        establishments=establishments or base.establishments,
        signals_per_establishment=(
            signals_per_establishment or base.signals_per_establishment
        ),
        executions_per_establishment=(
            executions_per_establishment or base.executions_per_establishment
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
    memberships = list(
        EstablishmentMembership.objects.filter(id__in=dataset.membership_ids)
        .select_related("establishment", "user")
        .order_by("establishment_id")
    )
    primary = memberships[0]
    filters = SignalFeedFilters()

    _prepare_execution_read_catch_up_fixture(dataset=dataset, membership=primary)
    read_catch_up_diagnostic = _run_query_diagnostic(
        _operation_execution_establishment(primary)
    )
    pre_warm_execution = _operation_execution_establishment(primary)
    pre_warm_diagnostic = _run_query_diagnostic(pre_warm_execution)
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
        "execution_read_catch_up": _diagnostic_payload(read_catch_up_diagnostic),
        "pre_warm_execution_read_path": _diagnostic_payload(pre_warm_diagnostic),
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
        "Scenarios:",
    ]
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


def _diagnostic_payload(diagnostic):
    queries = diagnostic["queries"]
    query_kinds = [_query_kind(row.sql) for row in queries]
    select_count = query_kinds.count("select")
    write_count = query_kinds.count("write")
    payload = {
        "mode": "instrumented_single_run",
        "wall_ms": diagnostic["wall_ms"],
        "query_count": diagnostic["query_count"],
        "select_query_count": select_count,
        "write_query_count": write_count,
        "control_query_count": diagnostic["query_count"] - select_count - write_count,
        "sql_total_ms": diagnostic["sql_total_ms"],
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
            }
        )
        if len(explanations) >= limit:
            break
    return explanations


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
    Notification.objects.filter(
        establishment__organization_id__in=organization_ids
    ).delete()
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
