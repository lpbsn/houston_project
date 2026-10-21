"""Visibility and copy rules still used by the sealed period capture.

The autonomous investigator does not call this module. ``capture_dossier`` and
``capture_period_dossier`` still do. Field text that counts is the Signal title
and structured summary.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime

ENGINE_VERSION = "investigation_v3"
ENGINE_VERSION_KEY = "engine_version"

PER_CALL_INPUT_TOKENS = 80_000
PER_CALL_OUTPUT_TOKENS = 8_000
PROVIDER_TIMEOUT_SECONDS = 180
MAX_DEEPENINGS = 2
MAX_SEMANTIC_READINGS = MAX_DEEPENINGS + 1
MAX_CORRECTIONS = 1
MAX_PROVIDER_CALLS = MAX_SEMANTIC_READINGS + MAX_CORRECTIONS

DEEPEN_SEASONAL_WINDOW = "seasonal_window"
DEEPEN_ACTIVITY_SUBJECT = "activity_subject_sample"
DEEPEN_COMPLETED_MEMORY = "completed_analysis_memory"
DEEPEN_PERIOD_INDEX = "period_index_identifier"
ACTIVITY_SAMPLE_LIMIT = 8
MEMORY_SAMPLE_LIMIT = 4
ATTEMPT_HARD_MARGIN_SECONDS = 60
LEASE_MARGIN_SECONDS = 60
DEEPENING_MENU = frozenset(
    {
        DEEPEN_SEASONAL_WINDOW,
        DEEPEN_ACTIVITY_SUBJECT,
        DEEPEN_COMPLETED_MEMORY,
        DEEPEN_PERIOD_INDEX,
    }
)

QUALIFICATION_COMPLETE = "complete"
QUALIFICATION_PARTIAL = "partial"
QUALIFICATION_REFUSED = "refused"
QUALIFICATION_FACTUAL = "factual_reading"

TREATMENT_COMPLETED = "completed"
TREATMENT_FAILED = "failed"
TREATMENT_CANCELED = "canceled"

SIGNAL_TEXT_FIELDS = ("title", "structured_summary")
SIGNAL_COPY_KEYS = frozenset(
    {
        "source_id",
        "recorded_at",
        *SIGNAL_TEXT_FIELDS,
        "location_text",
        "business_units",
        "activity_subject",
        "operational_unit",
        "status_at_period_start",
        "status_at_period_end",
        "events",
        "phenomenon_mentioned_at",
        "mention",
        "source_observation_link_counts",
    }
)
FORBIDDEN_SIGNAL_KEYS = frozenset(
    {
        "raw_text",
        "body",
        "comment",
        "transcription",
        "description",
        "request_comment",
        "review_comment",
        "cancel_comment",
        "skipped_reason",
        "instance_description",
        "observation",
        "observations",
        "source_observation",
        "raw_observation",
    }
)


@dataclass(frozen=True)
class TimingVerdict:
    """Whether one attempt can host every call the engine may start.

    The lease is renewed before a call, so it has to outlive the provider
    timeout and still leave the write. The worker soft and hard limits have
    to cover every call running up to that timeout.
    """

    coherent: bool
    needed_seconds: int
    issues: tuple[str, ...]


@dataclass(frozen=True)
class DeepeningDecision:
    accepted: bool
    code: str


@dataclass(frozen=True)
class HistoricalCopyDecision:
    copied: bool
    exclusion: str | None


@dataclass(frozen=True)
class HistoricalSignalCopy:
    payload: dict | None
    exclusion: str | None
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class SubjectFinding:
    key: str
    significant: bool = True
    examined: bool = False
    cause_established: bool = False
    verified_analytical: bool = False
    affirmative: bool = False
    unexamined_contradiction: bool = False
    undermines_published: bool = False
    named: bool = False


@dataclass(frozen=True)
class InvestigationFacts:
    """Evidence the backend already checked. The model does not supply the qualification."""

    subjects: tuple[SubjectFinding, ...]
    discovered_not_examined: tuple[str, ...] = ()
    competing_period_lead_excluded: bool = False
    reported_only: bool = False
    accepted_decomposition: bool = False
    treatment: str = TREATMENT_COMPLETED
    checks_impossible: bool = False
    coverage_incomplete: bool = False


@dataclass(frozen=True)
class QualificationResult:
    qualification: str | None
    investigation_succeeded: bool
    blocked_finding_keys: tuple[str, ...]


def investigation_engine(configuration: object) -> bool:
    """True only when admission has frozen this engine. Absence keeps the current executor."""
    if not isinstance(configuration, dict):
        return False
    return configuration.get(ENGINE_VERSION_KEY) == ENGINE_VERSION


def retained_execution_budget() -> dict[str, int]:
    """Budgets to freeze when V3 is activated. Worker settings stay as shipped.

    One task runs the investigation. The dossier already checkpoints each
    reading and each deepening, so a lost worker replays the persisted step
    and does not open another deepening. The task therefore has to survive
    every provider call at the full timeout: four calls times 180 seconds,
    plus the 60 second gap the workers already keep between the soft and hard
    limits.

    The lease stays one timeout plus that same 60 second gap, and it is
    renewed before each call, as the current executor already renews it. A
    lease as long as the whole task would keep the establishment blocked after
    a dead worker. Token ceilings stay the investigation copy, not the legacy
    twelve calls and 400 000 tokens.

    ``investigation_timing`` still refuses to start while the frozen attempt
    is the shipped 600 / 660 seconds.
    """
    timeout = PROVIDER_TIMEOUT_SECONDS
    span = MAX_PROVIDER_CALLS * timeout
    return {
        "provider_timeout_seconds": timeout,
        "lease_seconds": timeout + LEASE_MARGIN_SECONDS,
        "attempt_soft_seconds": span,
        "attempt_hard_seconds": span + ATTEMPT_HARD_MARGIN_SECONDS,
        "max_provider_calls": MAX_PROVIDER_CALLS,
    }


def investigation_ceilings() -> dict[str, int]:
    """Budgets the new engine will copy at admission. Live settings are not read."""
    return {
        "per_call_input_tokens": PER_CALL_INPUT_TOKENS,
        "per_call_output_tokens": PER_CALL_OUTPUT_TOKENS,
        "provider_timeout_seconds": PROVIDER_TIMEOUT_SECONDS,
        "max_semantic_readings": MAX_SEMANTIC_READINGS,
        "max_corrections": MAX_CORRECTIONS,
        "max_provider_calls": MAX_PROVIDER_CALLS,
        "total_input_tokens": MAX_PROVIDER_CALLS * PER_CALL_INPUT_TOKENS,
    }


def investigation_timing(ceilings: dict) -> TimingVerdict:
    """Coherence of provider timeout, worker lease, and the attempt limits.

    ``needed_seconds`` is one full timeout for every provider call. A lease
    that expires on the timeout leaves no time to persist the step. An attempt
    shorter than the calls is killed before the investigation can stop cleanly.
    """
    try:
        timeout = int(ceilings["provider_timeout_seconds"])
        lease = int(ceilings["lease_seconds"])
        soft = int(ceilings["attempt_soft_seconds"])
        hard = int(ceilings["attempt_hard_seconds"])
        calls = int(ceilings.get("max_provider_calls", MAX_PROVIDER_CALLS))
    except (KeyError, TypeError, ValueError):
        return TimingVerdict(False, 0, ("timing_unreadable",))
    if min(timeout, lease, soft, hard, calls) <= 0:
        return TimingVerdict(False, 0, ("timing_unreadable",))
    needed = calls * timeout
    issues: list[str] = []
    if lease <= timeout:
        issues.append("lease_not_after_timeout")
    if hard < needed:
        issues.append("attempt_shorter_than_calls")
    if soft >= hard:
        issues.append("soft_not_before_hard")
    if soft < needed:
        issues.append("soft_shorter_than_calls")
    return TimingVerdict(not issues, needed, tuple(issues))


def accept_deepening(
    *,
    kind: str,
    already_done: int,
    establishment_id: str,
    request_establishment_id: str,
) -> DeepeningDecision:
    """Decide a closed-menu deepening. This does not copy a row or call a provider.

    The model's ``target_at`` is not a bound. Each search keeps rows that
    already existed at the capture.
    """
    if already_done >= MAX_DEEPENINGS:
        return DeepeningDecision(False, "deepen_budget_exhausted")
    if kind not in DEEPENING_MENU:
        return DeepeningDecision(False, "outside_menu")
    if str(establishment_id) != str(request_establishment_id):
        return DeepeningDecision(False, "outside_establishment")
    return DeepeningDecision(True, "accepted")


def signal_boundary_issues(payload: object) -> tuple[str, ...]:
    """Issues that keep a Signal payload out of an investigation copy."""
    if not isinstance(payload, dict):
        return ("payload_invalid",)
    issues: list[str] = []
    for key in payload:
        if key not in SIGNAL_COPY_KEYS:
            issues.append(f"disallowed:{key}")
    for key in _walk_keys(payload):
        if key in FORBIDDEN_SIGNAL_KEYS:
            issues.append(f"forbidden:{key}")
    mention = payload.get("mention")
    if mention is not None:
        field = mention.get("field") if isinstance(mention, dict) else None
        if field not in SIGNAL_TEXT_FIELDS:
            issues.append("mention_field")
    return tuple(dict.fromkeys(issues))


def authoritative_signal_text(payload: dict) -> dict[str, str]:
    """The only Signal prose a conclusion may treat as field content."""
    return {
        "title": str(payload.get("title") or ""),
        "structured_summary": str(payload.get("structured_summary") or ""),
    }


def events_visible_at_capture(
    events: list[dict],
    capture_at: datetime,
) -> tuple[dict, ...]:
    """Keep lifecycle events that had already occurred at ``capture_at``."""
    visible = []
    for event in events:
        occurred_at = event.get("occurred_at") if isinstance(event, dict) else None
        if isinstance(occurred_at, datetime) and occurred_at <= capture_at:
            visible.append(event)
    return tuple(visible)


def project_signal_copy(
    payload: dict,
    *,
    capture_at: datetime,
) -> tuple[dict | None, tuple[str, ...]]:
    """Project one Signal into the investigation copy, or return no payload."""
    issues = list(signal_boundary_issues(payload))
    events = payload.get("events") if isinstance(payload, dict) else None
    if events is not None and not _events_within_capture(events, capture_at):
        issues.append("event_after_capture")
    unique = tuple(dict.fromkeys(issues))
    if unique:
        return None, unique
    projected = {key: payload[key] for key in payload if key in SIGNAL_COPY_KEYS}
    return copy.deepcopy(projected), ()


def historical_copy_decision(
    *,
    created_at: datetime,
    updated_at: datetime,
    capture_at: datetime,
) -> HistoricalCopyDecision:
    """Whether a row not yet in the dossier can be copied.

    A row already copied at ``capture_at`` is not passed here again. Its dossier
    text stays the copy. This decision has no field text.
    """
    try:
        if created_at > capture_at:
            return HistoricalCopyDecision(False, "absent_at_capture")
        if updated_at > capture_at:
            return HistoricalCopyDecision(False, "modified_after_capture")
    except TypeError:
        return HistoricalCopyDecision(False, "timestamp_unusable")
    return HistoricalCopyDecision(True, None)


def copy_historical_signal(
    *,
    created_at: datetime,
    updated_at: datetime,
    capture_at: datetime,
    payload: dict,
) -> HistoricalSignalCopy:
    """Copy a historical Signal, or exclude it without returning its live text."""
    decision = historical_copy_decision(
        created_at=created_at,
        updated_at=updated_at,
        capture_at=capture_at,
    )
    if not decision.copied:
        return HistoricalSignalCopy(None, decision.exclusion, ())
    projected, issues = project_signal_copy(payload, capture_at=capture_at)
    if issues:
        return HistoricalSignalCopy(None, None, issues)
    return HistoricalSignalCopy(projected, None, ())


def qualify(facts: InvestigationFacts) -> QualificationResult:
    """Qualification and investigation success. Treatment status is a separate input.

    ``discovered_not_examined`` does not block ``complete``. An identified
    contradiction that was not examined blocks the finding that depends on it
    and blocks ``complete``. ``failed`` and ``canceled`` have no success qualification.
    """
    if facts.treatment != TREATMENT_COMPLETED:
        return QualificationResult(None, False, ())

    blocked = tuple(
        subject.key
        for subject in facts.subjects
        if subject.affirmative
        and subject.examined
        and (subject.unexamined_contradiction or facts.competing_period_lead_excluded)
    )
    blocked_keys = set(blocked)
    verified = any(
        subject.verified_analytical and subject.examined and subject.key not in blocked_keys
        for subject in facts.subjects
    )
    analytical = verified or facts.accepted_decomposition
    if facts.reported_only and not analytical:
        return QualificationResult(QUALIFICATION_FACTUAL, False, blocked)
    if _is_complete(facts, blocked, analytical):
        return QualificationResult(QUALIFICATION_COMPLETE, True, ())
    if _is_partial(facts, analytical):
        return QualificationResult(QUALIFICATION_PARTIAL, True, blocked)
    return QualificationResult(QUALIFICATION_REFUSED, False, blocked)


def _is_complete(
    facts: InvestigationFacts,
    blocked: tuple[str, ...],
    analytical: bool,
) -> bool:
    if not analytical or blocked or facts.checks_impossible or facts.coverage_incomplete:
        return False
    if facts.competing_period_lead_excluded:
        return False
    if any(subject.unexamined_contradiction for subject in facts.subjects):
        return False
    if any(subject.undermines_published for subject in facts.subjects):
        return False
    significant = [subject for subject in facts.subjects if subject.significant]
    if not significant:
        return False
    for subject in significant:
        if not subject.examined:
            return False
        if not subject.cause_established and not subject.named:
            return False
    return True


def _is_partial(facts: InvestigationFacts, analytical: bool) -> bool:
    if not analytical or facts.checks_impossible:
        return False
    if any(subject.undermines_published for subject in facts.subjects):
        return False
    for subject in facts.subjects:
        if not subject.significant:
            continue
        inconclusive = subject.examined and not subject.cause_established
        if (not subject.examined or inconclusive) and not subject.named:
            return False
    return True


def _events_within_capture(events: object, capture_at: datetime) -> bool:
    if not isinstance(events, list):
        return False
    return all(_event_visible(event, capture_at) for event in events)


def _event_visible(event: object, capture_at: datetime) -> bool:
    if not isinstance(event, dict):
        return False
    occurred_at = event.get("occurred_at")
    return isinstance(occurred_at, datetime) and occurred_at <= capture_at


def _walk_keys(value: object):
    if isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)
