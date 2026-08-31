from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator
from unittest.mock import patch
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from houston.action_plans.constants import (
    EXECUTION_LIFECYCLE_EVENT_CANCELED,
    EXECUTION_LIFECYCLE_EVENT_MARKED_DONE,
    EXECUTION_LIFECYCLE_EVENT_STARTED,
    EXECUTION_LIFECYCLE_EVENT_VALIDATED,
)
from houston.action_plans.exceptions import ActionPlanServiceError
from houston.action_plans.lifecycle_promotion import promote_due_scheduled_executions
from houston.action_plans.models import ActionPlanExecution, ActionPlanExecutionLifecycleEvent
from houston.action_plans.permissions import can_create_linked_action_plan
from houston.action_plans.services import (
    cancel_action_plan_execution,
    create_action_plan_with_execution,
    mark_action_plan_execution_done,
    validate_action_plan_execution,
)
from houston.ai.observation_pipeline import FakeObservationPipelineProvider
from houston.ai.observation_pipeline_schema import (
    ObservationPipelineOutput,
    PipelineCandidateOutput,
)
from houston.analytics.classifier import FakePatternClassifierProvider
from houston.analytics.labels import normalize_pattern_label
from houston.analytics.models import SignalPatternAssignment
from houston.analytics.services import (
    PatternClassificationRetryableError,
    classify_signal_pattern,
)
from houston.core.dev_guards import assert_local_dev_environment
from houston.establishments.konoha_dataset_actors import (
    ESTABLISHMENT_AKATSUKI,
    ESTABLISHMENT_ANBU,
    NARUTO_EMAIL,
)
from houston.establishments.konoha_dataset_observations import (
    AUTHOR_DIRECTORY,
    OCCURRED_AT_MAX,
    PARIS_TZ,
    SIGNAL_GROUP_COUNT_RANGES,
    load_konoha_dataset_observations,
    validate_konoha_dataset_observations,
)
from houston.establishments.models import (
    ActivitySubject,
    BusinessUnit,
    Establishment,
    EstablishmentMembership,
    MembershipScope,
)
from houston.gamification.models import BadgeAward, GamificationSeason, PointTransaction
from houston.gamification.selectors import month_bounds_for_occurred_at
from houston.observations.models import Observation, ObservationProcessing
from houston.observations.services import submit_observation
from houston.signals.constants import (
    AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
    SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN,
    SIGNAL_RESOLUTION_ORIGIN_MANUAL,
    SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST,
)
from houston.signals.models import CandidateSignal, Signal, SignalResolutionRequest
from houston.signals.resolution_request_services import (
    approve_signal_resolution_request,
    create_signal_resolution_request,
    reject_signal_resolution_request,
)
from houston.signals.services import (
    mark_signal_interesting,
    normalize_issue_focus,
    qualify_signal_routing,
    resolve_signal,
    run_observation_pipeline,
)

KONOHA_ESTABLISHMENT_NAMES = (ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI)

EVENT_SUBMIT = "submit"
EVENT_QUALIFY = "qualify"
EVENT_RR_CREATE = "rr_create"
EVENT_RR_APPROVE = "rr_approve"
EVENT_RR_REJECT = "rr_reject"
EVENT_MARK_INTERESTING = "mark_interesting"
EVENT_PLAN_CREATE = "plan_create"
EVENT_PLAN_PROMOTE = "plan_promote"
EVENT_PLAN_MARK_DONE = "plan_mark_done"
EVENT_PLAN_VALIDATE = "plan_validate"
EVENT_PLAN_CANCEL = "plan_cancel"
EVENT_RESOLVE = "resolve"
EVENT_SORT = {
    EVENT_SUBMIT: 0,
    EVENT_QUALIFY: 1,
    EVENT_RR_CREATE: 2,
    EVENT_RR_APPROVE: 3,
    EVENT_RR_REJECT: 3,
    EVENT_MARK_INTERESTING: 4,
    EVENT_PLAN_CREATE: 5,
    EVENT_PLAN_PROMOTE: 6,
    EVENT_PLAN_MARK_DONE: 7,
    EVENT_PLAN_VALIDATE: 8,
    EVENT_PLAN_CANCEL: 9,
    EVENT_RESOLVE: 10,
}


class KonohaDatasetReplayError(Exception):
    def __init__(self, messages: tuple[str, ...] | list[str]):
        self.messages = tuple(messages)
        super().__init__("; ".join(self.messages))


@dataclass(frozen=True)
class ReplayEvent:
    kind: str
    at: datetime
    corpus_id: str
    signal_group: str
    pattern_group: str
    row: dict[str, Any] | None = None
    plan: Any = None
    workflow: dict[str, Any] | None = None


@dataclass(frozen=True)
class ReplayRuntime:
    establishments: dict[str, Establishment]
    poles: dict[tuple[str, str], BusinessUnit]
    memberships: dict[tuple[str, str], EstablishmentMembership]
    owners: dict[str, EstablishmentMembership]
    pole_members: dict[tuple[str, str], tuple[EstablishmentMembership, ...]] = field(
        default_factory=dict
    )


@dataclass
class ReplayResult:
    dry_run: bool
    resume: bool
    submitted: int = 0
    skipped: int = 0
    resolved: int = 0
    classified: int = 0
    plans_created: int = 0
    plans_promoted: int = 0
    plans_marked_done: int = 0
    plans_validated: int = 0
    plans_canceled: int = 0
    qualified: int = 0
    marked_interesting: int = 0
    rr_created: int = 0
    rr_approved: int = 0
    rr_rejected: int = 0
    events: tuple[ReplayEvent, ...] = ()
    signal_ids_by_group: dict[str, UUID] = field(default_factory=dict)
    pattern_ids_by_group: dict[str, UUID] = field(default_factory=dict)
    execution_ids_by_group: dict[str, UUID] = field(default_factory=dict)
    pattern_labels: dict[str, str] = field(default_factory=dict)


def freeze_django_now(at: datetime):
    if at.tzinfo is None:
        raise KonohaDatasetReplayError(["clock instant must be timezone-aware"])
    instant = at.astimezone(PARIS_TZ)
    if instant > OCCURRED_AT_MAX:
        raise KonohaDatasetReplayError(
            [f"refusing clock instant after cut-off: {instant.isoformat()}"]
        )

    def _now() -> datetime:
        return instant

    return patch("django.utils.timezone.now", _now)


@contextmanager
def _suppress_replay_side_effects() -> Iterator[None]:
    def _noop_delay(*_args: Any, **_kwargs: Any) -> None:
        return None

    def _noop_notification(*_args: Any, **_kwargs: Any) -> None:
        return None

    with ExitStack() as stack:
        stack.enter_context(
            patch("houston.signals.tasks.process_observation_task.delay", _noop_delay)
        )
        stack.enter_context(
            patch(
                "houston.analytics.tasks.classify_signal_pattern_task.delay",
                _noop_delay,
            )
        )
        stack.enter_context(
            patch(
                "houston.notifications.scheduling._run_notification_after_commit",
                _noop_notification,
            )
        )
        yield


def parse_corpus_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise KonohaDatasetReplayError([f"naive datetime is not allowed: {value}"])
    return parsed.astimezone(PARIS_TZ)


def build_replay_events(
    observations: list[dict[str, Any]],
    *,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> list[ReplayEvent]:
    from houston.establishments.konoha_dataset_action_cycles import (
        extend_replay_events_with_cycles,
    )

    events: list[ReplayEvent] = []
    for row in observations:
        occurred_at = parse_corpus_datetime(row["occurred_at"])
        events.append(
            ReplayEvent(
                kind=EVENT_SUBMIT,
                at=occurred_at,
                corpus_id=row["id"],
                signal_group=row["signal_group"],
                pattern_group=row["pattern_group"],
                row=row,
            )
        )
    extend_replay_events_with_cycles(events, observations, overrides=overrides)
    from houston.establishments.konoha_dataset_workflows import (
        extend_replay_events_with_workflows,
    )

    extend_replay_events_with_workflows(events, observations)
    events.sort(key=lambda event: (event.at, _event_sort(event.kind), event.corpus_id))
    return events


def _event_sort(kind: str) -> int:
    try:
        return EVENT_SORT[kind]
    except KeyError as exc:
        raise KonohaDatasetReplayError([f"unknown replay event kind {kind}"]) from exc


def pattern_canonical_label(pattern_group: str) -> str:
    return pattern_group.strip()


def _human_pattern_label_from_row(row: dict[str, Any]) -> str:
    candidate = row.get("candidate") if isinstance(row.get("candidate"), dict) else {}
    focus = str(candidate.get("issue_focus") or "").strip()
    title = str(candidate.get("title") or "").strip()
    return focus or title or pattern_canonical_label(str(row.get("pattern_group") or ""))


def _pattern_labels_by_group(observations: list[dict[str, Any]]) -> dict[str, str]:
    first_row: dict[str, dict[str, Any]] = {}
    for row in observations:
        group = row["pattern_group"]
        current = first_row.get(group)
        if current is None:
            first_row[group] = row
            continue
        current_at = parse_corpus_datetime(current["occurred_at"])
        row_at = parse_corpus_datetime(row["occurred_at"])
        if row_at < current_at or (row_at == current_at and row["id"] < current["id"]):
            first_row[group] = row
    labels: dict[str, str] = {}
    used: set[str] = set()
    ordered = sorted(
        first_row.items(),
        key=lambda item: (
            parse_corpus_datetime(item[1]["occurred_at"]),
            item[1]["id"],
        ),
    )
    for group, row in ordered:
        base = _human_pattern_label_from_row(row)
        label = base
        key = normalize_pattern_label(label)
        if key in used:
            label = f"{base} · {group.rsplit('.', 1)[-1]}"
            key = normalize_pattern_label(label)
        if key in used:
            label = f"{base} · {group}"
            key = normalize_pattern_label(label)
        used.add(key)
        labels[group] = label
    return labels


def _pattern_label_attempts(pattern_group: str, result: ReplayResult) -> tuple[str, ...]:
    base = (result.pattern_labels.get(pattern_group) or "").strip()
    if not base:
        base = pattern_canonical_label(pattern_group)
    tail = pattern_group.rsplit(".", 1)[-1]
    attempts: list[str] = []
    for label in (base, f"{base} · {tail}", f"{base} · {pattern_group}"):
        if label not in attempts:
            attempts.append(label)
    return tuple(attempts)


def load_replay_runtime() -> ReplayRuntime:
    establishments = {
        establishment.name: establishment
        for establishment in Establishment.objects.filter(
            name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
            status=Establishment.Status.ACTIVE,
        )
    }
    poles: dict[tuple[str, str], BusinessUnit] = {}
    for establishment in establishments.values():
        for pole in BusinessUnit.objects.filter(establishment=establishment, active=True):
            poles[(establishment.name, pole.specific_name)] = pole

    memberships: dict[tuple[str, str], EstablishmentMembership] = {}
    owners: dict[str, EstablishmentMembership] = {}
    active = EstablishmentMembership.objects.filter(
        establishment__name__in=establishments,
        status=EstablishmentMembership.Status.ACTIVE,
    ).select_related("user", "establishment")
    for membership in active:
        email = membership.user.email.lower()
        memberships[(membership.establishment.name, email)] = membership
        if (
            membership.role == EstablishmentMembership.Role.OWNER
            and email == NARUTO_EMAIL.lower()
        ):
            owners[membership.establishment.name] = membership
    pole_members: dict[tuple[str, str], list[EstablishmentMembership]] = {}
    scopes = MembershipScope.objects.filter(
        membership__status=EstablishmentMembership.Status.ACTIVE,
        membership__establishment__name__in=establishments,
        business_unit__active=True,
    ).select_related("membership__user", "membership__establishment", "business_unit")
    for scope in scopes:
        key = (scope.membership.establishment.name, scope.business_unit.specific_name)
        pole_members.setdefault(key, []).append(scope.membership)
    return ReplayRuntime(
        establishments=establishments,
        poles=poles,
        memberships=memberships,
        owners=owners,
        pole_members={
            key: tuple(sorted(values, key=lambda item: item.user.email.lower()))
            for key, values in pole_members.items()
        },
    )


def remap_candidate_to_pipeline_output(
    candidate: dict[str, Any],
    *,
    establishment_name: str,
    runtime: ReplayRuntime,
) -> ObservationPipelineOutput:
    affected_pole = candidate["affected_pole_specific_name"]
    responsible_pole = candidate["responsible_pole_specific_name"]
    affected = runtime.poles.get((establishment_name, affected_pole))
    responsible = runtime.poles.get((establishment_name, responsible_pole))
    if affected is None:
        raise KonohaDatasetReplayError(
            [f"missing affected pole {establishment_name}/{affected_pole}"]
        )
    if responsible is None:
        raise KonohaDatasetReplayError(
            [f"missing responsible pole {establishment_name}/{responsible_pole}"]
        )
    subject_key = candidate.get("activity_subject_catalog_key")
    subject_routing_key = None
    if subject_key:
        subject = ActivitySubject.objects.filter(
            business_unit=responsible,
            routing_key=subject_key,
            active=True,
        ).first()
        if subject is None:
            raise KonohaDatasetReplayError(
                [f"missing subject {subject_key} on {establishment_name}/{responsible_pole}"]
            )
        subject_routing_key = subject.routing_key
    mapped = PipelineCandidateOutput(
        title=candidate["title"],
        structured_summary=candidate["structured_summary"],
        issue_focus=candidate["issue_focus"],
        canonical_object=candidate["canonical_object"],
        signal_kind=candidate["signal_kind"],
        expected_action=candidate["expected_action"],
        information_type=candidate["information_type"],
        affected_business_unit_routing_key=affected.routing_key,
        responsible_business_unit_routing_key=responsible.routing_key,
        activity_subject_routing_key=subject_routing_key,
        operational_unit_key=None,
        location_text=candidate["location_text"],
    )
    return ObservationPipelineOutput(
        schema_version=AI_OBSERVATION_PIPELINE_SCHEMA_VERSION,
        candidates=[mapped],
    )


def preflight_konoha_dataset_replay(
    observations: list[dict[str, Any]],
    *,
    runtime: ReplayRuntime | None = None,
    resume: bool = False,
    dry_run: bool = False,
) -> list[str]:
    errors: list[str] = []
    loaded = runtime or load_replay_runtime()
    for name in (ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI):
        if name not in loaded.establishments:
            errors.append(f"missing active establishment {name}")
        if name not in loaded.owners:
            errors.append(f"missing owner membership for {name}")

    needed_poles = {
        (row["establishment"], row["candidate"]["affected_pole_specific_name"])
        for row in observations
    } | {
        (row["establishment"], row["candidate"]["responsible_pole_specific_name"])
        for row in observations
    } | {(row["establishment"], row["origin_pole_specific_name"]) for row in observations}
    for key in sorted(needed_poles):
        if key not in loaded.poles:
            errors.append(f"missing pole {key[0]}/{key[1]}")

    for row in observations:
        email = row["author_email"].lower()
        if email not in AUTHOR_DIRECTORY:
            errors.append(f"{row['id']}: author not in AUTHOR_DIRECTORY")
            continue
        membership_key = (row["establishment"], email)
        if membership_key not in loaded.memberships:
            errors.append(f"{row['id']}: missing membership for {email}")
        establishment_name = row["establishment"]
        candidate = row["candidate"]
        responsible = loaded.poles.get(
            (establishment_name, candidate["responsible_pole_specific_name"])
        )
        if responsible is None:
            continue
        subject_key = candidate["activity_subject_catalog_key"]
        if not ActivitySubject.objects.filter(
            business_unit=responsible,
            routing_key=subject_key,
            active=True,
        ).exists():
            errors.append(
                f"{row['id']}: missing subject {subject_key} on "
                f"{establishment_name}/{candidate['responsible_pole_specific_name']}"
            )

    seen_groups: set[str] = set()
    for row in observations:
        group = row["signal_group"]
        if group in seen_groups:
            continue
        seen_groups.add(group)
        if row["cycle"].get("resolution") != "linked_plan":
            continue
        pole = row["candidate"]["responsible_pole_specific_name"]
        members = loaded.pole_members.get((row["establishment"], pole), ())
        if not any(
            membership.role == EstablishmentMembership.Role.MANAGER for membership in members
        ):
            errors.append(f"{group}: missing manager on responsible pole {pole}")
        if not any(
            membership.role == EstablishmentMembership.Role.STAFF for membership in members
        ):
            errors.append(f"{group}: missing staff on responsible pole {pole}")

    if not resume and not dry_run:
        existing = Observation.objects.filter(
            establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI)
        ).exists()
        if existing:
            errors.append(
                "KONOHA observations already exist; clean operational data or use --resume"
            )
    from houston.establishments.konoha_dataset_workflows import (
        assert_kakashi_director,
        kakashi_required_for_workflows,
    )

    if kakashi_required_for_workflows(
        signal_groups={row["signal_group"] for row in observations}
    ):
        errors.extend(assert_kakashi_director(loaded))
    return errors


def _konoha_establishment_qs():
    return Establishment.objects.filter(name__in=KONOHA_ESTABLISHMENT_NAMES)


@transaction.atomic
def _wipe_konoha_gamification_state() -> None:
    establishment_ids = list(_konoha_establishment_qs().values_list("id", flat=True))
    PointTransaction.objects.filter(
        establishment_id__in=establishment_ids,
        reversed_transaction_id__isnull=False,
    ).delete()
    PointTransaction.objects.filter(establishment_id__in=establishment_ids).delete()
    BadgeAward.objects.filter(establishment_id__in=establishment_ids).delete()
    GamificationSeason.objects.filter(establishment_id__in=establishment_ids).delete()


def _same_instant(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return False
    return left.astimezone(PARIS_TZ) == right.astimezone(PARIS_TZ)


def _same_optional_instant(left: datetime | None, right: datetime | None) -> bool:
    if left is None and right is None:
        return True
    return _same_instant(left, right)


def _workflow_spec(event: ReplayEvent) -> dict[str, Any]:
    return event.workflow or {}


def _membership_email(membership: EstablishmentMembership | None) -> str | None:
    if membership is None or membership.user is None:
        return None
    return membership.user.email.lower()


def _resolution_request_for_group(
    event: ReplayEvent, result: ReplayResult
) -> SignalResolutionRequest | None:
    signal_id = result.signal_ids_by_group.get(event.signal_group)
    if signal_id is None:
        return None
    return (
        SignalResolutionRequest.objects.filter(signal_id=signal_id)
        .select_related("requested_by_membership__user", "reviewed_by_membership__user")
        .order_by("requested_at")
        .first()
    )


_QUALIFY_AUDIT_DIMENSIONS = (
    "affected",
    "responsible",
    "subject",
    "operational_unit",
)


def _qualify_pole_for_candidate(
    *,
    establishment_name: str,
    specific_name: str | None,
    catalog_key: str | None,
    runtime: ReplayRuntime,
) -> BusinessUnit | None:
    if not specific_name:
        return None
    pole = runtime.poles.get((establishment_name, specific_name))
    if pole is None or pole.specific_name != specific_name:
        return None
    pole_catalog = (
        pole.catalog_business_unit.key if pole.catalog_business_unit_id else None
    )
    if pole_catalog != catalog_key:
        return None
    return pole


def _qualify_candidate_snapshot(
    candidate: dict[str, Any],
    *,
    establishment_name: str,
    runtime: ReplayRuntime,
) -> tuple[Any, ...] | None:
    affected_name = candidate.get("affected_pole_specific_name")
    responsible_name = candidate.get("responsible_pole_specific_name")
    affected_catalog = candidate.get("affected_catalog_bu_key")
    responsible_catalog = candidate.get("responsible_catalog_bu_key")
    if affected_name or affected_catalog:
        affected = _qualify_pole_for_candidate(
            establishment_name=establishment_name,
            specific_name=affected_name,
            catalog_key=affected_catalog,
            runtime=runtime,
        )
        if affected is None:
            return None
        affected_key = affected.routing_key
    else:
        affected_key = None
    if responsible_name or responsible_catalog:
        responsible = _qualify_pole_for_candidate(
            establishment_name=establishment_name,
            specific_name=responsible_name,
            catalog_key=responsible_catalog,
            runtime=runtime,
        )
        if responsible is None:
            return None
        responsible_key = responsible.routing_key
    else:
        responsible_key = None
        responsible = None
    subject_key = candidate.get("activity_subject_catalog_key")
    if subject_key:
        if responsible is None:
            return None
        subject = ActivitySubject.objects.filter(
            business_unit=responsible,
            routing_key=subject_key,
            active=True,
        ).first()
        if subject is None:
            return None
        subject_routing_key = subject.routing_key
    else:
        subject_routing_key = None
    operational_key = candidate.get("operational_unit_key") or None
    return (
        affected_key,
        responsible_key,
        subject_routing_key,
        operational_key,
        normalize_issue_focus(candidate.get("issue_focus")),
        candidate.get("expected_action") or None,
    )


def _qualify_routing_snapshot(
    *,
    affected: BusinessUnit | None,
    responsible: BusinessUnit | None,
    subject: ActivitySubject | None,
    operational,
    issue_focus: str | None,
    expected_action: str | None,
) -> tuple[Any, ...]:
    return (
        affected.routing_key if affected is not None else None,
        responsible.routing_key if responsible is not None else None,
        subject.routing_key if subject is not None else None,
        operational.key if operational is not None else None,
        normalize_issue_focus(issue_focus),
        expected_action or None,
    )


def _qualify_live_snapshot(signal: Signal) -> tuple[Any, ...]:
    return _qualify_routing_snapshot(
        affected=signal.affected_business_unit,
        responsible=signal.responsible_business_unit,
        subject=signal.activity_subject,
        operational=signal.operational_unit,
        issue_focus=signal.issue_focus,
        expected_action=signal.expected_action,
    )


def _qualify_persisted_initial_snapshot(signal: Signal) -> tuple[Any, ...] | None:
    row = (
        CandidateSignal.objects.filter(result_signal=signal)
        .select_related(
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
            "operational_unit",
        )
        .order_by("created_at")
        .first()
    )
    if row is None:
        return None
    return _qualify_routing_snapshot(
        affected=row.affected_business_unit,
        responsible=row.responsible_business_unit,
        subject=row.activity_subject,
        operational=row.operational_unit,
        issue_focus=row.issue_focus,
        expected_action=row.expected_action,
    )


def _qualify_live_dimension_keys(signal: Signal) -> dict[str, str | None]:
    affected = signal.affected_business_unit
    responsible = signal.responsible_business_unit
    subject = signal.activity_subject
    operational = signal.operational_unit
    return {
        "affected": affected.routing_key if affected is not None else None,
        "responsible": responsible.routing_key if responsible is not None else None,
        "subject": subject.routing_key if subject is not None else None,
        "operational_unit": operational.key if operational is not None else None,
    }


def _manual_qualification_audit_matches_live(signal: Signal) -> bool:
    live_keys = _qualify_live_dimension_keys(signal)
    for row in CandidateSignal.objects.filter(result_signal=signal):
        events = (row.resolution_audit or {}).get("qualification_events") or []
        for envelope in events:
            if not isinstance(envelope, dict):
                continue
            if envelope.get("source") != "manual_qualification":
                continue
            nested = envelope.get("resolution_audit")
            if not isinstance(nested, dict):
                continue
            if all(
                isinstance(nested.get(dimension), dict)
                and nested[dimension].get("resolved_key") == live_keys[dimension]
                for dimension in _QUALIFY_AUDIT_DIMENSIONS
            ):
                return True
    return False


def _workflow_event_fingerprint(
    event: ReplayEvent, *, runtime: ReplayRuntime, result: ReplayResult
) -> str | None:
    if event.kind == EVENT_QUALIFY:
        signal_id = result.signal_ids_by_group.get(event.signal_group)
        if signal_id is None:
            return FINGERPRINT_MISSING
        if event.row is None:
            return FINGERPRINT_CONFLICT
        signal = Signal.objects.select_related(
            "affected_business_unit",
            "responsible_business_unit",
            "activity_subject",
            "operational_unit",
        ).get(pk=signal_id)
        establishment_name = event.row["establishment"]
        live = _qualify_live_snapshot(signal)
        initial_snapshot = _qualify_persisted_initial_snapshot(signal)
        if initial_snapshot is not None and live == initial_snapshot:
            return FINGERPRINT_MISSING
        final_snapshot = _qualify_candidate_snapshot(
            event.row["candidate"],
            establishment_name=establishment_name,
            runtime=runtime,
        )
        if (
            final_snapshot is not None
            and live == final_snapshot
            and _manual_qualification_audit_matches_live(signal)
        ):
            return FINGERPRINT_MATCH
        return FINGERPRINT_CONFLICT
    if event.kind == EVENT_MARK_INTERESTING:
        signal_id = result.signal_ids_by_group.get(event.signal_group)
        if signal_id is None:
            return FINGERPRINT_MISSING
        signal = Signal.objects.get(pk=signal_id)
        if signal.status != Signal.Status.INTERESTING:
            return FINGERPRINT_MISSING
        if _same_instant(signal.marked_interesting_at, event.at):
            return FINGERPRINT_MATCH
        return FINGERPRINT_CONFLICT
    if event.kind == EVENT_RR_CREATE:
        request = _resolution_request_for_group(event, result)
        if request is None:
            return FINGERPRINT_MISSING
        requester = (_workflow_spec(event).get("resolution_request") or {}).get(
            "requester_email"
        )
        if (
            _same_instant(request.requested_at, event.at)
            and _membership_email(request.requested_by_membership) == str(requester).lower()
        ):
            return FINGERPRINT_MATCH
        return FINGERPRINT_CONFLICT
    if event.kind == EVENT_RR_APPROVE:
        request = _resolution_request_for_group(event, result)
        signal_id = result.signal_ids_by_group.get(event.signal_group)
        if request is None or signal_id is None:
            return FINGERPRINT_MISSING
        signal = Signal.objects.get(pk=signal_id)
        reviewer = (_workflow_spec(event).get("resolution_request") or {}).get(
            "reviewer_email"
        )
        if request.status != SignalResolutionRequest.Status.APPROVED:
            return FINGERPRINT_MISSING
        if (
            _same_instant(request.reviewed_at, event.at)
            and _membership_email(request.reviewed_by_membership) == str(reviewer).lower()
            and signal.status == Signal.Status.RESOLVED
            and signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST
        ):
            return FINGERPRINT_MATCH
        return FINGERPRINT_CONFLICT
    if event.kind == EVENT_RR_REJECT:
        request = _resolution_request_for_group(event, result)
        signal_id = result.signal_ids_by_group.get(event.signal_group)
        if request is None or signal_id is None:
            return FINGERPRINT_MISSING
        if request.status == SignalResolutionRequest.Status.PENDING:
            return FINGERPRINT_MISSING
        signal = Signal.objects.get(pk=signal_id)
        spec = _workflow_spec(event).get("resolution_request") or {}
        requested_at = spec.get("requested_at")
        identity_matches = (
            request.signal_id == signal_id
            and request.status == SignalResolutionRequest.Status.REJECTED
            and _same_instant(request.reviewed_at, event.at)
            and _membership_email(request.reviewed_by_membership)
            == str(spec.get("reviewer_email")).lower()
            and _membership_email(request.requested_by_membership)
            == str(spec.get("requester_email")).lower()
            and isinstance(requested_at, str)
            and _same_instant(request.requested_at, parse_corpus_datetime(requested_at))
        )
        if not identity_matches:
            return FINGERPRINT_CONFLICT
        if signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST:
            return FINGERPRINT_CONFLICT
        return FINGERPRINT_MATCH
    return None


def _execution_for_group(event: ReplayEvent, result: ReplayResult) -> ActionPlanExecution | None:
    execution_id = result.execution_ids_by_group.get(event.signal_group)
    if execution_id is not None:
        return ActionPlanExecution.objects.filter(pk=execution_id).first()
    signal_id = result.signal_ids_by_group.get(event.signal_group)
    if signal_id is None:
        return None
    matches = list(ActionPlanExecution.objects.filter(source_signal_id=signal_id))
    if len(matches) > 1:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: expected at most one linked execution"]
        )
    if not matches:
        return None
    result.execution_ids_by_group[event.signal_group] = matches[0].id
    return matches[0]


def _lifecycle_at(
    execution: ActionPlanExecution, event_type: str, instant: datetime
) -> bool:
    return ActionPlanExecutionLifecycleEvent.objects.filter(
        action_plan_execution=execution,
        event_type=event_type,
        occurred_at=instant,
    ).exists()


FINGERPRINT_MATCH = "match"
FINGERPRINT_MISSING = "missing"
FINGERPRINT_CONFLICT = "conflict"


def _event_fingerprint(
    event: ReplayEvent, *, runtime: ReplayRuntime, result: ReplayResult
) -> str:
    if event.kind == EVENT_SUBMIT:
        if event.row is None:
            return FINGERPRINT_CONFLICT
        existing = _find_existing_observation(event.row, runtime)
        if existing is None:
            return FINGERPRINT_MISSING
        processing = getattr(existing, "processing", None)
        if processing is None or processing.status != ObservationProcessing.Status.PROCESSED:
            return FINGERPRINT_CONFLICT
        return FINGERPRINT_MATCH
    if event.kind == EVENT_RESOLVE:
        signal_id = result.signal_ids_by_group.get(event.signal_group)
        if signal_id is None:
            return FINGERPRINT_MISSING
        signal = Signal.objects.get(pk=signal_id)
        if signal.status != Signal.Status.RESOLVED:
            return FINGERPRINT_MISSING
        if signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST:
            return FINGERPRINT_CONFLICT
        if (
            _same_instant(signal.resolved_at, event.at)
            and signal.resolution_origin == SIGNAL_RESOLUTION_ORIGIN_MANUAL
        ):
            return FINGERPRINT_MATCH
        return FINGERPRINT_CONFLICT
    workflow_state = _workflow_event_fingerprint(event, runtime=runtime, result=result)
    if workflow_state is not None:
        return workflow_state
    execution = _execution_for_group(event, result)
    if event.kind == EVENT_PLAN_CREATE:
        if execution is None:
            return FINGERPRINT_MISSING
        if not _same_instant(execution.created_at, event.at):
            return FINGERPRINT_CONFLICT
        expected_end = getattr(event.plan, "end_at", None)
        if not _same_optional_instant(execution.end_at, expected_end):
            return FINGERPRINT_CONFLICT
        return FINGERPRINT_MATCH
    if execution is None:
        return FINGERPRINT_MISSING
    if event.kind == EVENT_PLAN_PROMOTE:
        if _lifecycle_at(execution, EXECUTION_LIFECYCLE_EVENT_STARTED, event.at):
            if _same_instant(execution.created_at, event.at):
                return FINGERPRINT_CONFLICT
            return FINGERPRINT_MATCH
        advanced = execution.status in {
            ActionPlanExecution.Status.PENDING_VALIDATION,
            ActionPlanExecution.Status.DONE,
            ActionPlanExecution.Status.CANCELED,
        }
        if advanced or (
            execution.status == ActionPlanExecution.Status.IN_PROGRESS
            and not _same_instant(execution.started_at, execution.created_at)
        ):
            return FINGERPRINT_CONFLICT
        return FINGERPRINT_MISSING
    if event.kind == EVENT_PLAN_MARK_DONE:
        if _same_instant(execution.marked_done_at, event.at) or _lifecycle_at(
            execution, EXECUTION_LIFECYCLE_EVENT_MARKED_DONE, event.at
        ):
            if execution.marked_done_at is not None and not _same_instant(
                execution.marked_done_at, event.at
            ):
                return FINGERPRINT_CONFLICT
            return FINGERPRINT_MATCH
        if execution.status in {
            ActionPlanExecution.Status.PENDING_VALIDATION,
            ActionPlanExecution.Status.DONE,
        }:
            return FINGERPRINT_CONFLICT
        if execution.marked_done_at is not None:
            return FINGERPRINT_CONFLICT
        return FINGERPRINT_MISSING
    if event.kind == EVENT_PLAN_VALIDATE:
        if _same_instant(execution.validated_at, event.at) or _lifecycle_at(
            execution, EXECUTION_LIFECYCLE_EVENT_VALIDATED, event.at
        ):
            if execution.validated_at is not None and not _same_instant(
                execution.validated_at, event.at
            ):
                return FINGERPRINT_CONFLICT
            return FINGERPRINT_MATCH
        if execution.status == ActionPlanExecution.Status.DONE:
            return FINGERPRINT_CONFLICT
        if execution.validated_at is not None:
            return FINGERPRINT_CONFLICT
        return FINGERPRINT_MISSING
    if event.kind == EVENT_PLAN_CANCEL:
        if _same_instant(execution.canceled_at, event.at) or _lifecycle_at(
            execution, EXECUTION_LIFECYCLE_EVENT_CANCELED, event.at
        ):
            if execution.canceled_at is not None and not _same_instant(
                execution.canceled_at, event.at
            ):
                return FINGERPRINT_CONFLICT
            return FINGERPRINT_MATCH
        if execution.status == ActionPlanExecution.Status.CANCELED:
            return FINGERPRINT_CONFLICT
        if execution.canceled_at is not None:
            return FINGERPRINT_CONFLICT
        return FINGERPRINT_MISSING
    raise KonohaDatasetReplayError([f"unknown replay event kind {event.kind}"])


def _first_remaining_mutating_event(
    events: tuple[ReplayEvent, ...] | list[ReplayEvent],
    result: ReplayResult,
    runtime: ReplayRuntime,
) -> ReplayEvent | None:
    for event in events:
        if _event_fingerprint(event, runtime=runtime, result=result) != FINGERPRINT_MATCH:
            return event
    return None


def _cutoff_month_starts_at(
    event: ReplayEvent,
    runtime: ReplayRuntime,
) -> datetime:
    if event.row is not None:
        establishment = runtime.establishments[event.row["establishment"]]
    else:
        establishment = next(iter(runtime.establishments.values()))
    starts_at, _ends_at = month_bounds_for_occurred_at(
        establishment=establishment,
        occurred_at=event.at,
    )
    return starts_at


def _assert_resume_konoha_gamification_seasons(
    events: tuple[ReplayEvent, ...] | list[ReplayEvent],
    result: ReplayResult,
    runtime: ReplayRuntime,
) -> None:
    remaining = _first_remaining_mutating_event(events, result, runtime)
    if remaining is None:
        return
    cutoff = _cutoff_month_starts_at(remaining, runtime)
    if GamificationSeason.objects.filter(
        establishment__name__in=KONOHA_ESTABLISHMENT_NAMES,
        starts_at__gt=cutoff,
    ).exists():
        raise KonohaDatasetReplayError(
            [
                "resume blocked: KONOHA gamification seasons exist after the remaining "
                "event month; run operational clean then --confirm"
            ]
        )


def _membership_for_row(
    row: dict[str, Any],
    runtime: ReplayRuntime,
) -> EstablishmentMembership:
    key = (row["establishment"], row["author_email"].lower())
    membership = runtime.memberships.get(key)
    if membership is None:
        raise KonohaDatasetReplayError([f"{row['id']}: missing author membership"])
    return membership


def _find_existing_observation(
    row: dict[str, Any],
    runtime: ReplayRuntime,
) -> Observation | None:
    membership = _membership_for_row(row, runtime)
    occurred_at = parse_corpus_datetime(row["occurred_at"])
    matches = list(
        Observation.objects.filter(
            establishment=runtime.establishments[row["establishment"]],
            submitted_by_membership=membership,
            submitted_at=occurred_at,
            raw_text=row["raw_text"],
        ).select_related("processing")
    )
    if len(matches) > 1:
        raise KonohaDatasetReplayError([f"{row['id']}: duplicate matching observations"])
    return matches[0] if matches else None


def _candidate_for_observation(observation: Observation) -> CandidateSignal:
    candidates = list(observation.candidate_signals.all())
    if len(candidates) != 1:
        raise KonohaDatasetReplayError(
            [f"observation {observation.id} must have exactly one candidate"]
        )
    return candidates[0]


def _record_signal_from_candidate(
    *,
    row: dict[str, Any],
    candidate: CandidateSignal,
    result: ReplayResult,
) -> Signal:
    signal = candidate.result_signal
    if signal is None:
        raise KonohaDatasetReplayError([f"{row['id']}: pipeline produced no signal"])
    group = row["signal_group"]
    relation = row["relation"]
    if relation == "same_signal":
        if candidate.outcome != CandidateSignal.Outcome.AGGREGATED_SIGNAL:
            raise KonohaDatasetReplayError(
                [f"{row['id']}: expected aggregation, got {candidate.outcome}"]
            )
        expected = result.signal_ids_by_group.get(group)
        if expected is not None and expected != signal.id:
            raise KonohaDatasetReplayError(
                [f"{row['id']}: aggregated into unexpected signal"]
            )
        result.signal_ids_by_group[group] = signal.id
        return signal
    if candidate.outcome != CandidateSignal.Outcome.CREATED_SIGNAL:
        raise KonohaDatasetReplayError(
            [f"{row['id']}: expected new signal, got {candidate.outcome}"]
        )
    if group in result.signal_ids_by_group:
        raise KonohaDatasetReplayError(
            [f"{row['id']}: signal_group {group} already bound"]
        )
    result.signal_ids_by_group[group] = signal.id
    return signal


def _classify_new_signal(*, signal: Signal, pattern_group: str, result: ReplayResult) -> None:
    assignment = None
    last_error: Exception | None = None
    for label in _pattern_label_attempts(pattern_group, result):
        try:
            assignment = classify_signal_pattern(
                signal.id,
                provider=FakePatternClassifierProvider(payload={"canonical_label": label}),
                duplicate_guard_enabled=False,
            )
        except PatternClassificationRetryableError as exc:
            last_error = exc
            continue
        break
    if assignment is None or assignment.pattern_id is None:
        detail = f": {last_error}" if last_error is not None else ""
        raise KonohaDatasetReplayError(
            [f"classification failed for signal {signal.id}{detail}"]
        )
    used_ids = {
        pattern_id
        for group, pattern_id in result.pattern_ids_by_group.items()
        if group != pattern_group
    }
    if assignment.pattern_id in used_ids:
        raise KonohaDatasetReplayError(
            [f"pattern divergence for {pattern_group}"]
        )
    existing = result.pattern_ids_by_group.get(pattern_group)
    if existing is not None and existing != assignment.pattern_id:
        raise KonohaDatasetReplayError(
            [f"pattern divergence for {pattern_group}"]
        )
    result.pattern_ids_by_group[pattern_group] = assignment.pattern_id
    result.classified += 1


def _assert_pattern_relation(row: dict[str, Any], signal: Signal, result: ReplayResult) -> None:
    if row["relation"] != "new_signal_same_pattern":
        return
    pattern_group = row["pattern_group"]
    expected = result.pattern_ids_by_group.get(pattern_group)
    assignment = (
        SignalPatternAssignment.objects.filter(signal=signal)
        .select_related("pattern")
        .first()
    )
    if expected is None:
        return
    if assignment is None or assignment.pattern_id != expected:
        raise KonohaDatasetReplayError(
            [f"{row['id']}: expected same OperationalPattern as {pattern_group}"]
        )


def _hydrate_resume_state(
    observations: list[dict[str, Any]],
    runtime: ReplayRuntime,
    result: ReplayResult,
) -> None:
    for row in observations:
        observation = _find_existing_observation(row, runtime)
        if observation is None:
            continue
        processing = getattr(observation, "processing", None)
        if processing is None or processing.status != ObservationProcessing.Status.PROCESSED:
            raise KonohaDatasetReplayError(
                [f"{row['id']}: existing observation is not PROCESSED"]
            )
        candidate = _candidate_for_observation(observation)
        signal = candidate.result_signal
        if signal is None:
            raise KonohaDatasetReplayError([f"{row['id']}: existing observation has no signal"])
        result.signal_ids_by_group[row["signal_group"]] = signal.id
        assignment = SignalPatternAssignment.objects.filter(signal=signal).first()
        if assignment is not None and assignment.pattern_id is not None:
            result.pattern_ids_by_group.setdefault(
                row["pattern_group"],
                assignment.pattern_id,
            )
        execution = (
            ActionPlanExecution.objects.filter(source_signal_id=signal.id)
            .order_by("created_at")
            .first()
        )
        if execution is not None:
            result.execution_ids_by_group[row["signal_group"]] = execution.id


def _submit_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    row = event.row
    if row is None:
        raise KonohaDatasetReplayError(["submit event missing corpus row"])
    existing = _find_existing_observation(row, runtime)
    if existing is not None:
        if not resume:
            raise KonohaDatasetReplayError(
                [f"{row['id']}: observation already exists"]
            )
        if row["signal_group"] not in result.signal_ids_by_group:
            candidate = _candidate_for_observation(existing)
            signal = _record_signal_from_candidate(
                row=row,
                candidate=candidate,
                result=result,
            )
            _assert_pattern_relation(row, signal, result)
        result.skipped += 1
        return

    occurred_at = parse_corpus_datetime(row["occurred_at"])
    membership = _membership_for_row(row, runtime)
    from houston.establishments.konoha_dataset_workflows import workflow_initial_candidate

    pipeline_candidate = workflow_initial_candidate(row["signal_group"]) or row["candidate"]
    output = remap_candidate_to_pipeline_output(
        pipeline_candidate,
        establishment_name=row["establishment"],
        runtime=runtime,
    )
    provider = FakeObservationPipelineProvider(payload=output.model_dump(mode="json"))
    with freeze_django_now(occurred_at):
        observation = submit_observation(
            membership=membership,
            text=row["raw_text"],
            temporary_upload_ids=[],
        )
        run_observation_pipeline(observation.id, provider=provider)
        observation.refresh_from_db()
        if observation.submitted_at != timezone.now():
            raise KonohaDatasetReplayError(
                [f"{row['id']}: submitted_at does not match frozen clock"]
            )
    observation.refresh_from_db()
    processing = observation.processing
    if processing.status != ObservationProcessing.Status.PROCESSED:
        raise KonohaDatasetReplayError(
            [f"{row['id']}: processing status {processing.status}"]
        )
    candidate = _candidate_for_observation(observation)
    created = candidate.outcome == CandidateSignal.Outcome.CREATED_SIGNAL
    signal = _record_signal_from_candidate(
        row=row,
        candidate=candidate,
        result=result,
    )
    if created:
        with freeze_django_now(occurred_at):
            _classify_new_signal(
                signal=signal,
                pattern_group=row["pattern_group"],
                result=result,
            )
        _assert_pattern_relation(row, signal, result)
    result.submitted += 1


def _skip_matching_fingerprint(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> bool:
    state = _event_fingerprint(event, runtime=runtime, result=result)
    if state == FINGERPRINT_MATCH:
        if not resume:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: {event.kind} already applied"]
            )
        result.skipped += 1
        return True
    if state == FINGERPRINT_CONFLICT:
        raise KonohaDatasetReplayError(
            [
                f"{event.signal_group}: {event.kind} fingerprint diverges at "
                f"{event.at.isoformat()}"
            ]
        )
    return False


def _plan_actors(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    signal: Signal,
) -> tuple[EstablishmentMembership, EstablishmentMembership, EstablishmentMembership]:
    if signal.responsible_business_unit is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: linked plan requires a responsible pole"]
        )
    establishment = signal.establishment.name
    pole = signal.responsible_business_unit.specific_name
    members = runtime.pole_members.get((establishment, pole), ())
    managers = [
        membership
        for membership in members
        if membership.role == EstablishmentMembership.Role.MANAGER
    ]
    staff = [
        membership
        for membership in members
        if membership.role == EstablishmentMembership.Role.STAFF
    ]
    spec = event.plan

    def _by_email(email: str | None) -> EstablishmentMembership | None:
        if not email:
            return None
        found = runtime.memberships.get((establishment, email.lower()))
        if found is None:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: missing overlay membership {email}"]
            )
        return found

    creator = _by_email(getattr(spec, "creator_email", None))
    if creator is None:
        for membership in managers:
            if can_create_linked_action_plan(membership, signal=signal):
                creator = membership
                break
    if creator is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: no manager can create a linked action plan"]
        )
    assignee = _by_email(getattr(spec, "assignee_email", None))
    if assignee is None:
        assignee = next((member for member in staff if member.id != creator.id), None)
    if assignee is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: missing staff assignee on {pole}"]
        )
    validator = _by_email(getattr(spec, "validator_email", None))
    if validator is None:
        validator = next((member for member in managers if member.id != creator.id), creator)
    return creator, assignee, validator


def _wrap_plan_writer(event: ReplayEvent, exc: Exception) -> KonohaDatasetReplayError:
    return KonohaDatasetReplayError(
        [f"{event.signal_group}: {event.kind} failed: {exc}"]
    )


def _plan_create_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    signal_id = result.signal_ids_by_group.get(event.signal_group)
    if signal_id is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot create a plan before submit"]
        )
    signal = Signal.objects.select_related(
        "establishment",
        "responsible_business_unit",
        "affected_business_unit",
        "activity_subject",
    ).get(pk=signal_id)
    if signal.status == Signal.Status.IN_PROGRESS:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: signal already in_progress without plan_create fingerprint"]
        )
    creator, assignee, _validator = _plan_actors(event, runtime=runtime, signal=signal)
    spec = event.plan
    row = event.row
    if row is None or spec is None:
        raise KonohaDatasetReplayError([f"{event.signal_group}: plan_create missing spec"])
    candidate = row["candidate"]
    title = candidate["title"][:200]
    task_text = candidate["title"][:500]
    try:
        with freeze_django_now(event.at):
            _plan, execution = create_action_plan_with_execution(
                establishment_id=signal.establishment_id,
                created_by=creator,
                pilot_business_unit_id=signal.responsible_business_unit_id,
                title=title,
                description=candidate.get("expected_action") or "",
                requires_validation=spec.requires_validation,
                tasks=[
                    {
                        "task": task_text,
                        "business_unit_id": signal.responsible_business_unit_id,
                        "position": 1,
                        "description": candidate.get("expected_action") or "",
                        **(
                            {"deadline_at": spec.end_at}
                            if spec.end_at is not None
                            else {}
                        ),
                    }
                ],
                assignees=[
                    {
                        "membership_id": assignee.id,
                        "business_unit_id": signal.responsible_business_unit_id,
                    }
                ],
                source_signal_id=signal.id,
                use_shared_chronology=True,
                start_at=spec.start_at,
                end_at=spec.end_at,
            )
    except ActionPlanServiceError as exc:
        raise _wrap_plan_writer(event, exc) from exc
    if not _same_instant(execution.created_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: execution created_at does not match frozen clock"]
        )
    result.execution_ids_by_group[event.signal_group] = execution.id
    signal.refresh_from_db()
    if signal.status != Signal.Status.IN_PROGRESS:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: linked plan did not move signal to in_progress"]
        )
    result.plans_created += 1


def _plan_promote_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    execution = _execution_for_group(event, result)
    if execution is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot promote before plan_create"]
        )
    try:
        with freeze_django_now(event.at):
            promoted = promote_due_scheduled_executions(
                establishment_id=execution.establishment_id,
                execution_id=execution.id,
            )
    except ActionPlanServiceError as exc:
        raise _wrap_plan_writer(event, exc) from exc
    if promoted < 1:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: plan_promote did not promote the execution"]
        )
    execution.refresh_from_db()
    if execution.status != ActionPlanExecution.Status.IN_PROGRESS:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: execution is not in_progress after promote"]
        )
    if not _same_instant(execution.started_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: started_at does not match plan_promote clock"]
        )
    result.plans_promoted += 1


def _plan_mark_done_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    execution = _execution_for_group(event, result)
    if execution is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot mark done before plan_create"]
        )
    signal = Signal.objects.get(pk=execution.source_signal_id)
    _creator, assignee, _validator = _plan_actors(event, runtime=runtime, signal=signal)
    try:
        with freeze_django_now(event.at):
            updated = mark_action_plan_execution_done(
                execution_id=execution.id,
                actor_membership=assignee,
            )
    except ActionPlanServiceError as exc:
        raise _wrap_plan_writer(event, exc) from exc
    if not _same_instant(updated.marked_done_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: marked_done_at does not match frozen clock"]
        )
    signal.refresh_from_db()
    if updated.requires_validation:
        if updated.status != ActionPlanExecution.Status.PENDING_VALIDATION:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: expected pending_validation after mark_done"]
            )
        if signal.status == Signal.Status.RESOLVED:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: signal resolved before plan_validate"]
            )
    else:
        if updated.status != ActionPlanExecution.Status.DONE:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: execution is not done after mark_done"]
            )
        if signal.status != Signal.Status.RESOLVED:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: signal not resolved after plan_mark_done"]
            )
        if signal.resolution_origin != SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: expected resolution_origin=action_plan"]
            )
        if not _same_instant(signal.resolved_at, event.at):
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: resolved_at does not match plan_mark_done"]
            )
    result.plans_marked_done += 1


def _plan_validate_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    execution = _execution_for_group(event, result)
    if execution is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot validate before plan_create"]
        )
    signal = Signal.objects.get(pk=execution.source_signal_id)
    _creator, _assignee, validator = _plan_actors(event, runtime=runtime, signal=signal)
    try:
        with freeze_django_now(event.at):
            updated = validate_action_plan_execution(
                execution_id=execution.id,
                actor_membership=validator,
                stars=5,
            )
    except ActionPlanServiceError as exc:
        raise _wrap_plan_writer(event, exc) from exc
    if not _same_instant(updated.validated_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: validated_at does not match frozen clock"]
        )
    if updated.status != ActionPlanExecution.Status.DONE:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: execution is not done after validate"]
        )
    signal.refresh_from_db()
    if signal.status != Signal.Status.RESOLVED:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: signal not resolved after plan_validate"]
        )
    if signal.resolution_origin != SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: expected resolution_origin=action_plan"]
        )
    if not _same_instant(signal.resolved_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: resolved_at does not match plan_validate"]
        )
    result.plans_validated += 1


def _plan_cancel_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    execution = _execution_for_group(event, result)
    if execution is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot cancel before plan_create"]
        )
    signal = Signal.objects.get(pk=execution.source_signal_id)
    creator, _assignee, _validator = _plan_actors(event, runtime=runtime, signal=signal)
    try:
        with freeze_django_now(event.at):
            updated = cancel_action_plan_execution(
                execution_id=execution.id,
                actor=creator,
            )
    except ActionPlanServiceError as exc:
        raise _wrap_plan_writer(event, exc) from exc
    if not _same_instant(updated.canceled_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: canceled_at does not match frozen clock"]
        )
    if updated.status != ActionPlanExecution.Status.CANCELED:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: execution is not canceled"]
        )
    signal.refresh_from_db()
    if signal.status != Signal.Status.OPEN:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: canceled execution must leave signal open"]
        )
    result.plans_canceled += 1


def _resolve_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    signal_id = result.signal_ids_by_group.get(event.signal_group)
    if signal_id is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot resolve before submit"]
        )
    signal = Signal.objects.get(pk=signal_id)
    if signal.status == Signal.Status.IN_PROGRESS:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: refusing resolve_signal on in_progress"]
        )
    actor = _resolve_actor(event, runtime=runtime, signal=signal)
    try:
        with freeze_django_now(event.at):
            resolved = resolve_signal(signal=signal, actor_membership=actor)
            if not _same_instant(resolved.resolved_at, timezone.now()):
                raise KonohaDatasetReplayError(
                    [f"{event.signal_group}: resolved_at does not match frozen clock"]
                )
    except KonohaDatasetReplayError:
        raise
    except Exception as exc:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: resolve failed: {exc}"]
        ) from exc
    if resolved.status != Signal.Status.RESOLVED:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: resolve did not reach resolved"]
        )
    if resolved.resolution_origin != SIGNAL_RESOLUTION_ORIGIN_MANUAL:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: expected resolution_origin=manual"]
        )
    result.resolved += 1


def _resolve_actor(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    signal: Signal,
) -> EstablishmentMembership:
    request = (_workflow_spec(event).get("resolution_request") or {})
    email = request.get("resolve_actor_email")
    if email:
        membership = runtime.memberships.get((signal.establishment.name, str(email).lower()))
        if membership is None:
            raise KonohaDatasetReplayError(
                [f"{event.signal_group}: missing resolve actor {email}"]
            )
        return membership
    owner = runtime.owners.get(signal.establishment.name)
    if owner is None:
        raise KonohaDatasetReplayError(
            [f"missing owner to resolve {event.signal_group}"]
        )
    return owner


def _actor_membership(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    email: str,
    establishment_name: str,
) -> EstablishmentMembership:
    membership = runtime.memberships.get((establishment_name, email.lower()))
    if membership is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: missing membership {email}"]
        )
    return membership


def _qualify_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    signal_id = result.signal_ids_by_group.get(event.signal_group)
    if signal_id is None or event.row is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot qualify before submit"]
        )
    signal = Signal.objects.select_related(
        "establishment",
        "affected_business_unit",
        "responsible_business_unit",
        "activity_subject",
    ).get(pk=signal_id)
    qualify = _workflow_spec(event).get("qualify") or {}
    actor = _actor_membership(
        event,
        runtime=runtime,
        email=qualify["actor_email"],
        establishment_name=signal.establishment.name,
    )
    candidate = event.row["candidate"]
    affected = runtime.poles.get(
        (signal.establishment.name, candidate["affected_pole_specific_name"])
    )
    responsible = runtime.poles.get(
        (signal.establishment.name, candidate["responsible_pole_specific_name"])
    )
    if affected is None or responsible is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: qualify target poles are missing"]
        )
    subject = ActivitySubject.objects.filter(
        business_unit=responsible,
        routing_key=candidate["activity_subject_catalog_key"],
        active=True,
    ).first()
    if subject is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: qualify target subject is missing"]
        )
    try:
        with freeze_django_now(event.at):
            outcome = qualify_signal_routing(
                signal=signal,
                membership=actor,
                patch={
                    "affected_business_unit_id": affected.id,
                    "responsible_business_unit_id": responsible.id,
                    "activity_subject_id": subject.id,
                    "operational_unit_id": None,
                },
            )
            if outcome.qualification_outcome != "updated":
                raise KonohaDatasetReplayError(
                    [
                        f"{event.signal_group}: expected qualify updated, "
                        f"got {outcome.qualification_outcome}"
                    ]
                )
            _classify_new_signal(
                signal=outcome.signal,
                pattern_group=event.pattern_group,
                result=result,
            )
    except KonohaDatasetReplayError:
        raise
    except Exception as exc:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: qualify failed: {exc}"]
        ) from exc
    result.signal_ids_by_group[event.signal_group] = outcome.signal.id
    result.qualified += 1


def _mark_interesting_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    signal_id = result.signal_ids_by_group.get(event.signal_group)
    if signal_id is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot mark interesting before submit"]
        )
    signal = Signal.objects.select_related("establishment").get(pk=signal_id)
    interesting = _workflow_spec(event).get("interesting") or {}
    actor = _actor_membership(
        event,
        runtime=runtime,
        email=interesting["actor_email"],
        establishment_name=signal.establishment.name,
    )
    try:
        with freeze_django_now(event.at):
            updated = mark_signal_interesting(signal=signal, actor_membership=actor)
    except Exception as exc:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: mark_interesting failed: {exc}"]
        ) from exc
    if updated.status != Signal.Status.INTERESTING:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: expected INTERESTING"]
        )
    if not _same_instant(updated.marked_interesting_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: marked_interesting_at does not match clock"]
        )
    result.marked_interesting += 1


def _rr_create_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    signal_id = result.signal_ids_by_group.get(event.signal_group)
    if signal_id is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot create resolution request before submit"]
        )
    signal = Signal.objects.select_related("establishment").get(pk=signal_id)
    request_spec = _workflow_spec(event).get("resolution_request") or {}
    actor = _actor_membership(
        event,
        runtime=runtime,
        email=request_spec["requester_email"],
        establishment_name=signal.establishment.name,
    )
    try:
        with freeze_django_now(event.at):
            created = create_signal_resolution_request(
                signal=signal,
                actor_membership=actor,
            )
    except Exception as exc:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: rr_create failed: {exc}"]
        ) from exc
    if not _same_instant(created.requested_at, event.at):
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: requested_at does not match clock"]
        )
    result.rr_created += 1


def _rr_approve_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    request = _resolution_request_for_group(event, result)
    if request is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot approve before rr_create"]
        )
    signal = Signal.objects.select_related("establishment").get(pk=request.signal_id)
    request_spec = _workflow_spec(event).get("resolution_request") or {}
    actor = _actor_membership(
        event,
        runtime=runtime,
        email=request_spec["reviewer_email"],
        establishment_name=signal.establishment.name,
    )
    try:
        with freeze_django_now(event.at):
            updated = approve_signal_resolution_request(
                resolution_request=request,
                actor_membership=actor,
            )
    except Exception as exc:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: rr_approve failed: {exc}"]
        ) from exc
    signal.refresh_from_db()
    if updated.status != SignalResolutionRequest.Status.APPROVED:
        raise KonohaDatasetReplayError([f"{event.signal_group}: expected APPROVED"])
    if signal.status != Signal.Status.RESOLVED:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: rr_approve did not resolve the signal"]
        )
    if signal.resolution_origin != SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: expected resolution_origin=resolution_request"]
        )
    result.rr_approved += 1


def _rr_reject_event(
    event: ReplayEvent,
    *,
    runtime: ReplayRuntime,
    result: ReplayResult,
    resume: bool,
) -> None:
    if _skip_matching_fingerprint(event, runtime=runtime, result=result, resume=resume):
        return
    request = _resolution_request_for_group(event, result)
    if request is None:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: cannot reject before rr_create"]
        )
    signal = Signal.objects.select_related("establishment").get(pk=request.signal_id)
    request_spec = _workflow_spec(event).get("resolution_request") or {}
    actor = _actor_membership(
        event,
        runtime=runtime,
        email=request_spec["reviewer_email"],
        establishment_name=signal.establishment.name,
    )
    try:
        with freeze_django_now(event.at):
            updated = reject_signal_resolution_request(
                resolution_request=request,
                actor_membership=actor,
            )
    except Exception as exc:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: rr_reject failed: {exc}"]
        ) from exc
    signal.refresh_from_db()
    if updated.status != SignalResolutionRequest.Status.REJECTED:
        raise KonohaDatasetReplayError([f"{event.signal_group}: expected REJECTED"])
    if signal.status != Signal.Status.OPEN:
        raise KonohaDatasetReplayError(
            [f"{event.signal_group}: rr_reject must leave the signal open"]
        )
    result.rr_rejected += 1


def _validate_final_state(
    observations: list[dict[str, Any]],
    result: ReplayResult,
) -> None:
    if len(observations) != 200:
        return
    counts: dict[tuple[str, str], set[str]] = {}
    first_by_group: dict[str, dict[str, Any]] = {}
    for row in observations:
        first_by_group.setdefault(row["signal_group"], row)
    for group, row in first_by_group.items():
        key = (row["establishment"], row["origin_pole_specific_name"])
        counts.setdefault(key, set()).add(group)
    for key, (low, high) in SIGNAL_GROUP_COUNT_RANGES.items():
        actual = len(counts.get(key, set()))
        if not (low <= actual <= high):
            raise KonohaDatasetReplayError(
                [f"{key}: unique signal_group count {actual} not in [{low}, {high}]"]
            )
    late = Observation.objects.filter(
        establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
        submitted_at__gt=OCCURRED_AT_MAX,
    ).exists()
    if late:
        raise KonohaDatasetReplayError(["observation submitted_at after cut-off"])
    late_resolve = Signal.objects.filter(
        establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
        resolved_at__gt=OCCURRED_AT_MAX,
    ).exists()
    if late_resolve:
        raise KonohaDatasetReplayError(["signal resolved_at after cut-off"])
    late_journal = ActionPlanExecutionLifecycleEvent.objects.filter(
        establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
        occurred_at__gt=OCCURRED_AT_MAX,
    ).exists()
    if late_journal:
        raise KonohaDatasetReplayError(["execution lifecycle event after cut-off"])
    late_points = PointTransaction.objects.filter(
        establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
        occurred_at__gt=OCCURRED_AT_MAX,
    ).exists()
    if late_points:
        raise KonohaDatasetReplayError(["point transaction after cut-off"])

    pattern_ids = list(result.pattern_ids_by_group.values())
    if len(pattern_ids) != len(set(pattern_ids)):
        raise KonohaDatasetReplayError(["pattern_group to pattern id must be 1:1"])

    from houston.establishments.konoha_dataset_action_cycles import (
        RESOLUTION_INTERESTING,
        RESOLUTION_LINKED_PLAN,
        RESOLUTION_MANUAL,
        load_konoha_dataset_action_overrides,
    )
    from houston.establishments.konoha_dataset_workflows import (
        load_konoha_dataset_workflow_overrides,
    )
    from houston.signals.models import SignalResolutionRequest

    payload = load_konoha_dataset_action_overrides()
    overrides = payload.get("overrides") if isinstance(payload.get("overrides"), dict) else {}
    workflow_payload = load_konoha_dataset_workflow_overrides()
    workflows = (
        workflow_payload.get("workflows")
        if isinstance(workflow_payload.get("workflows"), dict)
        else {}
    )
    pending_rr = SignalResolutionRequest.objects.filter(
        signal__establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
        status=SignalResolutionRequest.Status.PENDING,
    ).exists()
    if pending_rr:
        raise KonohaDatasetReplayError(["pending resolution request at cut-off"])
    unassigned = Signal.objects.filter(
        establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
        routing_status=Signal.RoutingStatus.UNASSIGNED,
    ).exists()
    if unassigned:
        raise KonohaDatasetReplayError(["unassigned signal remaining at cut-off"])
    for group, row in first_by_group.items():
        cycle = row["cycle"]
        signal_id = result.signal_ids_by_group.get(group)
        if signal_id is None:
            raise KonohaDatasetReplayError([f"{group}: missing replayed signal"])
        signal = Signal.objects.get(pk=signal_id)
        executions = list(ActionPlanExecution.objects.filter(source_signal_id=signal.id))
        if cycle["resolution"] == RESOLUTION_INTERESTING:
            if executions:
                raise KonohaDatasetReplayError(
                    [f"{group}: interesting cycle has a linked plan"]
                )
            if signal.status != Signal.Status.INTERESTING:
                raise KonohaDatasetReplayError(
                    [f"{group}: interesting cycle must finish INTERESTING"]
                )
            expected_marked = parse_corpus_datetime(cycle["marked_interesting_at"])
            if not _same_instant(signal.marked_interesting_at, expected_marked):
                raise KonohaDatasetReplayError(
                    [f"{group}: marked_interesting_at does not match corpus"]
                )
            continue
        if cycle["resolution"] == RESOLUTION_MANUAL:
            if executions:
                raise KonohaDatasetReplayError([f"{group}: manual cycle has a linked plan"])
            if cycle.get("open_at_cutoff") is True:
                if signal.status != Signal.Status.OPEN:
                    raise KonohaDatasetReplayError(
                        [f"{group}: open manual cycle must stay open"]
                    )
                continue
            request_spec = (workflows.get(group) or {}).get("resolution_request") or {}
            expected_origin = (
                SIGNAL_RESOLUTION_ORIGIN_RESOLUTION_REQUEST
                if request_spec.get("decision") == "approve"
                else SIGNAL_RESOLUTION_ORIGIN_MANUAL
            )
            if signal.resolution_origin != expected_origin:
                raise KonohaDatasetReplayError(
                    [f"{group}: expected resolution_origin={expected_origin}"]
                )
            expected_resolved = parse_corpus_datetime(cycle["resolved_at"])
            if not _same_instant(signal.resolved_at, expected_resolved):
                raise KonohaDatasetReplayError(
                    [f"{group}: resolved_at does not match corpus"]
                )
            continue
        if cycle["resolution"] != RESOLUTION_LINKED_PLAN:
            raise KonohaDatasetReplayError([f"{group}: unknown resolution"])
        if cycle.get("open_at_cutoff") is False:
            if signal.resolution_origin != SIGNAL_RESOLUTION_ORIGIN_ACTION_PLAN:
                raise KonohaDatasetReplayError(
                    [f"{group}: expected resolution_origin=action_plan"]
                )
            if not any(
                item.status == ActionPlanExecution.Status.DONE for item in executions
            ):
                raise KonohaDatasetReplayError(
                    [f"{group}: linked_plan cycle has no done execution"]
                )
            expected_resolved = parse_corpus_datetime(cycle["resolved_at"])
            if not _same_instant(signal.resolved_at, expected_resolved):
                raise KonohaDatasetReplayError(
                    [f"{group}: resolved_at does not match corpus"]
                )
            continue
        overlay = overrides.get(group) or {}
        status = overlay.get("cutoff_execution_status") or "scheduled"
        if not executions:
            raise KonohaDatasetReplayError(
                [f"{group}: open linked_plan is missing an execution"]
            )
        execution = executions[0]
        if status == "scheduled":
            if execution.status != ActionPlanExecution.Status.SCHEDULED:
                raise KonohaDatasetReplayError(
                    [f"{group}: expected scheduled execution at cut-off"]
                )
            if signal.status != Signal.Status.IN_PROGRESS:
                raise KonohaDatasetReplayError(
                    [f"{group}: scheduled plan should leave signal in_progress"]
                )
        elif status == "in_progress":
            if execution.status != ActionPlanExecution.Status.IN_PROGRESS:
                raise KonohaDatasetReplayError(
                    [f"{group}: expected in_progress execution at cut-off"]
                )
            if execution.marked_done_at is not None:
                raise KonohaDatasetReplayError(
                    [f"{group}: in_progress cut-off must not mark done"]
                )
        elif status == "pending_validation":
            if execution.status != ActionPlanExecution.Status.PENDING_VALIDATION:
                raise KonohaDatasetReplayError(
                    [f"{group}: expected pending_validation at cut-off"]
                )
            if signal.status == Signal.Status.RESOLVED:
                raise KonohaDatasetReplayError(
                    [f"{group}: pending_validation must not resolve the signal"]
                )
        elif status == "canceled":
            if execution.status != ActionPlanExecution.Status.CANCELED:
                raise KonohaDatasetReplayError(
                    [f"{group}: expected canceled execution at cut-off"]
                )
            if signal.status != Signal.Status.OPEN:
                raise KonohaDatasetReplayError(
                    [f"{group}: canceled execution must leave signal open"]
                )

    executions = list(
        ActionPlanExecution.objects.filter(
            establishment__name__in=(ESTABLISHMENT_ANBU, ESTABLISHMENT_AKATSUKI),
        ).prefetch_related("task_executions")
    )
    null_end = [item for item in executions if item.end_at is None]
    if len(null_end) != 5:
        raise KonohaDatasetReplayError(
            [f"expected exactly 5 KONOHA executions with null end_at, got {len(null_end)}"]
        )
    for execution in executions:
        for task in execution.task_executions.all():
            if not _same_optional_instant(task.deadline_at, execution.end_at):
                raise KonohaDatasetReplayError(
                    [
                        f"execution {execution.id}: task deadline_at must equal execution.end_at"
                    ]
                )


def replay_konoha_dataset_observations(
    *,
    dry_run: bool,
    resume: bool = False,
    observations: list[dict[str, Any]] | None = None,
    runtime: ReplayRuntime | None = None,
    skip_corpus_validation: bool = False,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> ReplayResult:
    assert_local_dev_environment()
    if observations is None:
        if not skip_corpus_validation:
            corpus_errors = validate_konoha_dataset_observations()
            if corpus_errors:
                raise KonohaDatasetReplayError(corpus_errors)
        observations = load_konoha_dataset_observations()
    events = build_replay_events(observations, overrides=overrides)
    loaded = runtime or load_replay_runtime()
    preflight_errors = preflight_konoha_dataset_replay(
        observations,
        runtime=loaded,
        resume=resume,
        dry_run=dry_run,
    )
    if preflight_errors:
        raise KonohaDatasetReplayError(preflight_errors)
    result = ReplayResult(dry_run=dry_run, resume=resume, events=tuple(events))
    result.pattern_labels = _pattern_labels_by_group(observations)
    if dry_run:
        return result
    if resume:
        _hydrate_resume_state(observations, loaded, result)
        _assert_resume_konoha_gamification_seasons(result.events, result, loaded)
    else:
        _wipe_konoha_gamification_state()
    handlers = {
        EVENT_SUBMIT: _submit_event,
        EVENT_QUALIFY: _qualify_event,
        EVENT_RR_CREATE: _rr_create_event,
        EVENT_RR_APPROVE: _rr_approve_event,
        EVENT_RR_REJECT: _rr_reject_event,
        EVENT_MARK_INTERESTING: _mark_interesting_event,
        EVENT_PLAN_CREATE: _plan_create_event,
        EVENT_PLAN_PROMOTE: _plan_promote_event,
        EVENT_PLAN_MARK_DONE: _plan_mark_done_event,
        EVENT_PLAN_VALIDATE: _plan_validate_event,
        EVENT_PLAN_CANCEL: _plan_cancel_event,
        EVENT_RESOLVE: _resolve_event,
    }
    with _suppress_replay_side_effects():
        for event in events:
            handler = handlers.get(event.kind)
            if handler is None:
                raise KonohaDatasetReplayError([f"unknown replay event kind {event.kind}"])
            handler(event, runtime=loaded, result=result, resume=resume)
    _validate_final_state(observations, result)
    return result
