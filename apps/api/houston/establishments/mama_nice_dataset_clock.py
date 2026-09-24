from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta
from unittest.mock import patch

from django.utils import timezone

from houston.establishments.mama_nice_dataset_constants import (
    OBJECT_TYPE_CLOCK,
    OVERDUE_MAX_DAYS,
    OVERDUE_MIN_DAYS,
    PARIS_TZ,
    SNAPSHOT,
)
from houston.establishments.mama_nice_dataset_exceptions import MamaNiceDatasetError

REFERENCE_SEED_KEY = "clock:reference_at"
IN_PROGRESS_LEAD = timedelta(hours=6)
IN_PROGRESS_HORIZON = timedelta(days=7)
PENDING_ON_TIME_HORIZON = timedelta(days=3)

_reference_at: ContextVar[datetime | None] = ContextVar("mama_nice_reference_at", default=None)


def freeze_django_now(at: datetime):
    if at.tzinfo is None:
        raise MamaNiceDatasetError(["clock instant must be timezone-aware"])
    instant = at.astimezone(PARIS_TZ)

    def _now() -> datetime:
        return instant

    return patch("django.utils.timezone.now", _now)


def assert_not_after_snapshot(at: datetime, *, allow_future: bool = False) -> None:
    if allow_future:
        return
    if at.astimezone(PARIS_TZ) > SNAPSHOT:
        raise MamaNiceDatasetError(
            [f"refusing historical clock after snapshot: {at.isoformat()}"]
        )


def establishment_timezone(establishment) -> datetime.tzinfo:
    name = getattr(establishment, "timezone", None) or "Europe/Paris"
    from zoneinfo import ZoneInfo

    return ZoneInfo(name)


def assert_reference_compatible(reference_at: datetime) -> None:
    instant = reference_at.astimezone(PARIS_TZ)
    if instant < SNAPSHOT:
        raise MamaNiceDatasetError(
            ["reference_at is before the authored snapshot; refusing to move historical data"]
        )
    limit = datetime(2026, 9, 24, 9, 0, tzinfo=PARIS_TZ)
    if instant >= limit:
        raise MamaNiceDatasetError(
            [
                "reference_at is outside the frozen public-event window; "
                f"refusing to move public events (limit {limit.isoformat()})"
            ]
        )


def parse_as_of(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise MamaNiceDatasetError(["--as-of must be timezone-aware"])
        return value.astimezone(PARIS_TZ)
    text = value.strip()
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PARIS_TZ)
    return parsed.astimezone(PARIS_TZ)


def operational_now() -> datetime:
    current = _reference_at.get()
    return current if current is not None else SNAPSHOT


@contextmanager
def use_reference_at(reference_at: datetime):
    if reference_at.tzinfo is None:
        raise MamaNiceDatasetError(["reference_at must be timezone-aware"])
    token = _reference_at.set(reference_at.astimezone(PARIS_TZ))
    try:
        yield reference_at.astimezone(PARIS_TZ)
    finally:
        _reference_at.reset(token)


def shift_sliding_instant(
    authored_at: datetime, *, reference_at: datetime | None = None
) -> datetime:
    ref = reference_at or operational_now()
    return authored_at + (ref - SNAPSHOT)


def in_progress_window(*, reference_at: datetime | None = None) -> tuple[datetime, datetime]:
    ref = reference_at or operational_now()
    start = ref - IN_PROGRESS_LEAD
    end = ref + IN_PROGRESS_HORIZON
    if end == ref:
        raise MamaNiceDatasetError(["in_progress end_at must not equal reference_at"])
    return start, end


def pending_on_time_window(*, reference_at: datetime | None = None) -> tuple[datetime, datetime]:
    ref = reference_at or operational_now()
    start = ref - timedelta(hours=4)
    end = ref + PENDING_ON_TIME_HORIZON
    if end == ref:
        raise MamaNiceDatasetError(["pending validation end_at must not equal reference_at"])
    return start, end


def overdue_end_at(*, days_late: int, reference_at: datetime | None = None) -> datetime:
    ref = reference_at or operational_now()
    end = ref - timedelta(days=days_late)
    if end == ref:
        raise MamaNiceDatasetError(["overdue end_at must not equal reference_at"])
    return end


def load_persisted_reference_at(establishment) -> datetime | None:
    from houston.establishments.models import MamaNiceSeedRecord

    record = MamaNiceSeedRecord.objects.filter(
        establishment=establishment,
        object_type=OBJECT_TYPE_CLOCK,
        seed_key=REFERENCE_SEED_KEY,
    ).first()
    if record is None:
        return None
    return record.event_at.astimezone(establishment_timezone(establishment))


def resolve_seed_reference_at(
    *,
    establishment,
    resume: bool,
    as_of: str | datetime | None = None,
    persist: bool = True,
) -> datetime:
    from houston.establishments.mama_nice_dataset_ledger import apply_seed_event

    tz = establishment_timezone(establishment)
    requested = parse_as_of(as_of)
    stored = load_persisted_reference_at(establishment)
    if stored is not None:
        if requested is not None and requested != stored:
            raise MamaNiceDatasetError(
                ["--resume must reuse the persisted reference_at; --as-of does not match"]
            )
        return stored
    if resume:
        raise MamaNiceDatasetError(["cannot --resume without a persisted reference_at"])
    candidate = (requested or timezone.now()).astimezone(tz)
    assert_reference_compatible(candidate)
    if persist:
        apply_seed_event(
            establishment=establishment,
            object_type=OBJECT_TYPE_CLOCK,
            seed_key=REFERENCE_SEED_KEY,
            event_kind="clock_reference",
            event_at=candidate,
            fingerprint_payload={"reference_at": candidate.isoformat()},
            resume=False,
            writer=lambda: establishment.id,
            target_exists=lambda object_id: object_id == establishment.id,
        )
    return candidate


def non_terminal_runtime_errors(*, executions, reference_at: datetime) -> list[str]:
    from houston.action_plans.constants import (
        ACTIVE_EXECUTION_STATUSES,
        EXECUTION_STATUS_IN_PROGRESS,
        EXECUTION_STATUS_PENDING_VALIDATION,
        EXECUTION_STATUS_SCHEDULED,
    )
    from houston.action_plans.selectors import action_plan_execution_overdue

    errors: list[str] = []
    active = [item for item in executions if item.status in ACTIVE_EXECUTION_STATUSES]
    overdue = [
        item
        for item in active
        if action_plan_execution_overdue(execution=item, now=reference_at)
    ]
    if len(overdue) != 6:
        errors.append(f"overdue executions {len(overdue)} != 6")
    if any(item.status != EXECUTION_STATUS_PENDING_VALIDATION for item in overdue):
        errors.append("overdue executions must be pending_validation")
    lates = sorted((reference_at - item.end_at).days for item in overdue)
    if lates and set(lates) != set(range(OVERDUE_MIN_DAYS, OVERDUE_MAX_DAYS + 1)):
        errors.append(f"overdue days {lates} must be 2 through 7")
    overdue_ids = {item.id for item in overdue}
    for item in active:
        if item.end_at is None:
            errors.append(f"{item.id}: non-terminal execution missing end_at")
            continue
        if item.end_at == reference_at:
            errors.append(f"{item.title}: end_at must not equal reference_at")
        if item.id in overdue_ids:
            continue
        if action_plan_execution_overdue(execution=item, now=reference_at):
            errors.append(f"{item.title}: extra overdue at reference_at")
        if item.status == EXECUTION_STATUS_IN_PROGRESS:
            if not (item.start_at <= reference_at < item.end_at):
                errors.append(
                    f"{item.title}: in_progress must satisfy start_at <= reference_at < end_at"
                )
        elif item.status == EXECUTION_STATUS_PENDING_VALIDATION:
            if item.end_at <= reference_at:
                errors.append(f"{item.title}: on-time validation must have a future deadline")
        elif item.status == EXECUTION_STATUS_SCHEDULED:
            if item.start_at <= reference_at:
                errors.append(f"{item.title}: scheduled execution must start after reference_at")
    return errors
