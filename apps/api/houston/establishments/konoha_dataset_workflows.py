from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from houston.establishments.konoha_dataset_actors import ESTABLISHMENT_ANBU
from houston.establishments.konoha_dataset_observations import (
    AUTHOR_DIRECTORY,
    DATA_DIR,
    OCCURRED_AT_MAX,
    RESOLUTION_INTERESTING,
    RESOLUTION_LINKED_PLAN,
    RESOLUTION_MANUAL,
)

WORKFLOW_OVERRIDES_SCHEMA_VERSION = "konoha_dataset_workflow_overrides_v1"
WORKFLOW_OVERRIDES_PATH = DATA_DIR / "konoha_dataset_workflow_overrides.json"
KAKASHI_EMAIL = "kakashi@konoha.com"
ALLOWED_WORKFLOW_KEYS = frozenset({"interesting", "qualify", "resolution_request"})
RR_DECISIONS = frozenset({"approve", "reject"})


@lru_cache(maxsize=1)
def load_konoha_dataset_workflow_overrides() -> dict[str, Any]:
    if not WORKFLOW_OVERRIDES_PATH.exists():
        from houston.establishments.konoha_dataset_replay import KonohaDatasetReplayError

        raise KonohaDatasetReplayError(
            [f"missing workflow overlay {WORKFLOW_OVERRIDES_PATH.name}"]
        )
    with WORKFLOW_OVERRIDES_PATH.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        from houston.establishments.konoha_dataset_replay import KonohaDatasetReplayError

        raise KonohaDatasetReplayError(["workflow overlay root must be an object"])
    return payload


def validate_konoha_dataset_workflow_overrides(
    observations: list[dict[str, Any]],
    *,
    payload: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    loaded = payload if payload is not None else _load_payload()
    if loaded is None:
        errors.append(f"missing workflow overlay {WORKFLOW_OVERRIDES_PATH.name}")
        return errors
    if loaded.get("schema_version") != WORKFLOW_OVERRIDES_SCHEMA_VERSION:
        errors.append(
            "workflow overlay schema_version must be "
            f"{WORKFLOW_OVERRIDES_SCHEMA_VERSION}"
        )
    workflows = loaded.get("workflows")
    if not isinstance(workflows, dict):
        errors.append("workflow overlay workflows must be an object")
        return errors

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        groups.setdefault(row["signal_group"], []).append(row)

    for group, spec in workflows.items():
        if group not in groups:
            errors.append(f"workflow overlay unknown signal_group {group}")
            continue
        if not isinstance(spec, dict):
            errors.append(f"{group}: workflow must be an object")
            continue
        extra = set(spec) - ALLOWED_WORKFLOW_KEYS
        if extra:
            errors.append(f"{group}: unexpected workflow keys {sorted(extra)}")
        cycle = groups[group][0]["cycle"]
        last = max(groups[group], key=lambda item: item["occurred_at"])
        if spec.get("interesting") is not None:
            _validate_interesting(
                group,
                spec["interesting"],
                cycle=cycle,
                last=last,
                errors=errors,
            )
        if spec.get("qualify") is not None:
            _validate_qualify(group, spec["qualify"], last=last, errors=errors)
        if spec.get("resolution_request") is not None:
            _validate_resolution_request(
                group,
                spec["resolution_request"],
                cycle=cycle,
                last=last,
                errors=errors,
            )
        if spec.get("interesting") and spec.get("resolution_request"):
            errors.append(f"{group}: interesting cannot combine with resolution_request")
        if spec.get("interesting") and cycle.get("resolution") == RESOLUTION_LINKED_PLAN:
            errors.append(f"{group}: interesting overlay on linked_plan cycle")
    return errors


def _load_payload() -> dict[str, Any] | None:
    path = Path(WORKFLOW_OVERRIDES_PATH)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else None


def _validate_email(email: Any, *, group: str, field: str, errors: list[str]) -> None:
    if not isinstance(email, str) or not email.strip():
        errors.append(f"{group}: {field} must be an email")
        return
    lowered = email.lower()
    if lowered == KAKASHI_EMAIL:
        return
    if lowered not in AUTHOR_DIRECTORY:
        errors.append(f"{group}: {field} is not in AUTHOR_DIRECTORY")


def _validate_instant(
    value: Any, *, group: str, field: str, errors: list[str]
) -> Any:
    from houston.establishments.konoha_dataset_action_cycles import (
        _try_parse_overlay_datetime,
    )

    parsed = _try_parse_overlay_datetime(value, group=group, field=field, errors=errors)
    if parsed is None:
        return None
    if parsed > OCCURRED_AT_MAX:
        errors.append(f"{group}: {field} is after cut-off")
    return parsed


def _validate_interesting(
    group: str,
    spec: Any,
    *,
    cycle: dict[str, Any],
    last: dict[str, Any],
    errors: list[str],
) -> None:
    if not isinstance(spec, dict):
        errors.append(f"{group}: interesting must be an object")
        return
    if cycle.get("resolution") != RESOLUTION_INTERESTING:
        errors.append(f"{group}: interesting overlay requires cycle.resolution=interesting")
    _validate_email(
        spec.get("actor_email"),
        group=group,
        field="interesting.actor_email",
        errors=errors,
    )
    marked = _validate_instant(
        spec.get("at"), group=group, field="interesting.at", errors=errors
    )
    cycle_marked = cycle.get("marked_interesting_at")
    if marked is not None and isinstance(cycle_marked, str) and spec.get("at") != cycle_marked:
        errors.append(f"{group}: interesting.at must match cycle.marked_interesting_at")
    last_obs = last.get("occurred_at")
    if marked is not None and isinstance(last_obs, str) and spec.get("at") <= last_obs:
        errors.append(f"{group}: interesting.at must be after last submit")


def _validate_qualify(
    group: str,
    spec: Any,
    *,
    last: dict[str, Any],
    errors: list[str],
) -> None:
    if not isinstance(spec, dict):
        errors.append(f"{group}: qualify must be an object")
        return
    _validate_email(
        spec.get("actor_email"),
        group=group,
        field="qualify.actor_email",
        errors=errors,
    )
    at = _validate_instant(spec.get("at"), group=group, field="qualify.at", errors=errors)
    last_obs = last.get("occurred_at")
    if at is not None and isinstance(last_obs, str) and spec.get("at") <= last_obs:
        errors.append(f"{group}: qualify.at must be after last submit")
    initial = spec.get("initial_candidate")
    if not isinstance(initial, dict):
        errors.append(f"{group}: qualify.initial_candidate must be an object")
        return
    for field in (
        "title",
        "structured_summary",
        "issue_focus",
        "canonical_object",
        "signal_kind",
        "expected_action",
        "affected_pole_specific_name",
        "responsible_pole_specific_name",
        "location_text",
    ):
        if field not in initial:
            errors.append(f"{group}: qualify.initial_candidate missing {field}")


def _validate_resolution_request(
    group: str,
    spec: Any,
    *,
    cycle: dict[str, Any],
    last: dict[str, Any],
    errors: list[str],
) -> None:
    if not isinstance(spec, dict):
        errors.append(f"{group}: resolution_request must be an object")
        return
    if cycle.get("resolution") != RESOLUTION_MANUAL:
        errors.append(f"{group}: resolution_request requires a manual cycle")
    if cycle.get("open_at_cutoff") is True:
        errors.append(f"{group}: resolution_request cannot stay open at cut-off")
    decision = spec.get("decision")
    if decision not in RR_DECISIONS:
        errors.append(f"{group}: resolution_request.decision must be approve or reject")
    _validate_email(
        spec.get("requester_email"),
        group=group,
        field="resolution_request.requester_email",
        errors=errors,
    )
    _validate_email(
        spec.get("reviewer_email"),
        group=group,
        field="resolution_request.reviewer_email",
        errors=errors,
    )
    requested = _validate_instant(
        spec.get("requested_at"),
        group=group,
        field="resolution_request.requested_at",
        errors=errors,
    )
    reviewed = _validate_instant(
        spec.get("reviewed_at"),
        group=group,
        field="resolution_request.reviewed_at",
        errors=errors,
    )
    last_obs = last.get("occurred_at")
    if requested is not None and isinstance(last_obs, str) and spec.get("requested_at") <= last_obs:
        errors.append(f"{group}: requested_at must be after last submit")
    if requested is not None and reviewed is not None and requested >= reviewed:
        errors.append(f"{group}: requested_at must be before reviewed_at")
    if decision == "approve" and spec.get("reviewed_at") != cycle.get("resolved_at"):
        errors.append(f"{group}: rr approve reviewed_at must match cycle.resolved_at")
    if decision == "reject":
        _validate_email(
            spec.get("resolve_actor_email"),
            group=group,
            field="resolution_request.resolve_actor_email",
            errors=errors,
        )
        if spec.get("reviewed_at") == cycle.get("resolved_at"):
            errors.append(f"{group}: rr reject reviewed_at cannot equal resolved_at")


def extend_replay_events_with_workflows(
    events: list[Any],
    observations: list[dict[str, Any]],
    *,
    workflows: dict[str, dict[str, Any]] | None = None,
) -> None:
    from houston.establishments.konoha_dataset_replay import (
        EVENT_MARK_INTERESTING,
        EVENT_QUALIFY,
        EVENT_RR_APPROVE,
        EVENT_RR_CREATE,
        EVENT_RR_REJECT,
        ReplayEvent,
        parse_corpus_datetime,
    )

    if workflows is None:
        payload = load_konoha_dataset_workflow_overrides()
        raw = payload.get("workflows") if isinstance(payload, dict) else {}
        workflows = raw if isinstance(raw, dict) else {}

    groups: dict[str, list[dict[str, Any]]] = {}
    for row in observations:
        groups.setdefault(row["signal_group"], []).append(row)

    for signal_group, spec in workflows.items():
        if signal_group not in groups or not isinstance(spec, dict):
            continue
        last = max(
            groups[signal_group],
            key=lambda item: parse_corpus_datetime(item["occurred_at"]),
        )
        if spec.get("qualify"):
            qualify = spec["qualify"]
            events.append(
                ReplayEvent(
                    kind=EVENT_QUALIFY,
                    at=parse_corpus_datetime(qualify["at"]),
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    workflow=spec,
                )
            )
        if spec.get("resolution_request"):
            request = spec["resolution_request"]
            events.append(
                ReplayEvent(
                    kind=EVENT_RR_CREATE,
                    at=parse_corpus_datetime(request["requested_at"]),
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    workflow=spec,
                )
            )
            decision = request.get("decision")
            kind = EVENT_RR_APPROVE if decision == "approve" else EVENT_RR_REJECT
            events.append(
                ReplayEvent(
                    kind=kind,
                    at=parse_corpus_datetime(request["reviewed_at"]),
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    workflow=spec,
                )
            )
        if spec.get("interesting"):
            interesting = spec["interesting"]
            events.append(
                ReplayEvent(
                    kind=EVENT_MARK_INTERESTING,
                    at=parse_corpus_datetime(interesting["at"]),
                    corpus_id=last["id"],
                    signal_group=signal_group,
                    pattern_group=last["pattern_group"],
                    row=last,
                    workflow=spec,
                )
            )
        _assert_workflow_order(events, signal_group=signal_group)


def _assert_workflow_order(events: list[Any], *, signal_group: str) -> None:
    from houston.establishments.konoha_dataset_replay import (
        EVENT_MARK_INTERESTING,
        EVENT_PLAN_CREATE,
        EVENT_QUALIFY,
        EVENT_RESOLVE,
        EVENT_RR_APPROVE,
        EVENT_RR_CREATE,
        EVENT_RR_REJECT,
        KonohaDatasetReplayError,
    )

    group_events = [event for event in events if event.signal_group == signal_group]
    qualify = next((event for event in group_events if event.kind == EVENT_QUALIFY), None)
    if qualify is None:
        return
    blockers = (
        EVENT_PLAN_CREATE,
        EVENT_MARK_INTERESTING,
        EVENT_RR_CREATE,
        EVENT_RR_APPROVE,
        EVENT_RR_REJECT,
        EVENT_RESOLVE,
    )
    for event in group_events:
        if event.kind in blockers and event.at < qualify.at:
            raise KonohaDatasetReplayError(
                [f"{signal_group}: {event.kind} is before qualify"]
            )


def workflow_initial_candidate(signal_group: str) -> dict[str, Any] | None:
    payload = load_konoha_dataset_workflow_overrides()
    workflows = payload.get("workflows") if isinstance(payload, dict) else {}
    spec = workflows.get(signal_group) if isinstance(workflows, dict) else None
    if not isinstance(spec, dict):
        return None
    qualify = spec.get("qualify")
    if not isinstance(qualify, dict):
        return None
    initial = qualify.get("initial_candidate")
    return initial if isinstance(initial, dict) else None


def kakashi_required_for_workflows(
    workflows: dict[str, dict[str, Any]] | None = None,
    *,
    signal_groups: set[str] | None = None,
) -> bool:
    if workflows is None:
        payload = load_konoha_dataset_workflow_overrides()
        raw = payload.get("workflows") if isinstance(payload, dict) else {}
        workflows = raw if isinstance(raw, dict) else {}
    for group, spec in workflows.items():
        if signal_groups is not None and group not in signal_groups:
            continue
        if not isinstance(spec, dict):
            continue
        request = spec.get("resolution_request")
        if not isinstance(request, dict):
            continue
        if str(request.get("reviewer_email", "")).lower() == KAKASHI_EMAIL:
            return True
    return False


def assert_kakashi_director(runtime: Any) -> list[str]:
    from houston.establishments.models import EstablishmentMembership

    membership = runtime.memberships.get((ESTABLISHMENT_ANBU, KAKASHI_EMAIL))
    if membership is None:
        return [
            f"{KAKASHI_EMAIL}: missing active ANBU membership with role DIRECTOR"
        ]
    if membership.role != EstablishmentMembership.Role.DIRECTOR:
        return [
            f"{KAKASHI_EMAIL}: ANBU membership must be DIRECTOR, got {membership.role}"
        ]
    if membership.status != EstablishmentMembership.Status.ACTIVE:
        return [f"{KAKASHI_EMAIL}: ANBU membership is not active"]
    return []
