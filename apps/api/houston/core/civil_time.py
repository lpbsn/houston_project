from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
HISTORY_PERIODS = frozenset({"7", "30", "90", "custom", "all"})
HISTORY_DEFAULT_PERIOD = "30"


@dataclass(frozen=True)
class CivilWindow:
    """Half-open Paris civil interval ``[start, end)``."""

    start: datetime
    end: datetime


def paris_day_start(civil: date) -> datetime:
    return datetime.combine(civil, time.min, tzinfo=PARIS)


def parse_civil_date(raw: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError("Date must be YYYY-MM-DD.") from exc


def history_civil_window(
    *,
    period: str,
    now: datetime,
    custom_from: date | None = None,
    custom_to: date | None = None,
) -> CivilWindow | None:
    """Inclusive Paris civil days for 7/30/90, custom ``[from 00:00, to 24:00)``, or unbounded."""
    if period not in HISTORY_PERIODS:
        raise ValueError("period must be 7, 30, 90, custom, or all.")
    if period == "all":
        return None
    if period == "custom":
        if custom_from is None or custom_to is None:
            raise ValueError("custom period requires from and to.")
        if custom_from > custom_to:
            raise ValueError("from must be on or before to.")
        return CivilWindow(
            start=paris_day_start(custom_from),
            end=paris_day_start(custom_to + timedelta(days=1)),
        )

    today = now.astimezone(PARIS).date()
    length = int(period)
    start_day = today - timedelta(days=length - 1)
    return CivilWindow(
        start=paris_day_start(start_day),
        end=paris_day_start(today + timedelta(days=1)),
    )
