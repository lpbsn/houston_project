from __future__ import annotations

import json
import math
import platform
import resource
import statistics
import time
import tracemalloc
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from houston.accounts.authentication import AccessTokenAuthContext
from houston.accounts.models import AccessToken, User, UserSession
from houston.analytics.api.views import (
    AnalyticsDashboardView,
    AnalyticsPatternDetailView,
    AnalyticsPatternFilterOptionsView,
    AnalyticsPatternListView,
    AnalyticsPatternSignalsView,
)
from houston.analytics.labels import normalize_pattern_label
from houston.analytics.models import OperationalPattern, SignalPatternAssignment
from houston.analytics.pattern_shortlist import (
    DUPLICATE_GUARD_SHORTLIST_STRATEGY,
    _duplicate_guard_shortlist,
)
from houston.core.dev_guards import assert_local_dev_environment
from houston.establishments.models import (
    BusinessUnit,
    CatalogBusinessUnit,
    Establishment,
    EstablishmentMembership,
)
from houston.organizations.models import Organization
from houston.signals.models import Signal

ANALYTICS_CAPACITY_SCHEMA_VERSION = "analytics_capacity_eval_v1"
ANALYTICS_CAPACITY_ARCHIVE_DIR = Path(".artifacts/analytics-capacity-eval")
ANALYTICS_CAPACITY_NAMESPACE = "T35 Analytics Capacity"
DEFAULT_SEED = 35
DEFAULT_EXPLAIN_MIN_MS = 25.0
DEFAULT_EXPLAIN_LIMIT = 2


@dataclass(frozen=True)
class CapacityProfile:
    name: str
    establishments: int
    signals: int
    patterns: int
    shortlist_cardinalities: tuple[int, ...]
    warmups: int
    timing_iterations: int


CAPACITY_PROFILES = {
    "smoke": CapacityProfile(
        name="smoke",
        establishments=3,
        signals=3_000,
        patterns=100,
        shortlist_cardinalities=(10, 100),
        warmups=1,
        timing_iterations=5,
    ),
    "intermediate": CapacityProfile(
        name="intermediate",
        establishments=25,
        signals=100_000,
        patterns=1_000,
        shortlist_cardinalities=(100, 1_000, 5_000),
        warmups=1,
        timing_iterations=7,
    ),
    "target": CapacityProfile(
        name="target",
        establishments=100,
        signals=1_000_000,
        patterns=5_000,
        shortlist_cardinalities=(100, 1_000, 5_000, 10_000),
        warmups=1,
        timing_iterations=10,
    ),
}


@dataclass(frozen=True)
class CapacityDataset:
    profile: str
    seed: int
    organization_id: uuid.UUID
    user_id: uuid.UUID
    establishment_ids: tuple[uuid.UUID, ...]
    business_unit_ids: tuple[uuid.UUID, ...]
    pattern_ids: tuple[uuid.UUID, ...]
    hot_pattern_id: uuid.UUID
    signal_count: int
    assignment_count: int
    shortlist_cases: tuple[tuple[int, uuid.UUID, uuid.UUID], ...]


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


def resolve_capacity_profile(
    profile_name: str,
    *,
    establishments: int | None = None,
    signals: int | None = None,
    patterns: int | None = None,
    warmups: int | None = None,
    timing_iterations: int | None = None,
) -> CapacityProfile:
    try:
        profile = CAPACITY_PROFILES[profile_name]
    except KeyError as exc:
        raise ValueError(f"Unknown capacity profile: {profile_name}") from exc
    resolved = CapacityProfile(
        name=profile.name,
        establishments=establishments if establishments is not None else profile.establishments,
        signals=signals if signals is not None else profile.signals,
        patterns=patterns if patterns is not None else profile.patterns,
        shortlist_cardinalities=profile.shortlist_cardinalities,
        warmups=warmups if warmups is not None else profile.warmups,
        timing_iterations=(
            timing_iterations
            if timing_iterations is not None
            else profile.timing_iterations
        ),
    )
    _validate_profile(resolved)
    return resolved


def seed_analytics_capacity_dataset(
    profile: CapacityProfile,
    *,
    seed: int = DEFAULT_SEED,
    include_shortlist_cases: bool = True,
) -> CapacityDataset:
    assert_local_dev_environment()
    _delete_capacity_dataset(profile, seed=seed)
    now = timezone.now().replace(microsecond=0)
    catalog_business_unit, _ = CatalogBusinessUnit.objects.get_or_create(
        key="analytics-capacity",
        defaults={
            "label": "Analytics capacity",
            "description": "Synthetic T35 capacity dataset",
            "sort_order": 32_000,
        },
    )
    organization = Organization.objects.create(
        id=_capacity_uuid(seed, f"organization-{profile.name}", 0),
        name=_capacity_name(profile.name, seed),
        status=Organization.Status.ACTIVE,
    )
    user = User.objects.create_user(
        id=_capacity_uuid(seed, f"user-{profile.name}", 0),
        username=f"analytics_capacity_{profile.name}_{seed}",
        email=f"analytics-capacity-{profile.name}-{seed}@example.invalid",
        password=None,
        status=User.Status.ACTIVE,
    )
    establishments = [
        Establishment(
            id=_capacity_uuid(seed, f"establishment-{profile.name}", index),
            organization=organization,
            name=f"Capacity establishment {index:03d}",
            status=Establishment.Status.ACTIVE,
            timezone=("Europe/Paris" if index % 3 == 0 else "UTC"),
        )
        for index in range(profile.establishments)
    ]
    Establishment.objects.bulk_create(establishments, batch_size=1_000)
    memberships = [
        EstablishmentMembership(
            id=_capacity_uuid(seed, f"membership-{profile.name}", index),
            user=user,
            establishment=establishment,
            role=EstablishmentMembership.Role.OWNER,
            status=EstablishmentMembership.Status.ACTIVE,
        )
        for index, establishment in enumerate(establishments)
    ]
    EstablishmentMembership.objects.bulk_create(memberships, batch_size=1_000)
    session = UserSession.objects.create(
        id=_capacity_uuid(seed, f"session-{profile.name}", 0),
        user=user,
        selected_establishment=establishments[0],
        status=UserSession.Status.ACTIVE,
        refresh_token_family_id=_capacity_uuid(
            seed,
            f"refresh-family-{profile.name}",
            0,
        ),
        refresh_expires_at=now + timedelta(days=30),
        absolute_expires_at=now + timedelta(days=30),
    )
    AccessToken.objects.create(
        id=_capacity_uuid(seed, f"access-token-{profile.name}", 0),
        session=session,
        token_digest=_capacity_uuid(
            seed,
            f"access-token-digest-{profile.name}",
            0,
        ).hex,
        expires_at=now + timedelta(days=30),
    )
    business_units = []
    for establishment_index, establishment in enumerate(establishments):
        for unit_index in range(2):
            row_index = establishment_index * 2 + unit_index
            business_units.append(
                BusinessUnit(
                    id=_capacity_uuid(
                        seed,
                        f"business-unit-{profile.name}",
                        row_index,
                    ),
                    establishment=establishment,
                    catalog_business_unit=catalog_business_unit,
                    source=BusinessUnit.Source.MANUAL,
                    active=True,
                    specific_name=f"Capacity unit {unit_index + 1}",
                    normalized_specific_name=f"capacity unit {unit_index + 1}",
                    routing_key=f"capacity-unit-{unit_index + 1}",
                )
            )
    BusinessUnit.objects.bulk_create(business_units, batch_size=1_000)
    patterns = [
        OperationalPattern(
            id=_capacity_uuid(seed, f"pattern-{profile.name}", index),
            organization=organization,
            label=_pattern_label(index),
            normalized_label=normalize_pattern_label(_pattern_label(index)),
            semantic_label=_pattern_label(index),
            normalized_semantic_label=normalize_pattern_label(_pattern_label(index)),
            status=OperationalPattern.Status.ACTIVE,
            created_by_membership=memberships[index % len(memberships)],
        )
        for index in range(profile.patterns)
    ]
    OperationalPattern.objects.bulk_create(patterns, batch_size=5_000)

    assignment_count = _copy_capacity_signals_and_assignments(
        profile=profile,
        seed=seed,
        now=now,
        establishments=establishments,
        business_units=business_units,
        patterns=patterns,
    )
    shortlist_cases = (
        _seed_shortlist_cases(
            profile.shortlist_cardinalities,
            profile_name=profile.name,
            seed=seed,
            now=now,
        )
        if include_shortlist_cases
        else ()
    )
    return CapacityDataset(
        profile=profile.name,
        seed=seed,
        organization_id=organization.id,
        user_id=user.id,
        establishment_ids=tuple(row.id for row in establishments),
        business_unit_ids=tuple(row.id for row in business_units),
        pattern_ids=tuple(row.id for row in patterns),
        hot_pattern_id=patterns[0].id,
        signal_count=profile.signals,
        assignment_count=assignment_count,
        shortlist_cases=shortlist_cases,
    )


def load_analytics_capacity_dataset(
    profile: CapacityProfile,
    *,
    seed: int = DEFAULT_SEED,
) -> CapacityDataset:
    organization = Organization.objects.get(name=_capacity_name(profile.name, seed))
    user = User.objects.get(username=f"analytics_capacity_{profile.name}_{seed}")
    establishment_ids = tuple(
        Establishment.objects.filter(organization=organization)
        .order_by("name")
        .values_list("id", flat=True)
    )
    business_unit_ids = tuple(
        BusinessUnit.objects.filter(establishment_id__in=establishment_ids)
        .order_by("establishment_id", "routing_key")
        .values_list("id", flat=True)
    )
    pattern_ids = tuple(
        OperationalPattern.objects.filter(organization=organization)
        .order_by("created_at", "id")
        .values_list("id", flat=True)
    )
    shortlist_cases = []
    for cardinality in profile.shortlist_cardinalities:
        shortlist_organization = Organization.objects.get(
            name=_shortlist_organization_name(profile.name, seed, cardinality)
        )
        shortlist_signal = Signal.objects.get(
            establishment__organization=shortlist_organization
        )
        shortlist_cases.append(
            (cardinality, shortlist_organization.id, shortlist_signal.id)
        )
    return CapacityDataset(
        profile=profile.name,
        seed=seed,
        organization_id=organization.id,
        user_id=user.id,
        establishment_ids=establishment_ids,
        business_unit_ids=business_unit_ids,
        pattern_ids=pattern_ids,
        hot_pattern_id=pattern_ids[0],
        signal_count=Signal.objects.filter(establishment__organization=organization).count(),
        assignment_count=SignalPatternAssignment.objects.filter(
            signal__establishment__organization=organization
        ).count(),
        shortlist_cases=tuple(shortlist_cases),
    )


def benchmark_analytics_capacity(
    dataset: CapacityDataset,
    profile: CapacityProfile,
    *,
    explain: bool = True,
    explain_min_ms: float = DEFAULT_EXPLAIN_MIN_MS,
    explain_limit: int = DEFAULT_EXPLAIN_LIMIT,
) -> dict[str, Any]:
    user = User.objects.get(pk=dataset.user_id)
    scenarios = _build_read_scenarios(dataset=dataset, user=user)
    scenario_reports = []
    for name, request_callable in scenarios:
        timing = _run_timing(
            request_callable,
            warmups=profile.warmups,
            iterations=profile.timing_iterations,
        )
        diagnostic = _run_query_diagnostic(request_callable)
        memory = _run_memory_diagnostic(request_callable)
        explanations = (
            _explain_slowest_selects(
                diagnostic["queries"],
                min_elapsed_ms=explain_min_ms,
                limit=explain_limit,
            )
            if explain
            else []
        )
        scenario_reports.append(
            {
                "name": name,
                "timing": timing,
                "diagnostic": {
                    key: value
                    for key, value in diagnostic.items()
                    if key != "queries"
                },
                "memory": memory,
                "explains": explanations,
            }
        )
    shortlist_reports = [
        _benchmark_shortlist_case(cardinality, signal_id)
        for cardinality, _organization_id, signal_id in dataset.shortlist_cases
    ]
    return {
        "schema_version": ANALYTICS_CAPACITY_SCHEMA_VERSION,
        "generated_at": timezone.now().isoformat(),
        "environment": _environment_payload(),
        "configuration": {
            "profile": asdict(profile),
            "seed": dataset.seed,
            "timing_isolated_from_diagnostics": True,
            "shortlist_strategy": DUPLICATE_GUARD_SHORTLIST_STRATEGY,
            "shortlist_min_score": (
                settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MIN_SCORE
            ),
            "shortlist_max_candidates": (
                settings.HOUSTON_ANALYTICS_PATTERN_DUPLICATE_GUARD_MAX_CANDIDATES
            ),
        },
        "dataset": {
            "organization_id": str(dataset.organization_id),
            "establishments": len(dataset.establishment_ids),
            "business_units": len(dataset.business_unit_ids),
            "patterns": len(dataset.pattern_ids),
            "signals": dataset.signal_count,
            "assignments": dataset.assignment_count,
        },
        "read_scenarios": scenario_reports,
        "token_overlap_v1": shortlist_reports,
    }


def write_analytics_capacity_archive(
    report: dict[str, Any],
    *,
    archive_dir: Path | None = None,
    filename: str | None = None,
) -> Path:
    target_dir = archive_dir or ANALYTICS_CAPACITY_ARCHIVE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    profile = report["configuration"]["profile"]["name"]
    target_name = filename or (
        f"analytics-capacity-{profile}-{timezone.now():%Y%m%d%H%M%S}.json"
    )
    path = target_dir / target_name
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return path


def format_analytics_capacity_report(report: dict[str, Any]) -> str:
    dataset = report["dataset"]
    lines = [
        f"Analytics capacity profile: {report['configuration']['profile']['name']}",
        (
            "Dataset: "
            f"{dataset['establishments']} establishments, "
            f"{dataset['patterns']} patterns, {dataset['signals']} signals"
        ),
        "Read scenarios:",
    ]
    for scenario in report["read_scenarios"]:
        timing = scenario["timing"]
        diagnostic = scenario["diagnostic"]
        lines.append(
            f"  {scenario['name']}: p50={timing['p50_ms']:.1f}ms "
            f"p95={timing['p95_ms']:.1f}ms queries={diagnostic['query_count']} "
            f"sql={diagnostic['sql_total_ms']:.1f}ms"
        )
    lines.append("token_overlap_v1:")
    for row in report["token_overlap_v1"]:
        lines.append(
            f"  {row['cardinality']} patterns: p50={row['timing']['p50_ms']:.1f}ms "
            f"p95={row['timing']['p95_ms']:.1f}ms "
            f"peak={row['memory']['python_peak_bytes']} bytes"
        )
    return "\n".join(lines)


def _copy_capacity_signals_and_assignments(
    *,
    profile: CapacityProfile,
    seed: int,
    now,
    establishments: list[Establishment],
    business_units: list[BusinessUnit],
    patterns: list[OperationalPattern],
) -> int:
    signal_columns = (
        "id",
        "establishment_id",
        "affected_business_unit_id",
        "responsible_business_unit_id",
        "activity_subject_id",
        "operational_unit_id",
        "status",
        "routing_status",
        "expected_action",
        "is_pinned",
        "pinned_at",
        "pinned_by_membership_id",
        "title",
        "structured_summary",
        "location_text",
        "issue_focus",
        "merged_into_id",
        "last_activity_at",
        "marked_interesting_by_membership_id",
        "marked_interesting_at",
        "resolved_by_membership_id",
        "resolved_at",
        "resolution_origin",
        "canceled_by_membership_id",
        "canceled_at",
        "archived_by_membership_id",
        "archived_at",
        "created_at",
        "updated_at",
    )
    assignment_columns = (
        "id",
        "signal_id",
        "pattern_id",
        "classification_status",
        "assigned_signature",
        "assigned_classifier_version",
        "assigned_at",
        "pending_signature",
        "pending_classifier_version",
        "attempt_count",
        "last_error_code",
        "last_attempted_at",
        "next_retry_at",
        "assignment_source",
        "owner_correction_signature",
        "created_at",
        "updated_at",
    )
    status_cycle = (
        Signal.Status.OPEN,
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.IN_PROGRESS,
        Signal.Status.INTERESTING,
        Signal.Status.RESOLVED,
        Signal.Status.RESOLVED,
        Signal.Status.RESOLVED,
        Signal.Status.ARCHIVED,
        Signal.Status.CANCELED,
    )
    assignment_count = 0
    with transaction.atomic(), connection.cursor() as cursor:
        signal_copy_sql = _copy_sql(Signal._meta.db_table, signal_columns)
        assignment_copy_sql = _copy_sql(
            SignalPatternAssignment._meta.db_table,
            assignment_columns,
        )
        with cursor.copy(signal_copy_sql) as copy:
            for index in range(profile.signals):
                signal_id = _capacity_uuid(seed, f"signal-{profile.name}", index)
                establishment_index = index % profile.establishments
                establishment = establishments[establishment_index]
                responsible_unit = (
                    None
                    if index % 5 == 0
                    else business_units[establishment_index * 2 + (index % 2)].id
                )
                created_at = (
                    now - timedelta(seconds=index + 1)
                    if index < len(patterns)
                    else _synthetic_created_at(now, index=index, seed=seed)
                )
                status = status_cycle[index % len(status_cycle)]
                resolved_at = (
                    created_at + timedelta(hours=2 + index % 96)
                    if status == Signal.Status.RESOLVED
                    else None
                )
                pattern_index = _assigned_pattern_index(index, len(patterns))
                copy.write_row(
                    (
                        signal_id,
                        establishment.id,
                        responsible_unit,
                        responsible_unit,
                        None,
                        None,
                        status,
                        Signal.RoutingStatus.RESOLVED,
                        None,
                        False,
                        None,
                        None,
                        f"{_pattern_label(pattern_index)} signal {index}",
                        f"Synthetic analytics capacity summary for pattern {pattern_index}.",
                        f"Zone {index % 50}",
                        f"capacity-focus-{pattern_index}-{index}",
                        None,
                        created_at,
                        None,
                        None,
                        None,
                        resolved_at,
                        (
                            Signal.ResolutionOrigin.MANUAL
                            if resolved_at is not None
                            else None
                        ),
                        None,
                        None,
                        None,
                        None,
                        created_at,
                        created_at,
                    )
                )
        with cursor.copy(assignment_copy_sql) as copy:
            for index in range(profile.signals):
                if index >= len(patterns) and index % 20 == 0:
                    continue
                signal_id = _capacity_uuid(seed, f"signal-{profile.name}", index)
                pattern_index = _assigned_pattern_index(index, len(patterns))
                assigned_at = (
                    now - timedelta(seconds=index + 1)
                    if index < len(patterns)
                    else _synthetic_created_at(now, index=index, seed=seed)
                )
                copy.write_row(
                    (
                        _capacity_uuid(seed, f"assignment-{profile.name}", index),
                        signal_id,
                        patterns[pattern_index].id,
                        SignalPatternAssignment.ClassificationStatus.SUCCEEDED,
                        f"capacity-{index:012d}",
                        "analytics-pattern-v2.1",
                        assigned_at,
                        "",
                        "",
                        1,
                        "",
                        assigned_at,
                        None,
                        SignalPatternAssignment.AssignmentSource.CLASSIFIER,
                        "",
                        assigned_at,
                        assigned_at,
                    )
                )
                assignment_count += 1
    return assignment_count


def _seed_shortlist_cases(
    cardinalities: Iterable[int],
    *,
    profile_name: str,
    seed: int,
    now,
) -> tuple[tuple[int, uuid.UUID, uuid.UUID], ...]:
    cases = []
    for case_index, cardinality in enumerate(cardinalities):
        organization = Organization.objects.create(
            id=_capacity_uuid(
                seed,
                f"shortlist-organization-{profile_name}",
                case_index,
            ),
            name=_shortlist_organization_name(profile_name, seed, cardinality),
            status=Organization.Status.ACTIVE,
        )
        establishment = Establishment.objects.create(
            id=_capacity_uuid(
                seed,
                f"shortlist-establishment-{profile_name}",
                case_index,
            ),
            organization=organization,
            name=f"Shortlist {cardinality}",
            status=Establishment.Status.ACTIVE,
            timezone="UTC",
        )
        patterns = [
            OperationalPattern(
                id=_capacity_uuid(
                    seed + case_index,
                    f"shortlist-pattern-{profile_name}",
                    pattern_index,
                ),
                organization=organization,
                label=(
                    "Climate equipment outage"
                    if pattern_index == 0
                    else f"Decoy inventory sector {pattern_index:06d}"
                ),
                normalized_label=normalize_pattern_label(
                    "Climate equipment outage"
                    if pattern_index == 0
                    else f"Decoy inventory sector {pattern_index:06d}"
                ),
                semantic_label=(
                    "Climate equipment outage"
                    if pattern_index == 0
                    else f"Decoy inventory sector {pattern_index:06d}"
                ),
                normalized_semantic_label=normalize_pattern_label(
                    "Climate equipment outage"
                    if pattern_index == 0
                    else f"Decoy inventory sector {pattern_index:06d}"
                ),
                status=OperationalPattern.Status.ACTIVE,
            )
            for pattern_index in range(cardinality)
        ]
        OperationalPattern.objects.bulk_create(patterns, batch_size=5_000)
        signal = Signal.objects.create(
            id=_capacity_uuid(
                seed,
                f"shortlist-signal-{profile_name}",
                case_index,
            ),
            establishment=establishment,
            status=Signal.Status.OPEN,
            routing_status=Signal.RoutingStatus.RESOLVED,
            title="Climate equipment offline",
            structured_summary="Climate equipment outage in guest area.",
            issue_focus="climate-equipment-outage",
            last_activity_at=now,
        )
        cases.append((cardinality, organization.id, signal.id))
    return tuple(cases)


def _build_read_scenarios(
    *,
    dataset: CapacityDataset,
    user: User,
) -> list[tuple[str, Callable[[], Any]]]:
    factory = APIRequestFactory()
    now = timezone.now().replace(microsecond=0)
    access_token = AccessToken.objects.select_related("session").get(
        session__user=user,
        revoked_at__isnull=True,
    )
    auth_context = AccessTokenAuthContext(
        session=access_token.session,
        access_token=access_token,
    )

    def view_request(view_class, path, query, **view_kwargs):
        def invoke():
            request = factory.get(path, data=query)
            force_authenticate(request, user=user, token=auth_context)
            response = view_class.as_view()(request, **view_kwargs)
            response.render()
            if response.status_code != 200:
                raise RuntimeError(
                    f"{path} returned {response.status_code}: {response.data}"
                )
            return response

        return invoke

    scenarios: list[tuple[str, Callable[[], Any]]] = []
    for days in (7, 30, 90):
        query = _period_query(now=now, days=days, organization_id=dataset.organization_id)
        scenarios.append(
            (
                f"dashboard_{days}d",
                view_request(AnalyticsDashboardView, "/api/v1/analytics/dashboard/", query),
            )
        )
        scenarios.append(
            (
                f"patterns_{days}d_page1",
                view_request(AnalyticsPatternListView, "/api/v1/analytics/patterns/", query),
            )
        )

    query_30 = _period_query(now=now, days=30, organization_id=dataset.organization_id)
    list_page1 = view_request(
        AnalyticsPatternListView,
        "/api/v1/analytics/patterns/",
        query_30,
    )()
    list_cursor = list_page1.data.get("next_cursor")
    if list_cursor:
        scenarios.append(
            (
                "patterns_30d_page2",
                view_request(
                    AnalyticsPatternListView,
                    "/api/v1/analytics/patterns/",
                    {**query_30, "cursor": list_cursor},
                ),
            )
        )
    scenarios.extend(
        [
            (
                "patterns_30d_recurrent",
                view_request(
                    AnalyticsPatternListView,
                    "/api/v1/analytics/patterns/",
                    {**query_30, "recurrence": "recurrent"},
                ),
            ),
            (
                "patterns_30d_filtered",
                view_request(
                    AnalyticsPatternListView,
                    "/api/v1/analytics/patterns/",
                    {
                        **query_30,
                        "signal_statuses": "open,in_progress",
                        "responsible_business_unit_ids": str(
                            dataset.business_unit_ids[0]
                        ),
                    },
                ),
            ),
            (
                "patterns_30d_search",
                view_request(
                    AnalyticsPatternListView,
                    "/api/v1/analytics/patterns/",
                    {**query_30, "q": "phenomenon 0000"},
                ),
            ),
            (
                "pattern_filter_options",
                view_request(
                    AnalyticsPatternFilterOptionsView,
                    "/api/v1/analytics/pattern-filter-options/",
                    {"organization_id": str(dataset.organization_id)},
                ),
            ),
            (
                "pattern_detail_30d",
                view_request(
                    AnalyticsPatternDetailView,
                    f"/api/v1/analytics/patterns/{dataset.hot_pattern_id}/",
                    query_30,
                    pattern_id=dataset.hot_pattern_id,
                ),
            ),
        ]
    )
    query_90 = _period_query(now=now, days=90, organization_id=dataset.organization_id)
    scenarios.append(
        (
            "pattern_detail_90d",
            view_request(
                AnalyticsPatternDetailView,
                f"/api/v1/analytics/patterns/{dataset.hot_pattern_id}/",
                query_90,
                pattern_id=dataset.hot_pattern_id,
            ),
        )
    )
    drilldown_page1 = view_request(
        AnalyticsPatternSignalsView,
        f"/api/v1/analytics/patterns/{dataset.hot_pattern_id}/signals/",
        query_30,
        pattern_id=dataset.hot_pattern_id,
    )
    page1_response = drilldown_page1()
    scenarios.append(("pattern_drilldown_30d_page1", drilldown_page1))
    drilldown_cursor = page1_response.data.get("next_cursor")
    if drilldown_cursor:
        scenarios.append(
            (
                "pattern_drilldown_30d_page2",
                view_request(
                    AnalyticsPatternSignalsView,
                    f"/api/v1/analytics/patterns/{dataset.hot_pattern_id}/signals/",
                    {**query_30, "cursor": drilldown_cursor},
                    pattern_id=dataset.hot_pattern_id,
                ),
            )
        )
    return scenarios


def _run_timing(
    operation: Callable[[], Any],
    *,
    warmups: int,
    iterations: int,
) -> dict[str, Any]:
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


def _run_query_diagnostic(operation: Callable[[], Any]) -> dict[str, Any]:
    recorder = _QueryRecorder()
    started_at = time.perf_counter()
    with connection.execute_wrapper(recorder):
        operation()
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    queries = sorted(recorder.queries, key=lambda row: row.elapsed_ms, reverse=True)
    return {
        "mode": "instrumented_single_run",
        "wall_ms": round(elapsed_ms, 3),
        "query_count": len(queries),
        "sql_total_ms": round(sum(row.elapsed_ms for row in queries), 3),
        "slowest_query_ms": round(queries[0].elapsed_ms, 3) if queries else 0.0,
        "queries": queries,
        "slowest_queries": [
            {
                "elapsed_ms": round(row.elapsed_ms, 3),
                "sql": row.sql,
            }
            for row in queries[:5]
        ],
    }


def _run_memory_diagnostic(operation: Callable[[], Any]) -> dict[str, Any]:
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    tracemalloc.start()
    operation()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return {
        "mode": "instrumented_single_run",
        "python_peak_bytes": peak,
        "process_max_rss_before": rss_before,
        "process_max_rss_after": rss_after,
        "process_max_rss_unit": "bytes" if platform.system() == "Darwin" else "kilobytes",
    }


def _explain_slowest_selects(
    queries: list[QueryDiagnostic],
    *,
    min_elapsed_ms: float,
    limit: int,
) -> list[dict[str, Any]]:
    explanations = []
    seen_sql = set()
    for query in queries:
        normalized = query.sql.lstrip().upper()
        if (
            query.elapsed_ms < min_elapsed_ms
            or not normalized.startswith("SELECT")
            or query.sql in seen_sql
        ):
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
                "explain_wall_ms": round((time.perf_counter() - started_at) * 1000, 3),
                "sql": query.sql,
                "plan": plan,
            }
        )
        if len(explanations) >= limit:
            break
    return explanations


def _benchmark_shortlist_case(cardinality: int, signal_id: uuid.UUID) -> dict[str, Any]:
    signal = Signal.objects.select_related(
        "establishment",
        "establishment__organization",
        "activity_subject",
        "operational_unit",
    ).get(pk=signal_id)

    def operation():
        return _duplicate_guard_shortlist(
            signal=signal,
            canonical_label="Climate equipment outage",
        )

    timing = _run_timing(operation, warmups=1, iterations=10)
    diagnostic = _run_query_diagnostic(operation)
    memory = _run_memory_diagnostic(operation)
    result = operation()
    return {
        "cardinality": cardinality,
        "metrics": result.metrics,
        "target_found": bool(result and result[0].semantic_label == "Climate equipment outage"),
        "timing": timing,
        "diagnostic": {
            key: value for key, value in diagnostic.items() if key != "queries"
        },
        "memory": memory,
    }


def _environment_payload() -> dict[str, Any]:
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


def _delete_capacity_dataset(profile: CapacityProfile, *, seed: int) -> None:
    del profile, seed
    organizations = Organization.objects.filter(
        name__startswith=ANALYTICS_CAPACITY_NAMESPACE
    )
    organization_ids = list(organizations.values_list("id", flat=True))
    SignalPatternAssignment.objects.filter(
        signal__establishment__organization_id__in=organization_ids
    ).delete()
    Signal.objects.filter(establishment__organization_id__in=organization_ids).delete()
    OperationalPattern.objects.filter(organization_id__in=organization_ids).delete()
    organizations.delete()
    User.objects.filter(username__startswith="analytics_capacity_").delete()


def _validate_profile(profile: CapacityProfile) -> None:
    for field_name in ("establishments", "signals", "patterns"):
        if getattr(profile, field_name) < 1:
            raise ValueError(f"{field_name} must be greater than zero")
    if profile.warmups < 0:
        raise ValueError("warmups must be zero or greater")
    if profile.timing_iterations < 2:
        raise ValueError("timing_iterations must be at least two")


def _capacity_name(profile_name: str, seed: int) -> str:
    return f"{ANALYTICS_CAPACITY_NAMESPACE} {profile_name} seed {seed}"


def _shortlist_organization_name(
    profile_name: str,
    seed: int,
    cardinality: int,
) -> str:
    return (
        f"{ANALYTICS_CAPACITY_NAMESPACE} shortlist {profile_name} "
        f"{cardinality} seed {seed}"
    )


def _capacity_uuid(seed: int, kind: str, index: int) -> uuid.UUID:
    namespace = uuid.uuid5(uuid.NAMESPACE_URL, f"houston-capacity:{seed}:{kind}")
    return uuid.UUID(int=((namespace.int >> 40) << 40) | index)


def _pattern_label(index: int) -> str:
    equipment = ("climate", "water", "linen", "lighting", "security")[index % 5]
    phenomenon = ("outage", "leak", "shortage", "delay", "failure")[(index // 5) % 5]
    return f"Phenomenon {index:05d} {equipment} {phenomenon}"


def _skewed_pattern_index(signal_index: int, pattern_count: int) -> int:
    uniform = ((signal_index * 2_654_435_761) % 1_000_003) / 1_000_003
    return min(int((uniform**2) * pattern_count), pattern_count - 1)


def _assigned_pattern_index(signal_index: int, pattern_count: int) -> int:
    if signal_index < pattern_count:
        return signal_index
    return _skewed_pattern_index(signal_index, pattern_count)


def _synthetic_created_at(now, *, index: int, seed: int):
    age_seconds = (index * 2_654_435_761 + seed) % (730 * 24 * 60 * 60)
    return now - timedelta(seconds=age_seconds)


def _copy_sql(table: str, columns: Iterable[str]) -> str:
    quoted_table = connection.ops.quote_name(table)
    quoted_columns = ", ".join(connection.ops.quote_name(column) for column in columns)
    return f"COPY {quoted_table} ({quoted_columns}) FROM STDIN"


def _period_query(*, now, days: int, organization_id: uuid.UUID) -> dict[str, str]:
    return {
        "period_start": (now - timedelta(days=days)).isoformat(),
        "period_end": now.isoformat(),
        "organization_id": str(organization_id),
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    rank = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[rank]
