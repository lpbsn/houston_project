from __future__ import annotations

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.utils.dateparse import parse_datetime

from houston.establishments.membership_scope import membership_business_unit_scope_ids
from houston.signals.models import Signal

FEED_CURSOR_VERSION = "v1"
FEED_CURSOR_COLLECTION_LIST = "L"
FEED_CURSOR_COLLECTION_PINS = "P"
SIGNAL_FEED_STATUS_ALL = "all"
SIGNAL_FEED_SCOPES = frozenset({"establishment", "cross"})
SIGNAL_FEED_STATUS_SELECTIONS = frozenset(
    {
        SIGNAL_FEED_STATUS_ALL,
        Signal.Status.OPEN,
        Signal.Status.IN_PROGRESS,
        Signal.Status.INTERESTING,
    }
)

OPERATIONAL_STATUS_RANK = {
    Signal.Status.OPEN: 0,
    Signal.Status.IN_PROGRESS: 1,
    Signal.Status.INTERESTING: 2,
}


class SignalFeedCursorError(Exception):
    def __init__(self, detail: str = "Invalid cursor.", *, code: str = "validation_error") -> None:
        self.detail = detail
        self.code = code
        super().__init__(detail)


@dataclass(frozen=True)
class SignalFeedCursor:
    collection: str
    scope: str
    view_mode: str
    status: str
    filter_hash: str
    auth_context_hash: str
    status_rank: int
    last_activity_at: datetime
    created_at: datetime
    signal_id: uuid.UUID


@dataclass(frozen=True)
class SignalFeedPinCursor:
    collection: str
    scope: str
    view_mode: str
    status: str
    filter_hash: str
    auth_context_hash: str
    pinned_at: datetime
    signal_id: uuid.UUID


def operational_status_rank_case() -> Case:
    return Case(
        When(status=Signal.Status.OPEN, then=Value(0)),
        When(status=Signal.Status.IN_PROGRESS, then=Value(1)),
        When(status=Signal.Status.INTERESTING, then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )


def status_rank_for_signal(signal: Signal) -> int:
    return OPERATIONAL_STATUS_RANK.get(signal.status, 3)


def signal_feed_filter_hash(
    *,
    business_unit_ids: tuple[uuid.UUID, ...],
    activity_subject_ids: tuple[uuid.UUID, ...],
    needs_qualification: bool,
) -> str:
    raw = json.dumps(
        {
            "activity_subject_ids": [str(value) for value in activity_subject_ids],
            "business_unit_ids": [str(value) for value in business_unit_ids],
            "needs_qualification": needs_qualification,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def signal_feed_auth_context_hash(
    *,
    memberships,
    view_mode: str,
    scope: str,
) -> str:
    rows = []
    for membership in sorted(memberships, key=lambda item: str(item.id)):
        scope_ids = sorted(
            str(scope_id) for scope_id in membership_business_unit_scope_ids(membership)
        )
        rows.append(
            {
                "membership_id": str(membership.id),
                "establishment_id": str(membership.establishment_id),
                "role": membership.role,
                "status": membership.status,
                "scope_business_unit_ids": scope_ids,
            }
        )
    raw = json.dumps(
        {
            "memberships": rows,
            "scope": scope,
            "view_mode": view_mode,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _encode_cursor_payload(payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def _decode_cursor_payload(raw: str) -> dict:
    padding = "=" * (-len(raw) % 4)
    try:
        decoded = base64.urlsafe_b64decode(f"{raw}{padding}").decode()
        payload = json.loads(decoded)
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SignalFeedCursorError() from exc
    if not isinstance(payload, dict) or payload.get("v") != FEED_CURSOR_VERSION:
        raise SignalFeedCursorError()
    return payload


def encode_signal_feed_cursor(
    signal: Signal,
    *,
    scope: str,
    view_mode: str,
    status: str,
    filter_hash: str,
    auth_context_hash: str,
) -> str:
    return _encode_cursor_payload(
        {
            "v": FEED_CURSOR_VERSION,
            "collection": FEED_CURSOR_COLLECTION_LIST,
            "scope": scope,
            "view_mode": view_mode,
            "status": status,
            "filter_hash": filter_hash,
            "auth_context_hash": auth_context_hash,
            "status_rank": status_rank_for_signal(signal),
            "last_activity_at": signal.last_activity_at.isoformat(),
            "created_at": signal.created_at.isoformat(),
            "signal_id": str(signal.id),
        }
    )


def encode_signal_feed_pin_cursor(
    signal: Signal,
    *,
    scope: str,
    view_mode: str,
    status: str,
    filter_hash: str,
    auth_context_hash: str,
) -> str:
    if signal.pinned_at is None:
        raise SignalFeedCursorError("Pinned signal cursor requires pinned_at.")
    return _encode_cursor_payload(
        {
            "v": FEED_CURSOR_VERSION,
            "collection": FEED_CURSOR_COLLECTION_PINS,
            "scope": scope,
            "view_mode": view_mode,
            "status": status,
            "filter_hash": filter_hash,
            "auth_context_hash": auth_context_hash,
            "pinned_at": signal.pinned_at.isoformat(),
            "signal_id": str(signal.id),
        }
    )


def _shared_cursor_fields(payload: dict) -> tuple[str, str, str, str, str, str]:
    try:
        collection = str(payload["collection"])
        scope = str(payload["scope"])
        view_mode = str(payload["view_mode"])
        status = str(payload["status"])
        filter_hash = str(payload["filter_hash"])
        auth_context_hash = str(payload["auth_context_hash"])
    except (KeyError, TypeError) as exc:
        raise SignalFeedCursorError() from exc
    if (
        scope not in SIGNAL_FEED_SCOPES
        or view_mode not in {"personal", "general"}
        or status not in SIGNAL_FEED_STATUS_SELECTIONS
    ):
        raise SignalFeedCursorError()
    return collection, scope, view_mode, status, filter_hash, auth_context_hash


def parse_signal_feed_cursor(raw: str | None) -> SignalFeedCursor | None:
    if not raw:
        return None
    payload = _decode_cursor_payload(raw.strip())
    collection, scope, view_mode, status, filter_hash, auth_context_hash = _shared_cursor_fields(
        payload
    )
    if collection != FEED_CURSOR_COLLECTION_LIST:
        raise SignalFeedCursorError()
    try:
        status_rank = int(payload["status_rank"])
        last_activity_at = parse_datetime(payload["last_activity_at"])
        created_at = parse_datetime(payload["created_at"])
        signal_id = uuid.UUID(payload["signal_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SignalFeedCursorError() from exc
    if last_activity_at is None or created_at is None:
        raise SignalFeedCursorError()
    return SignalFeedCursor(
        collection=collection,
        scope=scope,
        view_mode=view_mode,
        status=status,
        filter_hash=filter_hash,
        auth_context_hash=auth_context_hash,
        status_rank=status_rank,
        last_activity_at=last_activity_at,
        created_at=created_at,
        signal_id=signal_id,
    )


def parse_signal_feed_pin_cursor(raw: str | None) -> SignalFeedPinCursor | None:
    if not raw:
        return None
    payload = _decode_cursor_payload(raw.strip())
    collection, scope, view_mode, status, filter_hash, auth_context_hash = _shared_cursor_fields(
        payload
    )
    if collection != FEED_CURSOR_COLLECTION_PINS:
        raise SignalFeedCursorError()
    try:
        pinned_at = parse_datetime(payload["pinned_at"])
        signal_id = uuid.UUID(payload["signal_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SignalFeedCursorError() from exc
    if pinned_at is None:
        raise SignalFeedCursorError()
    return SignalFeedPinCursor(
        collection=collection,
        scope=scope,
        view_mode=view_mode,
        status=status,
        filter_hash=filter_hash,
        auth_context_hash=auth_context_hash,
        pinned_at=pinned_at,
        signal_id=signal_id,
    )


def validate_signal_feed_cursor_context(
    cursor: SignalFeedCursor | SignalFeedPinCursor,
    *,
    scope: str,
    view_mode: str,
    status: str,
    filter_hash: str,
    auth_context_hash: str,
) -> None:
    if (
        cursor.scope != scope
        or cursor.view_mode != view_mode
        or cursor.status != status
        or cursor.filter_hash != filter_hash
        or cursor.auth_context_hash != auth_context_hash
    ):
        raise SignalFeedCursorError(
            "cursor_context_mismatch",
            code="cursor_context_mismatch",
        )


def apply_signal_feed_cursor(
    queryset: QuerySet[Signal],
    cursor: SignalFeedCursor,
) -> QuerySet[Signal]:
    if "status_rank" not in queryset.query.annotations:
        queryset = queryset.annotate(status_rank=operational_status_rank_case())
    q = Q(status_rank__gt=cursor.status_rank)
    same_rank = Q(status_rank=cursor.status_rank)
    q |= same_rank & Q(last_activity_at__lt=cursor.last_activity_at)
    same_activity = same_rank & Q(last_activity_at=cursor.last_activity_at)
    q |= same_activity & Q(created_at__lt=cursor.created_at)
    q |= same_activity & Q(created_at=cursor.created_at) & Q(id__lt=cursor.signal_id)
    return queryset.filter(q)


def apply_signal_feed_pin_cursor(
    queryset: QuerySet[Signal],
    cursor: SignalFeedPinCursor,
) -> QuerySet[Signal]:
    return queryset.filter(
        Q(pinned_at__lt=cursor.pinned_at)
        | Q(pinned_at=cursor.pinned_at, id__lt=cursor.signal_id)
    )
