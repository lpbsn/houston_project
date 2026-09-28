from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from houston.core.civil_time import (
    HISTORY_DEFAULT_PERIOD,
    HISTORY_PERIODS,
    CivilWindow,
    history_civil_window,
    parse_civil_date,
)

HISTORY_DEFAULT_PAGE_SIZE = 25
HISTORY_MAX_PAGE_SIZE = 50


@dataclass(frozen=True)
class HistoryQuery:
    view_mode: str
    status: str
    period: str
    period_from: str | None
    period_to: str | None
    window: CivilWindow | None
    page_size: int
    custom_from: date | None
    custom_to: date | None


def _page_size(raw: str | None) -> int:
    if raw in (None, ""):
        return HISTORY_DEFAULT_PAGE_SIZE
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return HISTORY_DEFAULT_PAGE_SIZE
    return min(max(value, 1), HISTORY_MAX_PAGE_SIZE)


def parse_history_query(query_params, *, statuses: frozenset[str], now) -> HistoryQuery:
    view_mode = str(query_params.get("view_mode", "")).strip().lower()
    if view_mode not in {"personal", "general"}:
        raise ValueError("view_mode must be personal or general.")

    status = str(query_params.get("status", "all")).strip().lower() or "all"
    if status != "all" and status not in statuses:
        allowed = ", ".join(sorted(statuses))
        raise ValueError(f"status must be all, {allowed}.")

    raw_period = query_params.get("period", HISTORY_DEFAULT_PERIOD)
    period = str(raw_period).strip().lower() or HISTORY_DEFAULT_PERIOD
    if period not in HISTORY_PERIODS:
        raise ValueError("period must be 7, 30, 90, custom, or all.")

    custom_from = None
    custom_to = None
    period_from = None
    period_to = None
    if period == "custom":
        raw_from = str(query_params.get("from", "")).strip()
        raw_to = str(query_params.get("to", "")).strip()
        if not raw_from or not raw_to:
            raise ValueError("custom period requires from and to.")
        try:
            custom_from = parse_civil_date(raw_from)
            custom_to = parse_civil_date(raw_to)
        except ValueError as exc:
            raise ValueError("from and to must be YYYY-MM-DD.") from exc
        period_from = custom_from.isoformat()
        period_to = custom_to.isoformat()

    window = history_civil_window(
        period=period,
        now=now,
        custom_from=custom_from,
        custom_to=custom_to,
    )
    return HistoryQuery(
        view_mode=view_mode,
        status=status,
        period=period,
        period_from=period_from,
        period_to=period_to,
        window=window,
        page_size=_page_size(query_params.get("page_size")),
        custom_from=custom_from,
        custom_to=custom_to,
    )
