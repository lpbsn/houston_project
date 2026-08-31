from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from houston.establishments.konoha_dataset_actors import (
    POLE_COMMUNICATION,
    POLE_MAINTENANCE,
)
from houston.establishments.konoha_dataset_observations import (
    AUTHOR_DIRECTORY,
    DATA_DIR,
    OCCURRED_AT_MAX,
    PARIS_TZ,
)

ACTION_OVERRIDES_SCHEMA_VERSION = "konoha_dataset_action_overrides_v1"
ACTION_OVERRIDES_PATH = DATA_DIR / "konoha_dataset_action_overrides.json"
RESOLUTION_MANUAL = "manual"
RESOLUTION_LINKED_PLAN = "linked_plan"
RESOLUTION_INTERESTING = "interesting"
CYCLE_RESOLUTIONS = frozenset(
    {RESOLUTION_MANUAL, RESOLUTION_LINKED_PLAN, RESOLUTION_INTERESTING}
)
CUTOFF_EXECUTION_STATUSES = frozenset(
    {"scheduled", "in_progress", "pending_validation", "canceled"}
)
ALLOWED_OVERRIDE_KEYS = frozenset(
    {
        "requires_validation",
        "created_at",
        "start_at",
        "end_at",
        "marked_done_at",
        "canceled_at",
        "cutoff_execution_status",
        "creator_email",
        "assignee_email",
        "validator_email",
    }
)
VALIDATION_POLES = frozenset({POLE_MAINTENANCE, POLE_COMMUNICATION})
CLOSED_PLAN_END_AT_MARGINS = (
    timedelta(hours=1),
    timedelta(hours=2),
    timedelta(hours=12),
    timedelta(days=1),
    timedelta(days=2),
)
CLOSED_PLAN_NEAR_MARGIN_INDEXES = frozenset({0, 1})


@dataclass(frozen=True)
class PlanReplaySpec:
    requires_validation: bool
    start_at: datetime | None = None
    end_at: datetime | None = None
    cutoff_execution_status: str | None = None
    creator_email: str | None = None
    assignee_email: str | None = None
    validator_email: str | None = None


def parse_cycle_datetime(value: str) -> datetime:
    from houston.establishments.konoha_dataset_replay import (
        KonohaDatasetReplayError,
        parse_corpus_datetime,
    )

    try:
        return parse_corpus_datetime(value)
    except KonohaDatasetReplayError:
        raise
    except Exception as exc:
        raise KonohaDatasetReplayError([f"invalid cycle datetime: {value}"]) from exc


def _require_at_or_before_cutoff(instant: datetime, *, label: str, group: str) -> None:
    from houston.establishments.konoha_dataset_replay import KonohaDatasetReplayError

    if instant > OCCURRED_AT_MAX:
        raise KonohaDatasetReplayError(
            [f"{group}: {label} {instant.isoformat()} is after cut-off"]
        )


@lru_cache(maxsize=1)
def load_konoha_dataset_action_overrides() -> dict[str, dict[str, Any]]:
    if not ACTION_OVERRIDES_PATH.exists():
        from houston.establishments.konoha_dataset_replay import KonohaDatasetReplayError

        raise KonohaDatasetReplayError(
            [f"missing action overlay {ACTION_OVERRIDES_PATH.name}"]
        )
    with ACTION_OVERRIDES_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        from houston.establishments.konoha_dataset_replay import KonohaDatasetReplayError

        raise KonohaDatasetReplayError(["action overlay root must be an object"])
    return payload


def validate_konoha_dataset_action_overrides(
    observations: list[dict[str, Any]],
    *,
    payload: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    loaded = payload if payload is not None else _load_overrides_payload_for_validation()
    if loaded is None:
        errors.append(f"missing action overlay {ACTION_OVERRIDES_PATH.name}")
        return errors
    if loaded.get("schema_version") != ACTION_OVERRIDES_SCHEMA_VERSION:
        errors.append(
            f"action overlay schema_version must be {ACTION_OVERRIDES_SCHEMA_VERSION}"
        )
    overrides = loaded.get("overrides")
    if not isinstance(overrides, dict):
        errors.append("action overlay overrides must be an object")
        return errors

    groups: dict[str, dict[str, Any]] = {}
    for row in observations:
        groups.setdefault(row["signal_group"], row["cycle"])

    for group, spec in overrides.items():
        if group not in groups:
            errors.append(f"action overlay unknown signal_group {group}")
            continue
        if not isinstance(spec, dict):
            errors.append(f"{group}: overlay must be an object")
            continue
        extra = set(spec) - ALLOWED_OVERRIDE_KEYS
        if extra:
            errors.append(f"{group}: unexpected overlay keys {sorted(extra)}")
        cycle = groups[group]
        resolution = cycle.get("resolution")
        if resolution == RESOLUTION_MANUAL:
            errors.append(f"{group}: manual cycle cannot have a plan overlay")
            continue
        if resolution == RESOLUTION_INTERESTING:
            errors.append(f"{group}: interesting cycle cannot have a plan overlay")
            continue
        if cycle.get("open_at_cutoff") is False:
            if spec.get("cutoff_execution_status") is not None:
                errors.append(
                    f"{group}: closed linked_plan cannot set cutoff_execution_status"
                )
                continue
        status = spec.get("cutoff_execution_status")
        if status is not None and status not in CUTOFF_EXECUTION_STATUSES:
            errors.append(f"{group}: invalid cutoff_execution_status {status!r}")
        if spec.get("requires_validation") is not None and not isinstance(
            spec.get("requires_validation"), bool
        ):
            errors.append(f"{group}: requires_validation must be a boolean")
        if status == "pending_validation" and spec.get("requires_validation") is False:
            errors.append(f"{group}: pending_validation requires requires_validation=true")
        for field in (
            "created_at",
            "start_at",
            "end_at",
            "marked_done_at",
            "canceled_at",
        ):
            value = spec.get(field)
            if value is None:
                continue
            parsed = _try_parse_overlay_datetime(
                value, group=group, field=field, errors=errors
            )
            if parsed is None:
                continue
            if field != "start_at" and field != "end_at" and parsed > OCCURRED_AT_MAX:
                errors.append(f"{group}: overlay {field} is after cut-off")
        for email_field in ("creator_email", "assignee_email", "validator_email"):
            email = spec.get(email_field)
            if email is None:
                continue
            if not isinstance(email, str) or email.lower() not in AUTHOR_DIRECTORY:
                errors.append(f"{group}: {email_field} is not in AUTHOR_DIRECTORY")
        if status == "pending_validation" and spec.get("marked_done_at") is None:
            errors.append(f"{group}: pending_validation overlay must set marked_done_at")
        if status == "canceled" and spec.get("canceled_at") is None:
            errors.append(f"{group}: canceled overlay must set canceled_at")
    return errors


def _load_overrides_payload_for_validation() -> dict[str, Any] | None:
    path = Path(ACTION_OVERRIDES_PATH)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else None


def _try_parse_overlay_datetime(
    value: Any, *, group: str, field: str, errors: list[str]
) -> datetime | None:
    if not isinstance(value, str):
        errors.append(f"{group}: overlay {field} must be an ISO datetime string")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"{group}: overlay {field} is not a valid ISO datetime")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{group}: overlay {field} must be timezone-aware")
        return None
    return parsed.astimezone(PARIS_TZ)


def default_requires_validation(responsible_pole: str) -> bool:
    return responsible_pole in VALIDATION_POLES


def _last_and_first_rows(members: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    from houston.establishments.konoha_dataset_replay import parse_corpus_datetime

    last = max(members, key=lambda item: parse_corpus_datetime(item["occurred_at"]))
    first = min(members, key=lambda item: parse_corpus_datetime(item["occurred_at"]))
    return first, last


def _closed_plan_created_at(
    *, last_obs: datetime, resolved_at: datetime, group: str
) -> datetime:
    from houston.establishments.konoha_dataset_replay import KonohaDatasetReplayError

    candidate = min(last_obs + timedelta(minutes=30), resolved_at - timedelta(minutes=15))
    if candidate < last_obs or candidate > resolved_at:
        created_at = last_obs
    else:
        created_at = candidate
    if created_at > resolved_at:
        raise KonohaDatasetReplayError(
            [f"{group}: derived plan created_at is after resolved_at"]
        )
    _require_at_or_before_cutoff(created_at, label="plan created_at", group=group)
    return created_at


def _midpoint(start: datetime, end: datetime) -> datetime:
    return start + (end - start) / 2


def _override_dt(spec: dict[str, Any], field: str) -> datetime | None:
    value = spec.get(field)
    if value is None:
        return None
    return parse_cycle_datetime(value)


def _overlay_end_at(spec: dict[str, Any], *, default: datetime | None) -> datetime | None:
    if "end_at" not in spec:
        return default
    value = spec.get("end_at")
    if value is None:
        return None
    return parse_cycle_datetime(value)


def closed_plan_end_at_margin_index(signal_group: str) -> int:
    digest = hashlib.sha256(signal_group.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % len(CLOSED_PLAN_END_AT_MARGINS)


def _default_closed_plan_end_at(
    *,
    created_at: datetime,
    resolved_at: datetime,
    signal_group: str,
) -> datetime:
    from houston.establishments.konoha_dataset_replay import KonohaDatasetReplayError

    if resolved_at <= created_at:
        raise KonohaDatasetReplayError(
            [f"{signal_group}: resolved_at must be after plan created_at"]
        )
    end_at = resolved_at + CLOSED_PLAN_END_AT_MARGINS[
        closed_plan_end_at_margin_index(signal_group)
    ]
    if end_at <= created_at or end_at <= resolved_at:
        raise KonohaDatasetReplayError(
            [f"{signal_group}: derived closed end_at must be after created_at and resolved_at"]
        )
    return end_at


def _group_has_rr_approve(signal_group: str) -> bool:
    from houston.establishments.konoha_dataset_workflows import (
        load_konoha_dataset_workflow_overrides,
    )

    payload = load_konoha_dataset_workflow_overrides()
    workflows = payload.get("workflows") if isinstance(payload, dict) else {}
    spec = workflows.get(signal_group) if isinstance(workflows, dict) else None
    if not isinstance(spec, dict):
        return False
    request = spec.get("resolution_request")
    return isinstance(request, dict) and request.get("decision") == "approve"


def _resolve_workflow_for_group(signal_group: str) -> dict[str, Any] | None:
    from houston.establishments.konoha_dataset_workflows import (
        load_konoha_dataset_workflow_overrides,
    )

    payload = load_konoha_dataset_workflow_overrides()
    workflows = payload.get("workflows") if isinstance(payload, dict) else {}
    spec = workflows.get(signal_group) if isinstance(workflows, dict) else None
    return spec if isinstance(spec, dict) else None


def extend_replay_events_with_cycles(
    events: list[Any],
    observations: list[dict[str, Any]],
    *,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> None:
    from houston.establishments.konoha_dataset_replay import (
        EVENT_PLAN_CREATE,
        EVENT_PLAN_MARK_DONE,
        EVENT_PLAN_PROMOTE,
        EVENT_PLAN_VALIDATE,
        EVENT_RESOLVE,
        KonohaDatasetReplayError,
        ReplayEvent,
        parse_corpus_datetime,
    )

    if overrides is None:
        payload = load_konoha_dataset_action_overrides()
        raw_overrides = payload.get("overrides") if isinstance(payload, dict) else {}
        overrides = raw_overrides if isinstance(raw_overrides, dict) else {}

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        groups.setdefault(row["signal_group"], []).append(row)

    for signal_group, members in groups.items():
        cycle = members[0]["cycle"]
        resolution = cycle["resolution"]
        _first, last = _last_and_first_rows(members)
        overlay = overrides.get(signal_group) or {}
        if overlay and signal_group not in {
            row["signal_group"] for row in observations
        }:
            continue
        if resolution == RESOLUTION_INTERESTING:
            if overlay:
                raise KonohaDatasetReplayError(
                    [f"{signal_group}: interesting cycle cannot have a plan overlay"]
                )
            continue
        if resolution == RESOLUTION_MANUAL:
            if overlay:
                raise KonohaDatasetReplayError(
                    [f"{signal_group}: manual cycle cannot have a plan overlay"]
                )
            if cycle.get("open_at_cutoff") is True:
                continue
            if _group_has_rr_approve(signal_group):
                continue
            resolved_at = parse_corpus_datetime(cycle["resolved_at"])
            _require_at_or_before_cutoff(
                resolved_at, label="resolved_at", group=signal_group
            )
            events.append(
                ReplayEvent(
                    kind=EVENT_RESOLVE,
                    at=resolved_at,
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    workflow=_resolve_workflow_for_group(signal_group),
                )
            )
            continue

        responsible = last["candidate"]["responsible_pole_specific_name"]
        requires_validation = overlay.get(
            "requires_validation", default_requires_validation(responsible)
        )
        if not isinstance(requires_validation, bool):
            raise KonohaDatasetReplayError(
                [f"{signal_group}: requires_validation must be a boolean"]
            )
        last_obs = parse_corpus_datetime(last["occurred_at"])
        planned_action_at = (
            parse_corpus_datetime(cycle["planned_action_at"])
            if cycle.get("planned_action_at")
            else None
        )

        if cycle.get("open_at_cutoff") is True:
            _append_open_linked_plan_events(
                events,
                members=members,
                last=last,
                last_obs=last_obs,
                planned_action_at=planned_action_at,
                overlay=overlay,
                requires_validation=requires_validation,
                signal_group=signal_group,
            )
            continue

        resolved_at = parse_corpus_datetime(cycle["resolved_at"])
        _require_at_or_before_cutoff(resolved_at, label="resolved_at", group=signal_group)
        created_at = _override_dt(overlay, "created_at") or _closed_plan_created_at(
            last_obs=last_obs,
            resolved_at=resolved_at,
            group=signal_group,
        )
        if created_at < last_obs:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: plan created_at is before last observation"]
            )
        start_at = _override_dt(overlay, "start_at")
        end_at = _overlay_end_at(
            overlay,
            default=_default_closed_plan_end_at(
                created_at=created_at,
                resolved_at=resolved_at,
                signal_group=signal_group,
            ),
        )
        if start_at is not None and end_at is not None and end_at <= start_at:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: end_at must be after start_at"]
            )
        spec = PlanReplaySpec(
            requires_validation=requires_validation,
            start_at=start_at,
            end_at=end_at,
            creator_email=_optional_email(overlay.get("creator_email")),
            assignee_email=_optional_email(overlay.get("assignee_email")),
            validator_email=_optional_email(overlay.get("validator_email")),
        )
        events.append(
            ReplayEvent(
                kind=EVENT_PLAN_CREATE,
                at=created_at,
                corpus_id=last["id"],
                signal_group=signal_group,
                pattern_group=last["pattern_group"],
                row=last,
                plan=spec,
            )
        )
        if start_at is not None and start_at > created_at:
            _require_at_or_before_cutoff(
                start_at, label="plan_promote", group=signal_group
            )
            events.append(
                ReplayEvent(
                    kind=EVENT_PLAN_PROMOTE,
                    at=start_at,
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    plan=spec,
                )
            )
        if requires_validation:
            marked_done_at = _override_dt(overlay, "marked_done_at") or _midpoint(
                created_at, resolved_at
            )
            if marked_done_at < created_at:
                marked_done_at = created_at
            if marked_done_at > resolved_at:
                marked_done_at = resolved_at
            _require_at_or_before_cutoff(
                marked_done_at, label="plan_mark_done", group=signal_group
            )
            events.append(
                ReplayEvent(
                    kind=EVENT_PLAN_MARK_DONE,
                    at=marked_done_at,
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    plan=spec,
                )
            )
            _require_at_or_before_cutoff(
                resolved_at, label="plan_validate", group=signal_group
            )
            events.append(
                ReplayEvent(
                    kind=EVENT_PLAN_VALIDATE,
                    at=resolved_at,
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    plan=spec,
                )
            )
        else:
            _require_at_or_before_cutoff(
                resolved_at, label="plan_mark_done", group=signal_group
            )
            events.append(
                ReplayEvent(
                    kind=EVENT_PLAN_MARK_DONE,
                    at=resolved_at,
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    plan=spec,
                )
            )


def _optional_email(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).lower()


def _append_open_linked_plan_events(
    events: list[Any],
    *,
    members: list[dict[str, Any]],
    last: dict[str, Any],
    last_obs: datetime,
    planned_action_at: datetime | None,
    overlay: dict[str, Any],
    requires_validation: bool,
    signal_group: str,
) -> None:
    from houston.establishments.konoha_dataset_replay import (
        EVENT_PLAN_CANCEL,
        EVENT_PLAN_CREATE,
        EVENT_PLAN_MARK_DONE,
        EVENT_PLAN_PROMOTE,
        KonohaDatasetReplayError,
        ReplayEvent,
    )

    del members
    cutoff_status = overlay.get("cutoff_execution_status") or "scheduled"
    if cutoff_status not in CUTOFF_EXECUTION_STATUSES:
        raise KonohaDatasetReplayError(
            [f"{signal_group}: invalid cutoff_execution_status {cutoff_status!r}"]
        )
    if planned_action_at is None:
        raise KonohaDatasetReplayError(
            [f"{signal_group}: open linked_plan requires planned_action_at"]
        )
    created_at = _override_dt(overlay, "created_at")
    if created_at is None:
        created_at = min(last_obs + timedelta(minutes=30), OCCURRED_AT_MAX)
        if created_at < last_obs:
            created_at = last_obs
    if created_at < last_obs:
        raise KonohaDatasetReplayError(
            [f"{signal_group}: plan created_at is before last observation"]
        )
    _require_at_or_before_cutoff(created_at, label="plan created_at", group=signal_group)

    start_at = _override_dt(overlay, "start_at")
    end_at = _overlay_end_at(overlay, default=planned_action_at)
    marked_done_at = _override_dt(overlay, "marked_done_at")
    canceled_at = _override_dt(overlay, "canceled_at")

    if cutoff_status == "scheduled":
        if start_at is None:
            start_at = planned_action_at
        if start_at <= created_at:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: scheduled cut-off needs start_at after created_at"]
            )
    elif cutoff_status == "in_progress":
        if start_at is not None and start_at > OCCURRED_AT_MAX:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: in_progress start_at cannot be after cut-off"]
            )
    elif cutoff_status == "pending_validation":
        if not requires_validation:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: pending_validation requires requires_validation"]
            )
        if marked_done_at is None:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: pending_validation overlay must set marked_done_at"]
            )
        _require_at_or_before_cutoff(
            marked_done_at, label="marked_done_at", group=signal_group
        )
        if start_at is not None and start_at > created_at:
            _require_at_or_before_cutoff(start_at, label="start_at", group=signal_group)
        else:
            start_at = None
    elif cutoff_status == "canceled":
        if canceled_at is None:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: canceled overlay must set canceled_at"]
            )
        _require_at_or_before_cutoff(canceled_at, label="canceled_at", group=signal_group)

    spec = PlanReplaySpec(
        requires_validation=requires_validation,
        start_at=start_at,
        end_at=end_at,
        cutoff_execution_status=cutoff_status,
        creator_email=_optional_email(overlay.get("creator_email")),
        assignee_email=_optional_email(overlay.get("assignee_email")),
        validator_email=_optional_email(overlay.get("validator_email")),
    )
    events.append(
        ReplayEvent(
            kind=EVENT_PLAN_CREATE,
            at=created_at,
            corpus_id=last["id"],
            signal_group=signal_group,
            pattern_group=last["pattern_group"],
            row=last,
            plan=spec,
        )
    )
    promote_at = None
    if cutoff_status == "in_progress" and start_at is not None and start_at > created_at:
        promote_at = start_at
    if promote_at is not None:
        _require_at_or_before_cutoff(promote_at, label="plan_promote", group=signal_group)
        events.append(
            ReplayEvent(
                kind=EVENT_PLAN_PROMOTE,
                at=promote_at,
                corpus_id=last["id"],
                signal_group=signal_group,
                pattern_group=last["pattern_group"],
                row=last,
                plan=spec,
            )
        )
    if cutoff_status == "pending_validation" and marked_done_at is not None:
        events.append(
            ReplayEvent(
                kind=EVENT_PLAN_MARK_DONE,
                at=marked_done_at,
                corpus_id=last["id"],
                signal_group=signal_group,
                pattern_group=last["pattern_group"],
                row=last,
                plan=spec,
            )
        )
    if cutoff_status == "canceled" and canceled_at is not None:
        events.append(
            ReplayEvent(
                kind=EVENT_PLAN_CANCEL,
                at=canceled_at,
                corpus_id=last["id"],
                signal_group=signal_group,
                pattern_group=last["pattern_group"],
                row=last,
                plan=spec,
            )
        )
