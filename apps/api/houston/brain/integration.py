"""Versioned entry of the investigation engine.

Analyses whose frozen configuration has no ``engine_version`` stay on the lot
executor. This module captures the period, renews the lease around each call,
and publishes one result. It does not admit work and it does not rebuild the
reading loop.
"""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from houston.ai.models import AIUsageLog
from houston.brain.capture import capture_period_dossier
from houston.brain.dossier import reload_period_dossier
from houston.brain.errors import BrainWorkError, CaptureTimeout, CaptureVolumeExceeded
from houston.brain.investigation import (
    ENGINE_VERSION,
    ENGINE_VERSION_KEY,
    FORBIDDEN_SIGNAL_KEYS,
    QUALIFICATION_COMPLETE,
    QUALIFICATION_FACTUAL,
    QUALIFICATION_PARTIAL,
    QUALIFICATION_REFUSED,
    TREATMENT_CANCELED,
    TREATMENT_COMPLETED,
    investigation_ceilings,
    investigation_engine,
    investigation_timing,
    retained_execution_budget,
)
from houston.brain.investigation_contract import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    cited_item_ids,
    investigation_call_tokens,
    investigation_prompt,
    investigation_response_schema,
    subject_figures_verified,
)
from houston.brain.models import BrainAnalysis, BrainDossier, BrainSearchRun, BrainSlot
from houston.brain.openai_provider import OpenAIBrainProvider
from houston.brain.orchestration import STOP_CODE, _source_classes, run_investigation
from houston.brain.period import PeriodSnapshot
from houston.brain.provider import BrainProvider, BrainProviderUnavailable, FakeBrainProvider
from houston.brain.runtime import (
    _fail,
    _guard,
    _renew,
    _running,
    _usage,
)

logger = logging.getLogger(__name__)

_RUNNING = BrainAnalysis.Status.RUNNING
_PUBLISHED_QUALIFICATIONS = frozenset(
    {
        QUALIFICATION_COMPLETE,
        QUALIFICATION_PARTIAL,
        QUALIFICATION_REFUSED,
        QUALIFICATION_FACTUAL,
    }
)
_SUCCESS_QUALIFICATIONS = frozenset({QUALIFICATION_COMPLETE, QUALIFICATION_PARTIAL})


class _Stopped(Exception):
    """The attempt already reached a terminal row. The loop must not publish."""


def investigation_admission_enabled() -> bool:
    """True only when the process explicitly selects the investigation engine."""
    return str(getattr(settings, "HOUSTON_BRAIN_ENGINE_VERSION", "") or "") == ENGINE_VERSION


def freeze_investigation_configuration(configuration: dict) -> dict:
    """Copy V3 budgets onto an admission configuration. The lot ceilings stay available."""
    frozen = {key: value for key, value in configuration.items()}
    ceilings = dict(frozen.get("ceilings") or {})
    calls = investigation_ceilings()
    budget = retained_execution_budget()
    ceilings.update(
        {
            "per_call_input_tokens": calls["per_call_input_tokens"],
            "per_call_output_tokens": calls["per_call_output_tokens"],
            "total_input_tokens": calls["total_input_tokens"],
            "max_calls": calls["max_provider_calls"],
            "lease_seconds": budget["lease_seconds"],
            "provider_timeout_seconds": budget["provider_timeout_seconds"],
            "attempt_soft_seconds": budget["attempt_soft_seconds"],
            "attempt_hard_seconds": budget["attempt_hard_seconds"],
        }
    )
    frozen["ceilings"] = ceilings
    frozen[ENGINE_VERSION_KEY] = ENGINE_VERSION
    return frozen


def resolve_investigation_ceilings(configuration: object) -> dict[str, int]:
    """Call budgets plus the frozen lease and attempt. Live worker settings are not read."""
    resolved = investigation_ceilings()
    if not isinstance(configuration, dict):
        return resolved
    frozen = configuration.get("ceilings")
    if not isinstance(frozen, dict):
        return resolved
    for key in (
        "per_call_input_tokens",
        "per_call_output_tokens",
        "total_input_tokens",
        "max_semantic_readings",
        "max_corrections",
        "max_provider_calls",
        "lease_seconds",
        "provider_timeout_seconds",
        "attempt_soft_seconds",
        "attempt_hard_seconds",
    ):
        if key in frozen:
            resolved[key] = int(frozen[key])
    if "max_provider_calls" not in frozen and "max_calls" in frozen:
        resolved["max_provider_calls"] = int(frozen["max_calls"])
    budget = retained_execution_budget()
    resolved.setdefault("lease_seconds", budget["lease_seconds"])
    resolved.setdefault("attempt_soft_seconds", budget["attempt_soft_seconds"])
    resolved.setdefault("attempt_hard_seconds", budget["attempt_hard_seconds"])
    return resolved


def execute_investigation(
    analysis_id,
    token,
    *,
    provider: BrainProvider | None,
    started: float,
) -> None:
    """One claimed attempt. A transport failure leaves the dossier unpublished."""
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    if not investigation_engine(analysis.configuration):
        _fail(analysis_id, token, "configuration_unusable")
        return
    ceilings = resolve_investigation_ceilings(analysis.configuration)
    timing = investigation_timing(ceilings)
    if not timing.coherent:
        _fail(analysis_id, token, "timing_incoherent")
        return
    if provider is None:
        provider = _provider(analysis.configuration, ceilings)
        if provider is None:
            _fail(analysis_id, token, "provider_not_allowed")
            return
    if not _capture_if_open(analysis_id, token):
        return
    analysis = _running(analysis_id, token)
    if analysis is None or not _guard(analysis, token):
        return
    try:
        snapshot = reload_period_dossier(analysis_id)
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return
    pole, subject_start, subject_end = subject_focus(snapshot)
    governed = _GovernedProvider(
        provider,
        analysis_id=analysis_id,
        token=token,
        ceilings=ceilings,
        configuration=analysis.configuration,
        started=started,
    )
    try:
        outcome = run_investigation(
            analysis_id,
            provider=governed,
            subject_pole=pole,
            subject_start=subject_start,
            subject_end=subject_end,
            ceilings=ceilings,
        )
    except _Stopped:
        return
    except BrainProviderUnavailable:
        raise
    if outcome.treatment == "interrupted":
        raise BrainProviderUnavailable()
    settle_investigation(analysis_id, token, outcome)


def settle_investigation(analysis_id, token, outcome) -> None:
    """Write the terminal row once. A stored result is not replaced."""
    now = timezone.now()
    with transaction.atomic():
        row = (
            BrainAnalysis.objects.select_for_update()
            .filter(id=analysis_id, attempt_token=token, status=_RUNNING)
            .first()
        )
        if row is None or row.result is not None or _stop_published(analysis_id):
            return
        if row.cancel_requested_at is None and not _guard(row, token):
            return
        if row.cancel_requested_at is not None or outcome.treatment == TREATMENT_CANCELED:
            _terminal(row, status=BrainAnalysis.Status.CANCELED, failure_code="cancel_requested")
            _mark_published(analysis_id)
            return
        if outcome.treatment != TREATMENT_COMPLETED:
            _terminal(
                row,
                status=BrainAnalysis.Status.FAILED,
                failure_code=outcome.code or "response_invalid",
            )
            _mark_published(analysis_id)
            return
        try:
            snapshot = reload_period_dossier(analysis_id)
        except BrainWorkError as exc:
            _terminal(row, status=BrainAnalysis.Status.FAILED, failure_code=exc.code)
            return
        lecture = _lecture(analysis_id, outcome.semantic_readings)
        result = project_public_result(outcome, snapshot, lecture)
        if result is None or _contains_forbidden(result):
            _terminal(row, status=BrainAnalysis.Status.FAILED, failure_code="response_invalid")
            _mark_published(analysis_id)
            return
        row.provider_calls_used = max(row.provider_calls_used, outcome.provider_calls)
        row.status = BrainAnalysis.Status.COMPLETED
        row.failure_code = ""
        row.result = result
        row.lease_expires_at = None
        row.save(
            update_fields=[
                "provider_calls_used",
                "status",
                "failure_code",
                "result",
                "lease_expires_at",
                "updated_at",
            ]
        )
        BrainSlot.objects.filter(analysis_id=analysis_id).delete()
        _mark_published(analysis_id)
    logger.info(
        "brain_investigation_settled",
        extra={
            "event": "brain_investigation_settled",
            "analysis_id": str(analysis_id),
            "qualification": outcome.qualification,
            "at": now.isoformat(),
        },
    )


def project_public_result(outcome, snapshot: PeriodSnapshot | None, lecture) -> dict | None:
    """Backend qualification only. An unread copy is not marked examined."""
    if outcome.treatment != TREATMENT_COMPLETED:
        return None
    if outcome.qualification not in _PUBLISHED_QUALIFICATIONS:
        return None
    succeeded = (
        outcome.investigation_succeeded is True
        and outcome.qualification in _SUCCESS_QUALIFICATIONS
    )
    discovered = {str(item) for item in outcome.discovered_not_examined}
    examined = [str(item) for item in outcome.examined_ids if str(item) not in discovered]
    output = lecture.get("output") if isinstance(lecture, dict) else None
    if not isinstance(output, dict):
        output = {}
    signal_ids: set[str] = set()
    action_ids: set[str] = set()
    measures: dict = {}
    reporting_ids: set[str] = set()
    if snapshot is not None:
        signal_ids, action_ids, reporting_ids, measures = _source_classes(snapshot)
    citable = set(examined) | set(measures) | reporting_ids
    labels = _coverage_labels(lecture, snapshot)
    subjects = []
    for raw in output.get("subjects") or []:
        if isinstance(raw, dict):
            subjects.append(
                _public_subject(
                    raw,
                    discovered=discovered,
                    citable=citable,
                    measures=measures,
                    signal_ids=signal_ids,
                    action_ids=action_ids,
                    figures_allowed=outcome.qualification in _SUCCESS_QUALIFICATIONS,
                )
            )
    cited = _cited(output.get("subjects") or [], citable=citable, discovered=discovered)
    return {
        "schema_version": SCHEMA_VERSION,
        "qualification": outcome.qualification,
        "investigation_succeeded": succeeded,
        "code": outcome.code,
        "subjects": subjects,
        "examined_ids": examined,
        "examined_not_cited": [
            _coverage_item(source_id, labels, disposition="examined_not_cited")
            for source_id in examined
            if source_id not in set(cited)
        ],
        "cited_ids": cited,
        "cited": [_coverage_item(source_id, labels, disposition="cited") for source_id in cited],
        "discovered_not_examined": _discovered_rows(lecture, discovered, labels),
        "limits": [_public_limit(row) for row in outcome.limits if isinstance(row, dict)],
    }


def subject_focus(snapshot: PeriodSnapshot) -> tuple[str, date, date]:
    """Pole used to order the remainder of the first reading. The period is the reporting."""
    scopes = [str(row.get("scope") or "").strip() for row in snapshot.series]
    scopes = [scope for scope in scopes if scope]
    if scopes:
        pole = sorted(scopes, key=lambda name: (-scopes.count(name), name))[0]
    else:
        poles = [item.pole for item in snapshot.copies if item.pole]
        pole = sorted(poles, key=lambda name: (-poles.count(name), name))[0] if poles else ""
    return pole, snapshot.period_start, snapshot.period_end


class _GovernedProvider:
    """Renews the lease and applies the frozen budget around one provider call."""

    def __init__(self, inner, *, analysis_id, token, ceilings, configuration, started: float):
        self.inner = inner
        self.analysis_id = analysis_id
        self.token = token
        self.ceilings = ceilings
        self.configuration = configuration
        self.started = started

    def complete(self, *, analysis_id: str, lot_key: str, payload: dict, timeout_seconds: int):
        self._before(timeout_seconds)
        try:
            result = self.inner.complete(
                analysis_id=analysis_id,
                lot_key=lot_key,
                payload=payload,
                timeout_seconds=timeout_seconds,
            )
        except BrainProviderUnavailable:
            raise
        except BrainWorkError as exc:
            # A contract refusal is terminal. The provider body is not logged:
            # it can echo the dossier. Transport failures stay unavailable.
            cause = exc.__cause__
            logger.info(
                "brain_investigation_provider_rejected",
                extra={
                    "event": "brain_investigation_provider_rejected",
                    "analysis_id": str(self.analysis_id),
                    "failure_code": "response_invalid",
                    "provider_code": exc.code,
                    "provider_error": type(cause).__name__ if cause is not None else "",
                },
            )
            _fail(self.analysis_id, self.token, "response_invalid")
            raise _Stopped() from None
        self._charge(result, payload)
        return result

    def _before(self, timeout_seconds: int) -> None:
        analysis = _running(self.analysis_id, self.token)
        if analysis is None or not _guard(analysis, self.token):
            raise _Stopped()
        elapsed = time.monotonic() - self.started
        if elapsed + timeout_seconds > self.ceilings["attempt_soft_seconds"]:
            _fail(self.analysis_id, self.token, "attempt_exceeded")
            raise _Stopped()
        if (
            analysis.provider_calls_used >= self.ceilings["max_provider_calls"]
            or analysis.consumed_input_tokens >= self.ceilings["total_input_tokens"]
        ):
            _fail(self.analysis_id, self.token, "budget_exceeded")
            raise _Stopped()
        if not _renew(self.analysis_id, self.token, self.ceilings["lease_seconds"]):
            current = _running(self.analysis_id, self.token)
            if current is not None:
                _guard(current, self.token)
            raise _Stopped()

    def _charge(self, result, payload: dict) -> None:
        charged = result.input_tokens
        if charged is None:
            charged = investigation_call_tokens(payload)
        now = timezone.now()
        stopped = False
        with transaction.atomic():
            row = (
                BrainAnalysis.objects.select_for_update()
                .filter(id=self.analysis_id, attempt_token=self.token, status=_RUNNING)
                .first()
            )
            if row is None:
                stopped = True
            elif row.cancel_requested_at is not None:
                _terminal(
                    row,
                    status=BrainAnalysis.Status.CANCELED,
                    failure_code="cancel_requested",
                )
                stopped = True
            else:
                calls = row.provider_calls_used + 1
                consumed = row.consumed_input_tokens + max(0, int(charged))
                over = (
                    calls > self.ceilings["max_provider_calls"]
                    or consumed > self.ceilings["total_input_tokens"]
                    or (
                        result.input_tokens is not None
                        and result.input_tokens > self.ceilings["per_call_input_tokens"]
                    )
                )
                row.provider_calls_used = calls
                row.consumed_input_tokens = consumed
                logged = {
                    **self.configuration,
                    "schema_version": SCHEMA_VERSION,
                    "prompt_version": PROMPT_VERSION,
                }
                if over:
                    row.status = BrainAnalysis.Status.FAILED
                    row.failure_code = "budget_exceeded"
                    row.lease_expires_at = None
                    row.save(
                        update_fields=[
                            "provider_calls_used",
                            "consumed_input_tokens",
                            "status",
                            "failure_code",
                            "lease_expires_at",
                            "updated_at",
                        ]
                    )
                    BrainSlot.objects.filter(analysis_id=self.analysis_id).delete()
                    _usage(
                        row,
                        configuration=logged,
                        result=result,
                        error_code="budget_exceeded",
                        status=AIUsageLog.Status.FAILED,
                    )
                    stopped = True
                else:
                    row.lease_expires_at = now + timedelta(seconds=self.ceilings["lease_seconds"])
                    row.save(
                        update_fields=[
                            "provider_calls_used",
                            "consumed_input_tokens",
                            "lease_expires_at",
                            "updated_at",
                        ]
                    )
                    _usage(
                        row,
                        configuration=logged,
                        result=result,
                        error_code="",
                        status=(
                            AIUsageLog.Status.FAILED
                            if result.truncated
                            else AIUsageLog.Status.SUCCEEDED
                        ),
                    )
        if stopped:
            raise _Stopped()


def _provider(configuration: object, ceilings: dict[str, int]) -> BrainProvider | None:
    if not isinstance(configuration, dict):
        return None
    name = str(configuration.get("provider") or "").strip().lower()
    if name == "fake":
        return FakeBrainProvider()
    if name != "openai":
        return None
    api_key = str(settings.OPENAI_API_KEY or "").strip()
    model = str(configuration.get("model") or "").strip()
    if not api_key or not model:
        return None
    return OpenAIBrainProvider(
        api_key=api_key,
        model=model,
        timeout_seconds=ceilings["provider_timeout_seconds"],
        max_output_tokens=ceilings["per_call_output_tokens"],
        system_text=investigation_prompt(),
        response_format=investigation_response_schema(),
        accepted_schema=SCHEMA_VERSION,
    )


def _capture_if_open(analysis_id, token) -> bool:
    if BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False).exists():
        return True
    try:
        capture_period_dossier(analysis_id)
    except CaptureTimeout:
        _fail(analysis_id, token, "capture_timeout")
        return False
    except CaptureVolumeExceeded:
        _fail(analysis_id, token, "capture_volume_exceeded")
        return False
    except BrainWorkError as exc:
        _fail(analysis_id, token, exc.code)
        return False
    return BrainDossier.objects.filter(analysis_id=analysis_id, closed_at__isnull=False).exists()


def _terminal(row: BrainAnalysis, *, status: str, failure_code: str) -> None:
    row.status = status
    row.failure_code = failure_code
    row.lease_expires_at = None
    if status == BrainAnalysis.Status.CANCELED and row.cancel_requested_at is None:
        row.cancel_requested_at = timezone.now()
    row.save(
        update_fields=[
            "status",
            "failure_code",
            "lease_expires_at",
            "cancel_requested_at",
            "updated_at",
        ]
    )
    BrainSlot.objects.filter(analysis_id=row.id).delete()


def _lecture(analysis_id, readings: int) -> dict | None:
    if readings <= 0:
        return None
    row = (
        BrainSearchRun.objects.filter(
            dossier__analysis_id=analysis_id,
            code=f"lecture:{readings}",
        )
        .only("criteria")
        .first()
    )
    if row is None or not isinstance(row.criteria, dict):
        return None
    return row.criteria


def _stop_published(analysis_id) -> bool:
    row = (
        BrainSearchRun.objects.filter(dossier__analysis_id=analysis_id, code=STOP_CODE)
        .only("criteria")
        .first()
    )
    if row is None or not isinstance(row.criteria, dict):
        return False
    return row.criteria.get("published") is True


def _mark_published(analysis_id) -> None:
    row = (
        BrainSearchRun.objects.select_for_update()
        .filter(dossier__analysis_id=analysis_id, code=STOP_CODE)
        .first()
    )
    if row is None or not isinstance(row.criteria, dict):
        return
    criteria = dict(row.criteria)
    criteria["published"] = True
    row.criteria = criteria
    row.save(update_fields=["criteria", "updated_at"])


def _public_subject(
    raw: dict,
    *,
    discovered: set[str],
    citable: set[str],
    measures: dict,
    signal_ids: set[str],
    action_ids: set[str],
    figures_allowed: bool,
) -> dict:
    cited = {item for item in raw.get("evidence_ids") or [] if isinstance(item, str)}
    cited.update(item for item in raw.get("contradiction_ids") or [] if isinstance(item, str))
    unread = sorted(cited & discovered)
    retained = _cited(raw, citable=citable, discovered=discovered)
    examined = bool(raw.get("examined")) and not unread
    verified = examined and figures_allowed and subject_figures_verified(
        raw,
        measures=measures,
        signal_ids=signal_ids,
        action_ids=action_ids,
    )
    calculations = []
    breakdowns = []
    if verified:
        calculations = [
            {**calculation, "verified": True}
            for calculation in raw.get("calculations") or []
            if isinstance(calculation, dict)
        ]
        breakdowns = [
            {**breakdown, "verified": True}
            for breakdown in raw.get("breakdowns") or []
            if isinstance(breakdown, dict)
        ]
    limits = []
    gaps = []
    for limit in raw.get("limits") or []:
        if not isinstance(limit, dict):
            continue
        text = str(limit.get("text") or "")
        if text:
            limits.append(text)
        if limit.get("effect") in {"blocks_comparison", "coverage"} and text:
            gaps.append(text)
    return {
        "key": str(raw.get("key") or ""),
        "statement": str(raw.get("statement") or ""),
        "examined": examined,
        "cause": raw.get("cause") if examined else "unknown",
        "orientation": str(raw.get("orientation") or ""),
        "justification": str(raw.get("justification") or ""),
        "limits": limits,
        "gaps": gaps,
        "calculations": calculations,
        "breakdowns": breakdowns,
        "cited_ids": retained,
        "not_examined_ids": unread,
    }


def _cited(value, *, citable: set[str], discovered: set[str]) -> list[str]:
    """Citations the published reading can actually use. A discovered id is not one."""
    return sorted(
        item for item in cited_item_ids(value) if item in citable and item not in discovered
    )


def _coverage_labels(lecture, snapshot: PeriodSnapshot | None) -> dict[str, tuple[str, str]]:
    labels: dict[str, tuple[str, str]] = {}
    if snapshot is not None:
        for item in snapshot.copies:
            labels[item.source_id] = (item.title or "", item.pole or "")
        reporting = snapshot.reporting if isinstance(snapshot.reporting, dict) else {}
        for measure in reporting.get("measures") or []:
            if isinstance(measure, dict) and measure.get("measure_id"):
                labels[str(measure["measure_id"])] = (str(measure.get("label") or ""), "")
    payload = lecture.get("payload") if isinstance(lecture, dict) else None
    if isinstance(payload, dict):
        for row in payload.get("examined") or []:
            if not isinstance(row, dict):
                continue
            source_id = str(row.get("source_id") or "")
            if not source_id:
                continue
            known = labels.get(source_id, ("", ""))
            title = str(row.get("title") or row.get("label") or known[0])
            labels[source_id] = (title, known[1] or str(row.get("pole") or ""))
    return labels


def _coverage_item(source_id: str, labels: dict[str, tuple[str, str]], *, disposition: str) -> dict:
    label, pole = labels.get(source_id, ("", ""))
    return {
        "source_id": source_id,
        "label": label,
        "pole": pole,
        "disposition": disposition,
    }


def _discovered_rows(
    lecture,
    discovered: set[str],
    labels: dict[str, tuple[str, str]],
) -> list[dict]:
    rows = []
    seen: set[str] = set()
    source = lecture.get("discovered_not_examined") if isinstance(lecture, dict) else None
    for row in source or []:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "")
        if not source_id or source_id not in discovered or source_id in seen:
            continue
        seen.add(source_id)
        label, pole = labels.get(source_id, ("", str(row.get("pole") or "")))
        rows.append(
            {
                "source_id": source_id,
                "label": label,
                "pole": str(row.get("pole") or pole),
                "category": str(row.get("category") or ""),
                "disposition": "discovered_not_examined",
            }
        )
    for source_id in sorted(discovered - seen):
        label, pole = labels.get(source_id, ("", ""))
        rows.append(
            {
                "source_id": source_id,
                "label": label,
                "pole": pole,
                "category": "",
                "disposition": "discovered_not_examined",
            }
        )
    return rows


def _public_limit(row: dict) -> dict:
    return {
        "code": str(row.get("code") or ""),
        "source_id": str(row.get("source_id") or ""),
    }


def _contains_forbidden(value: object) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_SIGNAL_KEYS or _contains_forbidden(child):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden(child) for child in value)
    return False


__all__ = [
    "execute_investigation",
    "freeze_investigation_configuration",
    "investigation_admission_enabled",
    "project_public_result",
    "resolve_investigation_ceilings",
    "settle_investigation",
]
