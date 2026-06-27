from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final, Literal

OperationalInvalidationDispatch = Literal["by_subject_type", "by_reason"]

_CONTRACT_PATH = (
    Path(__file__).resolve().parents[4] / "contracts" / "operational-realtime-invalidation.json"
)
_VALID_DISPATCH: frozenset[str] = frozenset({"by_subject_type", "by_reason"})


@dataclass(frozen=True, slots=True)
class OperationalInvalidationEvent:
    subject_type: str
    reason: str
    dispatch: OperationalInvalidationDispatch


def contract_path() -> Path:
    return _CONTRACT_PATH


@lru_cache(maxsize=1)
def load_operational_invalidation_contract() -> dict:
    payload = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    if payload.get("version") != 1:
        msg = f"Unsupported operational invalidation contract version: {payload.get('version')!r}"
        raise ValueError(msg)
    events = payload.get("events")
    if not isinstance(events, list) or not events:
        msg = "Operational invalidation contract must define a non-empty events list"
        raise ValueError(msg)
    return payload


@lru_cache(maxsize=1)
def operational_invalidation_events() -> tuple[OperationalInvalidationEvent, ...]:
    events: list[OperationalInvalidationEvent] = []
    seen: set[tuple[str, str]] = set()
    for raw in load_operational_invalidation_contract()["events"]:
        subject_type = raw["subject_type"]
        reason = raw["reason"]
        dispatch = raw["dispatch"]
        if dispatch not in _VALID_DISPATCH:
            msg = f"Invalid dispatch {dispatch!r} for {subject_type}/{reason}"
            raise ValueError(msg)
        pair = (subject_type, reason)
        if pair in seen:
            msg = f"Duplicate operational invalidation event: {pair}"
            raise ValueError(msg)
        seen.add(pair)
        events.append(
            OperationalInvalidationEvent(
                subject_type=subject_type,
                reason=reason,
                dispatch=dispatch,
            )
        )
    return tuple(events)


def event_pairs() -> frozenset[tuple[str, str]]:
    return frozenset(
        (event.subject_type, event.reason) for event in operational_invalidation_events()
    )


OPERATIONAL_INVALIDATION_EVENTS: Final = event_pairs()

REASON_GATED_SUBJECT_TYPES: Final = frozenset(
    event.subject_type
    for event in operational_invalidation_events()
    if event.dispatch == "by_reason"
)

NOTIFICATION_INVALIDATION_SUBJECT_TYPE: Final = "notification"
NOTIFICATION_CREATED_REASON: Final = "notification.created"
NOTIFICATION_UPDATED_REASON: Final = "notification.updated"
NOTIFICATION_BULK_UPDATED_REASON: Final = "notification.bulk_updated"


def notification_reasons() -> frozenset[str]:
    return frozenset(
        event.reason
        for event in operational_invalidation_events()
        if event.subject_type == NOTIFICATION_INVALIDATION_SUBJECT_TYPE
    )
